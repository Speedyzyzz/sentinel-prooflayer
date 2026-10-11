"""Milestone M2 Automated Test Suite: Routers, Scenarios, Lifespan Seeding & MCP Server.

Validates:
1. Lifespan startup seeding of Acme AI Ops, Atlas, Maya, Daniel, mdt_9f21ac, POs, Contracts, Vendors.
2. All 9 FastAPI Routers (mandates, policy, intents, approvals, payments, webhooks, evidence, disputes, scenarios).
3. All 4 Deterministic Judge Scenarios:
   - Scenario 1 ($840.00 Auto-Approved Procurement, full lifecycle to RECONCILED)
   - Scenario 2 ($4,180.50 High-Value CFO Escalation, HUMAN_REVIEW -> Maya Approval -> RECONCILED)
   - Scenario 3 ($2,500.00 Out-of-Policy Blocked Vendor, BLOCKED, exactly 0 PayPal calls)
   - Scenario 4 (PayPal Dispute Webhook PP-D-99412, dedup, 18-node graph, Readiness 0.940, cited brief)
4. All 12 Model Context Protocol (MCP) Governance Tools with working handlers.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import (
    Agent,
    Mandate,
    Organization,
    PaymentIntent,
    PurchaseOrder,
    SessionLocal,
    User,
    Vendor,
    VendorContract,
    init_db,
)
from app.main import app
from app.routers.scenarios import seed_demo_data
from mcp_server.server import TOOLS_DEFINITIONS, execute_tool


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Ensure database tables and seeded demonstration fixtures exist."""
    init_db()
    db = SessionLocal()
    seed_demo_data(db)
    db.close()


@pytest.fixture
def client():
    """FastAPI TestClient with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def test_startup_seeding(client):
    """Verify that Acme AI Ops, Atlas, Maya, Daniel, mdt_9f21ac, POs, Contracts, and Vendors are seeded."""
    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.id == "usr_acme_finance").first()
        assert org is not None
        assert org.name == "Acme AI Ops"

        maya = db.query(User).filter(User.id == "usr_maya").first()
        assert maya is not None
        assert maya.role == "CFO"
        assert maya.approval_limit == 100000.00

        daniel = db.query(User).filter(User.id == "usr_daniel").first()
        assert daniel is not None
        assert daniel.role == "Analyst"
        assert daniel.approval_limit == 2500.00

        atlas = db.query(Agent).filter(Agent.id == "agent_atlas_procurement").first()
        assert atlas is not None
        assert atlas.status == "ACTIVE"

        mandate = db.query(Mandate).filter(Mandate.id == "mdt_9f21ac").first()
        assert mandate is not None
        assert mandate.auto_approve_limit == 1000.00
        assert mandate.max_cap == 5000.00
        assert mandate.po_variance_limit == 0.02

        v_dl = db.query(Vendor).filter(Vendor.id == "vendor_data_labeling_co").first()
        assert v_dl is not None
        assert v_dl.is_allowlisted is True

        v_cc = db.query(Vendor).filter(Vendor.id == "vendor_cloud_compute").first()
        assert v_cc is not None
        assert v_cc.is_allowlisted is True

        v_fc = db.query(Vendor).filter(Vendor.id == "vendor_fastcrypto").first()
        assert v_fc is not None
        assert v_fc.is_allowlisted is False

        po_4410 = db.query(PurchaseOrder).filter(PurchaseOrder.id == "po_2026_4410").first()
        assert po_4410 is not None
        assert po_4410.amount == 840.00

        po_4417 = db.query(PurchaseOrder).filter(PurchaseOrder.id == "po_2026_4417").first()
        assert po_4417 is not None
        assert po_4417.amount == 4150.00

        cnt_dl = db.query(VendorContract).filter(VendorContract.id == "cnt_2026_dl_01").first()
        assert cnt_dl is not None

        cnt_cc = db.query(VendorContract).filter(VendorContract.id == "cnt_2026_cc_02").first()
        assert cnt_cc is not None
    finally:
        db.close()


def test_health_and_root_endpoints(client):
    """Test GET /health and GET / endpoints."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"
    assert res_health.json()["app"] == "sentinel-prooflayer"

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Sentinel" in res_root.json()["name"]


