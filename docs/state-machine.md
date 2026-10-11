# Sentinel & ProofLayer: Canonical 12-State Machine Specification

## 1. Overview

The **Sentinel State Machine** governs the complete commercial lifecycle of autonomous agent transactions, from initial natural-language procurement proposal through policy validation, human executive escalation, PayPal payment execution, and post-payment dispute defense.

The state machine enforces four non-negotiable invariants:
1. **No Payment Without Governance**: No transaction can execute against the PayPal API without transitioning through both `POLICY_CHECK` and `EVIDENCE_VALIDATION`.
2. **Deterministic Routing**: Decisions to auto-approve, escalate to human review, or block are strictly computed via mathematical guards, never non-deterministic heuristics.
3. **Double-Spend Immunity**: State progression from `APPROVED` to `EXECUTING` acquires an atomic idempotency lock (`idempotency_key` and `PayPal-Request-Id`).
4. **Captures Are Immutable**: Emergency kill switch actions can halt intents, revoke agents, and void authorizations, but can **never** mutate or delete already-`CAPTURED` PayPal transactions.

---

## 2. Canonical 12-State Inventory

| # | State Name | Phase | Semantics |
|---|------------|-------|-----------|
| 1 | `PROPOSED` | Ingestion | Agent submits a raw payment intent referencing an invoice and purchase order. |
| 2 | `POLICY_CHECK` | Sentinel Pre-Flight | Intent validated against active Mandate thresholds, allowed vendors, and blocked categories. |
| 3 | `EVIDENCE_VALIDATION` | Sentinel Risk Engine | Multi-factor PO matching score ($M$) and transparent weighted risk score ($R$) computed. |
| 4 | `AUTO_APPROVED` | Autonomous Decision | Fast-path: Amount $\le L_{auto}$, $M \ge 0.85$, $R \le 0.25$. Ready for automatic execution. |
| 5 | `HUMAN_REVIEW` | Governance Escalation | Parked for executive sign-off due to amount ($L_{auto} < \text{Amount} \le L_{max}$) or moderate risk ($0.25 < R \le 0.60$). |
| 6 | `APPROVED` | Governance Sign-Off | Designated human approver (e.g. CFO Maya) has reviewed and cryptographically signed the intent. |
| 7 | `BLOCKED` | Terminal Guard | Intent rejected due to policy breach, unauthorized vendor, extreme risk, approver rejection, or kill switch. |
| 8 | `EXPIRED` | Terminal Timeout | Intent parked in `HUMAN_REVIEW` timed out past the SLA window (e.g., 24 hours). |
| 9 | `EXECUTING` | Payment Execution | Idempotency lock acquired; PayPal Orders v2 API request in flight. |
| 10 | `AUTHORIZED` | Payment Execution | PayPal Orders v2 authorization succeeded (`status: "COMPLETED"` or `"AUTHORIZED"`). |
| 11 | `CAPTURED` | Settlement | PayPal authorization capture succeeded (`status: "COMPLETED"`). Funds settled. |
| 12 | `RECONCILED` | Audit Confirmation | Capture receipt immutably anchored in the Merkle audit ledger. Baseline for ProofLayer. |
| 13 | `DISPUTE_OPEN` | ProofLayer Defense | PayPal webhook `CUSTOMER.DISPUTE.CREATED` received; dispute SLA countdown active. |
| 14 | `EVIDENCE_SUBMITTED`| ProofLayer Defense | Causal graph traversed, readiness score $\ge 0.85$, grounded brief submitted to PayPal Disputes API. |
| 15 | `RESOLVED` | Terminal Resolution | PayPal dispute closed via webhook `CUSTOMER.DISPUTE.RESOLVED`. |

*(Note: States 1–12 represent the core payment execution lifecycle, and 13–15 represent the post-payment ProofLayer dispute resolution cycle).*

---

## 3. Transition Matrix & Precondition Guards

