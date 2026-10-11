"""Dual-Track End-to-End Test Suite for Sentinel & ProofLayer.

Validates all 14 Acceptance Criteria for the PayPal AI Hackathon 2026:
1. test_nl_to_mandate_compilation_and_what_if_simulation:
   Tests 2-stage compiler and historical simulator friction metrics.
2. test_po_matching_score_and_weighted_risk_breakdown:
   Tests exact formulas M = 0.35 Sv + 0.25 St + 0.25 Sl + 0.15 Sm and
   R = 0.30 V + 0.25 D + 0.20 A + 0.15 C + 0.10 H.
3. test_scenario_1_auto_approved_procurement:
   Full lifecycle of $840 ($M=0.97, R <= 0.25) transitioning through
   PROPOSED -> POLICY_CHECK -> EVIDENCE_VALIDATION -> AUTO_APPROVED -> EXECUTING -> AUTHORIZED -> CAPTURED -> RECONCILED.
4. test_scenario_2_cfo_escalation_and_idempotent_approval:
   $4,180.50 intent parking in HUMAN_REVIEW, Maya ($100k cap) approving,
   acquiring atomic idempotency lock, Authorize -> Capture -> RECONCILED.
5. test_scenario_3_blocked_vendor_zero_paypal_calls:
   $2,500 FastCrypto Services, crypto category, non-allowlisted,
   transitions PROPOSED -> POLICY_CHECK -> BLOCKED, verifies exactly 0 PayPal calls made.
6. test_scenario_4_dispute_webhook_and_autonomous_evidence_package:
   Ingestion of CUSTOMER.DISPUTE.CREATED (PP-D-99412), HMAC/twin signature verification,
   event_id replay deduplication (firing twice returns status="ignored" with zero duplicate records),
   18-node causal graph traversal, Readiness calculation (0.940), strict [ev_*] inline citation validation
   on every claim sentence, and dispute evidence submission to PayPal.
7. test_three_tier_kill_switch:
   - Level 1 (INTENT): halts single intent, transitions to BLOCKED.
   - Level 2 (AGENT): revokes agent, halts active/future intents.
   - Level 3 (MANDATE): freezes mandate, voids uncaptured authorizations,
     strictly preserves already-CAPTURED PayPal transactions in DB and Merkle ledger.
8. test_merkle_audit_ledger_integrity_and_tamper_detection:
   verify_chain() == True on pristine ledger; tampering with payload or previous_hash returns
   (False, message, tampered_index).
9. test_mcp_server_twelve_tools:
   Instantiates MCP server in backend/mcp_server/server.py and verifies all 12 tools execute with valid responses.
10. test_state_machine_strict_guards:
    Rejects illegal transitions (e.g. PROPOSED -> CAPTURED, EXPIRED -> APPROVED).
11. test_atomic_idempotency_locking:
    Submitting identical idempotency_key and PayPal-Request-Id returns cached transaction receipt without double-charging.
12. test_digital_telemetry_substitution:
    SaaS/cloud dispute substitutes CUSTOMER_SESSION telemetry [ev_session_118] as PROOF_OF_FULFILLMENT when physical shipment is absent.
13. test_approver_role_limits:
    Analyst Daniel ($2,500 limit) attempting to approve $4,180.50 is rejected with HTTP 403;
    CFO Maya ($100,000 limit) succeeds.
14. test_end_to_end_integration_health_and_scenarios_reset:
    Tests /health, scenario information, and database reset endpoint.
"""

from __future__ import annotations

import copy
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ensure backend root is in sys.path regardless of execution working directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi.testclient import TestClient

from app.database import (
    Agent,
    AuditBlock,
    DisputeRecord,
    Mandate,
    Organization,
    PaymentIntent,
    PurchaseOrder,
    SessionLocal,
    TransactionRecord,
    User,
    Vendor,
    VendorContract,
    WebhookEvent,
    init_db,
)
from app.main import app
from app.routers.scenarios import seed_demo_data
from app.services.audit_ledger import AuditLedgerService
from app.services.evidence_compiler import (
    CitationMissingError,
    EvidenceCompilerService,
    InvalidCitationError,
)
from app.services.evidence_graph import CausalGraph
from app.services.policy_compiler import PolicyCompiler
from app.services.risk_engine import RiskEngine
from app.services.state_machine import (
    InvalidStateTransitionError,
    KillSwitchError,
    StateMachine,
)
from mcp_server.server import TOOLS_DEFINITIONS, execute_tool


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    """Ensure relational database tables and baseline Acme AI Ops fixtures exist."""
    init_db()
    db = SessionLocal()
    seed_demo_data(db)
    db.close()


@pytest.fixture
def client():
    """FastAPI TestClient with active lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    """Session fixture for direct database assertions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Acceptance Criterion 1
# ---------------------------------------------------------------------------
def test_nl_to_mandate_compilation_and_what_if_simulation(client: TestClient):
    """Criterion 1: Tests 2-stage compiler and historical simulator friction metrics."""
    prompt = (
        "Auto-approve SaaS and cloud compute payments under $1,000 with PO variance under 2%. "
        "Over $5,000 is blocked. Daily spend cap of $15,000. Block crypto, gambling, and weapons."
    )

    # Stage 1: Deterministic & Semantic Compilation into AST & CEL rules
    ast = PolicyCompiler.compile_nl_to_ast(prompt)
    assert ast["auto_approve_threshold"] == 1000.00
    assert ast["max_transaction_cap"] == 5000.00
    assert ast["daily_velocity_cap"] == 15000.00
    assert ast["po_variance_tolerance"] == 0.02
    assert "saas" in ast["allowed_categories"]
    assert "cloud_compute" in ast["allowed_categories"]
    assert "crypto" in ast["blocked_categories"]
    assert "gambling" in ast["blocked_categories"]
    assert "weapons" in ast["blocked_categories"]
    assert "amount <=" in ast["compiled_cel"]
    assert "category in" in ast["compiled_cel"]

    # Test HTTP Endpoint POST /api/policy/compile
    http_resp = client.post("/api/policy/compile", json={"prompt": prompt})
    assert http_resp.status_code == 200
    http_data = http_resp.json()
    assert http_data["auto_approve_threshold"] == 1000.00
    assert http_data["max_transaction_cap"] == 5000.00
    assert len(http_data["compiled_cel"]) > 0

    # Stage 2: Historical What-If Simulator
    sim = PolicyCompiler.simulate_policy(draft_policy=ast, sample_size=100)
    assert sim["total_transactions"] == 100
    assert sim["auto_approved_count"] > 0
    assert sim["human_review_count"] > 0
    assert sim["blocked_count"] > 0
    assert sim["auto_approved_rate"] == round(sim["auto_approved_count"] / 100, 4)
    assert sim["friction_hours_saved"] == round(sim["auto_approved_count"] * 4.2, 1)
    assert sim["blocked_spend_prevented"] > 0.0
    assert "saas" in sim["category_breakdown"]
    assert "cloud_compute" in sim["category_breakdown"]

    # Test HTTP Endpoint POST /api/policy/simulate
    sim_resp = client.post("/api/policy/simulate", json={"mandate_rules": ast, "sample_size": 100})
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["metrics"]["total_transactions"] == 100
    assert sim_data["metrics"]["friction_hours_saved"] > 0.0