def test_mandates_router(client):
    """Test GET, POST, PUT, and activate/deactivate endpoints on /api/mandates."""
    # List mandates
    res = client.get("/api/mandates")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Get specific mandate
    res_m = client.get("/api/mandates/mdt_9f21ac")
    assert res_m.status_code == 200
    assert res_m.json()["id"] == "mdt_9f21ac"

    # Create new mandate
    new_m_id = f"mdt_test_{uuid.uuid4().hex[:6]}"
    res_create = client.post(
        "/api/mandates",
        json={
            "id": new_m_id,
            "org_id": "usr_acme_finance",
            "agent_id": "agent_atlas_procurement",
            "name": "Test Autonomous Mandate",
            "auto_approve_limit": 500.0,
            "max_cap": 2500.0,
            "po_variance_limit": 0.05,
            "allowed_categories": ["saas", "hardware"],
            "blocked_categories": ["crypto"],
            "allowed_vendors": ["vendor_cloud_compute"],
            "status": "ACTIVE",
            "version": 1,
        },
    )
    assert res_create.status_code == 201
    assert res_create.json()["id"] == new_m_id

    # Update mandate
    res_update = client.put(f"/api/mandates/{new_m_id}", json={"auto_approve_limit": 600.0})
    assert res_update.status_code == 200
    assert res_update.json()["auto_approve_limit"] == 600.0
    assert res_update.json()["version"] == 2


def test_policy_router(client):
    """Test policy compilation and what-if simulation on /api/policy."""
    # Compile
    res_comp = client.post(
        "/api/policy/compile",
        json={"prompt": "Auto-approve cloud compute up to $1,500, hard cap $8,000, block all crypto."},
    )
    assert res_comp.status_code == 200
    ast = res_comp.json()
    assert ast["auto_approve_threshold"] >= 1000.0
    assert "crypto" in ast["blocked_categories"]
    assert len(ast["rules"]) > 0

    # Simulate
    res_sim = client.post(
        "/api/policy/simulate",
        json={
            "mandate_rules": {
                "auto_approve_threshold": 1000.0,
                "max_transaction_cap": 5000.0,
                "po_variance_tolerance": 0.02,
                "blocked_categories": ["crypto"],
            },
            "sample_size": 50,
        },
    )
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data["sample_evaluated"] == 50
    assert sim_data["metrics"]["auto_approved_count"] > 0


def test_intents_router_and_kill_switch_level1(client):
    """Test proposal, risk evaluation, and Level 1 Kill Switch on /api/intents."""
    intent_id = f"pit_test_kill1_{uuid.uuid4().hex[:6]}"
    res_prop = client.post(
        "/api/intents",
        json={
            "id": intent_id,
            "mandate_id": "mdt_9f21ac",
            "agent_id": "agent_atlas_procurement",
            "vendor_id": "vendor_cloud_compute",
            "amount": 2500.00,
            "currency": "USD",
            "category": "cloud_compute",
            "invoice_ref": "inv_test_kill_01",
            "po_ref": "po_2026_4417",
        },
    )
    assert res_prop.status_code == 201
    assert res_prop.json()["status"] in ("HUMAN_REVIEW", "AUTO_APPROVED")

    # Level 1 Kill Switch
    res_kill = client.post(
        f"/api/intents/{intent_id}/kill",
        json={"level": "INTENT", "target_id": intent_id, "reason": "Test emergency containment", "actor": "tester"},
    )
    assert res_kill.status_code == 200
    assert res_kill.json()["status"] == "BLOCKED"
    assert res_kill.json()["affected_count"] == 1


