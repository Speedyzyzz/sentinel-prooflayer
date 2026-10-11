"""PayPal Dispute Command Center & Auto-Defense Submission Router.

Endpoints:
- GET  /api/disputes: List active dispute portfolio with SLA deadlines and Readiness scores.
- GET  /api/disputes/{id}: Retrieve detailed dispute information.
- POST /api/disputes/{id}/submit-defense: Submit cited causal defense package to PayPal Disputes API.
- POST /api/disputes/{id}/resolve: Close and record final dispute outcome.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import DisputeRecord, PaymentIntent, get_db
from app.schemas import DisputeResponse, DisputeSubmitDefenseRequest
from app.services.audit_ledger import AuditLedgerService
from app.services.evidence_compiler import EvidenceCompilerService
from app.services.evidence_graph import CausalGraph
from app.services.paypal_client import PayPalAPIError, PayPalClient
from app.services.state_machine import StateMachine

router = APIRouter(prefix="/disputes", tags=["disputes"])


@router.get("", response_model=List[DisputeResponse])
def list_disputes(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (OPEN, UNDER_REVIEW, EVIDENCE_SUBMITTED, RESOLVED)"),
    db: Session = Depends(get_db),
) -> List[DisputeResponse]:
    """Retrieve dispute portfolio with SLA deadline countdown and evidence readiness scores."""
    query = db.query(DisputeRecord)
    if status_filter:
        query = query.filter(DisputeRecord.status == status_filter.upper())
    records = query.order_by(DisputeRecord.created_at.desc()).all()
    return [DisputeResponse.model_validate(r) for r in records]


@router.get("/{dispute_id}", response_model=DisputeResponse)
def get_dispute(
    dispute_id: str,
    db: Session = Depends(get_db),
) -> DisputeResponse:
    """Retrieve detailed dispute information and evidence submission status."""
    dispute = db.query(DisputeRecord).filter(DisputeRecord.id == dispute_id).first()
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute '{dispute_id}' not found.",
        )
    return DisputeResponse.model_validate(dispute)


@router.post("/{dispute_id}/submit-defense", response_model=DisputeResponse)
def submit_dispute_defense(
    dispute_id: str,
    payload: DisputeSubmitDefenseRequest = DisputeSubmitDefenseRequest(),
    db: Session = Depends(get_db),
) -> DisputeResponse:
    """Submit grounded causal defense package with inline citations to PayPal Disputes API

    and transition lifecycle to EVIDENCE_SUBMITTED.
    """
    dispute = db.query(DisputeRecord).filter(DisputeRecord.id == dispute_id).first()
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute '{dispute_id}' not found.",
        )

    intent = db.query(PaymentIntent).filter(PaymentIntent.id == dispute.intent_id).first()
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Associated PaymentIntent '{dispute.intent_id}' not found.",
        )

    # Hydrate or compile graph
    graph = CausalGraph.from_db(db=db, intent_id=intent.id)
    if not graph.get_nodes():
        from app.routers.evidence import _generate_canonical_18_node_graph
        graph = _generate_canonical_18_node_graph(intent)
        graph.save_to_db(db=db, intent_id=intent.id)

    readiness_score, _ = EvidenceCompilerService.compute_readiness_score(
        graph=graph,
        dispute_reason=dispute.reason,
    )

    narrative, cited_nodes, ev_type, tracking_info = EvidenceCompilerService.compile_grounded_defense_narrative(
        graph=graph,
        dispute_id=dispute.id,
        dispute_reason=dispute.reason,
    )

    # Use explicit override if requested
    evidence_type_to_use = payload.evidence_type or ev_type
    notes_to_use = payload.notes or narrative

    # Call PayPal Disputes API (with Sandbox Twin fallback)
    paypal = PayPalClient()
    try:
        sub_res = paypal.provide_dispute_evidence(
            dispute_id=dispute.id,
            evidence_type=evidence_type_to_use,
            notes=notes_to_use,
            tracking_info=tracking_info,
        )
    except PayPalAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PayPal Dispute API error: {str(exc)}",
        )

    # Transition state machine
    if intent.status in ("RECONCILED", "DISPUTE_OPEN"):
        if intent.status == "RECONCILED":
            StateMachine.transition_intent(db=db, intent=intent, target_state="DISPUTE_OPEN")
        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="EVIDENCE_SUBMITTED",
            reason=f"Evidence package successfully submitted for dispute {dispute.id} (readiness: {readiness_score:.3f})",
        )

    dispute.status = "EVIDENCE_SUBMITTED"
    dispute.readiness_score = readiness_score
    dispute.defense_narrative = notes_to_use
    dispute.evidence_package = {
        "readiness_score": readiness_score,
        "cited_nodes": cited_nodes,
        "paypal_evidence_type": evidence_type_to_use,
        "submission_receipt": sub_res,
    }
    dispute.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(dispute)

    AuditLedgerService.append_block(
        db=db,
        event_type="DISPUTE_DEFENSE_SUBMITTED",
        entity_type="DISPUTE",
        entity_id=dispute.id,
        actor="prooflayer_auto_defense",
        details={
            "dispute_id": dispute.id,
            "intent_id": intent.id,
            "readiness_score": readiness_score,
            "evidence_type": evidence_type_to_use,
            "cited_nodes": cited_nodes,
        },
    )

    return DisputeResponse.model_validate(dispute)


@router.post("/{dispute_id}/resolve", response_model=DisputeResponse)
def resolve_dispute(
    dispute_id: str,
    outcome: str = Query("RESOLVED_SELLER", description="Outcome (RESOLVED_SELLER, RESOLVED_BUYER)"),
    db: Session = Depends(get_db),
) -> DisputeResponse:
    """Close dispute and record final resolution status."""
    dispute = db.query(DisputeRecord).filter(DisputeRecord.id == dispute_id).first()
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute '{dispute_id}' not found.",
        )

    intent = db.query(PaymentIntent).filter(PaymentIntent.id == dispute.intent_id).first()
    if intent and intent.status == "EVIDENCE_SUBMITTED":
        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="RESOLVED",
            reason=f"Dispute {dispute.id} closed with outcome {outcome}",
        )

    dispute.status = outcome.upper()
    dispute.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(dispute)

    AuditLedgerService.append_block(
        db=db,
        event_type="DISPUTE_RESOLVED",
        entity_type="DISPUTE",
        entity_id=dispute.id,
        actor="system",
        details={"dispute_id": dispute.id, "outcome": outcome},
    )

    return DisputeResponse.model_validate(dispute)