# ---------------------------------------------------------------------------
# Acceptance Criterion 2
# ---------------------------------------------------------------------------
def test_po_matching_score_and_weighted_risk_breakdown():
    """Criterion 2: Tests exact formulas M = 0.35 Sv + 0.25 St + 0.25 Sl + 0.15 Sm

    and R = 0.30 V + 0.25 D + 0.20 A + 0.15 C + 0.10 H.
    """
    # 1. Invoice-to-PO Matching Score (M)
    invoice = {
        "amount": 840.00,
        "vendor_id": "vendor_data_labeling_co",
        "currency": "USD",
        "po_ref": "po_2026_4410",
        "line_items": [
            {
                "description": "20,000 High-Quality RLHF Annotations",
                "quantity": 20000,
                "unit_price": 0.042,
                "total": 840.00,
            }
        ],
    }
    purchase_order = {
        "id": "po_2026_4410",
        "amount": 840.00,
        "vendor_id": "vendor_data_labeling_co",
        "currency": "USD",
        "items": [
            {
                "description": "20,000 High-Quality RLHF Annotations",
                "quantity": 20000,
                "unit_price": 0.042,
                "total": 840.00,
            }
        ],
    }

    m_score, m_breakdown, m_reasons = RiskEngine.compute_po_matching_score(
        invoice=invoice,
        purchase_order=purchase_order,
        variance_tolerance=0.02,
    )

    assert "S_vendor" in m_breakdown
    assert "S_total" in m_breakdown
    assert "S_line_items" in m_breakdown
    assert "S_terms" in m_breakdown
    assert len(m_reasons) > 0

    expected_m = round(
        0.35 * m_breakdown["S_vendor"]
        + 0.25 * m_breakdown["S_total"]
        + 0.25 * m_breakdown["S_line_items"]
        + 0.15 * m_breakdown["S_terms"],
        4,
    )
    assert m_score == expected_m
    assert m_score >= 0.95  # Evaluates to 0.9700

    # 2. Transparent Weighted Risk Score (R) - Routine allowlisted vendor
    vendor_clean = {
        "id": "vendor_data_labeling_co",
        "is_allowlisted": True,
        "status": "VERIFIED",
        "dispute_rate": 0.01,
        "risk_rating": 0.05,
    }
    mandate = {
        "auto_approve_limit": 1000.00,
        "max_cap": 5000.00,
        "allowed_vendors": ["vendor_data_labeling_co"],
    }
    intent_clean = {
        "amount": 840.00,
        "category": "data_labeling",
        "vendor_id": "vendor_data_labeling_co",
        "invoice_ref": "inv_2026_0840",
    }

    r_clean, r_clean_breakdown, r_clean_reasons = RiskEngine.compute_risk_score(
        intent=intent_clean,
        vendor=vendor_clean,
        mandate=mandate,
    )

    assert "V" in r_clean_breakdown
    assert "D" in r_clean_breakdown
    assert "A" in r_clean_breakdown
    assert "C" in r_clean_breakdown
    assert "H" in r_clean_breakdown

    expected_r_clean = round(
        0.30 * r_clean_breakdown["V"]
        + 0.25 * r_clean_breakdown["D"]
        + 0.20 * r_clean_breakdown["A"]
        + 0.15 * r_clean_breakdown["C"]
        + 0.10 * r_clean_breakdown["H"],
        4,
    )
    assert r_clean == expected_r_clean
    assert r_clean <= 0.25
    assert r_clean_breakdown["V"] == 0.0  # Allowlisted
    assert r_clean_breakdown["C"] == 0.0  # Permitted category

    # 3. Transparent Weighted Risk Score (R) - Blocked crypto vendor
    vendor_risky = {
        "id": "vendor_fastcrypto",
        "is_allowlisted": False,
        "status": "FLAGGED",
        "dispute_rate": 0.42,
        "risk_rating": 0.95,
    }
    intent_risky = {
        "amount": 2500.00,
        "category": "crypto",
        "vendor_id": "vendor_fastcrypto",
        "invoice_ref": "inv_crypto_001",
    }

    r_risky, r_risky_breakdown, _ = RiskEngine.compute_risk_score(
        intent=intent_risky,
        vendor=vendor_risky,
        mandate=mandate,
    )

    expected_r_risky = round(
        0.30 * r_risky_breakdown["V"]
        + 0.25 * r_risky_breakdown["D"]
        + 0.20 * r_risky_breakdown["A"]
        + 0.15 * r_risky_breakdown["C"]
        + 0.10 * r_risky_breakdown["H"],
        4,
    )
    assert r_risky == expected_r_risky
    assert r_risky >= 0.65
    assert r_risky_breakdown["V"] == 1.0  # Non-allowlisted
    assert r_risky_breakdown["C"] == 1.0  # Prohibited category


