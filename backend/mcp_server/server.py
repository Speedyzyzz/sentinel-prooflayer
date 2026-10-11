"""Sentinel & ProofLayer Model Context Protocol (MCP) Server.

Exposes 12 governance tools conforming to the official Model Context Protocol (MCP) standard:
1. compile_policy: Compile natural language prompt into structured JSON AST & CEL.
2. simulate_policy: Run what-if simulations of proposed rules against historical transactions.
3. propose_payment_intent: Propose payment intent on behalf of an agent for policy check.
4. evaluate_risk: Compute deterministic PO match score M and 5-factor risk score R.
5. review_approval_queue: Fetch pending human review intents.
6. submit_approval_decision: Approve or reject intent with approver credentials and notes.
7. execute_payment: Execute approved intent via PayPal Orders v2 with idempotency lock.
8. trigger_kill_switch: Trigger 3-tier emergency kill switch (INTENT, AGENT, MANDATE).
9. query_evidence_graph: Query 18 node types and 13 edge types for an intent or dispute.
10. compute_evidence_readiness: Calculate 6-dimension readiness score for dispute defense.
11. compile_defense_brief: Generate grounded auto-defense brief with bracketed [ev_*] citations.
12. submit_dispute_evidence: Submit compiled evidence brief to PayPal Disputes API.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database import (
    ApprovalRecord,
    DisputeRecord,
    Mandate,
    PaymentIntent,
    PurchaseOrder,
    SessionLocal,
    TransactionRecord,
    User,
    Vendor,
    init_db,
)
from app.routers.approvals import approve_intent, reject_intent
from app.routers.disputes import submit_dispute_defense
from app.routers.evidence import get_evidence_graph
from app.routers.intents import propose_intent
from app.routers.payments import execute_payment
from app.routers.scenarios import seed_demo_data
from app.schemas import (
    ApprovalActionRequest,
    DisputeSubmitDefenseRequest,
    PaymentExecuteRequest,
    PaymentIntentCreate,
)
from app.services.evidence_compiler import EvidenceCompilerService
from app.services.evidence_graph import CausalGraph
from app.services.policy_compiler import PolicyCompiler
from app.services.risk_engine import RiskEngine
from app.services.state_machine import StateMachine

# Tool Definitions compliant with MCP JSON schema
TOOLS_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "compile_policy",
        "description": "Compile natural language procurement governance prompt into structured JSON AST and CEL rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Natural language procurement governance rule prompt",
                },
                "context": {
                    "type": "object",
                    "description": "Optional organizational context or existing mandate metadata",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "simulate_policy",
        "description": "Execute historical What-If simulation measuring friction, human review hours, and blocked spend against transaction benchmarks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandate_rules": {
                    "type": "object",
                    "description": "Compiled or draft mandate rules dictionary",
                },
                "sample_size": {
                    "type": "integer",
                    "default": 100,
                    "description": "Number of synthetic/historical transactions to evaluate",
                },
            },
            "required": ["mandate_rules"],
        },
    },
    {
        "name": "propose_payment_intent",
        "description": "Propose a new agent payment intent and run automated Sentinel policy and risk checks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandate_id": {"type": "string", "description": "Mandate identifier, e.g. mdt_9f21ac"},
                "agent_id": {"type": "string", "description": "Agent identifier, e.g. agent_atlas_procurement"},
                "vendor_id": {"type": "string", "description": "Vendor identifier, e.g. vendor_cloud_compute"},
                "amount": {"type": "number", "description": "Transaction amount in USD"},
                "currency": {"type": "string", "default": "USD"},
                "category": {"type": "string", "description": "Procurement category, e.g. cloud_compute"},
                "invoice_ref": {"type": "string", "description": "Vendor invoice number or reference"},
                "po_ref": {"type": "string", "description": "Optional baseline Purchase Order ID"},
                "line_items": {"type": "array", "description": "Optional line items list"},
            },
            "required": ["mandate_id", "agent_id", "vendor_id", "amount", "category", "invoice_ref"],
        },
    },
    {
        "name": "evaluate_risk",
        "description": "Compute multi-component Invoice-to-PO matching score M and 5-factor transparent weighted risk score R.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "object", "description": "Invoice and intent parameters"},
                "vendor": {"type": "object", "description": "Optional vendor allowlist and historical risk profile"},
                "mandate": {"type": "object", "description": "Mandate spend limits and category whitelists"},
                "purchase_order": {"type": "object", "description": "Optional baseline Purchase Order for 3-way matching"},
            },
            "required": ["intent"],
        },
    },
    {
        "name": "review_approval_queue",
        "description": "Fetch all payment intents currently parked in the HUMAN_REVIEW queue awaiting executive authorization.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50, "description": "Maximum number of items to return"},
            },
        },
    },
    {
        "name": "submit_approval_decision",
        "description": "Submit CFO or Analyst approval or rejection decision on an intent in HUMAN_REVIEW with idempotency lock.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent_id": {"type": "string", "description": "PaymentIntent ID to decide"},
                "approver_id": {"type": "string", "description": "User ID of approver (e.g. usr_maya or usr_daniel)"},
                "decision": {"type": "string", "enum": ["APPROVED", "REJECTED"], "default": "APPROVED"},
                "notes": {"type": "string", "description": "Approval or rejection notes"},
                "idempotency_key": {"type": "string", "description": "Optional atomic idempotency key"},
            },
            "required": ["intent_id", "approver_id", "decision"],
        },
    },
    {
        "name": "execute_payment",
        "description": "Execute approved payment intent through PayPal Orders v2 (Authorize -> Capture) with strict idempotency lock.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent_id": {"type": "string", "description": "PaymentIntent ID to settle"},
                "idempotency_key": {"type": "string", "description": "Atomic idempotency key / PayPal-Request-Id"},
            },
            "required": ["intent_id", "idempotency_key"],
        },
    },
    {
        "name": "trigger_kill_switch",
        "description": "Trigger 3-Tier Granular Emergency Kill Switch (Level 1: INTENT, Level 2: AGENT, Level 3: MANDATE).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["INTENT", "AGENT", "MANDATE"]},
                "target_id": {"type": "string", "description": "ID of intent, agent, or mandate to halt"},
                "reason": {"type": "string", "description": "Emergency containment rationale"},
                "actor": {"type": "string", "default": "mcp_operator"},
            },
            "required": ["level", "target_id", "reason"],
        },
    },
    {
        "name": "query_evidence_graph",
        "description": "Retrieve or construct 18-node, 13-edge causal property graph for an intent or dispute with topological coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent_id": {"type": "string", "description": "Target payment intent identifier"},
            },
            "required": ["intent_id"],
        },
    },
    {
        "name": "compute_evidence_readiness",
        "description": "Calculate multi-dimensional Evidence Readiness Score (0.0 to 1.0) across Completeness, Freshness, Provenance, Consistency, Relevance, and Verifiability.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent_id": {"type": "string", "description": "Target payment intent identifier"},
                "dispute_reason": {"type": "string", "default": "ITEM_NOT_RECEIVED"},
            },
            "required": ["intent_id"],
        },
    },
    {
        "name": "compile_defense_brief",
        "description": "Synthesize formal dispute response narrative where 100% of factual sentences contain verified inline [ev_*] citations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent_id": {"type": "string", "description": "Target payment intent identifier"},
                "dispute_id": {"type": "string", "default": "PP-D-99412"},
                "dispute_reason": {"type": "string", "default": "ITEM_NOT_RECEIVED"},
            },
            "required": ["intent_id"],
        },
    },
    {
        "name": "submit_dispute_evidence",
        "description": "Submit compiled causal evidence defense brief to PayPal Disputes API and transition state to EVIDENCE_SUBMITTED.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dispute_id": {"type": "string", "description": "PayPal dispute identifier, e.g. PP-D-99412"},
                "evidence_type": {"type": "string", "description": "Optional PayPal evidence_type override"},
                "notes": {"type": "string", "description": "Optional defense brief text override"},
            },
            "required": ["dispute_id"],
        },
    },
]


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one of the 12 Sentinel & ProofLayer MCP tools."""
    init_db()
    db = SessionLocal()
    try:
        if name == "compile_policy":
            prompt = arguments.get("prompt", "")
            context = arguments.get("context")
            ast = PolicyCompiler.compile_nl_to_ast(prompt=prompt, context=context)
            return {"status": "success", "compiled_ast": ast}

        elif name == "simulate_policy":
            mandate_rules = arguments.get("mandate_rules", {})
            sample_size = int(arguments.get("sample_size", 100))
            sim_res = PolicyCompiler.simulate_policy(draft_policy=mandate_rules, sample_size=sample_size)
            return {"status": "success", "simulation_results": sim_res}

        elif name == "propose_payment_intent":
            payload = PaymentIntentCreate(
                id=arguments.get("id"),
                mandate_id=arguments["mandate_id"],
                agent_id=arguments["agent_id"],
                vendor_id=arguments["vendor_id"],
                amount=float(arguments["amount"]),
                currency=arguments.get("currency", "USD"),
                category=arguments["category"],
                invoice_ref=arguments["invoice_ref"],
                po_ref=arguments.get("po_ref"),
                line_items=arguments.get("line_items", []),
            )
            intent = propose_intent(payload=payload, db=db)
            return {
                "status": "success",
                "intent_id": intent.id,
                "current_status": intent.status,
                "amount": intent.amount,
                "po_match_score": intent.po_match_score,
                "risk_score": intent.risk_score,
                "risk_breakdown": intent.risk_breakdown,
                "reasons": intent.policy_evaluation_reasons,
            }

        elif name == "evaluate_risk":
            intent_dict = arguments.get("intent", {})
            vendor_dict = arguments.get("vendor")
            mandate_dict = arguments.get("mandate")
            po_dict = arguments.get("purchase_order")

            m_score, m_breakdown, m_reasons = RiskEngine.compute_po_matching_score(
                invoice=intent_dict,
                purchase_order=po_dict,
            )
            r_score, r_breakdown, r_reasons = RiskEngine.compute_risk_score(
                intent=intent_dict,
                vendor=vendor_dict,
                mandate=mandate_dict,
            )
            return {
                "status": "success",
                "matching_score": m_score,
                "matching_breakdown": m_breakdown,
                "risk_score": r_score,
                "risk_breakdown": r_breakdown,
                "reasons": m_reasons + r_reasons,
            }

        elif name == "review_approval_queue":
            limit = int(arguments.get("limit", 50))
            intents = (
                db.query(PaymentIntent)
                .filter(PaymentIntent.status == "HUMAN_REVIEW")
                .order_by(PaymentIntent.created_at.desc())
                .limit(limit)
                .all()
            )
            items = []
            for it in intents:
                vendor = db.query(Vendor).filter(Vendor.id == it.vendor_id).first()
                items.append({
                    "intent_id": it.id,
                    "agent_id": it.agent_id,
                    "vendor_id": it.vendor_id,
                    "vendor_name": vendor.name if vendor else it.vendor_id,
                    "amount": it.amount,
                    "currency": it.currency,
                    "category": it.category,
                    "po_match_score": it.po_match_score,
                    "risk_score": it.risk_score,
                    "created_at": it.created_at.isoformat(),
                })
            return {"status": "success", "count": len(items), "queue": items}

        elif name == "submit_approval_decision":
            intent_id = arguments["intent_id"]
            decision = arguments.get("decision", "APPROVED").upper()
            payload = ApprovalActionRequest(
                approver_id=arguments["approver_id"],
                decision=decision,  # type: ignore
                notes=arguments.get("notes"),
                idempotency_key=arguments.get("idempotency_key"),
            )
            if decision == "APPROVED":
                res = approve_intent(intent_id=intent_id, payload=payload, db=db)
            else:
                res = reject_intent(intent_id=intent_id, payload=payload, db=db)
            return {
                "status": "success",
                "approval_id": res.id,
                "intent_id": res.intent_id,
                "decision": res.decision,
                "intent_status": res.intent_status,
            }

        elif name == "execute_payment":
            intent_id = arguments["intent_id"]
            idempotency_key = arguments["idempotency_key"]
            payload = PaymentExecuteRequest(intent_id=intent_id, idempotency_key=idempotency_key)
            exec_res = execute_payment(payload=payload, db=db)
            return {
                "status": "success",
                "intent_id": exec_res.intent_id,
                "payment_status": exec_res.status,
                "paypal_order_id": exec_res.paypal_order_id,
                "paypal_capture_id": exec_res.paypal_capture_id,
                "amount": exec_res.amount,
                "cached_replay": exec_res.cached_replay,
            }

        elif name == "trigger_kill_switch":
            lvl = arguments["level"].upper()
            target_id = arguments["target_id"]
            reason = arguments["reason"]
            actor = arguments.get("actor", "mcp_operator")
            if lvl == "INTENT":
                res = StateMachine.kill_intent(db=db, intent_id=target_id, reason=reason, actor=actor)
            elif lvl == "AGENT":
                res = StateMachine.kill_agent(db=db, agent_id=target_id, reason=reason, actor=actor)
            elif lvl == "MANDATE":
                res = StateMachine.kill_mandate(db=db, mandate_id=target_id, reason=reason, actor=actor)
            else:
                raise ValueError(f"Unknown kill switch level '{lvl}'. Must be INTENT, AGENT, or MANDATE.")
            return {"status": "success", "kill_switch_result": res}

        elif name == "query_evidence_graph":
            intent_id = arguments["intent_id"]
            graph_res = get_evidence_graph(intent_id=intent_id, db=db)
            return {
                "status": "success",
                "intent_id": graph_res.intent_id,
                "node_count": graph_res.node_count,
                "edge_count": graph_res.edge_count,
                "nodes": [n.model_dump(mode="json") for n in graph_res.nodes],
                "edges": [e.model_dump(mode="json") for e in graph_res.edges],
            }

        elif name == "compute_evidence_readiness":
            intent_id = arguments["intent_id"]
            dispute_reason = arguments.get("dispute_reason", "ITEM_NOT_RECEIVED")
            # Ensure graph exists
            get_evidence_graph(intent_id=intent_id, db=db)
            graph = CausalGraph.from_db(db=db, intent_id=intent_id)
            readiness, breakdown = EvidenceCompilerService.compute_readiness_score(graph, dispute_reason)
            return {
                "status": "success",
                "intent_id": intent_id,
                "readiness_score": readiness,
                "readiness_breakdown": breakdown,
            }

        elif name == "compile_defense_brief":
            intent_id = arguments["intent_id"]
            dispute_id = arguments.get("dispute_id", "PP-D-99412")
            dispute_reason = arguments.get("dispute_reason", "ITEM_NOT_RECEIVED")
            get_evidence_graph(intent_id=intent_id, db=db)
            graph = CausalGraph.from_db(db=db, intent_id=intent_id)
            narrative, cited_nodes, ev_type, tracking_info = EvidenceCompilerService.compile_grounded_defense_narrative(
                graph=graph,
                dispute_id=dispute_id,
                dispute_reason=dispute_reason,
            )
            return {
                "status": "success",
                "intent_id": intent_id,
                "dispute_id": dispute_id,
                "paypal_evidence_type": ev_type,
                "cited_nodes": cited_nodes,
                "defense_narrative": narrative,
                "tracking_info": tracking_info,
            }

        elif name == "submit_dispute_evidence":
            dispute_id = arguments["dispute_id"]
            payload = DisputeSubmitDefenseRequest(
                evidence_type=arguments.get("evidence_type"),
                notes=arguments.get("notes"),
            )
            res = submit_dispute_defense(dispute_id=dispute_id, payload=payload, db=db)
            return {
                "status": "success",
                "dispute_id": res.id,
                "dispute_status": res.status,
                "readiness_score": res.readiness_score,
                "evidence_package": res.evidence_package,
            }

        else:
            raise ValueError(f"Unknown tool '{name}'")

    finally:
        db.close()


def run_stdio_server() -> None:
    """Run standard Model Context Protocol (MCP) JSON-RPC 2.0 loop over stdin/stdout."""
    for line in sys.stdin:
        line_clean = line.strip()
        if not line_clean:
            continue
        try:
            req = json.loads(line_clean)
            msg_id = req.get("id")
            method = req.get("method")

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {
                            "name": "sentinel-prooflayer-governance",
                            "version": "1.0.0",
                        },
                        "capabilities": {
                            "tools": {},
                        },
                    },
                }
            elif method == "tools/list":
                res = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": TOOLS_DEFINITIONS,
                    },
                }
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name", "")
                args = params.get("arguments", {})
                try:
                    tool_output = execute_tool(tool_name, args)
                    res = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(tool_output, indent=2),
                                }
                            ],
                        },
                    }
                except Exception as err:
                    res = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "isError": True,
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error executing tool '{tool_name}': {str(err)}",
                                }
                            ],
                        },
                    }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}",
                },
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