```
                              ┌────────────────────────────────────────┐
                              │               PROPOSED                 │
                              └───────────────────┬────────────────────┘
                                                  │ Intent payload valid
                                                  ▼
                              ┌────────────────────────────────────────┐
                              │             POLICY_CHECK               │
                              └───────┬────────────────────────┬───────┘
                                      │                        │ Blocked Category / Unallowlisted / Frozen Mandate
                                      │ Policy Valid           ▼
                                      │                    ┌─────────────────┐
                                      │                    │     BLOCKED     │
                                      ▼                    └─────────────────┘
                              ┌────────────────────────────────────────┐
                              │          EVIDENCE_VALIDATION           │
                              └───────┬──────────────┬─────────┬───────┘
                                      │              │         │ PO Mismatch (M < 0.70) / Extreme Risk (R > 0.60)
         Amount <= $1k, M >= 0.85,    │              │         ▼
         R <= 0.25                    │              │     ┌─────────────────┐
                                      ▼              │     │     BLOCKED     │
                        ┌───────────────────┐        │     └─────────────────┘
                        │   AUTO_APPROVED   │        │
                        └─────────┬─────────┘        │ Amount > $1k, M >= 0.85, R <= 0.60
                                  │                  ▼
                                  │         ┌─────────────────┐
                                  │         │  HUMAN_REVIEW   │
                                  │         └────────┬────────┘
                                  │                  │ Approver (Maya Lin) approves
                                  │                  ▼
                                  │         ┌─────────────────┐
                                  │         │    APPROVED     │
                                  │         └────────┬────────┘
                                  │                  │
                                  └─────────┬────────┘
                                            │ Acquire Idempotency Lock
                                            ▼
                              ┌────────────────────────────────────────┐
                              │               EXECUTING                │
                              └───────────────────┬────────────────────┘
                                                  │ PayPal Orders v2 Authorize (200 OK)
                                                  ▼
                              ┌────────────────────────────────────────┐
                              │              AUTHORIZED                │
                              └───────────────────┬────────────────────┘
                                                  │ PayPal Payments Capture (200 OK)
                                                  ▼
                              ┌────────────────────────────────────────┐
                              │               CAPTURED                 │
                              └───────────────────┬────────────────────┘
                                                  │ Anchored in Merkle Ledger
                                                  ▼
                              ┌────────────────────────────────────────┐
                              │              RECONCILED                │
                              └───────────────────┬────────────────────┘
                                                  │ CUSTOMER.DISPUTE.CREATED Webhook
                                                  ▼
                              ┌────────────────────────────────────────┐
                              │             DISPUTE_OPEN               │
                              └───────────────────┬────────────────────┘
                                                  │ Readiness >= 0.85, Brief Submitted
                                                  ▼
                              ┌────────────────────────────────────────┐
                              │          EVIDENCE_SUBMITTED            │
                              └───────────────────┬────────────────────┘
                                                  │ CUSTOMER.DISPUTE.RESOLVED Webhook
                                                  ▼
                              ┌────────────────────────────────────────┐
                              │               RESOLVED                 │
                              └────────────────────────────────────────┘
```

### Transition Specification Table

| Transition | Event / Trigger | Guard Conditions | Action Taken |
|------------|-----------------|------------------|--------------|
| `PROPOSED -> POLICY_CHECK` | Ingestion | Intent schema valid, active agent | Record genesis intent block |
| `POLICY_CHECK -> BLOCKED` | Policy Gate | Category blocked OR Agent revoked OR Mandate frozen | Log rejection reasons; zero PayPal calls |
| `POLICY_CHECK -> EVIDENCE_VALIDATION` | Policy Gate | Mandate active, vendor allowlisted, amount $\le L_{max}$ | Dispatch to Risk Engine |
| `EVIDENCE_VALIDATION -> AUTO_APPROVED`| Risk Engine | Amount $\le L_{auto} \land M \ge 0.85 \land R \le 0.25$ | Set auto-dispatch flag |
| `EVIDENCE_VALIDATION -> HUMAN_REVIEW`| Risk Engine | $L_{auto} < \text{Amount} \le L_{max} \land M \ge 0.85$ | Queue in Approvals console; notify approver |
| `EVIDENCE_VALIDATION -> BLOCKED` | Risk Engine | $M < 0.70 \lor R > 0.60 \lor \text{Amount} > L_{max}$ | Log mismatch / risk breakdown |
| `HUMAN_REVIEW -> APPROVED` | Human Sign-Off | Approver limit $\ge \text{Amount}$, valid signature | Generate execution token |
| `HUMAN_REVIEW -> BLOCKED` | Human Rejection | Explicit human rejection | Log approver rejection notes |
| `HUMAN_REVIEW -> EXPIRED` | Timeout | Intent age exceeds SLA window | Transition to expired |
| `AUTO_APPROVED -> EXECUTING` | Dispatch | Idempotency lock acquired (`idempotency_key`) | Dispatch PayPal Orders v2 |
| `APPROVED -> EXECUTING` | Dispatch | Idempotency lock acquired (`idempotency_key`) | Dispatch PayPal Orders v2 |
| `EXECUTING -> AUTHORIZED` | PayPal API | PayPal returns `status: "COMPLETED"/"AUTHORIZED"` | Record order/auth IDs in ledger |
| `AUTHORIZED -> CAPTURED` | PayPal API | PayPal capture returns `status: "COMPLETED"` | Record capture receipt |
| `CAPTURED -> RECONCILED` | Ledger Service | SHA-256 block anchored in Merkle ledger | Emit reconciliation event |
| `RECONCILED -> DISPUTE_OPEN` | Webhook | Valid signature on `CUSTOMER.DISPUTE.CREATED` | Start SLA countdown timer |
| `DISPUTE_OPEN -> EVIDENCE_SUBMITTED` | ProofLayer | $Readiness \ge 0.85$, valid citations, PayPal 200 OK | Submit via PayPal Disputes API |
| `EVIDENCE_SUBMITTED -> RESOLVED` | Webhook | Valid `CUSTOMER.DISPUTE.RESOLVED` webhook | Close dispute record |