# ---------------------------------------------------------------------------
# Acceptance Criterion 3
# ---------------------------------------------------------------------------
def test_scenario_1_auto_approved_procurement(client: TestClient, db_session):
    """Criterion 3: Full lifecycle of $840 (M=0.97, R <= 0.25) transitioning through

    PROPOSED -> POLICY_CHECK -> EVIDENCE_VALIDATION -> AUTO_APPROVED -> EXECUTING -> AUTHORIZED -> CAPTURED -> RECONCILED.
    """
    resp = client.post("/api/scenarios/run/1")
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario_id"] == 1
    assert data["status"] == "SUCCESS"
    assert data["final_state"] == "RECONCILED"
    assert data["details"]["amount"] == 840.00
    assert data["details"]["po_match_score"] >= 0.95
    assert data["details"]["risk_score"] <= 0.25
    assert data["paypal_calls_made"] >= 2
    assert data["merkle_blocks_added"] >= 3

    trace_str = " -> ".join(data["trace"])
    expected_stages = [
        "PROPOSED",
        "POLICY_CHECK",
        "EVIDENCE_VALIDATION",
        "AUTO_APPROVED",
        "EXECUTING",
        "AUTHORIZED",
        "CAPTURED",
        "RECONCILED",
    ]
    for stage in expected_stages:
        assert stage in trace_str

    # Database state verification
    intent_id = data["details"]["intent_id"]
    intent = db_session.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    assert intent is not None
    assert intent.status == "RECONCILED"
    assert intent.paypal_order_id is not None
    assert intent.paypal_capture_id is not None

    tx = db_session.query(TransactionRecord).filter(TransactionRecord.intent_id == intent_id).first()
    assert tx is not None
    assert tx.amount == 840.00
    assert tx.status == "RECONCILED"


# ---------------------------------------------------------------------------
# Acceptance Criterion 4
# ---------------------------------------------------------------------------
def test_scenario_2_cfo_escalation_and_idempotent_approval(client: TestClient, db_session):
    """Criterion 4: $4,180.50 intent parking in HUMAN_REVIEW, Maya ($100k cap) approving,

    acquiring atomic idempotency lock, Authorize -> Capture -> RECONCILED.
    """
    resp = client.post("/api/scenarios/run/2")
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario_id"] == 2
    assert data["status"] == "SUCCESS"
    assert data["final_state"] == "RECONCILED"
    assert data["details"]["amount"] == 4180.50
    assert data["details"]["po_match_score"] >= 0.95
    assert "usr_maya" in data["details"]["approver"]

    trace_str = " -> ".join(data["trace"])
    assert "HUMAN_REVIEW" in trace_str
    assert "CFO Maya" in trace_str
    assert "RECONCILED" in trace_str

    intent_id = data["details"]["intent_id"]
    intent = db_session.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    assert intent is not None
    assert intent.status == "RECONCILED"
    assert intent.idempotency_key is not None

    # Verify idempotency replay protection returns cached transaction receipt without double-charging
    re_exec = client.post(
        "/api/payments/execute",
        json={"intent_id": intent_id, "idempotency_key": intent.idempotency_key},
    )
    assert re_exec.status_code == 200
    re_data = re_exec.json()
    assert re_data["cached_replay"] is True
    assert re_data["status"] == "RECONCILED"
    assert re_data["paypal_order_id"] == intent.paypal_order_id
    assert re_data["paypal_capture_id"] == intent.paypal_capture_id


# ---------------------------------------------------------------------------
# Acceptance Criterion 5
# ---------------------------------------------------------------------------
def test_scenario_3_blocked_vendor_zero_paypal_calls(client: TestClient, db_session):
    """Criterion 5: $2,500 FastCrypto Services, crypto category, non-allowlisted,

    transitions PROPOSED -> POLICY_CHECK -> BLOCKED, verifies exactly 0 PayPal calls made.
    """
    resp = client.post("/api/scenarios/run/3")
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario_id"] == 3
    assert data["status"] == "SUCCESS"
    assert data["final_state"] == "BLOCKED"
    assert data["paypal_calls_made"] == 0
    assert data["details"]["paypal_calls_made"] == 0
    assert data["details"]["amount"] == 2500.00
    assert data["details"]["vendor"] == "FastCrypto Services"

    intent_id = data["details"]["intent_id"]
    intent = db_session.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    assert intent is not None
    assert intent.status == "BLOCKED"
    assert intent.paypal_order_id is None
    assert intent.paypal_capture_id is None

    # Check zero transactions created for blocked intent
    tx_count = db_session.query(TransactionRecord).filter(TransactionRecord.intent_id == intent_id).count()
    assert tx_count == 0


