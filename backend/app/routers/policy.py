"""Policy Compiler & What-If Simulator Router for Sentinel Control Plane.

Endpoints:
- POST /api/policy/compile: Compile natural language rules into structured JSON AST & CEL.
- POST /api/policy/simulate: Run what-if simulation against historical transaction benchmarks.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from app.schemas import (
    PolicyCompileRequest,
    PolicyCompileResponse,
    PolicyRule,
    PolicySimulateRequest,
    PolicySimulateResponse,
    SimulationMetric,
)
from app.services.policy_compiler import PolicyCompiler, PolicySyntaxError

router = APIRouter(prefix="/policy", tags=["policy"])


@router.post("/compile", response_model=PolicyCompileResponse)
def compile_policy(payload: PolicyCompileRequest) -> PolicyCompileResponse:
    """Compile natural language procurement governance prompt into structured JSON AST and CEL."""
    try:
        ast = PolicyCompiler.compile_nl_to_ast(
            prompt=payload.prompt,
            context=payload.context,
        )
    except PolicySyntaxError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    rules = [
        PolicyRule(
            id=r["id"],
            expression=r["expression"],
            action=r["action"],
            description=r.get("description"),
        )
        for r in ast.get("rules", [])
    ]

    return PolicyCompileResponse(
        mandate_id=ast.get("mandate_id", f"mdt_{uuid.uuid4().hex[:6]}"),
        version=str(ast.get("version", "1")),
        currency=ast.get("currency", "USD"),
        auto_approve_threshold=ast.get("auto_approve_threshold", 1000.0),
        max_transaction_cap=ast.get("max_transaction_cap", 5000.0),
        daily_velocity_cap=ast.get("daily_velocity_cap", 25000.0),
        po_variance_tolerance=ast.get("po_variance_tolerance", 0.02),
        po_matching_required=ast.get("po_matching_required", True),
        allowed_categories=ast.get("allowed_categories", PolicyCompiler.DEFAULT_ALLOWED_CATEGORIES),
        blocked_categories=ast.get("blocked_categories", PolicyCompiler.DEFAULT_BLOCKED_CATEGORIES),
        allowed_vendors=ast.get("allowed_vendors", PolicyCompiler.DEFAULT_ALLOWED_VENDORS),
        escalation_role=ast.get("escalation_role", "usr_maya"),
        rules=rules,
        compiled_cel=ast.get("compiled_cel", "true"),
    )


@router.post("/simulate", response_model=PolicySimulateResponse)
def simulate_policy(payload: PolicySimulateRequest) -> PolicySimulateResponse:
    """Execute historical What-If simulation measuring friction, human review hours, and blocked spend."""
    if not payload.mandate_rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mandate rules dictionary cannot be empty.",
        )

    simulation_results = PolicyCompiler.simulate_policy(
        draft_policy=payload.mandate_rules,
        historical_transactions=payload.historical_transactions,
        sample_size=payload.sample_size,
    )

    metrics = SimulationMetric(
        total_transactions=simulation_results.get("total_transactions", 0),
        auto_approved_count=simulation_results.get("auto_approved_count", 0),
        auto_approved_rate=simulation_results.get("auto_approved_rate", 0.0),
        human_review_count=simulation_results.get("human_review_count", 0),
        human_review_rate=simulation_results.get("human_review_rate", 0.0),
        blocked_count=simulation_results.get("blocked_count", 0),
        blocked_rate=simulation_results.get("blocked_rate", 0.0),
        friction_hours_saved=simulation_results.get("friction_hours_saved", 0.0),
        blocked_spend_prevented=simulation_results.get("blocked_spend_prevented", 0.0),
        auto_approved_spend=simulation_results.get("auto_approved_spend", 0.0),
        human_review_spend=simulation_results.get("human_review_spend", 0.0),
    )

    return PolicySimulateResponse(
        simulation_id=f"sim_{uuid.uuid4().hex[:8]}",
        metrics=metrics,
        sample_evaluated=simulation_results.get("total_transactions", 0),
        breakdown_by_category=simulation_results.get("category_breakdown", {}),
    )
