"""Sentinel & ProofLayer FastAPI API Routers.

Exposes all 9 modular routers:
1. mandates: Spend mandate governance CRUD, activation, and Level 3 Kill Switch.
2. policy: Natural Language to CEL Mandate Compiler and historical What-If Simulator.
3. intents: Agent payment intent proposal, risk evaluation, and Level 1 Kill Switch.
4. approvals: Human approval queue, authority validation, and dual-signoff actions.
5. payments: PayPal Orders v2 execution, idempotency locking, and Level 2 Kill Switch.
6. webhooks: PayPal incoming webhook ingestion, HMAC/Twin verification, and replay dedup.
7. evidence: 18-node Causal Evidence Graph queries, node fact inspector, and package compilation.
8. disputes: PayPal dispute queue, SLA countdowns, and cited auto-defense submission.
9. scenarios: 4 deterministic judge scenario runners and database reset.
"""

from app.routers.approvals import router as approvals_router
from app.routers.disputes import router as disputes_router
from app.routers.evidence import router as evidence_router
from app.routers.intents import router as intents_router
from app.routers.mandates import router as mandates_router
from app.routers.payments import router as payments_router
from app.routers.policy import router as policy_router
from app.routers.scenarios import router as scenarios_router
from app.routers.webhooks import router as webhooks_router

__all__ = [
    "approvals_router",
    "disputes_router",
    "evidence_router",
    "intents_router",
    "mandates_router",
    "payments_router",
    "policy_router",
    "scenarios_router",
    "webhooks_router",
]
