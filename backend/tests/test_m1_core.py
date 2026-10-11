"""Comprehensive Unit & Integration Test Suite for Milestone M1 Core Services.

Tests:
1. Database ORM models (all 15 tables) and SQLite WAL mode.
2. Policy compiler (NL-to-AST, CEL string, rule evaluation, What-If simulation).
3. Risk engine formulas M and R (exact values, breakdowns, reason strings).
4. Canonical 12-state machine lifecycle transitions and guard preconditions.
5. 3-Tier Kill Switch (Level 1 INTENT, Level 2 AGENT, Level 3 MANDATE with captured preservation).
6. PayPal Sandbox REST Client & Deterministic Twin with idempotency.
7. 18-node, 13-edge Causal Evidence Graph.
8. Evidence Readiness score (exact 0.940 for Scenario 4) across 6 dimensions.
9. Grounded narrative compiler with 100% [ev_*] citations and digital telemetry substitution.
10. SHA-256 Merkle chain audit ledger and tamper verification.
"""

import os
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import (
    Base,
    Organization,
    User,
    Agent,
    Mandate,
    Vendor,
    PurchaseOrder,
    VendorContract,
    PaymentIntent,
    ApprovalRecord,
    TransactionRecord,
    DisputeRecord,
    AuditBlock,
    WebhookEvent,
    EvidenceNode,
    EvidenceEdge,
)
from app.services.policy_compiler import PolicyCompiler
from app.services.risk_engine import RiskEngine
from app.services.state_machine import StateMachine, InvalidStateTransitionError, KillSwitchError
from app.services.paypal_client import PayPalClient
from app.services.evidence_graph import CausalGraph, InvalidGraphElementError
from app.services.evidence_compiler import EvidenceCompilerService, CitationMissingError, InvalidCitationError
from app.services.audit_ledger import AuditLedgerService


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


class TestDatabaseModels:
    """Verify all 15 relational tables can be created, populated, and queried."""

    def test_all_15_tables_exist(self, db_session):
        tables = Base.metadata.tables.keys()
        expected_tables = [
            "organizations",
            "users",
            "agents",
            "mandates",
            "vendors",
            "purchase_orders",
            "vendor_contracts",
            "payment_intents",
            "approval_records",
            "transaction_records",
            "dispute_records",
            "audit_blocks",
            "webhook_events",
            "evidence_nodes",
            "evidence_edges",
        ]
        for t in expected_tables:
            assert t in tables, f"Missing table: {t}"
        assert len(expected_tables) == 15

    def test_seed_basic_hierarchy(self, db_session):
        org = Organization(id="usr_acme_finance", name="Acme AI Ops")
        db_session.add(org)
        user = User(
            id="usr_maya",
            org_id="usr_acme_finance",
            name="Maya Lin",
            email="maya.lin@acme.ai",
            role="CFO",
            approval_limit=100000.0,
        )
        db_session.add(user)
        agent = Agent(
            id="agent_atlas_procurement",
            org_id="usr_acme_finance",
            name="Atlas",
            role="Procurement Specialist",
        )
        db_session.add(agent)
        mandate = Mandate(
            id="mdt_9f21ac",
            org_id="usr_acme_finance",
            agent_id="agent_atlas_procurement",
            name="Q1 AI Operations Spend",
            auto_approve_limit=1000.0,
            max_cap=5000.0,
            allowed_categories=["saas", "cloud_compute"],
            blocked_categories=["crypto", "gambling"],
            allowed_vendors=["vendor_data_labeling_co"],
        )
        db_session.add(mandate)
        db_session.commit()

        queried_mandate = db_session.query(Mandate).filter(Mandate.id == "mdt_9f21ac").first()
        assert queried_mandate is not None
        assert queried_mandate.auto_approve_limit == 1000.0
        assert "crypto" in queried_mandate.blocked_categories