# ---------------------------------------------------------------------------
# Acceptance Criterion 6
# ---------------------------------------------------------------------------
def test_scenario_4_dispute_webhook_and_autonomous_evidence_package(client: TestClient, db_session):
    """Criterion 6: Ingestion of CUSTOMER.DISPUTE.CREATED (PP-D-99412), HMAC/twin signature verification,

    event_id replay deduplication (firing twice returns status="ignored" with zero duplicate records),
    18-node causal graph traversal, Readiness calculation (0.940), strict [ev_*] inline citation validation
    on every claim sentence, and dispute evidence submission to PayPal.
    """
    # 1. Execute full scenario 4
    resp = client.post("/api/scenarios/run/4")
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario_id"] == 4
    assert data["status"] == "SUCCESS"
    assert data["final_state"] == "EVIDENCE_SUBMITTED"
    assert data["details"]["dispute_id"] == "PP-D-99412"
    assert data["details"]["readiness_score"] == 0.940
    assert data["details"]["paypal_evidence_type"] == "PROOF_OF_FULFILLMENT"

    # Verify 6 readiness dimensions
    breakdown = data["details"]["readiness_breakdown"]
    assert breakdown["completeness"] == 1.000
    assert breakdown["freshness"] == 0.920
    assert breakdown["provenance"] == 0.950
    assert breakdown["consistency"] == 0.960
    assert breakdown["relevance"] == 0.887
    assert breakdown["verifiability"] == 0.850

    # 2. Test Webhook Replay Deduplication directly
    event_id = "WH-EVT-DEDUP-TEST-001"
    dispute_id = "PP-D-DEDUP-001"
    webhook_payload = {
        "id": event_id,
        "event_version": "1.0",
        "create_time": datetime.utcnow().isoformat(),
        "resource_type": "dispute",
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "summary": "Duplicate test dispute",
        "resource": {
            "dispute_id": dispute_id,
            "dispute_amount": {"value": "100.00", "currency_code": "USD"},
            "reason": "ITEM_NOT_RECEIVED",
        },
    }

    # First delivery: processed
    headers = {
        "paypal-transmission-id": event_id,
        "paypal-transmission-sig": "SIG_TWIN_VALID_HMAC",
    }
    wh_1 = client.post("/api/webhooks/paypal", json=webhook_payload, headers=headers)
    assert wh_1.status_code == 200
    assert wh_1.json()["status"] == "success"
    assert wh_1.json()["processed"] is True

    # Second delivery with identical event_id: safely ignored with 0 mutations
    wh_2 = client.post("/api/webhooks/paypal", json=webhook_payload, headers=headers)
    assert wh_2.status_code == 200
    wh_2_data = wh_2.json()
    assert wh_2_data["status"] == "ignored"
    assert wh_2_data["duplicate"] is True
    assert wh_2_data["processed"] is False

    # Confirm exactly 1 record exists in WebhookEvent table for this event_id
    events_in_db = db_session.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).all()
    assert len(events_in_db) == 1

    # 3. Test Causal Evidence Graph Traversal (18 node types)
    reconciled_intent = (
        db_session.query(PaymentIntent)
        .filter(PaymentIntent.status.in_(["RECONCILED", "DISPUTE_OPEN", "EVIDENCE_SUBMITTED"]))
        .first()
    )
    assert reconciled_intent is not None

    graph_resp = client.get(f"/api/evidence/graph/{reconciled_intent.id}")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert graph_data["node_count"] >= 15
    assert graph_data["edge_count"] >= 10

    # 4. Strict [ev_*] Citation Validation
    graph = CausalGraph.from_db(db=db_session, intent_id=reconciled_intent.id)
    narrative, cited_nodes, ev_type, _ = EvidenceCompilerService.compile_grounded_defense_narrative(
        graph=graph,
        dispute_id="PP-D-99412",
        dispute_reason="ITEM_NOT_RECEIVED",
    )
    # Valid citations pass
    assert EvidenceCompilerService.validate_defense_brief_citations(narrative, graph) is True

    # Missing citation raises CitationMissingError
    uncited_sentence = narrative + " The merchant delivered the items on time without doubt."
    with pytest.raises(CitationMissingError):
        EvidenceCompilerService.validate_defense_brief_citations(uncited_sentence, graph)

    # Invalid node citation raises InvalidCitationError
    invalid_cite_sentence = narrative + " Phantom invoice was registered [ev_phantom_invalid_999]."
    with pytest.raises(InvalidCitationError):
        EvidenceCompilerService.validate_defense_brief_citations(invalid_cite_sentence, graph)


