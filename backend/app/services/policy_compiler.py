"""2-Stage Natural Language to JSON/CEL Mandate Compiler & What-If Simulator.

Stage 1: Deterministic & semantic parsing of procurement policies into structured JSON AST.
Stage 2: CEL & Predicate rule compiler and evaluator with priority guards.
Historical What-If Simulator: Projects auto-approval, review, and block metrics against historical spend.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple


class PolicySyntaxError(Exception):
    """Raised when natural language policy cannot be parsed into a coherent mandate."""
    def __init__(self, message: str):
        super().__init__(message)


class PolicyCompiler:
    """Enterprise policy compilation and historical simulation engine."""

    DEFAULT_ALLOWED_CATEGORIES = [
        "saas",
        "cloud_compute",
        "data_labeling",
        "ai_models",
        "hardware",
        "office_supplies",
    ]

    DEFAULT_BLOCKED_CATEGORIES = [
        "crypto",
        "gambling",
        "gift_cards",
        "adult",
        "weapons",
    ]

    DEFAULT_ALLOWED_VENDORS = [
        "vendor_data_labeling_co",
        "vendor_cloud_compute",
        "vendor_ai_infra",
        "vendor_aws",
        "vendor_slack",
    ]

    @classmethod
    def compile_nl_to_ast(
        cls,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Stage 1: Parse natural language procurement rules into a structured JSON AST."""
        if not prompt or not prompt.strip():
            raise PolicySyntaxError("Policy prompt cannot be empty.")

        text = prompt.strip()
        ctx = context or {}

        # 1. Parse auto-approve threshold ($X)
        auto_approve_match = re.search(
            r"(?:auto[- ]?approve|under|up to)\s*(?:payments\s*(?:up to|under)?\s*)?\$?([0-9,]+(?:\.[0-9]{2})?)",
            text,
            re.IGNORECASE,
        )
        if auto_approve_match:
            auto_approve_threshold = float(auto_approve_match.group(1).replace(",", ""))
        else:
            auto_approve_threshold = float(ctx.get("auto_approve_threshold", 1000.00))

        # 2. Parse max cap ($Y)
        max_cap_match = re.search(
            r"(?:max(?:imum)?\s*(?:cap|limit)|hard cap|over\s*\$?([0-9,]+(?:\.[0-9]{2})?)\s*(?:is\s*)?block(?:ed)?|between\s*\$[0-9,]+\s*and\s*\$?([0-9,]+(?:\.[0-9]{2})?))",
            text,
            re.IGNORECASE,
        )
        if max_cap_match:
            matched_val = max_cap_match.group(1) or max_cap_match.group(2)
            max_transaction_cap = float(matched_val.replace(",", "")) if matched_val else 5000.00
        else:
            max_transaction_cap = float(ctx.get("max_transaction_cap", 5000.00))

        # Ensure logical sanity
        if auto_approve_threshold > max_transaction_cap:
            max_transaction_cap = auto_approve_threshold * 2.0

        # 3. Daily velocity cap
        velocity_match = re.search(
            r"daily\s*(?:spend|velocity|limit)?\s*(?:cap\s*(?:of)?\s*)?\$?([0-9,]+(?:\.[0-9]{2})?)",
            text,
            re.IGNORECASE,
        )
        if velocity_match:
            daily_velocity_cap = float(velocity_match.group(1).replace(",", ""))
        else:
            daily_velocity_cap = float(ctx.get("daily_velocity_cap", max(10000.00, max_transaction_cap * 2)))

        # 4. Variance tolerance (X%)
        variance_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:po\s*)?variance", text, re.IGNORECASE)
        if variance_match:
            po_variance_tolerance = float(variance_match.group(1)) / 100.0
        else:
            po_variance_tolerance = float(ctx.get("po_variance_tolerance", 0.02))

        # 5. PO matching required
        po_matching_required = "po match" in text.lower() or "purchase order" in text.lower() or ctx.get("po_matching_required", True)

        # 6. Categories & Vendors
        text_lower = text.lower()
        blocked_cats = list(cls.DEFAULT_BLOCKED_CATEGORIES)
        for cat in ["crypto", "gambling", "gift_cards", "adult", "weapons", "cannabis"]:
            if cat in text_lower and cat not in blocked_cats:
                blocked_cats.append(cat)

        allowed_cats = list(cls.DEFAULT_ALLOWED_CATEGORIES)
        for cat in ["saas", "data_labeling", "cloud_compute", "ai_models", "hardware", "office_supplies", "consulting"]:
            if cat in text_lower and cat not in allowed_cats:
                allowed_cats.append(cat)

        allowed_vendors = list(cls.DEFAULT_ALLOWED_VENDORS)
        if "allowed_vendors" in ctx and isinstance(ctx["allowed_vendors"], list):
            allowed_vendors = ctx["allowed_vendors"]

        mandate_id = ctx.get("mandate_id", f"mdt_{uuid.uuid4().hex[:8]}")
        version = ctx.get("version", "1.0.0")
        agent_id = ctx.get("agent_id", "agent_atlas_procurement")
        org_id = ctx.get("organization_id", "usr_acme_finance")
        escalation_role = ctx.get("escalation_role", "usr_maya")

        # Rules List
        rules = [
            {
                "id": "RULE_BLOCK_CATEGORY",
                "expression": f"category in {blocked_cats}",
                "action": "BLOCK",
                "description": "Block prohibited merchant categories directly",
            },
            {
                "id": "RULE_HARD_CAP",
                "expression": f"amount > {max_transaction_cap:.2f}",
                "action": "BLOCK",
                "description": f"Block single payments exceeding ${max_transaction_cap:,.2f}",
            },
            {
                "id": "RULE_AUTO_APPROVE",
                "expression": f"amount <= {auto_approve_threshold:.2f} && po_match_score >= 0.85 && risk_score <= 0.25",
                "action": "AUTO_APPROVE",
                "description": f"Auto-approve matched invoices <= ${auto_approve_threshold:,.2f} with risk <= 0.25",
            },
            {
                "id": "RULE_ESCALATE_CFO",
                "expression": f"amount > {auto_approve_threshold:.2f} && amount <= {max_transaction_cap:.2f}",
                "action": "REQUIRE_HUMAN_REVIEW",
                "description": f"Require CFO approval for amounts between ${auto_approve_threshold:,.2f} and ${max_transaction_cap:,.2f}",
            },
        ]

        compiled_cel = (
            f"category in {blocked_cats} ? BLOCK : "
            f"(amount > {max_transaction_cap:.2f} ? BLOCK : "
            f"(amount <= {auto_approve_threshold:.2f} && po_match_score >= 0.85 && risk_score <= 0.25 ? AUTO_APPROVE : REQUIRE_HUMAN_REVIEW))"
        )

        return {
            "mandate_id": mandate_id,
            "version": version,
            "agent_id": agent_id,
            "organization_id": org_id,
            "currency": "USD",
            "auto_approve_threshold": auto_approve_threshold,
            "max_transaction_cap": max_transaction_cap,
            "daily_velocity_cap": daily_velocity_cap,
            "po_variance_tolerance": po_variance_tolerance,
            "po_matching_required": po_matching_required,
            "allowed_categories": allowed_cats,
            "blocked_categories": blocked_cats,
            "allowed_vendors": allowed_vendors,
            "escalation_role": escalation_role,
            "rules": rules,
            "compiled_cel": compiled_cel,
        }

    @classmethod
    def evaluate_intent(
        cls,
        ast: Dict[str, Any],
        intent_context: Dict[str, Any],
    ) -> Tuple[str, List[str]]:
        """Stage 2: Evaluate a payment intent against compiled mandate rules.

        Returns:
            Tuple of (decision, reasons_list)
            where decision is one of 'AUTO_APPROVE', 'REQUIRE_HUMAN_REVIEW', 'BLOCK'.
        """
        amount = float(intent_context.get("amount", 0.0))
        category = str(intent_context.get("category", "")).lower()
        vendor_id = str(intent_context.get("vendor_id", ""))
        po_match_score = float(intent_context.get("po_match_score", 0.0) or 0.0)
        risk_score = float(intent_context.get("risk_score", 0.0) or 0.0)
        reasons: List[str] = []

        blocked_categories = [c.lower() for c in ast.get("blocked_categories", cls.DEFAULT_BLOCKED_CATEGORIES)]
        auto_approve_threshold = float(ast.get("auto_approve_threshold", 1000.00))
        max_cap = float(ast.get("max_transaction_cap", 5000.00))
        allowed_vendors = ast.get("allowed_vendors", cls.DEFAULT_ALLOWED_VENDORS)

        # 1. Prohibited category check
        if category in blocked_categories:
            reasons.append(f"Blocked category '{category}' is prohibited under active mandate.")
            return "BLOCK", reasons

        # 2. Hard max cap check
        if amount > max_cap:
            reasons.append(f"Amount ${amount:,.2f} exceeds mandate hard cap of ${max_cap:,.2f}.")
            return "BLOCK", reasons

        # 3. High risk threshold check
        if risk_score > 0.60:
            reasons.append(f"Risk score {risk_score:.3f} exceeds maximum risk threshold 0.600.")
            return "BLOCK", reasons

        # 4. Critical PO mismatch check
        if po_match_score < 0.70 and ast.get("po_matching_required", True):
            reasons.append(f"PO match score {po_match_score:.3f} is below minimum tolerance 0.700.")
            return "BLOCK", reasons

        # 5. Non-allowlisted vendor check
        if allowed_vendors and vendor_id not in allowed_vendors:
            reasons.append(f"Vendor '{vendor_id}' is not present on corporate allowlist.")
            # If high risk or out of policy, block or escalate
            if risk_score >= 0.50:
                return "BLOCK", reasons
            return "REQUIRE_HUMAN_REVIEW", reasons

        # 6. Auto-approval criteria ($Amount <= L_auto AND M >= 0.85 AND R <= 0.25)
        if amount <= auto_approve_threshold and po_match_score >= 0.85 and risk_score <= 0.25:
            reasons.append(f"Amount ${amount:,.2f} <= ${auto_approve_threshold:,.2f}, PO match {po_match_score:.2f} >= 0.85, and risk {risk_score:.2f} <= 0.25.")
            return "AUTO_APPROVE", reasons

        # 7. Human review escalation
        if amount > auto_approve_threshold:
            reasons.append(f"Amount ${amount:,.2f} exceeds auto-approval threshold ${auto_approve_threshold:,.2f}; routed to CFO for review.")
        elif po_match_score < 0.85:
            reasons.append(f"PO match score {po_match_score:.2f} is below auto-approval threshold 0.850.")
        elif risk_score > 0.25:
            reasons.append(f"Risk score {risk_score:.2f} exceeds auto-approval ceiling 0.250.")

        return "REQUIRE_HUMAN_REVIEW", reasons

    @classmethod
    def simulate_policy(
        cls,
        draft_policy: Dict[str, Any],
        historical_transactions: Optional[List[Dict[str, Any]]] = None,
        sample_size: int = 100,
    ) -> Dict[str, Any]:
        """Historical What-If Simulator.

        Evaluates candidate mandate rules against historical transaction datasets,
        computing friction reduction, human review hours saved, and prevented spend.
        """
        transactions = historical_transactions or cls._generate_benchmark_transactions(sample_size)
        total_count = len(transactions)

        if total_count == 0:
            return {
                "total_transactions": 0,
                "auto_approved_count": 0,
                "auto_approved_rate": 0.0,
                "human_review_count": 0,
                "human_review_rate": 0.0,
                "blocked_count": 0,
                "blocked_rate": 0.0,
                "friction_hours_saved": 0.0,
                "blocked_spend_prevented": 0.0,
                "auto_approved_spend": 0.0,
                "human_review_spend": 0.0,
                "category_breakdown": {},
            }

        auto_count = 0
        review_count = 0
        block_count = 0

        auto_spend = 0.0
        review_spend = 0.0
        block_spend = 0.0

        category_breakdown: Dict[str, Dict[str, int]] = {}

        for tx in transactions:
            category = str(tx.get("category", "other"))
            if category not in category_breakdown:
                category_breakdown[category] = {"AUTO_APPROVE": 0, "REQUIRE_HUMAN_REVIEW": 0, "BLOCK": 0}

            decision, _ = cls.evaluate_intent(draft_policy, tx)
            amount = float(tx.get("amount", 0.0))

            if decision == "AUTO_APPROVE":
                auto_count += 1
                auto_spend += amount
                category_breakdown[category]["AUTO_APPROVE"] += 1
            elif decision == "REQUIRE_HUMAN_REVIEW":
                review_count += 1
                review_spend += amount
                category_breakdown[category]["REQUIRE_HUMAN_REVIEW"] += 1
            else:
                block_count += 1
                block_spend += amount
                category_breakdown[category]["BLOCK"] += 1

        # Average CFO approval latency is 4.2 hours per escalated transaction
        friction_hours_saved = round(auto_count * 4.2, 1)

        return {
            "total_transactions": total_count,
            "auto_approved_count": auto_count,
            "auto_approved_rate": round(auto_count / total_count, 4),
            "human_review_count": review_count,
            "human_review_rate": round(review_count / total_count, 4),
            "blocked_count": block_count,
            "blocked_rate": round(block_count / total_count, 4),
            "friction_hours_saved": friction_hours_saved,
            "blocked_spend_prevented": round(block_spend, 2),
            "auto_approved_spend": round(auto_spend, 2),
            "human_review_spend": round(review_spend, 2),
            "category_breakdown": category_breakdown,
        }

    @classmethod
    def _generate_benchmark_transactions(cls, count: int = 100) -> List[Dict[str, Any]]:
        """Generate deterministic enterprise benchmark transactions for what-if simulation."""
        benchmarks: List[Dict[str, Any]] = []
        for i in range(count):
            idx = i % 10
            if idx in (0, 1, 2, 3, 4):  # 50% routine SaaS / labeling under $1k
                amount = 200.0 + (i * 14.5) % 700.0
                category = "saas" if i % 2 == 0 else "data_labeling"
                vendor = "vendor_data_labeling_co" if category == "data_labeling" else "vendor_slack"
                po_match = 0.95 + (i % 5) * 0.01
                risk = 0.05 + (i % 4) * 0.03
            elif idx in (5, 6, 7):  # 30% higher value $1k - $4.5k
                amount = 1200.0 + (i * 37.0) % 3200.0
                category = "cloud_compute"
                vendor = "vendor_cloud_compute"
                po_match = 0.92 + (i % 6) * 0.01
                risk = 0.12 + (i % 3) * 0.04
            elif idx == 8:  # 10% blocked categories (crypto, gambling)
                amount = 500.0 + (i * 100.0) % 2500.0
                category = "crypto" if i % 2 == 0 else "gambling"
                vendor = "vendor_fastcrypto"
                po_match = 0.40
                risk = 0.95
            else:  # 10% excessive cap over $5k
                amount = 5500.0 + (i * 250.0) % 4000.0
                category = "hardware"
                vendor = "vendor_ai_infra"
                po_match = 0.88
                risk = 0.35

            benchmarks.append({
                "id": f"tx_bench_{i+1:03d}",
                "amount": round(amount, 2),
                "category": category,
                "vendor_id": vendor,
                "po_match_score": round(po_match, 3),
                "risk_score": round(risk, 3),
            })
        return benchmarks
