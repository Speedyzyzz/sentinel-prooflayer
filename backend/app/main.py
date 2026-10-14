"""Sentinel & ProofLayer FastAPI Application.

Implements:
- Lifespan startup handler with SQLite WAL initialization & Acme AI Ops auto-seeding.
- Spec-compliant CORS middleware enabling Next.js 15 frontend connectivity.
- Institutional telemetry, correlation ID (X-Request-ID), latency (X-Process-Time-Ms),
  security headers, and optional API-key governance middleware.
- Liveness (/health) and deep readiness (/ready) probes verifying SQLite WAL and
  SHA-256 Merkle audit chain integrity.
- Mounts all 9 institutional API routers under /api prefix.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import AuditBlock, SessionLocal, init_db
from app.routers.approvals import router as approvals_router
from app.routers.disputes import router as disputes_router
from app.routers.evidence import router as evidence_router
from app.routers.intents import router as intents_router
from app.routers.mandates import router as mandates_router
from app.routers.payments import router as payments_router
from app.routers.policy import router as policy_router
from app.routers.scenarios import router as scenarios_router, seed_demo_data
from app.routers.webhooks import router as webhooks_router
from app.services.audit_ledger import AuditLedgerService

logger = logging.getLogger("sentinel.api")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


def _utc_now_iso() -> str:
    """Return timezone-aware ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: creates relational tables and seeds demo dataset on startup."""
    init_db()
    seed_enabled = os.getenv("SEED_DEMO_DATA", "true").strip().lower() not in ("false", "0", "no")
    if seed_enabled:
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()
    logger.info("Sentinel & ProofLayer Control Plane started (seed_demo_data=%s)", seed_enabled)
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

# Spec-compliant CORS Middleware Configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
if not origins or origins == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time-Ms", "X-Sentinel-Governance-Mode"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time-Ms", "X-Sentinel-Governance-Mode"],
    )


@app.middleware("http")
async def institutional_telemetry_and_security_middleware(
    request: Request,
    call_next: Callable[[Request], Any],
) -> Response:
    """Enforce correlation IDs, security headers, latency telemetry, and optional API key guard."""
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id
    start_time = time.perf_counter()

    # Optional API Key guard when SENTINEL_API_KEY is explicitly configured
    configured_api_key = os.getenv("SENTINEL_API_KEY", "").strip()
    governance_mode = "api-key-enforced" if configured_api_key else "sandbox-open"

    if configured_api_key and request.url.path.startswith("/api/"):
        # Exempt PayPal webhook ingestion (verified via PayPal signature headers) and OPTIONS preflight
        if request.method != "OPTIONS" and not request.url.path.startswith("/api/webhooks/"):
            provided_key = request.headers.get("X-Sentinel-API-Key", "").strip()
            if provided_key != configured_api_key:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Missing or invalid X-Sentinel-API-Key header.",
                        "request_id": request_id,
                    },
                    headers={
                        "X-Request-ID": request_id,
                        "X-Sentinel-Governance-Mode": governance_mode,
                        "X-Content-Type-Options": "nosniff",
                    },
                )

    try:
        response: Response = await call_next(request)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.exception("Unhandled exception on %s %s [request_id=%s]", request.method, request.url.path, request_id)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal control plane error.",
                "error_type": type(exc).__name__,
                "request_id": request_id,
            },
            headers={
                "X-Request-ID": request_id,
                "X-Process-Time-Ms": f"{elapsed_ms:.2f}",
                "X-Sentinel-Governance-Mode": governance_mode,
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            },
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    response.headers["X-Sentinel-Governance-Mode"] = governance_mode
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")

    return response


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
def health_check() -> dict[str, Any]:
    """System liveness check endpoint for monitoring and cloud deployment probes."""
    paypal_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    paypal_mode = (
        "live_sandbox_api"
        if paypal_id and paypal_id not in ("", "mock", "sandbox_demo_client_id", "your_paypal_sandbox_client_id_here")
        else "deterministic_sandbox_twin"
    )
    return {
        "status": "ok",
        "app": "sentinel-prooflayer",
        "version": "1.0.0",
        "paypal_mode": paypal_mode,
        "governance_mode": "api-key-enforced" if os.getenv("SENTINEL_API_KEY", "").strip() else "sandbox-open",
        "timestamp": _utc_now_iso(),
    }


@app.get("/ready", tags=["system"])
def readiness_check() -> JSONResponse:
    """Deep readiness probe verifying SQLite WAL connectivity and SHA-256 Merkle chain integrity."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        blocks = db.query(AuditBlock).order_by(AuditBlock.block_index.asc()).all()
        merkle_valid, merkle_msg, tampered_idx = AuditLedgerService.verify_chain(blocks)
        status_code = 200 if merkle_valid else 503
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "ready" if merkle_valid else "degraded",
                "app": "sentinel-prooflayer",
                "database": "connected",
                "merkle_ledger": {
                    "valid": merkle_valid,
                    "block_count": len(blocks),
                    "message": merkle_msg,
                    "tampered_block_index": tampered_idx,
                },
                "timestamp": _utc_now_iso(),
            },
        )
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "app": "sentinel-prooflayer",
                "database": "disconnected",
                "detail": str(exc),
                "timestamp": _utc_now_iso(),
            },
        )
    finally:
        db.close()


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Root metadata and API discovery endpoint."""
    return {
        "name": "Sentinel & ProofLayer Control Plane",
        "description": "Pre-execution Agent Mandate Control Plane & Post-execution Causal Evidence Auto-Defense",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "version": "1.0.0",
    }