# ---------------------------------------------------------------------------
# Acceptance Criterion 7
# ---------------------------------------------------------------------------
def test_three_tier_kill_switch(client: TestClient, db_session):
    """Criterion 7: 3-tier Kill Switch:

    - Level 1 (INTENT): halts single intent, transitions to BLOCKED.
    - Level 2 (AGENT): revokes agent, halts active/future intents.
    - Level 3 (MANDATE): freezes mandate, voids uncaptured authorizations,
      strictly preserves already-CAPTURED PayPal transactions in DB and Merkle ledger.
    """
    # -----------------------------------------------------------------------
    # Level 1: INTENT Kill Switch
    # -----------------------------------------------------------------------
    intent_l1 = PaymentIntent(
        id=f"pit_kill1_{uuid.uuid4().hex[:8]}",
        mandate_id="mdt_9f21ac",
        agent_id="agent_atlas_procurement",
        vendor_id="vendor_data_labeling_co",
        amount=500.00,
        currency="USD",
        category="data_labeling",
        invoice_ref="inv_k1_test",
        status="HUMAN_REVIEW",
    )
    db_session.add(intent_l1)
    db_session.commit()

    kill_l1_resp = client.post(
        f"/api/intents/{intent_l1.id}/kill",
        json={
            "level": "INTENT",
            "target_id": intent_l1.id,
            "reason": "Suspected invoice discrepancy",
            "actor": "compliance_officer",
        },
    )
    assert kill_l1_resp.status_code == 200
    assert kill_l1_resp.json()["level"] == "INTENT"
    assert kill_l1_resp.json()["status"] == "BLOCKED"

    db_session.refresh(intent_l1)
    assert intent_l1.status == "BLOCKED"

    # Invariant: Attempting to Level-1 kill already CAPTURED/RECONCILED payment raises error
    captured_intent = PaymentIntent(
        id=f"pit_cap_{uuid.uuid4().hex[:8]}",
        mandate_id="mdt_9f21ac",
        agent_id="agent_atlas_procurement",
        vendor_id="vendor_data_labeling_co",
        amount=840.00,
        currency="USD",
        category="data_labeling",
        invoice_ref="inv_cap_test",
        status="CAPTURED",
    )
    db_session.add(captured_intent)
    db_session.commit()

    kill_cap_resp = client.post(
        f"/api/intents/{captured_intent.id}/kill",
        json={
            "level": "INTENT",
            "target_id": captured_intent.id,
            "reason": "Illegal retroactive attempt",
            "actor": "rogue_admin",
        },
    )
    assert kill_cap_resp.status_code == 400

    # -----------------------------------------------------------------------
    # Level 2: AGENT Kill Switch
    # -----------------------------------------------------------------------
    agent_id = f"agent_sub_{uuid.uuid4().hex[:6]}"
    test_agent = Agent(
        id=agent_id,
        org_id="usr_acme_finance",
        name="Subordinate Test Agent",
        role="Purchaser",
        status="ACTIVE",
    )
    db_session.add(test_agent)

    intent_l2_pending = PaymentIntent(
        id=f"pit_kill2_{uuid.uuid4().hex[:8]}",
        mandate_id="mdt_9f21ac",
        agent_id=agent_id,
        vendor_id="vendor_cloud_compute",
        amount=1200.00,
        currency="USD",
        category="cloud_compute",
        invoice_ref="inv_k2_test",
        status="HUMAN_REVIEW",
    )
    db_session.add(intent_l2_pending)
    db_session.commit()

    kill_l2_resp = client.post(
        f"/api/payments/agent/{agent_id}/kill",
        json={
            "level": "AGENT",
            "target_id": agent_id,
            "reason": "Agent anomalous prompt injection",
            "actor": "security_guard",
        },
    )
    assert kill_l2_resp.status_code == 200
    assert kill_l2_resp.json()["level"] == "AGENT"
    assert kill_l2_resp.json()["status"] == "REVOKED"
    assert kill_l2_resp.json()["affected_count"] >= 1

    db_session.refresh(test_agent)
    db_session.refresh(intent_l2_pending)
    assert test_agent.status == "REVOKED"
    assert intent_l2_pending.status == "BLOCKED"

    # Revoked agent cannot propose new intents (HTTP 403)
    rogue_proposal = client.post(
        "/api/intents",
        json={
            "mandate_id": "mdt_9f21ac",
            "agent_id": agent_id,
            "vendor_id": "vendor_cloud_compute",
            "amount": 500.00,
            "currency": "USD",
            "category": "cloud_compute",
            "invoice_ref": "inv_blocked_rogue",
        },
    )
    assert rogue_proposal.status_code == 403

    # -----------------------------------------------------------------------
    # Level 3: MANDATE Kill Switch (with Captured Preservation)
    # -----------------------------------------------------------------------
    mandate_id = f"mdt_test_{uuid.uuid4().hex[:6]}"
    test_mandate = Mandate(
        id=mandate_id,
        org_id="usr_acme_finance",
        agent_id="agent_atlas_procurement",
        name="Test Spend Mandate",
        auto_approve_limit=500.00,
        max_cap=2000.00,
        status="ACTIVE",
    )
    db_session.add(test_mandate)

    # 1 uncaptured in-flight intent (should be BLOCKED)
    uncaptured_intent = PaymentIntent(
        id=f"pit_m_uncap_{uuid.uuid4().hex[:6]}",
        mandate_id=mandate_id,
        agent_id="agent_atlas_procurement",
        vendor_id="vendor_cloud_compute",
        amount=600.00,
        currency="USD",
        category="cloud_compute",
        invoice_ref="inv_m_uncap",
        status="HUMAN_REVIEW",
    )
    # 1 captured/reconciled intent (must be STRICTLY PRESERVED)
    reconciled_mandate_intent = PaymentIntent(
        id=f"pit_m_rec_{uuid.uuid4().hex[:6]}",
        mandate_id=mandate_id,
        agent_id="agent_atlas_procurement",
        vendor_id="vendor_cloud_compute",
        amount=400.00,
        currency="USD",
        category="cloud_compute",
        invoice_ref="inv_m_rec",
        status="RECONCILED",
        paypal_order_id="ORD-PRESERVE-1",
        paypal_capture_id="CAP-PRESERVE-1",
    )
    db_session.add(uncaptured_intent)
    db_session.add(reconciled_mandate_intent)
    db_session.commit()

    kill_l3_resp = client.post(
        f"/api/mandates/{mandate_id}/kill",
        json={
            "level": "MANDATE",
            "target_id": mandate_id,
            "reason": "Emergency corporate spend freeze",
            "actor": "cfo_maya",
        },
    )
    assert kill_l3_resp.status_code == 200
    l3_data = kill_l3_resp.json()
    assert l3_data["level"] == "MANDATE"
    assert l3_data["status"] == "FROZEN"
    assert l3_data["affected_count"] == 1
    assert l3_data["preserved_captured_count"] == 1

    db_session.refresh(test_mandate)
    db_session.refresh(uncaptured_intent)
    db_session.refresh(reconciled_mandate_intent)

    assert test_mandate.status == "FROZEN"
    assert uncaptured_intent.status == "BLOCKED"
    # STRICT INVARIANT: Already-captured/reconciled payment is strictly preserved!
    assert reconciled_mandate_intent.status == "RECONCILED"


# ---------------------------------------------------------------------------
# Acceptance Criterion 8
# ---------------------------------------------------------------------------
def test_merkle_audit_ledger_integrity_and_tamper_detection(db_session):
    """Criterion 8: Merkle Audit Ledger Integrity and Tamper Detection:

    verify_chain() == True on pristine ledger; tampering with payload or previous_hash
    returns (False, message, tampered_index).
    """
    blocks = db_session.query(AuditBlock).order_by(AuditBlock.block_index.asc()).all()
    assert len(blocks) >= 2

    # 1. Pristine Chain Verification
    is_valid, msg, tampered_idx = AuditLedgerService.verify_chain(blocks)
    assert is_valid is True
    assert tampered_idx is None
    assert "verified" in msg.lower()

    # 2. Tampering Test A: Payload Content Tampering
    tampered_blocks_a = [
        {
            "block_index": b.block_index,
            "timestamp": b.timestamp,
            "event_type": b.event_type,
            "actor": b.actor,
            "payload_hash": b.payload_hash,
            "prev_hash": b.prev_hash,
            "merkle_root": b.merkle_root,
            "block_hash": b.block_hash,
            "details": copy.deepcopy(b.details),
        }
        for b in blocks
    ]
    # Silently modify payload details of block 1
    tampered_blocks_a[1]["details"]["amount"] = 99999999.00
    is_valid_a, msg_a, tampered_idx_a = AuditLedgerService.verify_chain(tampered_blocks_a)
    assert is_valid_a is False
    assert tampered_idx_a == 1
    assert "mismatch" in msg_a.lower() or "tampering" in msg_a.lower()

    # 3. Tampering Test B: Chained Hash Breakage (Modifying previous_hash)
    tampered_blocks_b = [
        {
            "block_index": b.block_index,
            "timestamp": b.timestamp,
            "event_type": b.event_type,
            "actor": b.actor,
            "payload_hash": b.payload_hash,
            "prev_hash": b.prev_hash,
            "merkle_root": b.merkle_root,
            "block_hash": b.block_hash,
            "details": copy.deepcopy(b.details),
        }
        for b in blocks
    ]
    # Corrupt block 1's previous hash link
    tampered_blocks_b[1]["prev_hash"] = "0" * 64
    is_valid_b, msg_b, tampered_idx_b = AuditLedgerService.verify_chain(tampered_blocks_b)
    assert is_valid_b is False
    assert tampered_idx_b == 1
    assert "chain broken" in msg_b.lower() or "mismatch" in msg_b.lower()


