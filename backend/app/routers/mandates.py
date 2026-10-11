"""Mandate Governance Router for Sentinel Control Plane.

Endpoints:
- GET  /api/mandates: List governance mandates with optional org/agent/status filters.
- POST /api/mandates: Register new governance mandate with spend caps.
- GET  /api/mandates/{id}: Retrieve detailed mandate configuration.
- PUT  /api/mandates/{id}: Update mandate parameters and increment version.
- POST /api/mandates/{id}/activate: Activate an inactive mandate.
- POST /api/mandates/{id}/deactivate: Deactivate an active mandate.
- POST /api/mandates/{id}/kill: Level 3 Kill Switch - freezes mandate, aborts uncaptured authorizations, preserves captured payments.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import Mandate, get_db
from app.schemas import (
    KillSwitchRequest,
    KillSwitchResponse,
    MandateCreate,
    MandateResponse,
    MandateUpdate,
)
from app.services.audit_ledger import AuditLedgerService
from app.services.state_machine import KillSwitchError, StateMachine

router = APIRouter(prefix="/mandates", tags=["mandates"])


@router.get("", response_model=List[MandateResponse])
def list_mandates(
    org_id: Optional[str] = Query(None, description="Filter by organization ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (ACTIVE, FROZEN, INACTIVE)"),
    db: Session = Depends(get_db),
) -> List[MandateResponse]:
    """Retrieve all corporate spend governance mandates matching optional query criteria."""
    query = db.query(Mandate)
    if org_id:
        query = query.filter(Mandate.org_id == org_id)
    if agent_id:
        query = query.filter(Mandate.agent_id == agent_id)
    if status_filter:
        query = query.filter(Mandate.status == status_filter.upper())
    return query.order_by(Mandate.created_at.desc()).all()


@router.post("", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
def create_mandate(
    payload: MandateCreate,
    db: Session = Depends(get_db),
) -> MandateResponse:
    """Create a new corporate spend governance mandate."""
    if payload.auto_approve_limit > payload.max_cap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auto-approve limit (${payload.auto_approve_limit:,.2f}) cannot exceed max cap (${payload.max_cap:,.2f}).",
        )

    existing = db.query(Mandate).filter(Mandate.id == payload.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mandate with ID '{payload.id}' already exists.",
        )

    mandate = Mandate(
        id=payload.id,
        org_id=payload.org_id,
        agent_id=payload.agent_id,
        name=payload.name,
        description=payload.description,
        auto_approve_limit=payload.auto_approve_limit,
        max_cap=payload.max_cap,
        po_variance_limit=payload.po_variance_limit,
        allowed_categories=payload.allowed_categories,
        blocked_categories=payload.blocked_categories,
        allowed_vendors=payload.allowed_vendors,
        cel_rules=payload.cel_rules,
        status=payload.status,
        version=payload.version,
    )
    db.add(mandate)
    db.commit()
    db.refresh(mandate)

    AuditLedgerService.append_block(
        db=db,
        event_type="MANDATE_CREATED",
        entity_type="MANDATE",
        entity_id=mandate.id,
        actor="system",
        details={
            "mandate_id": mandate.id,
            "org_id": mandate.org_id,
            "agent_id": mandate.agent_id,
            "auto_approve_limit": mandate.auto_approve_limit,
            "max_cap": mandate.max_cap,
            "status": mandate.status,
        },
    )

    return mandate


@router.get("/{mandate_id}", response_model=MandateResponse)
def get_mandate(
    mandate_id: str,
    db: Session = Depends(get_db),
) -> MandateResponse:
    """Fetch details of a single governance mandate by identifier."""
    mandate = db.query(Mandate).filter(Mandate.id == mandate_id).first()
    if not mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{mandate_id}' not found.",
        )
    return mandate


@router.put("/{mandate_id}", response_model=MandateResponse)
def update_mandate(
    mandate_id: str,
    payload: MandateUpdate,
    db: Session = Depends(get_db),
) -> MandateResponse:
    """Update mandate rules, spend limits, or status; automatically increments version."""
    mandate = db.query(Mandate).filter(Mandate.id == mandate_id).first()
    if not mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{mandate_id}' not found.",
        )

    auto_lim = payload.auto_approve_limit if payload.auto_approve_limit is not None else mandate.auto_approve_limit
    max_cap = payload.max_cap if payload.max_cap is not None else mandate.max_cap
    if auto_lim > max_cap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auto-approve limit (${auto_lim:,.2f}) cannot exceed max cap (${max_cap:,.2f}).",
        )

    if payload.name is not None:
        mandate.name = payload.name
    if payload.description is not None:
        mandate.description = payload.description
    if payload.auto_approve_limit is not None:
        mandate.auto_approve_limit = payload.auto_approve_limit
    if payload.max_cap is not None:
        mandate.max_cap = payload.max_cap
    if payload.po_variance_limit is not None:
        mandate.po_variance_limit = payload.po_variance_limit
    if payload.allowed_categories is not None:
        mandate.allowed_categories = payload.allowed_categories
    if payload.blocked_categories is not None:
        mandate.blocked_categories = payload.blocked_categories
    if payload.allowed_vendors is not None:
        mandate.allowed_vendors = payload.allowed_vendors
    if payload.cel_rules is not None:
        mandate.cel_rules = payload.cel_rules
    if payload.status is not None:
        mandate.status = payload.status

    mandate.version += 1
    mandate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(mandate)

    AuditLedgerService.append_block(
        db=db,
        event_type="MANDATE_UPDATED",
        entity_type="MANDATE",
        entity_id=mandate.id,
        actor="system",
        details={
            "mandate_id": mandate.id,
            "new_version": mandate.version,
            "status": mandate.status,
            "auto_approve_limit": mandate.auto_approve_limit,
            "max_cap": mandate.max_cap,
        },
    )

    return mandate


@router.post("/{mandate_id}/activate", response_model=MandateResponse)
def activate_mandate(
    mandate_id: str,
    db: Session = Depends(get_db),
) -> MandateResponse:
    """Transition mandate to ACTIVE status."""
    mandate = db.query(Mandate).filter(Mandate.id == mandate_id).first()
    if not mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{mandate_id}' not found.",
        )
    mandate.status = "ACTIVE"
    mandate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(mandate)

    AuditLedgerService.append_block(
        db=db,
        event_type="MANDATE_ACTIVATED",
        entity_type="MANDATE",
        entity_id=mandate.id,
        actor="system",
        details={"mandate_id": mandate.id, "status": "ACTIVE"},
    )
    return mandate


@router.post("/{mandate_id}/deactivate", response_model=MandateResponse)
def deactivate_mandate(
    mandate_id: str,
    db: Session = Depends(get_db),
) -> MandateResponse:
    """Transition mandate to INACTIVE status."""
    mandate = db.query(Mandate).filter(Mandate.id == mandate_id).first()
    if not mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{mandate_id}' not found.",
        )
    mandate.status = "INACTIVE"
    mandate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(mandate)

    AuditLedgerService.append_block(
        db=db,
        event_type="MANDATE_DEACTIVATED",
        entity_type="MANDATE",
        entity_id=mandate.id,
        actor="system",
        details={"mandate_id": mandate.id, "status": "INACTIVE"},
    )
    return mandate


@router.post("/{mandate_id}/kill", response_model=KillSwitchResponse)
def kill_mandate(
    mandate_id: str,
    payload: KillSwitchRequest,
    db: Session = Depends(get_db),
) -> KillSwitchResponse:
    """Level 3 Kill Switch: Freezes mandate, aborts uncaptured authorizations,

    while strictly preserving already-captured and reconciled payments.
    """
    try:
        result = StateMachine.kill_mandate(
            db=db,
            mandate_id=mandate_id,
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
        event_type="KILL_SWITCH_MANDATE",
        entity_type="MANDATE",
        entity_id=mandate_id,
        actor=payload.actor,
        details=result,
    )

    return KillSwitchResponse(
        level="MANDATE",
        target_id=mandate_id,
        status=result["status"],
        affected_count=result["affected_count"],
        reason=payload.reason,
        actor=payload.actor,
        timestamp=datetime.fromisoformat(result["timestamp"]) if isinstance(result["timestamp"], str) else result["timestamp"],
        preserved_captured_count=result.get("preserved_captured_count", 0),
    )
