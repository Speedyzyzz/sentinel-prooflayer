"""Comprehensive Pydantic v2 Schemas for Sentinel & ProofLayer.

Includes strong typing, validation constraints, enum-like constants,
and serializable payload contracts across all models and API routes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Base Schema Configuration
# ---------------------------------------------------------------------------

class SentinelBaseSchema(BaseModel):
    """Base schema enabling ORM mode and attribute hydration."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Organization & User Schemas
# ---------------------------------------------------------------------------

class OrganizationBase(SentinelBaseSchema):
    id: str = Field(..., description="Unique organization identifier, e.g. usr_acme_finance")
    name: str = Field(..., description="Corporate name of organization")


class OrganizationCreate(OrganizationBase):
    """Payload schema for tenant organization registration."""


class OrganizationResponse(OrganizationBase):
    created_at: datetime


class UserBase(SentinelBaseSchema):
    id: str = Field(..., description="Unique user identifier, e.g. usr_maya")
    org_id: str
    name: str
    email: str
    role: str = Field(..., description="Corporate role: CFO, ANALYST, ADMIN, OPERATOR")
    approval_limit: float = Field(default=0.0, ge=0.0)
    is_active: bool = True


class UserCreate(UserBase):
    """Payload schema for registering human corporate operators and approvers."""


class UserResponse(UserBase):
    created_at: datetime


# ---------------------------------------------------------------------------
# Agent & Mandate Schemas
# ---------------------------------------------------------------------------

class AgentBase(SentinelBaseSchema):
    id: str = Field(..., description="Unique agent identifier, e.g. agent_atlas_procurement")
    org_id: str
    name: str
    role: str
    status: Literal["ACTIVE", "REVOKED", "SUSPENDED"] = "ACTIVE"


class AgentCreate(AgentBase):
    """Payload schema for registering procurement/finance agents."""


class AgentResponse(AgentBase):
    created_at: datetime


class MandateBase(SentinelBaseSchema):
    id: str = Field(..., description="Unique mandate identifier, e.g. mdt_9f21ac")
    org_id: str
    agent_id: str
    name: str
    description: Optional[str] = None
    auto_approve_limit: float = Field(default=1000.00, ge=0.0)
    max_cap: float = Field(default=5000.00, ge=0.0)
    po_variance_limit: float = Field(default=0.02, ge=0.0, le=1.0)
    allowed_categories: List[str] = Field(default_factory=list)
    blocked_categories: List[str] = Field(default_factory=list)
    allowed_vendors: List[str] = Field(default_factory=list)
    cel_rules: Optional[str] = None
    status: Literal["ACTIVE", "FROZEN", "INACTIVE"] = "ACTIVE"
    version: int = 1


class MandateCreate(MandateBase):
    """Payload schema for establishing new governance spend mandates."""