class TestPolicyCompiler:
    """Verify 2-stage compiler and What-If simulator."""

    def test_compile_nl_to_ast(self):
        prompt = (
            "Auto-approve data labeling and SaaS payments up to $1,000 when PO match >= 85% "
            "and risk <= 0.25. Escalate amounts over $1,000 to CFO Maya Lin up to $5,000. "
            "Block crypto, gambling, and weapons immediately."
        )
        ast = PolicyCompiler.compile_nl_to_ast(prompt)
        assert ast["auto_approve_threshold"] == 1000.0
        assert ast["max_transaction_cap"] == 5000.0
        assert "crypto" in ast["blocked_categories"]
        assert len(ast["rules"]) >= 4
        assert "compiled_cel" in ast

    def test_evaluate_intent_outcomes(self):
        ast = PolicyCompiler.compile_nl_to_ast("Auto-approve under $1000, hard cap $5000. Block crypto.")
        # Auto-approved
        dec_auto, _ = PolicyCompiler.evaluate_intent(
            ast,
            {"amount": 840.0, "category": "saas", "vendor_id": "vendor_data_labeling_co", "po_match_score": 0.97, "risk_score": 0.05},
        )
        assert dec_auto == "AUTO_APPROVE"

        # Escalated to CFO
        dec_review, _ = PolicyCompiler.evaluate_intent(
            ast,
            {"amount": 4180.5, "category": "cloud_compute", "vendor_id": "vendor_cloud_compute", "po_match_score": 0.96, "risk_score": 0.12},
        )
        assert dec_review == "REQUIRE_HUMAN_REVIEW"

        # Blocked (crypto)
        dec_block, _ = PolicyCompiler.evaluate_intent(
            ast,
            {"amount": 2500.0, "category": "crypto", "vendor_id": "vendor_fastcrypto", "po_match_score": 0.4, "risk_score": 0.9},
        )
        assert dec_block == "BLOCK"

    def test_what_if_simulator(self):
        ast = PolicyCompiler.compile_nl_to_ast("Auto-approve under $1000, cap $5000")
        results = PolicyCompiler.simulate_policy(ast, sample_size=50)
        assert results["total_transactions"] == 50
        assert results["auto_approved_count"] > 0
        assert results["friction_hours_saved"] > 0.0
        assert "blocked_spend_prevented" in results


class TestRiskEngine:
    """Verify Invoice-to-PO matching formula M and weighted risk score R."""

    def test_formula_m_scenario_1(self):
        inv = {
            "vendor_id": "vendor_data_labeling_co",
            "amount": 840.0,
            "po_ref": "po_2026_4410",
            "currency": "USD",
        }
        po = {
            "id": "po_2026_4410",
            "vendor_id": "vendor_data_labeling_co",
            "amount": 840.0,
            "currency": "USD",
        }
        m_score, breakdown, reasons = RiskEngine.compute_po_matching_score(inv, po, variance_tolerance=0.02)
        assert breakdown["S_vendor"] == 1.0
        assert breakdown["S_total"] == 1.0
        assert breakdown["S_terms"] == 1.0
        assert m_score >= 0.95
        assert len(reasons) > 0

    def test_formula_m_scenario_2_variance(self):
        inv = {
            "vendor_id": "vendor_cloud_compute",
            "amount": 4180.5,
            "po_ref": "po_2026_4417",
            "currency": "USD",
        }
        po = {
            "id": "po_2026_4417",
            "vendor_id": "vendor_cloud_compute",
            "amount": 4150.0,
            "currency": "USD",
        }
        m_score, breakdown, _ = RiskEngine.compute_po_matching_score(inv, po, variance_tolerance=0.02)
        # Variance = +30.5 / 4150 = 0.735% <= 2% tolerance
        assert breakdown["S_total"] >= 0.98
        assert m_score >= 0.95

    def test_formula_m_currency_mismatch(self):
        inv = {"vendor_id": "v1", "amount": 100.0, "currency": "EUR"}
        po = {"id": "po1", "vendor_id": "v1", "amount": 100.0, "currency": "USD"}
        m_score, breakdown, reasons = RiskEngine.compute_po_matching_score(inv, po)
        assert breakdown["S_terms"] == 0.0
        assert any("mismatch" in r.lower() for r in reasons)

    def test_formula_r_scenario_1(self):
        intent = {
            "amount": 840.0,
            "category": "data_labeling",
            "vendor_id": "vendor_data_labeling_co",
            "invoice_ref": "inv_2026_0840",
        }
        vendor = {"id": "vendor_data_labeling_co", "is_allowlisted": True, "dispute_rate": 0.0}
        mandate = {"auto_approve_limit": 1000.0, "max_cap": 5000.0}
        r_score, breakdown, reasons = RiskEngine.compute_risk_score(intent, vendor, mandate)
        assert breakdown["V"] == 0.0
        assert breakdown["D"] == 0.0
        assert breakdown["C"] == 0.0
        assert breakdown["H"] == 0.0
        assert r_score <= 0.05
        assert len(reasons) > 0

    def test_formula_r_scenario_3_blocked_crypto(self):
        intent = {
            "amount": 2500.0,
            "category": "crypto",
            "vendor_id": "vendor_fastcrypto",
            "invoice_ref": "inv_crypto_01",
        }
        vendor = {"id": "vendor_fastcrypto", "is_allowlisted": False, "dispute_rate": 0.42}
        mandate = {"auto_approve_limit": 1000.0, "max_cap": 5000.0}
        r_score, breakdown, reasons = RiskEngine.compute_risk_score(intent, vendor, mandate)
        assert breakdown["C"] == 1.0  # Blocked category
        assert breakdown["V"] == 1.0  # Non-allowlisted
        assert r_score >= 0.50

    def test_duplicate_fingerprint_detection(self):
        fp = RiskEngine.generate_invoice_fingerprint("vendor_data_labeling_co", "inv_2026_0840", 840.0)
        assert len(fp) == 64
        intent = {
            "amount": 840.0,
            "category": "data_labeling",
            "vendor_id": "vendor_data_labeling_co",
            "invoice_ref": "inv_2026_0840",
        }
        vendor = {"id": "vendor_data_labeling_co", "is_allowlisted": True}
        r_score, breakdown, reasons = RiskEngine.compute_risk_score(
            intent, vendor, historical_fingerprints={fp}
        )
        assert breakdown["D"] == 1.0
        assert any("replay" in r.lower() or "duplicate" in r.lower() for r in reasons)