---

## 4. 3-Tier Emergency Kill Switch

The 3-tier Kill Switch provides instantaneous, cascade-isolated intervention for operators and governance officers.

```
[ LEVEL 1: INTENT ]  ──► Target: Single Intent ID
                         Halt specific in-flight proposal/review.
                         Transitions to BLOCKED. Zero side effects on other intents.

[ LEVEL 2: AGENT ]   ──► Target: Agent ID (e.g. agent_atlas_procurement)
                         Revokes agent credentials.
                         Blocks all current and future intent submissions.

[ LEVEL 3: MANDATE ] ──► Target: Mandate ID (e.g. mdt_9f21ac)
                         Freezes organizational mandate boundary.
                         Aborts all uncaptured authorizations.
                         PRESERVES all already-CAPTURED transactions!
```

### Detailed Kill Switch Rules

1. **Level 1 (Intent-Level Halt)**:
   - Target: `intent_id`.
   - Effect: Halts an individual intent currently in `PROPOSED`, `POLICY_CHECK`, `EVIDENCE_VALIDATION`, or `HUMAN_REVIEW`.
   - State Outcome: Moves intent immediately to `BLOCKED` with reason `"kill_switch_intent_engaged"`.
   - Invariant: Does not alter agent status or affect any other intent.

2. **Level 2 (Agent-Level Revocation)**:
   - Target: `agent_id` (e.g., `agent_atlas_procurement`).
   - Effect: Sets agent status to `REVOKED`.
   - State Outcome:
     - All active intents for that agent in `PROPOSED`, `POLICY_CHECK`, `EVIDENCE_VALIDATION`, or `HUMAN_REVIEW` transition to `BLOCKED`.
     - Future API requests from this agent are rejected with HTTP 403 Forbidden.
   - Invariant: Does not freeze other agents operating under the same organizational mandate.

3. **Level 3 (Mandate-Level Freeze)**:
   - Target: `mandate_id` (e.g., `mdt_9f21ac`).
   - Effect: Sets mandate status to `FROZEN`.
   - State Outcome:
     - Freezes all execution under the mandate.
     - Voids any uncaptured PayPal authorizations (`POST /v2/checkout/orders/{id}/void` in live/twin).
     - **CRITICAL DOUBLE-ENTRY ACCOUNTING INVARIANT**: All transactions already in `CAPTURED` or `RECONCILED` state remain 100% untouched. Their ledger integrity and settlement receipts are strictly preserved to maintain accounting truth.

---

## 5. Documentation Cross-References

- [Root Project README](../README.md): System architecture, mathematical formulas, API reference, and quickstart.
- [System Architecture & Security Blueprint](architecture.md): Dual-engine specifications, 18-node causal graph, 7 PayPal dispute reasons mapping, and Merkle ledger.
- [3-Minute Video Walkthrough Script](demo-script.md): Scripted judging walkthrough across Scenarios 1–4.
- [Devpost Submission Narrative](devpost.md): Official Devpost hackathon submission narrative.