class MandateUpdate(SentinelBaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    auto_approve_limit: Optional[float] = None
    max_cap: Optional[float] = None
    po_variance_limit: Optional[float] = None
    allowed_categories: Optional[List[str]] = None
    blocked_categories: Optional[List[str]] = None
    allowed_vendors: Optional[List[str]] = None
    cel_rules: Optional[str] = None
    status: Optional[Literal["ACTIVE", "FROZEN", "INACTIVE"]] = None


class MandateResponse(MandateBase):
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Vendor, Purchase Order & Contract Schemas
# ---------------------------------------------------------------------------

class VendorBase(SentinelBaseSchema):
    id: str = Field(..., description="Unique vendor identifier, e.g. vendor_data_labeling_co")
    name: str
    legal_name: str
    category: str
    is_allowlisted: bool = False
    risk_rating: float = Field(default=0.0, ge=0.0, le=1.0)
    dispute_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    paypal_merchant_id: Optional[str] = None


class VendorCreate(VendorBase):
    """Payload schema for vendor onboarding and allowlisting."""


class VendorResponse(VendorBase):
    created_at: datetime


class PurchaseOrderItem(SentinelBaseSchema):
    description: str
    quantity: float
    unit_price: float
    total: float


class PurchaseOrderBase(SentinelBaseSchema):
    id: str = Field(..., description="Unique purchase order identifier, e.g. po_2026_4410")
    vendor_id: str
    amount: float = Field(..., ge=0.0)
    currency: str = "USD"
    items: List[Dict[str, Any]] = Field(default_factory=list)
    terms: str = "Net-30"
    contract_ref: Optional[str] = None
    status: Literal["OPEN", "MATCHED", "CLOSED"] = "OPEN"


class PurchaseOrderCreate(PurchaseOrderBase):
    """Payload schema for generating baseline purchase orders."""


class PurchaseOrderResponse(PurchaseOrderBase):
    created_at: datetime


class VendorContractBase(SentinelBaseSchema):
    id: str = Field(..., description="Unique contract identifier, e.g. cnt_2026_dl_01")
    vendor_id: str
    title: str
    terms: str
    sla_details: str
    signed_at: datetime


class VendorContractCreate(VendorContractBase):
    """Payload schema for executing master service agreements."""


class VendorContractResponse(VendorContractBase):
    created_at: datetime


# ---------------------------------------------------------------------------
# Risk & PO Matching Schemas
# ---------------------------------------------------------------------------

class MatchingScoreBreakdown(SentinelBaseSchema):
    S_vendor: float = Field(..., description="Vendor match score (0.0 to 1.0, weight 0.35)")
    S_total: float = Field(..., description="Amount variance tolerance score (0.0 to 1.0, weight 0.25)")
    S_line_items: float = Field(..., description="Line items description/unit price alignment (0.0 to 1.0, weight 0.25)")
    S_terms: float = Field(..., description="Currency and terms validity (0.0 to 1.0, weight 0.15)")


class MatchingScoreResult(SentinelBaseSchema):
    score: float = Field(..., description="Combined matching score M in [0, 1]")
    breakdown: MatchingScoreBreakdown
    reasons: List[str] = Field(default_factory=list)


class RiskScoreBreakdown(SentinelBaseSchema):
    V: float = Field(..., description="Vendor allowlist / verification risk (weight 0.30)")
    D: float = Field(..., description="Duplicate invoice fingerprint & velocity risk (weight 0.25)")
    A: float = Field(..., description="Amount cap ratio risk (weight 0.20)")
    C: float = Field(..., description="Blocked category risk (weight 0.15)")
    H: float = Field(..., description="Historical dispute and refund risk (weight 0.10)")


class RiskEvaluationResult(SentinelBaseSchema):
    score: float = Field(..., description="Combined risk score R in [0, 1]")
    breakdown: RiskScoreBreakdown
    reasons: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Payment Intent Schemas
# ---------------------------------------------------------------------------

class LineItemPayload(SentinelBaseSchema):
    description: str
    quantity: float
    unit_price: float
    total: float


class PaymentIntentBase(SentinelBaseSchema):
    mandate_id: str
    agent_id: str
    vendor_id: str
    amount: float = Field(..., gt=0.0)
    currency: str = "USD"
    category: str
    invoice_ref: str
    po_ref: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class PaymentIntentCreate(PaymentIntentBase):
    id: Optional[str] = None


class PaymentIntentEvaluateRequest(SentinelBaseSchema):
    dry_run: bool = False


class PaymentIntentResponse(PaymentIntentBase):
    id: str
    status: str
    po_match_score: Optional[float] = None
    risk_score: Optional[float] = None
    risk_breakdown: Optional[Dict[str, Any]] = None
    policy_evaluation_reasons: Optional[List[str]] = None
    idempotency_key: Optional[str] = None
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Approvals & Human Review Schemas
# ---------------------------------------------------------------------------

class ApprovalActionRequest(SentinelBaseSchema):
    approver_id: str
    decision: Literal["APPROVED", "REJECTED"] = "APPROVED"
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None


class ApprovalResponse(SentinelBaseSchema):
    id: str
    intent_id: str
    approver_id: str
    decision: str
    notes: Optional[str] = None
    created_at: datetime
    intent_status: str


class ApprovalQueueItem(SentinelBaseSchema):
    intent_id: str
    agent_id: str
    vendor_id: str
    vendor_name: str
    amount: float
    currency: str
    category: str
    invoice_ref: str
    po_ref: Optional[str] = None
    po_match_score: Optional[float] = None
    risk_score: Optional[float] = None
    risk_breakdown: Optional[Dict[str, Any]] = None
    policy_evaluation_reasons: Optional[List[str]] = None
    created_at: datetime


class ApprovalDetailResponse(SentinelBaseSchema):
    intent: PaymentIntentResponse
    purchase_order: Optional[PurchaseOrderResponse] = None
    vendor: Optional[VendorResponse] = None
    mandate: Optional[MandateResponse] = None
    prior_approvals: List[ApprovalResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Payments Execution & Transactions Schemas
# ---------------------------------------------------------------------------

class PaymentExecuteRequest(SentinelBaseSchema):
    intent_id: str
    idempotency_key: str = Field(..., description="Atomic idempotency key / PayPal-Request-Id")


class PaymentExecuteResponse(SentinelBaseSchema):
    intent_id: str
    status: str
    paypal_order_id: str
    paypal_capture_id: Optional[str] = None
    amount: float
    currency: str
    idempotency_key: str
    cached_replay: bool = False
    reconciled_at: datetime


class TransactionResponse(SentinelBaseSchema):
    id: str
    intent_id: str
    amount: float
    currency: str
    paypal_order_id: str
    paypal_capture_id: Optional[str] = None
    status: str
    raw_response: Optional[Dict[str, Any]] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Kill Switch Schemas
# ---------------------------------------------------------------------------

class KillSwitchRequest(SentinelBaseSchema):
    level: Literal["INTENT", "AGENT", "MANDATE"]
    target_id: str = Field(..., description="ID of intent, agent, or mandate to kill")
    reason: str
    actor: str = Field(default="system", description="User or system triggering emergency kill")


class KillSwitchResponse(SentinelBaseSchema):
    level: str
    target_id: str
    status: str
    affected_count: int
    reason: str
    actor: str
    timestamp: datetime
    preserved_captured_count: int = 0


# ---------------------------------------------------------------------------
# Policy Compiler & Simulator Schemas
# ---------------------------------------------------------------------------

class PolicyCompileRequest(SentinelBaseSchema):
    prompt: str = Field(..., min_length=1, description="Natural language procurement governance rule prompt")
    context: Optional[Dict[str, Any]] = None


class PolicyRule(SentinelBaseSchema):
    id: str
    expression: str
    action: Literal["AUTO_APPROVE", "REQUIRE_HUMAN_REVIEW", "BLOCK"]
    description: Optional[str] = None


class PolicyCompileResponse(SentinelBaseSchema):
    mandate_id: str
    version: str
    currency: str = "USD"
    auto_approve_threshold: float
    max_transaction_cap: float
    daily_velocity_cap: float
    po_variance_tolerance: float
    po_matching_required: bool
    allowed_categories: List[str]
    blocked_categories: List[str]
    allowed_vendors: List[str]
    escalation_role: str = "usr_maya"
    rules: List[PolicyRule]
    compiled_cel: str


class PolicySimulateRequest(SentinelBaseSchema):
    mandate_rules: Dict[str, Any]
    historical_transactions: Optional[List[Dict[str, Any]]] = None
    sample_size: int = 100


class SimulationMetric(SentinelBaseSchema):
    total_transactions: int
    auto_approved_count: int
    auto_approved_rate: float
    human_review_count: int
    human_review_rate: float
    blocked_count: int
    blocked_rate: float
    friction_hours_saved: float
    blocked_spend_prevented: float
    auto_approved_spend: float
    human_review_spend: float


class PolicySimulateResponse(SentinelBaseSchema):
    simulation_id: str
    metrics: SimulationMetric
    sample_evaluated: int
    breakdown_by_category: Dict[str, Dict[str, int]]


# ---------------------------------------------------------------------------
# Causal Evidence Graph & Auto-Defense Schemas
# ---------------------------------------------------------------------------

class EvidenceNodeBase(SentinelBaseSchema):
    id: str
    intent_id: str
    node_type: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class EvidenceNodeCreate(EvidenceNodeBase):
    """Payload schema for generating causal evidence graph nodes."""


class EvidenceNodeResponse(EvidenceNodeBase):
    created_at: datetime


class EvidenceEdgeBase(SentinelBaseSchema):
    id: str
    intent_id: str
    source_id: str
    target_id: str
    edge_type: str
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EvidenceEdgeCreate(EvidenceEdgeBase):
    """Payload schema for creating causal property graph edges."""


class EvidenceEdgeResponse(EvidenceEdgeBase):
    created_at: datetime


class EvidenceGraphResponse(SentinelBaseSchema):
    intent_id: str
    nodes: List[EvidenceNodeResponse]
    edges: List[EvidenceEdgeResponse]
    node_count: int
    edge_count: int


class ReadinessBreakdown(SentinelBaseSchema):
    completeness: float = Field(..., description="Weight 0.25 - required nodes presence")
    freshness: float = Field(..., description="Weight 0.15 - delta t decay from dispute")
    provenance: float = Field(..., description="Weight 0.20 - Merkle signed anchoring")
    consistency: float = Field(..., description="Weight 0.15 - PO vs invoice variance")
    relevance: float = Field(..., description="Weight 0.15 - refutation of dispute claim")
    verifiability: float = Field(..., description="Weight 0.10 - PayPal API IDs and external proof")


class EvidenceCompileRequest(SentinelBaseSchema):
    intent_id: str
    dispute_id: str = "PP-D-99412"
    dispute_reason: str = "ITEM_NOT_RECEIVED"


class EvidenceCompileResponse(SentinelBaseSchema):
    intent_id: str
    dispute_id: str
    readiness_score: float = Field(..., description="Overall Readiness score, e.g. 0.940")
    readiness_breakdown: ReadinessBreakdown
    defense_narrative: str
    cited_nodes: List[str]
    paypal_evidence_type: str
    tracking_info: Optional[List[Dict[str, Any]]] = None
    meets_defense_threshold: bool = True


# ---------------------------------------------------------------------------
# Disputes Schemas
# ---------------------------------------------------------------------------

class DisputeBase(SentinelBaseSchema):
    id: str
    transaction_id: Optional[str] = None
    intent_id: str
    amount: float
    currency: str = "USD"
    reason: str
    status: str = "OPEN"
    evidence_package: Optional[Dict[str, Any]] = None
    readiness_score: Optional[float] = None
    defense_narrative: Optional[str] = None
    sla_deadline: Optional[datetime] = None


class DisputeResponse(DisputeBase):
    created_at: datetime
    updated_at: datetime


class DisputeSubmitDefenseRequest(SentinelBaseSchema):
    evidence_type: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Cryptographic Audit Ledger & Tamper Verification Schemas
# ---------------------------------------------------------------------------

class AuditBlockResponse(SentinelBaseSchema):
    id: int
    block_index: int
    timestamp: datetime
    event_type: str
    entity_type: str
    entity_id: str
    actor: str
    payload_hash: str
    prev_hash: str
    merkle_root: str
    block_hash: str
    details: Optional[Dict[str, Any]] = None


class ChainVerificationResponse(SentinelBaseSchema):
    is_valid: bool
    message: str
    total_blocks: int
    tampered_block_index: Optional[int] = None


# ---------------------------------------------------------------------------
# Webhook Schemas
# ---------------------------------------------------------------------------

class WebhookPayload(SentinelBaseSchema):
    id: Optional[str] = None
    event_version: Optional[str] = "1.0"
    create_time: Optional[str] = None
    resource_type: str
    event_type: str
    summary: Optional[str] = None
    resource: Dict[str, Any]


class WebhookResponse(SentinelBaseSchema):
    status: str
    event_id: str
    event_type: str
    processed: bool
    duplicate: bool = False
    message: str


# ---------------------------------------------------------------------------
# Scenario Schemas
# ---------------------------------------------------------------------------

class ScenarioInfoResponse(SentinelBaseSchema):
    scenario_id: int
    name: str
    description: str
    expected_outcome: str
    test_amount: float
    vendor_name: str


class ScenarioRunResponse(SentinelBaseSchema):
    scenario_id: int
    scenario_name: str
    status: Literal["SUCCESS", "FAILED"]
    final_state: str
    details: Dict[str, Any]
    trace: List[str]
    paypal_calls_made: int
    merkle_blocks_added: int


class ResetResponse(SentinelBaseSchema):
    status: str
    message: str
    seeded_counts: Dict[str, int]