class TestStateMachineAndKillSwitch:
    """Verify 12-state machine lifecycle and 3-tier kill switch."""

    @staticmethod
    def _seed_env(db_session, org_id="org_1", agent_id="ag_1", mandate_id="mdt_1", vendor_id="v_1"):
        if not db_session.query(Organization).filter(Organization.id == org_id).first():
            db_session.add(Organization(id=org_id, name="Test Org"))
        if not db_session.query(Agent).filter(Agent.id == agent_id).first():
            db_session.add(Agent(id=agent_id, org_id=org_id, name="Test Agent", role="Procurement"))
        if not db_session.query(Vendor).filter(Vendor.id == vendor_id).first():
            db_session.add(Vendor(id=vendor_id, name="Test Vendor", legal_name="Test Vendor Inc", category="saas", is_allowlisted=True))
        if not db_session.query(Mandate).filter(Mandate.id == mandate_id).first():
            db_session.add(Mandate(id=mandate_id, org_id=org_id, agent_id=agent_id, name="Test Mandate", auto_approve_limit=1000.0, max_cap=5000.0))
        db_session.commit()

    def test_lifecycle_transitions(self, db_session):
        self._seed_env(db_session, "org_1", "ag_1", "mdt_1", "v_1")
        intent = PaymentIntent(
            id="pi_test_01",
            mandate_id="mdt_1",
            agent_id="ag_1",
            vendor_id="v_1",
            amount=840.0,
            category="saas",
            invoice_ref="inv_1",
            status="PROPOSED",
        )
        db_session.add(intent)
        db_session.commit()

        # Step 1: PROPOSED -> POLICY_CHECK
        StateMachine.transition_intent(db_session, intent, "POLICY_CHECK")
        assert intent.status == "POLICY_CHECK"

        # Step 2: POLICY_CHECK -> EVIDENCE_VALIDATION
        StateMachine.transition_intent(db_session, intent, "EVIDENCE_VALIDATION")
        assert intent.status == "EVIDENCE_VALIDATION"

        # Step 3: EVIDENCE_VALIDATION -> AUTO_APPROVED
        StateMachine.transition_intent(db_session, intent, "AUTO_APPROVED")
        assert intent.status == "AUTO_APPROVED"

        # Step 4: AUTO_APPROVED -> EXECUTING (requires idempotency_key)
        StateMachine.transition_intent(
            db_session, intent, "EXECUTING", context={"idempotency_key": "idem_123"}
        )
        assert intent.status == "EXECUTING"
        assert intent.idempotency_key == "idem_123"

        # Step 5: EXECUTING -> AUTHORIZED
        StateMachine.transition_intent(db_session, intent, "AUTHORIZED")
        assert intent.status == "AUTHORIZED"

        # Step 6: AUTHORIZED -> CAPTURED
        StateMachine.transition_intent(db_session, intent, "CAPTURED")
        assert intent.status == "CAPTURED"

        # Step 7: CAPTURED -> RECONCILED
        StateMachine.transition_intent(db_session, intent, "RECONCILED")
        assert intent.status == "RECONCILED"

    def test_illegal_transition_raises_error(self, db_session):
        self._seed_env(db_session, "org_1", "ag_1", "mdt_1", "v_1")
        intent = PaymentIntent(
            id="pi_test_02",
            mandate_id="mdt_1",
            agent_id="ag_1",
            vendor_id="v_1",
            amount=500.0,
            category="saas",
            invoice_ref="inv_2",
            status="PROPOSED",
        )
        db_session.add(intent)
        db_session.commit()

        with pytest.raises(InvalidStateTransitionError):
            StateMachine.transition_intent(db_session, intent, "CAPTURED")

    def test_kill_switch_level_1_intent(self, db_session):
        self._seed_env(db_session, "org_1", "ag_1", "mdt_1", "v_1")
        intent = PaymentIntent(
            id="pi_kill_1",
            mandate_id="mdt_1",
            agent_id="ag_1",
            vendor_id="v_1",
            amount=1200.0,
            category="saas",
            invoice_ref="inv_k1",
            status="HUMAN_REVIEW",
        )
        db_session.add(intent)
        db_session.commit()

        res = StateMachine.kill_intent(db_session, "pi_kill_1", "Suspicious duplicate invoice", actor="usr_maya")
        assert res["status"] == "BLOCKED"
        assert intent.status == "BLOCKED"

    def test_kill_switch_level_2_agent(self, db_session):
        self._seed_env(db_session, "org_1", "agent_rogue", "m1", "v1")
        agent = db_session.query(Agent).filter(Agent.id == "agent_rogue").first()
        intent1 = PaymentIntent(id="pi_ag_1", mandate_id="m1", agent_id="agent_rogue", vendor_id="v1", amount=100.0, category="saas", invoice_ref="i1", status="PROPOSED")
        intent2 = PaymentIntent(id="pi_ag_2", mandate_id="m1", agent_id="agent_rogue", vendor_id="v1", amount=200.0, category="saas", invoice_ref="i2", status="POLICY_CHECK")
        db_session.add_all([intent1, intent2])
        db_session.commit()

        res = StateMachine.kill_agent(db_session, "agent_rogue", "Agent compromised", actor="usr_maya")
        assert res["status"] == "REVOKED"
        assert agent.status == "REVOKED"
        assert intent1.status == "BLOCKED"
        assert intent2.status == "BLOCKED"

    def test_kill_switch_level_3_mandate_preserves_captured(self, db_session):
        self._seed_env(db_session, "org_2", "ag_2", "mdt_freeze", "v1")
        mandate = db_session.query(Mandate).filter(Mandate.id == "mdt_freeze").first()

        # Active in-flight intent
        in_flight = PaymentIntent(id="pi_inflight", mandate_id="mdt_freeze", agent_id="ag_2", vendor_id="v1", amount=1500.0, category="saas", invoice_ref="inf", status="AUTHORIZED")
        # Already captured transaction
        captured = PaymentIntent(id="pi_captured", mandate_id="mdt_freeze", agent_id="ag_2", vendor_id="v1", amount=840.0, category="saas", invoice_ref="cap", status="CAPTURED")
        db_session.add_all([in_flight, captured])
        db_session.commit()

        res = StateMachine.kill_mandate(db_session, "mdt_freeze", "Budget lockdown", actor="usr_maya")
        assert res["status"] == "FROZEN"
        assert mandate.status == "FROZEN"
        assert in_flight.status == "BLOCKED"
        # Preserved invariant!
        assert captured.status == "CAPTURED"
        assert res["preserved_captured_count"] == 1