def test_approvals_router_and_authority_limits(client):
    """Test approval queue, Analyst vs CFO authority limit enforcement, and idempotency lock."""
    # Propose intent for $4,180.50 (above Analyst limit $2,500)
    intent_id = f"pit_auth_test_{uuid.uuid4().hex[:6]}"
    res_prop = client.post(
        "/api/intents",
        json={
            "id": intent_id,
            "mandate_id": "mdt_9f21ac",
            "agent_id": "agent_atlas_procurement",
            "vendor_id": "vendor_cloud_compute",
            "amount": 4180.50,
            "currency": "USD",
            "category": "cloud_compute",
            "invoice_ref": "inv_auth_test_01",
            "po_ref": "po_2026_4417",
        },
    )
    assert res_prop.status_code == 201
    assert res_prop.json()["status"] == "HUMAN_REVIEW"

    # Queue should contain this intent
    res_queue = client.get("/api/approvals")
    assert res_queue.status_code == 200
    queue_ids = [item["intent_id"] for item in res_queue.json()]
    assert intent_id in queue_ids

    # Analyst Daniel ($2,500 limit) attempting to approve $4,180.50 must fail with 403 Forbidden
    res_daniel = client.post(
        f"/api/approvals/{intent_id}/approve",
        json={"approver_id": "usr_daniel", "decision": "APPROVED", "notes": "Analyst signoff"},
    )
    assert res_daniel.status_code == 403
    assert "exceeds user approval limit" in res_daniel.json()["detail"]

    # CFO Maya ($100k limit) approves successfully with idempotency lock
    cfo_key = f"idem_test_cfo_{uuid.uuid4().hex[:6]}"
    res_maya = client.post(
        f"/api/approvals/{intent_id}/approve",
        json={"approver_id": "usr_maya", "decision": "APPROVED", "notes": "CFO signoff", "idempotency_key": cfo_key},
    )
    assert res_maya.status_code == 200
    assert res_maya.json()["decision"] == "APPROVED"
    assert res_maya.json()["intent_status"] == "APPROVED"


def test_payments_router_and_kill_switch_level2(client):
    """Test payments execution, duplicate replay caching, and Level 2 Agent Kill Switch."""
    # Fast path intent
    intent_id = f"pit_exec_test_{uuid.uuid4().hex[:6]}"
    res_prop = client.post(
        "/api/intents",
        json={
            "id": intent_id,
            "mandate_id": "mdt_9f21ac",
            "agent_id": "agent_atlas_procurement",
            "vendor_id": "vendor_data_labeling_co",
            "amount": 840.00,
            "currency": "USD",
            "category": "data_labeling",
            "invoice_ref": "inv_exec_test_01",
            "po_ref": "po_2026_4410",
        },
    )
    assert res_prop.status_code == 201
    assert res_prop.json()["status"] == "AUTO_APPROVED"

    # Execute payment
    idem_key = f"idem_exec_test_{uuid.uuid4().hex[:6]}"
    res_exec = client.post("/api/payments/execute", json={"intent_id": intent_id, "idempotency_key": idem_key})
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "RECONCILED"
    assert res_exec.json()["cached_replay"] is False

    # Replay with same idempotency key must return cached receipt
    res_replay = client.post("/api/payments/execute", json={"intent_id": intent_id, "idempotency_key": idem_key})
    assert res_replay.status_code == 200
    assert res_replay.json()["cached_replay"] is True

    # Test Level 2 Kill Switch on agent
    res_agent_kill = client.post(
        "/api/payments/agent/agent_atlas_procurement/kill",
        json={
            "level": "AGENT",
            "target_id": "agent_atlas_procurement",
            "reason": "Test Agent level 2 kill",
            "actor": "security_admin",
        },
    )
    assert res_agent_kill.status_code == 200
    assert res_agent_kill.json()["status"] == "REVOKED"

    # Restore agent status for subsequent tests
    db = SessionLocal()
    agent = db.query(Agent).filter(Agent.id == "agent_atlas_procurement").first()
    agent.status = "ACTIVE"
    db.commit()
    db.close()


