"""Canonical 12-State Lifecycle Engine & 3-Tier Granular Kill Switch.

Enforces:
1. Canonical lifecycle transitions with strict guard preconditions:
   PROPOSED -> POLICY_CHECK -> EVIDENCE_VALIDATION
   -> (AUTO_APPROVED | HUMAN_REVIEW | BLOCKED | EXPIRED)
   -> APPROVED -> EXECUTING -> AUTHORIZED -> CAPTURED -> RECONCILED
   -> DISPUTE_OPEN -> EVIDENCE_SUBMITTED -> RESOLVED

2. 3-Tier Kill Switch blast-radius containment:
   Level 1 (INTENT): Halts single intent before capture.
   Level 2 (AGENT): Revokes agent ID, blocks in-flight and future proposals.
   Level 3 (MANDATE): Freezes mandate boundary, voids uncaptured authorizations,
   STRICTLY preserves already-CAPTURED and RECONCILED transactions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.database import Agent, Mandate, PaymentIntent, User


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""
    def __init__(self, message: str):
        super().__init__(message)


class KillSwitchError(Exception):
    """Raised when a kill switch operation violates system invariants."""
    def __init__(self, message: str):
        super().__init__(message)


class StateMachine:
    """State transition validator and kill-switch manager for payment intents."""

    CANONICAL_STATES: Set[str] = {
        "PROPOSED",
        "POLICY_CHECK",
        "EVIDENCE_VALIDATION",
        "AUTO_APPROVED",
        "HUMAN_REVIEW",
        "BLOCKED",
        "EXPIRED",
        "APPROVED",
        "EXECUTING",
        "AUTHORIZED",
        "CAPTURED",
        "RECONCILED",
        "DISPUTE_OPEN",
        "EVIDENCE_SUBMITTED",
        "RESOLVED",
    }

    # Allowed transitions map: Source State -> Set of Allowed Target States
    TRANSITION_MATRIX: Dict[str, Set[str]] = {
        "PROPOSED": {"POLICY_CHECK", "BLOCKED"},
        "POLICY_CHECK": {"EVIDENCE_VALIDATION", "BLOCKED"},
        "EVIDENCE_VALIDATION": {"AUTO_APPROVED", "HUMAN_REVIEW", "BLOCKED"},
        "AUTO_APPROVED": {"EXECUTING", "BLOCKED"},
        "HUMAN_REVIEW": {"APPROVED", "BLOCKED", "EXPIRED"},
        "APPROVED": {"EXECUTING", "BLOCKED"},
        "EXECUTING": {"AUTHORIZED", "BLOCKED"},
        "AUTHORIZED": {"CAPTURED", "BLOCKED"},
        "CAPTURED": {"RECONCILED", "DISPUTE_OPEN"},
        "RECONCILED": {"DISPUTE_OPEN"},
        "DISPUTE_OPEN": {"EVIDENCE_SUBMITTED", "RESOLVED"},
        "EVIDENCE_SUBMITTED": {"RESOLVED"},
        "BLOCKED": set(),  # Terminal state
        "EXPIRED": {"PROPOSED"},  # Expired requires re-proposal, cannot transition directly to APPROVED
        "RESOLVED": set(),  # Terminal state
    }

    @classmethod
    def can_transition(cls, current_state: str, target_state: str) -> bool:
        """Check if transition from current_state to target_state is legally allowed."""
        if current_state not in cls.CANONICAL_STATES or target_state not in cls.CANONICAL_STATES:
            return False
        return target_state in cls.TRANSITION_MATRIX.get(current_state, set())

    @classmethod
    def transition_intent(
        cls,
        db: Session,
        intent: PaymentIntent,
        target_state: str,
        reason: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PaymentIntent:
        """Execute state transition on a payment intent with strict guard validation."""
        current_state = intent.status

        # Self-transition is a no-op
        if current_state == target_state:
            return intent

        if not cls.can_transition(current_state, target_state):
            raise InvalidStateTransitionError(
                f"Cannot transition PaymentIntent '{intent.id}' from '{current_state}' to '{target_state}'. "
                f"Allowed targets: {cls.TRANSITION_MATRIX.get(current_state, set())}"
            )

        ctx = context or {}

        # Guard: Check human approval authority limits
        if current_state == "HUMAN_REVIEW" and target_state == "APPROVED":
            approver_id = ctx.get("approver_id")
            if approver_id:
                approver = db.query(User).filter(User.id == approver_id).first()
                if approver and approver.approval_limit < intent.amount:
                    raise InvalidStateTransitionError(
                        f"Amount ${intent.amount:,.2f} exceeds approver '{approver.id}' limit of ${approver.approval_limit:,.2f}."
                    )

        # Guard: Executing requires idempotency key
        if target_state == "EXECUTING":
            if not intent.idempotency_key and not ctx.get("idempotency_key"):
                raise InvalidStateTransitionError("Transition to EXECUTING requires an active idempotency_key.")
            if ctx.get("idempotency_key") and not intent.idempotency_key:
                intent.idempotency_key = ctx["idempotency_key"]

        # Apply transition
        intent.status = target_state
        intent.updated_at = datetime.utcnow()

        if reason:
            existing_reasons = intent.policy_evaluation_reasons or []
            if isinstance(existing_reasons, list):
                existing_reasons.append(reason)
                intent.policy_evaluation_reasons = existing_reasons

        db.commit()
        db.refresh(intent)
        return intent

    # -----------------------------------------------------------------------
    # 3-Tier Kill Switch
    # -----------------------------------------------------------------------

    @classmethod
    def kill_intent(
        cls,
        db: Session,
        intent_id: str,
        reason: str,
        actor: str = "system",
    ) -> Dict[str, Any]:
        """Level 1 Kill Switch: Halts a single intent before payment capture."""
        intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
        if not intent:
            raise KillSwitchError(f"PaymentIntent '{intent_id}' not found.")

        # Invariant check: cannot kill already captured/reconciled payment
        if intent.status in ("CAPTURED", "RECONCILED", "DISPUTE_OPEN", "EVIDENCE_SUBMITTED", "RESOLVED"):
            raise KillSwitchError(
                f"Cannot execute Level 1 Kill Switch on intent '{intent_id}' in '{intent.status}' state. "
                "Already captured transactions cannot be altered retroactively."
            )

        if intent.status == "BLOCKED":
            return {
                "level": "INTENT",
                "target_id": intent_id,
                "status": "ALREADY_BLOCKED",
                "affected_count": 0,
                "reason": reason,
                "actor": actor,
                "timestamp": datetime.utcnow().isoformat(),
                "preserved_captured_count": 0,
            }

        prev_status = intent.status
        intent.status = "BLOCKED"
        intent.updated_at = datetime.utcnow()

        reasons = intent.policy_evaluation_reasons or []
        if isinstance(reasons, list):
            reasons.append(f"KILL_SWITCH_LEVEL_1_ENGAGED by {actor}: {reason}")
            intent.policy_evaluation_reasons = reasons

        db.commit()
        db.refresh(intent)

        return {
            "level": "INTENT",
            "target_id": intent_id,
            "previous_status": prev_status,
            "status": "BLOCKED",
            "affected_count": 1,
            "reason": reason,
            "actor": actor,
            "timestamp": datetime.utcnow().isoformat(),
            "preserved_captured_count": 0,
        }

    @classmethod
    def kill_agent(
        cls,
        db: Session,
        agent_id: str,
        reason: str,
        actor: str = "system",
    ) -> Dict[str, Any]:
        """Level 2 Kill Switch: Revokes agent ID and cancels all in-flight uncaptured intents."""
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise KillSwitchError(f"Agent '{agent_id}' not found.")

        agent.status = "REVOKED"

        # Cancel all uncaptured in-flight intents
        pending_intents = db.query(PaymentIntent).filter(
            PaymentIntent.agent_id == agent_id,
            PaymentIntent.status.in_(["PROPOSED", "POLICY_CHECK", "EVIDENCE_VALIDATION", "AUTO_APPROVED", "HUMAN_REVIEW", "APPROVED", "EXECUTING", "AUTHORIZED"])
        ).all()

        halted_count = 0
        for intent in pending_intents:
            intent.status = "BLOCKED"
            intent.updated_at = datetime.utcnow()
            reasons = intent.policy_evaluation_reasons or []
            if isinstance(reasons, list):
                reasons.append(f"KILL_SWITCH_LEVEL_2_AGENT_REVOKED ({agent_id}) by {actor}: {reason}")
                intent.policy_evaluation_reasons = reasons
            halted_count += 1

        db.commit()
        db.refresh(agent)

        return {
            "level": "AGENT",
            "target_id": agent_id,
            "agent_status": "REVOKED",
            "status": "REVOKED",
            "affected_count": halted_count,
            "reason": reason,
            "actor": actor,
            "timestamp": datetime.utcnow().isoformat(),
            "preserved_captured_count": 0,
        }

    @classmethod
    def kill_mandate(
        cls,
        db: Session,
        mandate_id: str,
        reason: str,
        actor: str = "system",
    ) -> Dict[str, Any]:
        """Level 3 Kill Switch: Freezes mandate boundary, voids uncaptured authorizations,

        and STRICTLY preserves already-CAPTURED and RECONCILED transactions.
        """
        mandate = db.query(Mandate).filter(Mandate.id == mandate_id).first()
        if not mandate:
            raise KillSwitchError(f"Mandate '{mandate_id}' not found.")

        mandate.status = "FROZEN"

        # Find in-flight uncaptured intents to block/void
        in_flight_intents = db.query(PaymentIntent).filter(
            PaymentIntent.mandate_id == mandate_id,
            PaymentIntent.status.in_(["PROPOSED", "POLICY_CHECK", "EVIDENCE_VALIDATION", "AUTO_APPROVED", "HUMAN_REVIEW", "APPROVED", "EXECUTING", "AUTHORIZED"])
        ).all()

        voided_count = 0
        for intent in in_flight_intents:
            intent.status = "BLOCKED"
            intent.updated_at = datetime.utcnow()
            reasons = intent.policy_evaluation_reasons or []
            if isinstance(reasons, list):
                reasons.append(f"KILL_SWITCH_LEVEL_3_MANDATE_FROZEN ({mandate_id}) by {actor}: {reason}")
                intent.policy_evaluation_reasons = reasons
            voided_count += 1

        # Count preserved captured/reconciled transactions (must NEVER be altered)
        preserved_count = db.query(PaymentIntent).filter(
            PaymentIntent.mandate_id == mandate_id,
            PaymentIntent.status.in_(["CAPTURED", "RECONCILED", "DISPUTE_OPEN", "EVIDENCE_SUBMITTED", "RESOLVED"])
        ).count()

        db.commit()
        db.refresh(mandate)

        return {
            "level": "MANDATE",
            "target_id": mandate_id,
            "mandate_status": "FROZEN",
            "status": "FROZEN",
            "affected_count": voided_count,
            "preserved_captured_count": preserved_count,
            "reason": reason,
            "actor": actor,
            "timestamp": datetime.utcnow().isoformat(),
        }