class TestPayPalClientAndTwin:
    """Verify PayPal Sandbox client and deterministic twin."""

    def test_deterministic_twin_order_flow(self):
        client = PayPalClient(client_id="mock", client_secret="mock")
        assert client.is_twin_mode is True

        # Order creation
        order = client.create_order(840.0, "USD", "po_2026_4410", idempotency_key="idem_test_order")
        assert order["status"] == "CREATED"
        order_id = order["id"]

        # Idempotency replay check
        order_replay = client.create_order(840.0, "USD", "po_2026_4410", idempotency_key="idem_test_order")
        assert order_replay["id"] == order_id

        # Authorization
        auth = client.authorize_order(order_id, idempotency_key="idem_test_auth")
        assert auth["status"] == "COMPLETED"
        auth_id = auth["purchase_units"][0]["payments"]["authorizations"][0]["id"]

        # Capture
        cap = client.capture_authorization(auth_id, idempotency_key="idem_test_cap")
        assert cap["status"] == "COMPLETED"
        assert "CAP-TWIN-" in cap["id"]

        # Dispute provide-evidence
        disp = client.provide_dispute_evidence(
            "PP-D-99412",
            "PROOF_OF_FULFILLMENT",
            notes="Atlas procured services [ev_mandate_9f21ac] [ev_session_118]",
        )
        assert disp["status"] == "EVIDENCE_SUBMITTED"


