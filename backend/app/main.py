"""Sentinel & ProofLayer FastAPI Application.

Implements:
- Lifespan startup handler with SQLite WAL initialization & Acme AI Ops auto-seeding.
- CORS middleware enabling Next.js 15 frontend connectivity.
- Healthcheck endpoint GET /health.
- Mounts all 9 institutional API routers under /api prefix.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import SessionLocal, init_db
from app.routers.approvals import router as approvals_router
from app.routers.disputes import router as disputes_router
from app.routers.evidence import router as evidence_router
from app.routers.intents import router as intents_router
from app.routers.mandates import router as mandates_router
from app.routers.payments import router as payments_router
from app.routers.policy import router as policy_router
from app.routers.scenarios import router as scenarios_router, seed_demo_data
from app.routers.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: creates relational tables and seeds demo dataset on startup."""
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Sentinel & ProofLayer Control Plane",
    description=(
        "Production-grade Agent Mandate Control Plane (Sentinel) and Causal Pre-Dispute Evidence Graph "
        "(ProofLayer) for the PayPal AI Hackathon 2026."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware Configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount 9 Institutional Routers under /api
app.include_router(mandates_router, prefix="/api")
app.include_router(policy_router, prefix="/api")
app.include_router(intents_router, prefix="/api")
app.include_router(approvals_router, prefix="/api")
app.include_router(payments_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(disputes_router, prefix="/api")
app.include_router(scenarios_router, prefix="/api")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """System health check endpoint for monitoring and cloud deployment probes."""
    return {
        "status": "ok",
        "app": "sentinel-prooflayer",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Root metadata and API discovery endpoint."""
    return {
        "name": "Sentinel & ProofLayer Control Plane",
        "description": "Pre-execution Agent Mandate Control Plane & Post-execution Causal Evidence Auto-Defense",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
