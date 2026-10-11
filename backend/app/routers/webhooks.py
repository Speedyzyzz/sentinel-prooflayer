"""PayPal Webhook Receiver & Replay Deduplication Router.

Endpoints:
- POST /api/webhooks/paypal: Ingest incoming PayPal webhooks, verify cryptographic/Twin signatures,
  deduplicate event_ids, and trigger dispute lifecycle transitions.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import (
    DisputeRecord,
    PaymentIntent,
    TransactionRecord,
    WebhookEvent,
    get_db,
)
from app.schemas import WebhookResponse
from app.services.audit_ledger import AuditLedgerService
from app.services.paypal_client import PayPalClient
from app.services.state_machine import StateMachine

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/paypal", response_model=WebhookResponse)
async def handle_paypal_webhook(
    request: Request,
    paypal_transmission_id: Optional[str] = Header(None, alias="paypal-transmission-id"),
    paypal_transmission_time: Optional[str] = Header(None, alias="paypal-transmission-time"),
    paypal_transmission_sig: Optional[str] = Header(None, alias="paypal-transmission-sig"),
    paypal_cert_url: Optional[str] = Header(None, alias="paypal-cert-url"),
    paypal_auth_algo: Optional[str] = Header(None, alias="paypal-auth-algo"),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    """Ingest PayPal webhooks, verify signature, deduplicate on event_id, and transition state."""
    try:
        body_json: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    event_id = str(body_json.get("id") or paypal_transmission_id or "").strip()
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing webhook event ID in payload or transmission headers.",
        )

    event_type = str(body_json.get("event_type", "UNKNOWN")).strip()
    resource_type = str(body_json.get("resource_type", "dispute")).strip()
    resource = body_json.get("resource", {})

    # 1. Signature Verification
    paypal = PayPalClient()
    webhook_id = "WH-SENTINEL-PROOFLAYER-SANDBOX"
    if paypal_transmission_id and paypal_transmission_sig:
        is_valid = paypal.verify_webhook_signature(
            transmission_id=paypal_transmission_id,
            transmission_time=paypal_transmission_time or "",
            transmission_sig=paypal_transmission_sig,
            cert_url=paypal_cert_url or "",
            auth_algo=paypal_auth_algo or "",
            webhook_id=webhook_id,
            webhook_event=body_json,
        )
        if not is_valid and not paypal.is_twin_mode:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="PayPal webhook signature verification failed.",
            )

    # 2. Replay Deduplication: If already seen, return HTTP 200 ignored
    existing_evt = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if existing_evt:
        return WebhookResponse(
            status="ignored",
            event_id=event_id,
            event_type=event_type,
            processed=False,
            duplicate=True,
            message="Duplicate event_id detected. Event safely ignored with zero duplicate side effects.",
        )

    # 3. Record Webhook Event for idempotency
    resource_id = str(resource.get("dispute_id") or resource.get("id") or "res_unknown")
    webhook_rec = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=body_json.get("summary", f"Received {event_type}"),
        status="PROCESSED",
        received_at=datetime.utcnow(),
    )
    db.add(webhook_rec)
    db.commit()

    # 4. Handle Dispute Created Event
    if event_type in ("CUSTOMER.DISPUTE.CREATED", "CUSTOMER.DISPUTE.UPDATED"):
        dispute_id = str(resource.get("dispute_id") or resource.get("id", "PP-D-99412"))
        dispute_amount_val = 0.0
        currency = "USD"
        if "dispute_amount" in resource:
            dispute_amount_val = float(resource["dispute_amount"].get("value", 0.0))
            currency = resource["dispute_amount"].get("currency_code", "USD")

        dispute_reason = str(resource.get("reason", "ITEM_NOT_RECEIVED"))

        # Find target payment intent / transaction
        # Check by dispute transaction id, order id, or capture id
        disputed_txs = resource.get("disputed_transactions", [])
        target_tx: Optional[TransactionRecord] = None
        target_intent: Optional[PaymentIntent] = None

        if disputed_txs:
            first_tx = disputed_txs[0]
            seller_tx_id = first_tx.get("seller_transaction_id")
            if seller_tx_id:
                target_tx = (
                    db.query(TransactionRecord)
                    .filter(
                        (TransactionRecord.id == seller_tx_id)
                        | (TransactionRecord.paypal_capture_id == seller_tx_id)
                        | (TransactionRecord.paypal_order_id == seller_tx_id)
                    )
                    .first()
                )

        if not target_tx:
            # Fallback: look for latest reconciled payment intent matching the amount or any reconciled intent
            if dispute_amount_val > 0:
                target_intent = (
                    db.query(PaymentIntent)
                    .filter(PaymentIntent.status == "RECONCILED", PaymentIntent.amount == dispute_amount_val)
                    .order_by(PaymentIntent.created_at.desc())
                    .first()
                )
            if not target_intent:
                target_intent = (
                    db.query(PaymentIntent)
                    .filter(PaymentIntent.status == "RECONCILED")
                    .order_by(PaymentIntent.created_at.desc())
                    .first()
                )
            if target_intent:
                target_tx = (
                    db.query(TransactionRecord)
                    .filter(TransactionRecord.intent_id == target_intent.id)
                    .first()
                )
        else:
            target_intent = db.query(PaymentIntent).filter(PaymentIntent.id == target_tx.intent_id).first()

        # If found, transition state machine
        if target_intent:
            if target_intent.status == "RECONCILED":
                StateMachine.transition_intent(
                    db=db,
                    intent=target_intent,
                    target_state="DISPUTE_OPEN",
                    reason=f"Inbound dispute {dispute_id} for reason {dispute_reason}",
                )

            # Record or update DisputeRecord
            existing_dispute = db.query(DisputeRecord).filter(DisputeRecord.id == dispute_id).first()
            if not existing_dispute:
                new_dispute = DisputeRecord(
                    id=dispute_id,
                    transaction_id=target_tx.id if target_tx else None,
                    intent_id=target_intent.id,
                    amount=dispute_amount_val or target_intent.amount,
                    currency=currency or target_intent.currency,
                    reason=dispute_reason,
                    status="OPEN",
                    sla_deadline=datetime.utcnow() + timedelta(days=10),
                )
                db.add(new_dispute)
                db.commit()

            AuditLedgerService.append_block(
                db=db,
                event_type="DISPUTE_OPENED",
                entity_type="DISPUTE",
                entity_id=dispute_id,
                actor="paypal_webhook",
                details={
                    "event_id": event_id,
                    "dispute_id": dispute_id,
                    "intent_id": target_intent.id,
                    "amount": dispute_amount_val or target_intent.amount,
                    "reason": dispute_reason,
                },
            )

    return WebhookResponse(
        status="success",
        event_id=event_id,
        event_type=event_type,
        processed=True,
        duplicate=False,
        message=f"Webhook event '{event_type}' processed successfully.",
    )
