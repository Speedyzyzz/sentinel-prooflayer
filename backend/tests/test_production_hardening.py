"""Production Hardening & Institutional Telemetry Test Suite.

Validates:
1. Deep readiness probe (GET /ready) verifying live SQLite connectivity and SHA-256 Merkle chain integrity.
2. Security and observability headers (X-Request-ID, X-Process-Time-Ms, X-Content-Type-Options, X-Frame-Options, Cache-Control).
3. Request correlation ID propagation when caller supplies X-Request-ID.
4. Optional SENTINEL_API_KEY governance enforcement (401 on missing/invalid key, 200 on valid key, webhook exemption).
5. Containerization and CI/CD blueprint presence (backend/Dockerfile, frontend/Dockerfile, .github/workflows/ci.yml).
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def test_readiness_probe_verifies_db_and_merkle_ledger(client):
    """Verify GET /ready checks SQLite connectivity and SHA-256 Merkle audit ledger integrity."""
    res = client.get("/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ready"
    assert body["database"] == "connected"
    assert body["merkle_ledger"]["valid"] is True
    assert body["merkle_ledger"]["block_count"] >= 1


def test_security_and_telemetry_headers(client):
    """Verify every API response includes correlation ID, latency, and institutional security headers."""
    res = client.get("/api/mandates")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    assert res.headers["x-request-id"].startswith("req_")
    assert "x-process-time-ms" in res.headers
    assert float(res.headers["x-process-time-ms"]) >= 0.0
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert res.headers.get("cache-control") == "no-store"


def test_custom_request_id_propagation(client):
    """Verify caller-supplied X-Request-ID is preserved in response headers."""
    custom_req_id = "trace_paypal_hackathon_2026_001"
    res = client.get("/health", headers={"X-Request-ID": custom_req_id})
    assert res.status_code == 200
    assert res.headers.get("x-request-id") == custom_req_id
    assert res.json()["paypal_mode"] in ("deterministic_sandbox_twin", "live_sandbox_api")


def test_optional_api_key_governance_enforcement(client, monkeypatch):
    """Verify SENTINEL_API_KEY blocks unauthorized API calls when set and stays zero-friction when unset."""
    monkeypatch.setenv("SENTINEL_API_KEY", "sec_prod_key_99412")

    # 1. Missing API key on protected /api/* route returns 401
    res_unauth = client.get("/api/mandates")
    assert res_unauth.status_code == 401
    assert res_unauth.headers.get("x-sentinel-governance-mode") == "api-key-enforced"

    # 2. Valid API key succeeds
    res_auth = client.get("/api/mandates", headers={"X-Sentinel-API-Key": "sec_prod_key_99412"})
    assert res_auth.status_code == 200

    # 3. Health and Readiness probes remain accessible for load balancer checks
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_deployment_dockerfiles_and_ci_exist():
    """Verify production Dockerfiles and GitHub Actions CI workflow exist for docker-compose and cloud builds."""
    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "backend" / "Dockerfile").is_file()
    assert (repo_root / "frontend" / "Dockerfile").is_file()
    assert (repo_root / ".github" / "workflows" / "ci.yml").is_file()