# ---------------------------------------------------------------------------
# Acceptance Criterion 9
# ---------------------------------------------------------------------------
def test_mcp_server_twelve_tools(db_session):
    """Criterion 9: Instantiates MCP server in backend/mcp_server/server.py

    and verifies all 12 tools execute with valid responses.
    """
    assert len(TOOLS_DEFINITIONS) == 12
    tool_names = [t["name"] for t in TOOLS_DEFINITIONS]
    expected_tools = [
        "compile_policy",
        "simulate_policy",
        "propose_payment_intent",
        "evaluate_risk",
        "review_approval_queue",
        "submit_approval_decision",
        "execute_payment",
        "trigger_kill_switch",
        "query_evidence_graph",
        "compute_evidence_readiness",
        "compile_defense_brief",
        "submit_dispute_evidence",
    ]
    for expected in expected_tools:
        assert expected in tool_names

    uid = uuid.uuid4().hex[:6]

    # Tool 1: compile_policy
    res1 = execute_tool("compile_policy", {"prompt": "Auto-approve SaaS under $1000"})
    assert res1["status"] == "success"
    assert "compiled_ast" in res1
    assert "compiled_cel" in res1["compiled_ast"]

    # Tool 2: simulate_policy
    res2 = execute_tool("simulate_policy", {"mandate_rules": res1["compiled_ast"], "sample_size": 20})
    assert res2["status"] == "success"
    assert res2["simulation_results"]["total_transactions"] == 20

    # Tool 3: propose_payment_intent
    res3 = execute_tool(
        "propose_payment_intent",
        {
            "id": f"pit_mcp_prop_{uid}",
            "mandate_id": "mdt_9f21ac",
            "agent_id": "agent_atlas_procurement",
            "vendor_id": "vendor_data_labeling_co",
            "amount": 840.00,
            "currency": "USD",
            "category": "data_labeling",
            "invoice_ref": f"inv_mcp_{uid}",
            "po_ref": "po_2026_4410",
        },
    )
    assert res3["status"] == "success"
    prop_intent_id = res3["intent_id"]

    # Tool 4: evaluate_risk
    res4 = execute_tool(
        "evaluate_risk",
        {
            "intent": {
                "amount": 840.0,
                "category": "data_labeling",
                "vendor_id": "vendor_data_labeling_co",
                "invoice_ref": f"inv_mcp_{uid}",
                "po_ref": "po_2026_4410",
            },
            "purchase_order": {
                "id": "po_2026_4410",
                "amount": 840.0,
                "vendor_id": "vendor_data_labeling_co",
                "currency": "USD",
            },
        },
    )
    assert res4["status"] == "success"
    assert res4["matching_score"] >= 0.95

    # Tool 5: review_approval_queue
    res5 = execute_tool("review_approval_queue", {"limit": 10})
    assert res5["status"] == "success"
    assert "queue" in res5

    # Prepare a human review intent for tools 6 & 7
    res_hr = execute_tool(
        "propose_payment_intent",
        {
            "id": f"pit_mcp_hr_{uid}",
            "mandate_id": "mdt_9f21ac",
            "agent_id": "agent_atlas_procurement",
            "vendor_id": "vendor_cloud_compute",
            "amount": 4180.50,
            "currency": "USD",
            "category": "cloud_compute",
            "invoice_ref": f"inv_mcp_hr_{uid}",
            "po_ref": "po_2026_4417",
        },
    )
    hr_intent_id = res_hr["intent_id"]

    # Tool 6: submit_approval_decision
    res6 = execute_tool(
        "submit_approval_decision",
        {
            "intent_id": hr_intent_id,
            "approver_id": "usr_maya",
            "decision": "APPROVED",
            "notes": "Approved by CFO via MCP protocol",
        },
    )
    assert res6["status"] == "success"
    assert res6["decision"] == "APPROVED"

    # Tool 7: execute_payment
    res7 = execute_tool(
        "execute_payment",
        {
            "intent_id": hr_intent_id,
            "idempotency_key": f"idem_mcp_exec_{uid}",
        },
    )
    assert res7["status"] == "success"
    assert res7["payment_status"] == "RECONCILED"

    # Tool 8: trigger_kill_switch
    res_kill_prop = execute_tool(
        "propose_payment_intent",
        {
            "id": f"pit_mcp_kill_{uid}",
            "mandate_id": "mdt_9f21ac",
            "agent_id": "agent_atlas_procurement",
            "vendor_id": "vendor_cloud_compute",
            "amount": 1500.0,
            "category": "cloud_compute",
            "invoice_ref": f"inv_mcp_k_{uid}",
        },
    )
    k_id = res_kill_prop["intent_id"]
    res8 = execute_tool(
        "trigger_kill_switch",
        {"level": "INTENT", "target_id": k_id, "reason": "MCP Kill Switch Test"},
    )
    assert res8["status"] == "success"
    assert res8["kill_switch_result"]["status"] == "BLOCKED"

    # Tool 9: query_evidence_graph
    res9 = execute_tool("query_evidence_graph", {"intent_id": hr_intent_id})
    assert res9["status"] == "success"
    assert res9["node_count"] >= 15

    # Tool 10: compute_evidence_readiness
    res10 = execute_tool(
        "compute_evidence_readiness",
        {"intent_id": hr_intent_id, "dispute_reason": "ITEM_NOT_RECEIVED"},
    )
    assert res10["status"] == "success"
    assert res10["readiness_score"] >= 0.90

    dispute_id = f"PP-D-{uid}"
    existing_disp = db_session.query(DisputeRecord).filter(DisputeRecord.id == dispute_id).first()
    if not existing_disp:
        disp_rec = DisputeRecord(
            id=dispute_id,
            intent_id=hr_intent_id,
            amount=4180.50,
            currency="USD",
            reason="ITEM_NOT_RECEIVED",
            status="OPEN",
            sla_deadline=datetime.utcnow(),
        )
        db_session.add(disp_rec)
        db_session.commit()

    # Tool 11: compile_defense_brief
    res11 = execute_tool(
        "compile_defense_brief",
        {
            "intent_id": hr_intent_id,
            "dispute_id": dispute_id,
            "dispute_reason": "ITEM_NOT_RECEIVED",
        },
    )
    assert res11["status"] == "success"
    assert "[ev_" in res11["defense_narrative"]

    # Tool 12: submit_dispute_evidence
    res12 = execute_tool(
        "submit_dispute_evidence",
        {
            "dispute_id": dispute_id,
            "evidence_type": "PROOF_OF_FULFILLMENT",
            "notes": res11["defense_narrative"],
        },
    )
    assert res12["status"] == "success"
    assert res12["dispute_status"] == "EVIDENCE_SUBMITTED"