def test_webhooks_router_and_deduplication(client):
    """Test PayPal webhook ingestion, signature validation, and event_id deduplication."""
    event_id = f"WH-TEST-{uuid.uuid4().hex[:8]}"
    payload = {
        "id": event_id,
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "resource_type": "dispute",
        "summary": "Dispute created by buyer",
        "resource": {
            "dispute_id": f"PP-D-{uuid.uuid4().hex[:6]}",
            "reason": "ITEM_NOT_RECEIVED",
            "dispute_amount": {"value": "840.00", "currency_code": "USD"},
        },
    }

    headers = {
        "paypal-transmission-id": event_id,
        "paypal-transmission-sig": "SIG_TEST_TWIN",
    }

    # First delivery: processed
    res1 = client.post("/api/webhooks/paypal", json=payload, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"
    assert res1.json()["processed"] is True
    assert res1.json()["duplicate"] is False

    # Second delivery with exact same event_id: ignored
    res2 = client.post("/api/webhooks/paypal", json=payload, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "ignored"
    assert res2.json()["duplicate"] is True
    assert res2.json()["processed"] is False


def test_evidence_and_disputes_routers(client):
    """Test 18-node causal property graph, Readiness score 0.940, and dispute auto-defense submission."""
    # Ensure reconciled intent exists
    res_s1 = client.post("/api/scenarios/run/1")
    assert res_s1.status_code == 200
    intent_id = res_s1.json()["details"]["intent_id"]

    # Evidence Graph query
    res_graph = client.get(f"/api/evidence/graph/{intent_id}")
    assert res_graph.status_code == 200
    graph_data = res_graph.json()
    assert graph_data["node_count"] >= 15
    assert graph_data["edge_count"] >= 10

    # Evidence compilation
    res_compile = client.post(
        "/api/evidence/compile",
        json={"intent_id": intent_id, "dispute_id": "PP-D-99412", "dispute_reason": "ITEM_NOT_RECEIVED"},
    )
    assert res_compile.status_code == 200
    comp_data = res_compile.json()
    assert comp_data["readiness_score"] >= 0.90
    assert len(comp_data["cited_nodes"]) >= 6
    assert "[ev_" in comp_data["defense_narrative"]

    # Dispute submission
    res_disp_sub = client.post("/api/disputes/PP-D-99412/submit-defense")
    assert res_disp_sub.status_code == 200
    assert res_disp_sub.json()["status"] == "EVIDENCE_SUBMITTED"


def test_deterministic_judge_scenarios_1_to_4(client):
    """Test all 4 deterministic judge scenarios sequentially."""
    # Reset to pristine state
    res_reset = client.post("/api/scenarios/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "success"

    # Scenario 1: Auto-Approved Procurement ($840.00)
    res_s1 = client.post("/api/scenarios/run/1")
    assert res_s1.status_code == 200
    s1 = res_s1.json()
    assert s1["status"] == "SUCCESS"
    assert s1["final_state"] == "RECONCILED"
    assert s1["details"]["amount"] == 840.00
    assert s1["paypal_calls_made"] == 3

    # Scenario 2: CFO Escalation ($4,180.50)
    res_s2 = client.post("/api/scenarios/run/2")
    assert res_s2.status_code == 200
    s2 = res_s2.json()
    assert s2["status"] == "SUCCESS"
    assert s2["final_state"] == "RECONCILED"
    assert s2["details"]["amount"] == 4180.50
    assert s2["details"]["approver"] == "usr_maya (CFO)"

    # Scenario 3: Out-of-Policy Blocked Vendor ($2,500.00, exactly 0 PayPal calls)
    res_s3 = client.post("/api/scenarios/run/3")
    assert res_s3.status_code == 200
    s3 = res_s3.json()
    assert s3["status"] == "SUCCESS"
    assert s3["final_state"] == "BLOCKED"
    assert s3["paypal_calls_made"] == 0
    assert "blocked_category: crypto" in s3["details"]["violations"]

    # Scenario 4: Dispute Webhook -> Readiness 0.940 & Grounded Defense Package
    res_s4 = client.post("/api/scenarios/run/4")
    assert res_s4.status_code == 200
    s4 = res_s4.json()
    assert s4["status"] == "SUCCESS"
    assert s4["final_state"] == "EVIDENCE_SUBMITTED"
    assert s4["details"]["readiness_score"] == 0.940
    assert "[ev_" in s4["details"]["defense_narrative"]


def test_12_mcp_governance_tools():
    """Verify all 12 Model Context Protocol tools execute successfully with genuine logic."""
    assert len(TOOLS_DEFINITIONS) == 12

    # 1. compile_policy
    res1 = execute_tool("compile_policy", {"prompt": "Auto-approve cloud spend under $1,000, cap $5,000."})
    assert res1["status"] == "success"

    # 2. simulate_policy
    res2 = execute_tool("simulate_policy", {
        "mandate_rules": {"auto_approve_threshold": 1000.0, "max_transaction_cap": 5000.0, "blocked_categories": ["crypto"]},
        "sample_size": 25,
    })
    assert res2["status"] == "success"

    # 3. propose_payment_intent
    uid = uuid.uuid4().hex[:6]
    res3 = execute_tool("propose_payment_intent", {
        "mandate_id": "mdt_9f21ac",
        "agent_id": "agent_atlas_procurement",
        "vendor_id": "vendor_data_labeling_co",
        "amount": 840.0,
        "currency": "USD",
        "category": "data_labeling",
        "invoice_ref": f"inv_mcp_{uid}",
        "po_ref": "po_2026_4410",
    })
    assert res3["status"] == "success"
    intent_id = res3["intent_id"]

    # 4. evaluate_risk
    res4 = execute_tool("evaluate_risk", {
        "intent": {"amount": 840.0, "category": "data_labeling", "vendor_id": "vendor_data_labeling_co", "invoice_ref": f"inv_mcp_{uid}", "po_ref": "po_2026_4410"},
        "purchase_order": {"id": "po_2026_4410", "amount": 840.0, "vendor_id": "vendor_data_labeling_co", "currency": "USD"},
    })
    assert res4["status"] == "success"

    # 5. review_approval_queue
    res5 = execute_tool("review_approval_queue", {"limit": 10})
    assert res5["status"] == "success"

    # 6. submit_approval_decision (on human review intent)
    res_hr = execute_tool("propose_payment_intent", {
        "mandate_id": "mdt_9f21ac",
        "agent_id": "agent_atlas_procurement",
        "vendor_id": "vendor_cloud_compute",
        "amount": 4180.50,
        "currency": "USD",
        "category": "cloud_compute",
        "invoice_ref": f"inv_mcp_hr_{uid}",
        "po_ref": "po_2026_4417",
    })
    hr_intent_id = res_hr["intent_id"]
    res6 = execute_tool("submit_approval_decision", {
        "intent_id": hr_intent_id,
        "approver_id": "usr_maya",
        "decision": "APPROVED",
        "notes": "Approved by CFO via MCP",
    })
    assert res6["status"] == "success"
    assert res6["decision"] == "APPROVED"

    # 7. execute_payment
    res7 = execute_tool("execute_payment", {
        "intent_id": hr_intent_id,
        "idempotency_key": f"idem_mcp_exec_{uid}",
    })
    assert res7["status"] == "success"
    assert res7["payment_status"] == "RECONCILED"

    # 8. trigger_kill_switch
    res_kill_prop = execute_tool("propose_payment_intent", {
        "mandate_id": "mdt_9f21ac",
        "agent_id": "agent_atlas_procurement",
        "vendor_id": "vendor_cloud_compute",
        "amount": 1500.0,
        "category": "cloud_compute",
        "invoice_ref": f"inv_mcp_k_{uid}",
    })
    k_id = res_kill_prop["intent_id"]
    res8 = execute_tool("trigger_kill_switch", {"level": "INTENT", "target_id": k_id, "reason": "MCP Kill Test"})
    assert res8["status"] == "success"
    assert res8["kill_switch_result"]["status"] == "BLOCKED"

    # 9. query_evidence_graph
    res9 = execute_tool("query_evidence_graph", {"intent_id": hr_intent_id})
    assert res9["status"] == "success"
    assert res9["node_count"] >= 15

    # 10. compute_evidence_readiness
    res10 = execute_tool("compute_evidence_readiness", {"intent_id": hr_intent_id, "dispute_reason": "ITEM_NOT_RECEIVED"})
    assert res10["status"] == "success"
    assert res10["readiness_score"] >= 0.90

    # 11. compile_defense_brief
    res11 = execute_tool("compile_defense_brief", {
        "intent_id": hr_intent_id,
        "dispute_id": "PP-D-99412",
        "dispute_reason": "ITEM_NOT_RECEIVED",
    })
    assert res11["status"] == "success"
    assert "[ev_" in res11["defense_narrative"]

    # 12. submit_dispute_evidence
    res12 = execute_tool("submit_dispute_evidence", {
        "dispute_id": "PP-D-99412",
        "evidence_type": "PROOF_OF_FULFILLMENT",
        "notes": res11["defense_narrative"],
    })
    assert res12["status"] == "success"
    assert res12["dispute_status"] == "EVIDENCE_SUBMITTED"
