"""Payment Execution & Settlement Ledger Router for Sentinel Control Plane.

Endpoints:
- POST /api/payments/execute: Execute approved payment intent through PayPal Orders v2 with atomic idempotency.
- GET  /api/payments: List settled transaction records.
- GET  /api/payments/{id}: Retrieve detailed transaction receipt.
- POST /api/payments/agent/{agent_id}/kill: Level 2 Kill Switch - revokes agent and cancels all uncaptured proposals.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import PaymentIntent, TransactionRecord, get_db
from app.schemas import (
    KillSwitchRequest,
    KillSwitchResponse,
    PaymentExecuteRequest,
    PaymentExecuteResponse,
    TransactionResponse,
)
from app.services.audit_ledger import AuditLedgerService
from app.services.paypal_client import PayPalAPIError, PayPalClient
from app.services.state_machine import (
    InvalidStateTransitionError,
    KillSwitchError,
    StateMachine,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/execute", response_model=PaymentExecuteResponse)
def execute_payment(
    payload: PaymentExecuteRequest,
    db: Session = Depends(get_db),
) -> PaymentExecuteResponse:
    """Execute an approved payment intent via PayPal Orders v2 (Authorize -> Capture)

    guaranteeing strict idempotency via idempotency_key and PayPal-Request-Id.
    """
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payload.intent_id).first()
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PaymentIntent '{payload.intent_id}' not found.",
        )

    # 1. Idempotency Lock Check: Replay detection
    existing_tx = (
        db.query(TransactionRecord)
        .filter(TransactionRecord.intent_id == intent.id)
        .order_by(TransactionRecord.created_at.desc())
        .first()
    )

    if intent.status == "RECONCILED" and existing_tx:
        return PaymentExecuteResponse(
            intent_id=intent.id,
            status="RECONCILED",
            paypal_order_id=existing_tx.paypal_order_id,
            paypal_capture_id=existing_tx.paypal_capture_id,
            amount=existing_tx.amount,
            currency=existing_tx.currency,
            idempotency_key=intent.idempotency_key or payload.idempotency_key,
            cached_replay=True,
            reconciled_at=existing_tx.created_at,
        )

    # 2. Status Validation: must be AUTO_APPROVED or APPROVED
    if intent.status not in ("AUTO_APPROVED", "APPROVED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot execute payment for intent in '{intent.status}' state. Must be AUTO_APPROVED or APPROVED.",
        )

    # Lock idempotency key
    intent.idempotency_key = payload.idempotency_key

    # 3. Transition to EXECUTING
    try:
        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="EXECUTING",
            reason=f"Initiating PayPal Orders v2 execution with key {payload.idempotency_key}",
            context={"idempotency_key": payload.idempotency_key},
        )
    except InvalidStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # 4. PayPal API Execution
    paypal = PayPalClient()
    try:
        # Step A: Create Order
        order_res = paypal.create_order(
            amount=intent.amount,
            currency=intent.currency,
            reference_id=intent.po_ref or intent.id,
            description=f"Sentinel Settlement for Intent {intent.id}",
            idempotency_key=f"order_{payload.idempotency_key}",
            intent="AUTHORIZE",
        )
        paypal_order_id = order_res.get("id", f"ORD-TWIN-{intent.id}")
        intent.paypal_order_id = paypal_order_id
        db.commit()

        # Step B: Authorize Order
        auth_res = paypal.authorize_order(
            order_id=paypal_order_id,
            idempotency_key=f"auth_{payload.idempotency_key}",
        )
        auth_id = ""
        try:
            pu_payments = auth_res.get("purchase_units", [{}])[0].get("payments", {})
            authorizations = pu_payments.get("authorizations", [{}])
            auth_id = authorizations[0].get("id", "")
        except Exception:
            auth_id = f"AUTH-TWIN-{paypal_order_id}"

        if not auth_id:
            auth_id = f"AUTH-TWIN-{paypal_order_id}"

        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="AUTHORIZED",
            reason=f"Authorized PayPal order {paypal_order_id} (auth: {auth_id})",
        )

        # Step C: Capture Authorization
        cap_res = paypal.capture_authorization(
            authorization_id=auth_id,
            idempotency_key=f"cap_{payload.idempotency_key}",
        )
        capture_id = cap_res.get("id", f"CAP-TWIN-{auth_id}")
        intent.paypal_capture_id = capture_id

        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="CAPTURED",
            reason=f"Captured funds from authorization {auth_id} (capture: {capture_id})",
        )

        # Step D: Record Reconciled Transaction
        tx_id = f"tx_{uuid.uuid4().hex[:10]}"
        tx_record = TransactionRecord(
            id=tx_id,
            intent_id=intent.id,
            amount=intent.amount,
            currency=intent.currency,
            paypal_order_id=paypal_order_id,
            paypal_capture_id=capture_id,
            status="RECONCILED",
            raw_response={
                "order": order_res,
                "authorization": auth_res,
                "capture": cap_res,
            },
            created_at=datetime.utcnow(),
        )
        db.add(tx_record)

        # Step E: Transition to RECONCILED
        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="RECONCILED",
            reason=f"Payment reconciled with capture receipt {capture_id}",
        )

        AuditLedgerService.append_block(
            db=db,
            event_type="PAYMENT_RECONCILED",
            entity_type="TRANSACTION",
            entity_id=tx_id,
            actor="sentinel_payments_worker",
            details={
                "transaction_id": tx_id,
                "intent_id": intent.id,
                "amount": intent.amount,
                "paypal_order_id": paypal_order_id,
                "paypal_capture_id": capture_id,
                "idempotency_key": payload.idempotency_key,
            },
        )

        return PaymentExecuteResponse(
            intent_id=intent.id,
            status="RECONCILED",
            paypal_order_id=paypal_order_id,
            paypal_capture_id=capture_id,
            amount=intent.amount,
            currency=intent.currency,
            idempotency_key=payload.idempotency_key,
            cached_replay=False,
            reconciled_at=tx_record.created_at,
        )

    except PayPalAPIError as exc:
        StateMachine.transition_intent(
            db=db,
            intent=intent,
            target_state="BLOCKED",
            reason=f"PayPal API error: {str(exc)}",
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PayPal API execution error: {str(exc)}",
        )


@router.get("", response_model=List[TransactionResponse])
def list_payments(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[TransactionResponse]:
    """List settled and reconciled transaction records."""
    records = (
        db.query(TransactionRecord)
        .order_by(TransactionRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [TransactionResponse.model_validate(r) for r in records]


@router.get("/{payment_id}", response_model=TransactionResponse)
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """Retrieve detailed transaction receipt by transaction ID or intent ID."""
    record = (
        db.query(TransactionRecord)
        .filter((TransactionRecord.id == payment_id) | (TransactionRecord.intent_id == payment_id))
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{payment_id}' not found.",
        )
    return TransactionResponse.model_validate(record)


@router.post("/agent/{agent_id}/kill", response_model=KillSwitchResponse)
def kill_agent(
    agent_id: str,
    payload: KillSwitchRequest,
    db: Session = Depends(get_db),
) -> KillSwitchResponse:
    """Level 2 Kill Switch: Revokes agent ID and immediately cancels all in-flight uncaptured intents."""
    try:
        result = StateMachine.kill_agent(
            db=db,
            agent_id=agent_id,
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
        event_type="KILL_SWITCH_AGENT",
        entity_type="AGENT",
        entity_id=agent_id,
        actor=payload.actor,
        details=result,
    )

    return KillSwitchResponse(
        level="AGENT",
        target_id=agent_id,
        status=result["status"],
        affected_count=result["affected_count"],
        reason=payload.reason,
        actor=payload.actor,
        timestamp=datetime.fromisoformat(result["timestamp"]) if isinstance(result["timestamp"], str) else result["timestamp"],
        preserved_captured_count=0,
    )