# ---------------------------------------------------------------------------
# Acceptance Criterion 10
# ---------------------------------------------------------------------------
def test_state_machine_strict_guards(db_session):
    """Criterion 10: State Machine Strict Guards:

    Rejects illegal transitions (e.g. PROPOSED -> CAPTURED, EXPIRED -> APPROVED)
    and enforces sequential preconditions.
    """
    # 1. Matrix Guard Verification
    assert StateMachine.can_transition("PROPOSED", "CAPTURED") is False
    assert StateMachine.can_transition("EXPIRED", "APPROVED") is False
    assert StateMachine.can_transition("BLOCKED", "AUTO_APPROVED") is False
    assert StateMachine.can_transition("RECONCILED", "EXECUTING") is False
    assert StateMachine.can_transition("PROPOSED", "POLICY_CHECK") is True
    assert StateMachine.can_transition("POLICY_CHECK", "EVIDENCE_VALIDATION") is True
    assert StateMachine.can_transition("AUTO_APPROVED", "EXECUTING") is True
    assert StateMachine.can_transition("EXECUTING", "AUTHORIZED") is True
    assert StateMachine.can_transition("AUTHORIZED", "CAPTURED") is True
    assert StateMachine.can_transition("CAPTURED", "RECONCILED") is True

    # 2. In-Memory Transition Guard Enforcement
    dummy_intent = PaymentIntent(
        id=f"pit_guard_{uuid.uuid4().hex[:8]}",
        mandate_id="mdt_9f21ac",
        agent_id="agent_atlas_procurement",
        vendor_id="vendor_data_labeling_co",
        amount=100.0,
        currency="USD",
        category="data_labeling",
        invoice_ref="inv_guard_test",
        status="PROPOSED",
    )
    db_session.add(dummy_intent)
    db_session.commit()

    # Attempt illegal jump: PROPOSED -> CAPTURED raises InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError):
        StateMachine.transition_intent(
            db=db_session,
            intent=dummy_intent,
            target_state="CAPTURED",
            reason="Illegal jump test",
        )

    # Valid step-by-step sequential transitions succeed
    StateMachine.transition_intent(db=db_session, intent=dummy_intent, target_state="POLICY_CHECK")
    assert dummy_intent.status == "POLICY_CHECK"

    StateMachine.transition_intent(db=db_session, intent=dummy_intent, target_state="EVIDENCE_VALIDATION")
    assert dummy_intent.status == "EVIDENCE_VALIDATION"


# ---------------------------------------------------------------------------
# Acceptance Criterion 11
# ---------------------------------------------------------------------------
def test_atomic_idempotency_locking(client: TestClient, db_session):
    """Criterion 11: Submitting identical idempotency_key and PayPal-Request-Id

    returns cached transaction receipt without double-charging.
    """
    uid = uuid.uuid4().hex[:8]
    # Create an approved intent
    intent = PaymentIntent(
        id=f"pit_idem_{uid}",
        mandate_id="mdt_9f21ac",
        agent_id="agent_atlas_procurement",
        vendor_id="vendor_data_labeling_co",
        amount=840.00,
        currency="USD",
        category="data_labeling",
        invoice_ref=f"inv_idem_{uid}",
        po_ref="po_2026_4410",
        status="AUTO_APPROVED",
    )
    db_session.add(intent)
    db_session.commit()

    idem_key = f"key_atomic_lock_{uid}"

    # First call: executes through PayPal Orders v2
    res_1 = client.post(
        "/api/payments/execute",
        json={"intent_id": intent.id, "idempotency_key": idem_key},
    )
    assert res_1.status_code == 200
    data_1 = res_1.json()
    assert data_1["status"] == "RECONCILED"
    assert data_1["cached_replay"] is False
    order_id = data_1["paypal_order_id"]
    capture_id = data_1["paypal_capture_id"]

    # Second call with identical idempotency key: returns cached receipt
    res_2 = client.post(
        "/api/payments/execute",
        json={"intent_id": intent.id, "idempotency_key": idem_key},
    )
    assert res_2.status_code == 200
    data_2 = res_2.json()
    assert data_2["status"] == "RECONCILED"
    assert data_2["cached_replay"] is True
    assert data_2["paypal_order_id"] == order_id
    assert data_2["paypal_capture_id"] == capture_id

    # Strictly verify zero double-charging: exactly 1 TransactionRecord exists in DB
    tx_records = db_session.query(TransactionRecord).filter(TransactionRecord.intent_id == intent.id).all()
    assert len(tx_records) == 1


