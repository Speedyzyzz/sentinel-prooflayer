"""Approval Queue & Human Review Governance Router for Sentinel Control Plane.

Endpoints:
- GET  /api/approvals: List all payment intents parked in HUMAN_REVIEW queue.
- GET  /api/approvals/{id}: Retrieve full approval context (intent, vendor, PO, mandate, history).
- POST /api/approvals/{intent_id}/approve: Authorize payment intent subject to approver limits and idempotency lock.
- POST /api/approvals/{intent_id}/reject: Reject payment intent and transition status to BLOCKED.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import (
    ApprovalRecord,
    Mandate,
    PaymentIntent,
    PurchaseOrder,
    User,
    Vendor,
    get_db,
)
from app.schemas import (
    ApprovalActionRequest,
    ApprovalDetailResponse,
    ApprovalQueueItem,
    ApprovalResponse,
    MandateResponse,
    PaymentIntentResponse,
    PurchaseOrderResponse,
    VendorResponse,
)
from app.services.audit_ledger import AuditLedgerService
from app.services.state_machine import InvalidStateTransitionError, StateMachine

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=List[ApprovalQueueItem])
def list_pending_approvals(db: Session = Depends(get_db)) -> List[ApprovalQueueItem]:
    """Retrieve all payment intents currently parked in the HUMAN_REVIEW queue."""
    pending_intents = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.status == "HUMAN_REVIEW")
        .order_by(PaymentIntent.created_at.desc())
        .all()
    )

    items: List[ApprovalQueueItem] = []
    for intent in pending_intents:
        vendor = db.query(Vendor).filter(Vendor.id == intent.vendor_id).first()
        vendor_name = vendor.name if vendor else intent.vendor_id

        items.append(
            ApprovalQueueItem(
                intent_id=intent.id,
                agent_id=intent.agent_id,
                vendor_id=intent.vendor_id,
                vendor_name=vendor_name,
                amount=intent.amount,
                currency=intent.currency,
                category=intent.category,
                invoice_ref=intent.invoice_ref,
                po_ref=intent.po_ref,
                po_match_score=intent.po_match_score,
                risk_score=intent.risk_score,
                risk_breakdown=intent.risk_breakdown,
                policy_evaluation_reasons=intent.policy_evaluation_reasons or [],
                created_at=intent.created_at,
            )
        )
    return items


@router.get("/{intent_id}", response_model=ApprovalDetailResponse)
def get_approval_detail(
    intent_id: str,
    db: Session = Depends(get_db),
) -> ApprovalDetailResponse:
    """Retrieve complete context for human approval inspection: intent, PO, vendor, and mandate."""
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PaymentIntent '{intent_id}' not found.",
        )

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == intent.po_ref).first() if intent.po_ref else None
    vendor = db.query(Vendor).filter(Vendor.id == intent.vendor_id).first()
    mandate = db.query(Mandate).filter(Mandate.id == intent.mandate_id).first()
    approvals = (
        db.query(ApprovalRecord)
        .filter(ApprovalRecord.intent_id == intent_id)
        .order_by(ApprovalRecord.created_at.asc())
        .all()
    )

    return ApprovalDetailResponse(
        intent=PaymentIntentResponse.model_validate(intent),
        purchase_order=PurchaseOrderResponse.model_validate(po) if po else None,
        vendor=VendorResponse.model_validate(vendor) if vendor else None,
        mandate=MandateResponse.model_validate(mandate) if mandate else None,
        prior_approvals=[
            ApprovalResponse(
                id=a.id,
                intent_id=a.intent_id,
                approver_id=a.approver_id,
                decision=a.decision,
                notes=a.notes,
                created_at=a.created_at,
                intent_status=intent.status,
            )
            for a in approvals
        ],
    )


@router.post("/{intent_id}/approve", response_model=ApprovalResponse)
def approve_intent(
    intent_id: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    """Authorize a human-review payment intent with role authority limit checks and idempotency lock."""
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PaymentIntent '{intent_id}' not found.",
        )

    # Replay check: already approved with same idempotency key
    if intent.status in ("APPROVED", "EXECUTING", "AUTHORIZED", "CAPTURED", "RECONCILED"):
        last_rec = (
            db.query(ApprovalRecord)
            .filter(ApprovalRecord.intent_id == intent_id, ApprovalRecord.decision == "APPROVED")
            .order_by(ApprovalRecord.created_at.desc())
            .first()
        )
        if last_rec:
            return ApprovalResponse(
                id=last_rec.id,
                intent_id=intent.id,
                approver_id=last_rec.approver_id,
                decision="APPROVED",
                notes=last_rec.notes,
                created_at=last_rec.created_at,
                intent_status=intent.status,
            )

    if intent.status != "HUMAN_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PaymentIntent '{intent_id}' is in status '{intent.status}', cannot approve.",
        )

    approver = db.query(User).filter(User.id == payload.approver_id).first()
    if not approver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approver User '{payload.approver_id}' not found.",
        )

    # Validate approver spending limit
    if intent.amount > approver.approval_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Amount ${intent.amount:,.2f} exceeds user approval limit ${approver.approval_limit:,.2f}.",
        )

    # Lock idempotency key
    idem_key = payload.idempotency_key or f"idem_{approver.id}_{intent.id}"
    if payload.idempotency_key:
        other_intent = db.query(PaymentIntent).filter(
            PaymentIntent.idempotency_key == payload.idempotency_key,
            PaymentIntent.id != intent.id,
        ).first()
        if other_intent:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency key '{payload.idempotency_key}' is already bound to intent '{other_intent.id}'.",
            )
    intent.idempotency_key = idem_key

    approval_id = f"app_{uuid.uuid4().hex[:8]}"
    approval_rec = ApprovalRecord(
        id=approval_id,
        intent_id=intent.id,
        approver_id=approver.id,
        decision="APPROVED",
        notes=payload.notes or f"Approved by {approver.name} ({approver.role})",
        created_at=datetime.utcnow(),
    )
    db.add(approval_rec)

    try:
        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="APPROVED",
            reason=f"Approved by {approver.name} ({approver.role}) - ${intent.amount:,.2f}",
            context={"approver_id": approver.id, "idempotency_key": idem_key},
        )
    except InvalidStateTransitionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    AuditLedgerService.append_block(
        db=db,
        event_type="APPROVAL_GRANTED",
        entity_type="APPROVAL_RECORD",
        entity_id=approval_id,
        actor=approver.id,
        details={
            "approval_id": approval_id,
            "intent_id": intent.id,
            "approver_id": approver.id,
            "approver_role": approver.role,
            "amount": intent.amount,
            "idempotency_key": idem_key,
        },
    )

    return ApprovalResponse(
        id=approval_id,
        intent_id=intent.id,
        approver_id=approver.id,
        decision="APPROVED",
        notes=approval_rec.notes,
        created_at=approval_rec.created_at,
        intent_status=intent.status,
    )


@router.post("/{intent_id}/reject", response_model=ApprovalResponse)
def reject_intent(
    intent_id: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    """Reject a payment intent in HUMAN_REVIEW and transition to BLOCKED."""
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PaymentIntent '{intent_id}' not found.",
        )

    if intent.status != "HUMAN_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PaymentIntent '{intent_id}' is in status '{intent.status}', cannot reject.",
        )

    approver = db.query(User).filter(User.id == payload.approver_id).first()
    if not approver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approver User '{payload.approver_id}' not found.",
        )

    approval_id = f"app_{uuid.uuid4().hex[:8]}"
    approval_rec = ApprovalRecord(
        id=approval_id,
        intent_id=intent.id,
        approver_id=approver.id,
        decision="REJECTED",
        notes=payload.notes or f"Rejected by {approver.name} ({approver.role})",
        created_at=datetime.utcnow(),
    )
    db.add(approval_rec)

    try:
        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="BLOCKED",
            reason=f"Rejected by {approver.name}: {payload.notes or 'No reason provided'}",
        )
    except InvalidStateTransitionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    AuditLedgerService.append_block(
        db=db,
        event_type="APPROVAL_REJECTED",
        entity_type="APPROVAL_RECORD",
        entity_id=approval_id,
        actor=approver.id,
        details={
            "approval_id": approval_id,
            "intent_id": intent.id,
            "approver_id": approver.id,
            "approver_role": approver.role,
            "amount": intent.amount,
            "notes": payload.notes,
        },
    )

    return ApprovalResponse(
        id=approval_id,
        intent_id=intent.id,
        approver_id=approver.id,
        decision="REJECTED",
        notes=approval_rec.notes,
        created_at=approval_rec.created_at,
        intent_status=intent.status,
    )