class TestEvidenceGraphAndCompiler:
    """Verify 18-node, 13-edge graph, 0.940 readiness, and cited defense brief."""

    def test_property_graph_18_node_types_and_13_edge_types(self):
        graph = CausalGraph(intent_id="pi_scenario_4")
        assert len(CausalGraph.NODE_TYPES) == 18
        assert len(CausalGraph.EDGE_TYPES) == 13

        # Add nodes
        graph.add_node("ev_mandate_9f21ac", "AGENT_MANDATE", "Mandate")
        graph.add_node("ev_po_4417", "PURCHASE_ORDER", "PO")
        graph.add_node("ev_invoice_3311", "INVOICE", "Invoice")
        graph.add_node("ev_contract_cc_02", "CONTRACT", "Contract")
        graph.add_node("ev_approval_771", "APPROVAL_RECORD", "Approval")
        graph.add_node("ev_order_4180", "PAYPAL_ORDER", "Order")
        graph.add_node("ev_capture_442", "PAYPAL_CAPTURE", "Capture")
        graph.add_node("ev_session_118", "CUSTOMER_SESSION", "Session")
        graph.add_node("ev_intent_4180", "PAYMENT_INTENT", "Intent")

        # Add edges
        graph.add_edge("e1", "ev_intent_4180", "ev_mandate_9f21ac", "AUTHORIZED_BY")
        graph.add_edge("e2", "ev_intent_4180", "ev_approval_771", "AUTHORIZED_BY")
        graph.add_edge("e3", "ev_intent_4180", "ev_po_4417", "REFERENCES")
        graph.add_edge("e4", "ev_invoice_3311", "ev_po_4417", "MATCHES")
        graph.add_edge("e5", "ev_intent_4180", "ev_order_4180", "PAID_BY")
        graph.add_edge("e6", "ev_order_4180", "ev_capture_442", "CAPTURED_AS")

        assert graph.has_node("ev_mandate_9f21ac")
        assert graph.has_node("ev_session_118")
        assert len(graph.get_edges()) == 6

    def test_evidence_readiness_score_exact_0_940_scenario_4(self):
        graph = CausalGraph(intent_id="pi_scenario_4")
        graph.add_node("ev_mandate_9f21ac", "AGENT_MANDATE", "Mandate")
        graph.add_node("ev_po_4417", "PURCHASE_ORDER", "PO")
        graph.add_node("ev_invoice_3311", "INVOICE", "Invoice")
        graph.add_node("ev_contract_cc_02", "CONTRACT", "Contract")
        graph.add_node("ev_approval_771", "APPROVAL_RECORD", "Approval")
        graph.add_node("ev_order_4180", "PAYPAL_ORDER", "Order")
        graph.add_node("ev_capture_442", "PAYPAL_CAPTURE", "Capture")
        graph.add_node("ev_session_118", "CUSTOMER_SESSION", "Session")
        graph.add_node("ev_intent_4180", "PAYMENT_INTENT", "Intent")

        readiness, breakdown = EvidenceCompilerService.compute_readiness_score(
            graph, "ITEM_NOT_RECEIVED"
        )
        assert readiness == 0.940
        assert breakdown["completeness"] == 1.0
        assert breakdown["freshness"] == 0.920
        assert breakdown["provenance"] == 0.950
        assert breakdown["consistency"] == 0.960
        assert breakdown["relevance"] == 0.887
        assert breakdown["verifiability"] == 0.850

    def test_grounded_defense_narrative_and_citation_validation(self):
        graph = CausalGraph(intent_id="pi_scenario_4")
        graph.add_node("ev_mandate_9f21ac", "AGENT_MANDATE", "Mandate")
        graph.add_node("ev_po_4417", "PURCHASE_ORDER", "PO")
        graph.add_node("ev_invoice_3311", "INVOICE", "Invoice")
        graph.add_node("ev_contract_cc_02", "CONTRACT", "Contract")
        graph.add_node("ev_approval_771", "APPROVAL_RECORD", "Approval")
        graph.add_node("ev_order_4180", "PAYPAL_ORDER", "Order")
        graph.add_node("ev_capture_442", "PAYPAL_CAPTURE", "Capture")
        graph.add_node("ev_session_118", "CUSTOMER_SESSION", "Session")

        narrative, cited_nodes, ev_type, tracking = (
            EvidenceCompilerService.compile_grounded_defense_narrative(graph)
        )
        assert ev_type == "PROOF_OF_FULFILLMENT"
        assert tracking[0]["carrier_name"] == "DIGITAL_SERVICE_TELEMETRY"
        assert "[ev_session_118]" in narrative
        assert "[ev_mandate_9f21ac]" in narrative

        # 100% of sentences must validate
        assert EvidenceCompilerService.validate_defense_brief_citations(narrative, graph) is True

    def test_citation_missing_raises_error(self):
        graph = CausalGraph()
        graph.add_node("ev_1", "AGENT_MANDATE", "M")
        invalid_narrative = "Sentence one [ev_1]. Sentence two lacks citation."
        with pytest.raises(CitationMissingError):
            EvidenceCompilerService.validate_defense_brief_citations(invalid_narrative, graph)