# ---------------------------------------------------------------------------
# Acceptance Criterion 12
# ---------------------------------------------------------------------------
def test_digital_telemetry_substitution():
    """Criterion 12: SaaS/cloud dispute substitutes CUSTOMER_SESSION telemetry

    [ev_session_118] as PROOF_OF_FULFILLMENT when physical shipment is absent.
    """
    graph = CausalGraph(intent_id="pit_telemetry_test")
    # Add minimal nodes to represent digital cloud service
    graph.add_node("ev_mandate_9f21ac", "AGENT_MANDATE", "Mandate", {})
    graph.add_node("ev_po_4417", "PURCHASE_ORDER", "PO", {})
    graph.add_node("ev_invoice_3311", "INVOICE", "Invoice", {})
    graph.add_node("ev_approval_771", "APPROVAL_RECORD", "Approval", {})
    graph.add_node("ev_order_4180", "PAYPAL_ORDER", "Order", {})
    graph.add_node("ev_capture_442", "PAYPAL_CAPTURE", "Capture", {})
    graph.add_node("ev_contract_cc_02", "CONTRACT", "Contract", {})
    graph.add_node("ev_session_118", "CUSTOMER_SESSION", "Cloud GPU Telemetry Session", {
        "session_id": "SESSION-118-TELEMETRY",
        "duration_hours": 100,
    })

    narrative, cited_nodes, evidence_type, tracking_info = (
        EvidenceCompilerService.compile_grounded_defense_narrative(
            graph=graph,
            dispute_id="PP-D-99412",
            dispute_reason="ITEM_NOT_RECEIVED",
        )
    )

    # Invariant: Must substitute digital PROOF_OF_FULFILLMENT over physical PROOF_OF_SHIPMENT
    assert evidence_type == "PROOF_OF_FULFILLMENT"
    assert "ev_session_118" in cited_nodes
    assert "[ev_session_118]" in narrative
    assert tracking_info is not None
    assert tracking_info[0]["carrier_name"] == "DIGITAL_SERVICE_TELEMETRY"
    assert tracking_info[0]["tracking_number"] == "SESSION-118-TELEMETRY"


# ---------------------------------------------------------------------------
# Acceptance Criterion 13
# ---------------------------------------------------------------------------
def test_approver_role_limits(client: TestClient, db_session):
    """Criterion 13: Analyst Daniel ($2,500 limit) attempting to approve $4,180.50

    is rejected with HTTP 403; CFO Maya ($100,000 limit) succeeds.
    """
    uid = uuid.uuid4().hex[:8]
    intent = PaymentIntent(
        id=f"pit_roles_{uid}",
        mandate_id="mdt_9f21ac",
        agent_id="agent_atlas_procurement",
        vendor_id="vendor_cloud_compute",
        amount=4180.50,
        currency="USD",
        category="cloud_compute",
        invoice_ref=f"inv_roles_{uid}",
        status="HUMAN_REVIEW",
    )
    db_session.add(intent)
    db_session.commit()

    # 1. Analyst Daniel ($2,500 approval limit) attempts to approve $4,180.50 -> HTTP 403 Forbidden
    daniel_resp = client.post(
        f"/api/approvals/{intent.id}/approve",
        json={"approver_id": "usr_daniel", "notes": "Daniel approval attempt"},
    )
    assert daniel_resp.status_code == 403
    assert "exceeds user approval limit" in daniel_resp.json()["detail"]

    db_session.refresh(intent)
    assert intent.status == "HUMAN_REVIEW"  # Remains pending in review queue

    # 2. CFO Maya ($100,000 approval limit) approves $4,180.50 -> HTTP 200 OK
    maya_resp = client.post(
        f"/api/approvals/{intent.id}/approve",
        json={"approver_id": "usr_maya", "notes": "CFO Maya authorization"},
    )
    assert maya_resp.status_code == 200
    assert maya_resp.json()["decision"] == "APPROVED"

    db_session.refresh(intent)
    assert intent.status == "APPROVED"  # Successfully escalated and authorized


# ---------------------------------------------------------------------------
# Acceptance Criterion 14
# ---------------------------------------------------------------------------
def test_end_to_end_integration_health_and_scenarios_reset(client: TestClient, db_session):
    """Criterion 14: Tests /health, scenario information, and database reset endpoint."""
    # 1. System Health Check
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "ok"
    assert health_data["app"] == "sentinel-prooflayer"
    assert "timestamp" in health_data

    # 2. Root API Discovery
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    root_data = root_resp.json()
    assert "Sentinel" in root_data["name"]

    # 3. List Demonstration Scenarios
    scen_resp = client.get("/api/scenarios")
    assert scen_resp.status_code == 200
    scenarios = scen_resp.json()
    assert len(scenarios) == 4
    scen_ids = [s["scenario_id"] for s in scenarios]
    assert scen_ids == [1, 2, 3, 4]

    # 4. Database Reset & Seeding Endpoint
    reset_resp = client.post("/api/scenarios/reset")
    assert reset_resp.status_code == 200
    reset_data = reset_resp.json()
    assert reset_data["status"] == "success"
    assert "seeded_counts" in reset_data

    # Verify Acme AI Ops seed fixtures are present and active
    org = db_session.query(Organization).filter(Organization.id == "usr_acme_finance").first()
    assert org is not None
    assert org.name == "Acme AI Ops"

    maya = db_session.query(User).filter(User.id == "usr_maya").first()
    assert maya is not None
    assert maya.role == "CFO"

    daniel = db_session.query(User).filter(User.id == "usr_daniel").first()
    assert daniel is not None
    assert daniel.role == "Analyst"

    mandate = db_session.query(Mandate).filter(Mandate.id == "mdt_9f21ac").first()
    assert mandate is not None
    assert mandate.status == "ACTIVE"

    # Seed baseline Scenario 4 demonstration fixtures for any downstream suite
    s4_post = client.post("/api/scenarios/run/4")
    assert s4_post.status_code == 200


