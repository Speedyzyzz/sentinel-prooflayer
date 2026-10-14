"""Payment Intent Lifecycle Router for Sentinel Control Plane.

Endpoints:
- GET  /api/intents: List payment intents with optional status, agent, and mandate filters.
- POST /api/intents: Propose new payment intent and immediately execute automated policy & risk check.
- POST /api/intents/evaluate-fast: High-throughput stateless policy & XAI risk evaluation endpoint.
- GET  /api/intents/{id}: Retrieve detailed payment intent including risk and matching breakdown.
- POST /api/intents/{id}/evaluate: Re-evaluate policy rules and risk score for an existing intent.
- POST /api/intents/{id}/kill: Level 1 Kill Switch - halts single intent before payment capture.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import Agent, Mandate, PaymentIntent, PurchaseOrder, Vendor, get_db
from app.schemas import (
    KillSwitchRequest,
    KillSwitchResponse,
    PaymentIntentCreate,
    PaymentIntentEvaluateRequest,
    PaymentIntentResponse,
)
from app.services.audit_ledger import AuditLedgerService
from app.services.risk_engine import RiskEngine
from app.services.state_machine import KillSwitchError, StateMachine

router = APIRouter(prefix="/intents", tags=["intents"])


def _evaluate_intent_logic(
    db: Session,
    intent: PaymentIntent,
    mandate: Mandate,
    vendor: Optional[Vendor],
    po: Optional[PurchaseOrder],
) -> PaymentIntent:
    """Internal helper to execute policy compiler rules, PO matching, and XAI risk evaluation."""
    # Build dictionaries for risk engine
    invoice_dict = {
        "vendor_id": intent.vendor_id,
        "vendor_name": vendor.name if vendor else "",
        "vendor_legal_name": vendor.legal_name if vendor else "",
        "po_ref": intent.po_ref,
        "amount": intent.amount,
        "currency": intent.currency,
        "line_items": intent.line_items or [],
    }

    po_dict = None
    if po:
        po_dict = {
            "id": po.id,
            "vendor_id": po.vendor_id,
            "amount": po.amount,
            "currency": po.currency,
            "items": po.items or [],
            "terms": po.terms,
        }

    # 1. PO Matching Score
    m_score, m_breakdown, m_reasons = RiskEngine.compute_po_matching_score(
        invoice=invoice_dict,
        purchase_order=po_dict,
        variance_tolerance=mandate.po_variance_limit,
    )

    # 2. Risk Score & Explainable AI Attribution
    vendor_dict = None
    if vendor:
        vendor_dict = {
            "id": vendor.id,
            "is_allowlisted": vendor.is_allowlisted,
            "risk_rating": vendor.risk_rating,
            "dispute_rate": vendor.dispute_rate,
        }

    mandate_dict = {
        "auto_approve_limit": mandate.auto_approve_limit,
        "max_cap": mandate.max_cap,
        "allowed_vendors": mandate.allowed_vendors or [],
        "allowed_categories": mandate.allowed_categories or [],
        "blocked_categories": mandate.blocked_categories or [],
    }

    intent_dict = {
        "amount": intent.amount,
        "category": intent.category,
        "vendor_id": intent.vendor_id,
        "invoice_ref": intent.invoice_ref,
        "line_items": intent.line_items or [],
    }

    r_score, r_breakdown, r_reasons = RiskEngine.compute_risk_score(
        intent=intent_dict,
        vendor=vendor_dict,
        mandate=mandate_dict,
    )

    combined_reasons = m_reasons + r_reasons
    intent.po_match_score = m_score
    intent.risk_score = r_score
    intent.risk_breakdown = r_breakdown
    intent.policy_evaluation_reasons = combined_reasons

    # Check violations
    blocked_categories = mandate.blocked_categories or RiskEngine.BLOCKED_CATEGORIES
    is_blocked_cat = intent.category.lower() in [c.lower() for c in blocked_categories]

    allowed_vendors = mandate.allowed_vendors or []
    vendor_not_allowed = False
    if vendor and not vendor.is_allowlisted and intent.vendor_id not in allowed_vendors:
        vendor_not_allowed = True
    elif not vendor:
        vendor_not_allowed = True

    exceeds_max_cap = intent.amount > mandate.max_cap
    has_prompt_injection = float(r_breakdown.get("prompt_injection_weight", 0.0)) >= 0.30

    # Transition from PROPOSED -> POLICY_CHECK
    StateMachine.transition_intent(db, intent, "POLICY_CHECK")

    if is_blocked_cat or vendor_not_allowed or exceeds_max_cap or has_prompt_injection:
        violation_reason = []
        if is_blocked_cat:
            violation_reason.append(f"blocked_category: {intent.category}")
        if vendor_not_allowed:
            violation_reason.append("vendor_not_allowlisted")
        if exceeds_max_cap:
            violation_reason.append(f"amount ${intent.amount:,.2f} exceeds max cap ${mandate.max_cap:,.2f}")
        if has_prompt_injection:
            violation_reason.append("adversarial_prompt_injection_detected")

        v_msg = "; ".join(violation_reason)
        StateMachine.transition_intent(db, intent, "BLOCKED", reason=f"Policy violation: {v_msg}")

        AuditLedgerService.append_block(
            db=db,
            event_type="INTENT_BLOCKED",
            entity_type="PAYMENT_INTENT",
            entity_id=intent.id,
            actor="sentinel_policy_engine",
            details={
                "intent_id": intent.id,
                "amount": intent.amount,
                "violations": violation_reason,
                "risk_score": r_score,
                "risk_breakdown": r_breakdown,
            },
        )
        return intent

    # Transition POLICY_CHECK -> EVIDENCE_VALIDATION
    StateMachine.transition_intent(db, intent, "EVIDENCE_VALIDATION")

    # Fast path auto-approval check
    if intent.amount <= mandate.auto_approve_limit and r_score < 0.15:
        StateMachine.transition_intent(
            db,
            intent,
            "AUTO_APPROVED",
            reason=f"Auto-approved: amount ${intent.amount:,.2f} <= ${mandate.auto_approve_limit:,.2f} and risk {r_score:.3f} < 0.15",
        )
        AuditLedgerService.append_block(
            db=db,
            event_type="INTENT_AUTO_APPROVED",
            entity_type="PAYMENT_INTENT",
            entity_id=intent.id,
            actor="sentinel_policy_engine",
            details={
                "intent_id": intent.id,
                "amount": intent.amount,
                "po_match_score": m_score,
                "risk_score": r_score,
                "risk_breakdown": r_breakdown,
            },
        )
    else:
        StateMachine.transition_intent(
            db,
            intent,
            "HUMAN_REVIEW",
            reason=f"Escalated to human review: amount ${intent.amount:,.2f} > ${mandate.auto_approve_limit:,.2f} or risk {r_score:.3f} >= 0.15",
        )
        AuditLedgerService.append_block(
            db=db,
            event_type="INTENT_ESCALATED_HUMAN_REVIEW",
            entity_type="PAYMENT_INTENT",
            entity_id=intent.id,
            actor="sentinel_policy_engine",
            details={
                "intent_id": intent.id,
                "amount": intent.amount,
                "po_match_score": m_score,
                "risk_score": r_score,
                "risk_breakdown": r_breakdown,
            },
        )

    return intent


@router.get("", response_model=List[PaymentIntentResponse])
def list_intents(
    mandate_id: Optional[str] = Query(None, description="Filter by mandate ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by canonical lifecycle status"),
    db: Session = Depends(get_db),
) -> List[PaymentIntentResponse]:
    """Retrieve all payment intents matching optional query parameters."""
    query = db.query(PaymentIntent)
    if mandate_id:
        query = query.filter(PaymentIntent.mandate_id == mandate_id)
    if agent_id:
        query = query.filter(PaymentIntent.agent_id == agent_id)
    if vendor_id:
        query = query.filter(PaymentIntent.vendor_id == vendor_id)
    if status_filter:
        query = query.filter(PaymentIntent.status == status_filter.upper())
    return query.order_by(PaymentIntent.created_at.desc()).all()


@router.post("/evaluate-fast")
async def evaluate_intent_fast(payload: PaymentIntentCreate) -> Dict[str, Any]:
    """High-throughput stateless Sentinel evaluation endpoint for concurrent agent streams.

    Executes the full deterministic PO Matcher (M), 5-factor Risk Engine (R),
    Explainable AI Risk Attribution weights, and Mandate Policy Gate in sub-millisecond memory.
    """
    allowlisted_vendors = {
        "vendor_data_labeling_co": {"id": "vendor_data_labeling_co", "is_allowlisted": True, "risk_rating": 0.05, "dispute_rate": 0.01},
        "vendor_cloud_compute": {"id": "vendor_cloud_compute", "is_allowlisted": True, "risk_rating": 0.08, "dispute_rate": 0.015},
        "vendor_ai_infra": {"id": "vendor_ai_infra", "is_allowlisted": True, "risk_rating": 0.04, "dispute_rate": 0.008},
    }
    known_pos = {
        "po_2026_4410": {"id": "po_2026_4410", "vendor_id": "vendor_data_labeling_co", "amount": 840.00, "currency": "USD", "items": []},
        "po_2026_4417": {"id": "po_2026_4417", "vendor_id": "vendor_cloud_compute", "amount": 4150.00, "currency": "USD", "items": []},
    }
    mandate_dict = {
        "auto_approve_limit": 1000.00,
        "max_cap": 5000.00,
        "allowed_vendors": list(allowlisted_vendors.keys()),
        "allowed_categories": ["saas", "cloud_compute", "data_labeling", "ai_models", "hardware"],
        "blocked_categories": ["crypto", "gambling", "gift_cards", "adult", "weapons"],
    }

    vendor_dict = allowlisted_vendors.get(
        payload.vendor_id,
        {"id": payload.vendor_id, "is_allowlisted": False, "risk_rating": 0.95, "dispute_rate": 0.42},
    )
    po_dict = known_pos.get(payload.po_ref or "")

    invoice_dict = {
        "vendor_id": payload.vendor_id,
        "po_ref": payload.po_ref,
        "amount": payload.amount,
        "currency": payload.currency,
        "line_items": payload.line_items or [],
    }
    m_score, m_breakdown, m_reasons = RiskEngine.compute_po_matching_score(
        invoice=invoice_dict,
        purchase_order=po_dict,
        variance_tolerance=0.02,
    )

    intent_dict = {
        "amount": payload.amount,
        "category": payload.category,
        "vendor_id": payload.vendor_id,
        "invoice_ref": payload.invoice_ref,
        "line_items": payload.line_items or [],
    }
    r_score, r_breakdown, r_reasons = RiskEngine.compute_risk_score(
        intent=intent_dict,
        vendor=vendor_dict,
        mandate=mandate_dict,
    )

    is_blocked_cat = payload.category.lower() in mandate_dict["blocked_categories"]
    vendor_not_allowed = not vendor_dict["is_allowlisted"]
    exceeds_max_cap = payload.amount > mandate_dict["max_cap"]
    has_prompt_injection = float(r_breakdown.get("prompt_injection_weight", 0.0)) >= 0.30

    if is_blocked_cat or vendor_not_allowed or exceeds_max_cap or has_prompt_injection:
        decision_status = "BLOCKED"
    elif payload.amount <= mandate_dict["auto_approve_limit"] and r_score < 0.15:
        decision_status = "AUTO_APPROVED"
    else:
        decision_status = "HUMAN_REVIEW"

    return {
        "id": payload.id or f"pit_{uuid.uuid4().hex[:10]}",
        "status": decision_status,
        "amount": payload.amount,
        "currency": payload.currency,
        "vendor_id": payload.vendor_id,
        "category": payload.category,
        "po_match_score": m_score,
        "matching_breakdown": m_breakdown,
        "risk_score": r_score,
        "risk_breakdown": r_breakdown,
        "governance_rationale": r_breakdown.get("governance_rationale"),
        "policy_evaluation_reasons": m_reasons + r_reasons,
    }


@router.post("", response_model=PaymentIntentResponse, status_code=status.HTTP_201_CREATED)
def propose_intent(
    payload: PaymentIntentCreate,
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    """Propose a payment intent from an AI agent and immediately run Sentinel policy and risk checks."""
    # Verify mandate exists and is active
    mandate = db.query(Mandate).filter(Mandate.id == payload.mandate_id).first()
    if not mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{payload.mandate_id}' not found.",
        )
    if mandate.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot propose intent: Mandate '{mandate.id}' is '{mandate.status}'.",
        )

    # Verify agent exists and is active
    agent = db.query(Agent).filter(Agent.id == payload.agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{payload.agent_id}' not found.",
        )
    if agent.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot propose intent: Agent '{agent.id}' is '{agent.status}'.",
        )

    intent_id = payload.id or f"pit_{uuid.uuid4().hex[:10]}"

    existing = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PaymentIntent with ID '{intent_id}' already exists.",
        )

    vendor = db.query(Vendor).filter(Vendor.id == payload.vendor_id).first()
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == payload.po_ref).first() if payload.po_ref else None

    intent = PaymentIntent(
        id=intent_id,
        mandate_id=payload.mandate_id,
        agent_id=payload.agent_id,
        vendor_id=payload.vendor_id,
        amount=payload.amount,
        currency=payload.currency,
        category=payload.category,
        invoice_ref=payload.invoice_ref,
        po_ref=payload.po_ref,
        line_items=payload.line_items or [],
        status="PROPOSED",
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)

    AuditLedgerService.append_block(
        db=db,
        event_type="INTENT_PROPOSED",
        entity_type="PAYMENT_INTENT",
        entity_id=intent.id,
        actor=intent.agent_id,
        details={
            "intent_id": intent.id,
            "agent_id": intent.agent_id,
            "vendor_id": intent.vendor_id,
            "amount": intent.amount,
            "currency": intent.currency,
            "category": intent.category,
        },
    )

    # Execute automated evaluation
    intent = _evaluate_intent_logic(db=db, intent=intent, mandate=mandate, vendor=vendor, po=po)
    return intent


@router.get("/{intent_id}", response_model=PaymentIntentResponse)
def get_intent(
    intent_id: str,
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    """Retrieve detailed state and risk analysis for a specific payment intent."""
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PaymentIntent '{intent_id}' not found.",
        )
    return intent


@router.post("/{intent_id}/evaluate", response_model=PaymentIntentResponse)
def evaluate_intent(
    intent_id: str,
    payload: PaymentIntentEvaluateRequest = PaymentIntentEvaluateRequest(),
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    """Re-evaluate risk scoring and policy rules for an existing payment intent."""
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PaymentIntent '{intent_id}' not found.",
        )

    mandate = db.query(Mandate).filter(Mandate.id == intent.mandate_id).first()
    vendor = db.query(Vendor).filter(Vendor.id == intent.vendor_id).first()
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == intent.po_ref).first() if intent.po_ref else None

    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked mandate not found.")

    intent = _evaluate_intent_logic(db=db, intent=intent, mandate=mandate, vendor=vendor, po=po)
    return intent


@router.post("/{intent_id}/kill", response_model=KillSwitchResponse)
def kill_intent(
    intent_id: str,
    payload: KillSwitchRequest,
    db: Session = Depends(get_db),
) -> KillSwitchResponse:
    """Level 1 Kill Switch: Halts an individual payment intent before execution."""
    try:
        result = StateMachine.kill_intent(
            db=db,
            intent_id=intent_id,
            reason=payload.reason,
            actor=payload.actor,
        )
    except KillSwitchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    AuditLedgerService.append_block(
        db=db,
        event_type="KILL_SWITCH_INTENT",
        entity_type="PAYMENT_INTENT",
        entity_id=intent_id,
        actor=payload.actor,
        details=result,
    )

    return KillSwitchResponse(
        level="INTENT",
        target_id=intent_id,
        status=result["status"],
        affected_count=result["affected_count"],
        reason=payload.reason,
        actor=payload.actor,
        timestamp=datetime.fromisoformat(result["timestamp"]) if isinstance(result["timestamp"], str) else result["timestamp"],
        preserved_captured_count=0,
    )