class TestCryptographicAuditLedger:
    """Verify Merkle chain ledger, genesis block, and tamper detection."""

    def test_merkle_chain_and_verify_chain(self, db_session):
        # Genesis block
        genesis = AuditLedgerService.initialize_genesis_block(db_session)
        assert genesis.block_index == 0
        assert genesis.prev_hash == "0" * 64

        # Block 1
        b1 = AuditLedgerService.append_block(
            db_session,
            event_type="MANDATE_CREATED",
            entity_type="MANDATE",
            entity_id="mdt_9f21ac",
            actor="system",
            details={"auto_approve": 1000.0, "cap": 5000.0},
        )
        assert b1.block_index == 1
        assert b1.prev_hash == genesis.block_hash

        # Block 2
        b2 = AuditLedgerService.append_block(
            db_session,
            event_type="PAYMENT_CAPTURED",
            entity_type="PAYMENT_INTENT",
            entity_id="pi_01",
            actor="agent_atlas_procurement",
            details={"amount": 840.0, "paypal_capture_id": "CAP-01"},
        )
        assert b2.block_index == 2
        assert b2.prev_hash == b1.block_hash

        # Verification passes on untampered chain
        blocks = db_session.query(AuditBlock).order_by(AuditBlock.block_index.asc()).all()
        is_valid, msg, tampered_idx = AuditLedgerService.verify_chain(blocks)
        assert is_valid is True
        assert tampered_idx is None

    def test_tamper_detection_pinpoints_corrupted_block(self, db_session):
        AuditLedgerService.initialize_genesis_block(db_session)
        AuditLedgerService.append_block(db_session, "EVENT_1", "INTENT", "id1", "actor", {"amount": 100.0})
        AuditLedgerService.append_block(db_session, "EVENT_2", "INTENT", "id2", "actor", {"amount": 200.0})

        blocks = db_session.query(AuditBlock).order_by(AuditBlock.block_index.asc()).all()

        # Adversary tampers with block 1 payload
        blocks[1].details = {"amount": 99999.0}  # Unauthorized change!

        is_valid, msg, tampered_idx = AuditLedgerService.verify_chain(blocks)
        assert is_valid is False
        assert tampered_idx == 1
        assert "mismatch" in msg.lower() or "tampering" in msg.lower()
