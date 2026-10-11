"""Database Engine, Session, and SQLAlchemy ORM Models for Sentinel & ProofLayer.

Implements all 15 relational tables with SQLite WAL mode concurrency,
foreign key cascades, JSON column storage, and index optimizations.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Generator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sentinel.db")

connect_args: dict[str, Any] = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Enforce WAL journaling mode and foreign key constraints on SQLite connections."""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


class Organization(Base):
    """Multi-tenant organization boundary."""

    __tablename__ = "organizations"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="organization", cascade="all, delete-orphan")
    mandates = relationship("Mandate", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Organization id={self.id!r} name={self.name!r}>"


class User(Base):
    """Human corporate actors (CFO, Analysts, Operators) with approval limits."""

    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(String(64), nullable=False)  # CFO, ANALYST, ADMIN, OPERATOR
    approval_limit = Column(Float, default=0.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="users")
    approvals = relationship("ApprovalRecord", back_populates="approver")

    def __repr__(self) -> str:
        return f"<User id={self.id!r} role={self.role!r} limit={self.approval_limit}>"


class Agent(Base):
    """Registered AI procurement/finance agents operating under corporate mandates."""

    __tablename__ = "agents"

    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(64), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, REVOKED, SUSPENDED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="agents")
    mandates = relationship("Mandate", back_populates="agent")
    payment_intents = relationship("PaymentIntent", back_populates="agent")

    def __repr__(self) -> str:
        return f"<Agent id={self.id!r} status={self.status!r}>"


class Mandate(Base):
    """Institutional spend governance boundary, velocity caps, and category whitelists."""

    __tablename__ = "mandates"

    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    auto_approve_limit = Column(Float, default=1000.0, nullable=False)
    max_cap = Column(Float, default=5000.0, nullable=False)
    po_variance_limit = Column(Float, default=0.02, nullable=False)  # 2% default tolerance
    allowed_categories = Column(JSON, nullable=False, default=list)
    blocked_categories = Column(JSON, nullable=False, default=list)
    allowed_vendors = Column(JSON, nullable=False, default=list)
    cel_rules = Column(Text, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, FROZEN, INACTIVE
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="mandates")
    agent = relationship("Agent", back_populates="mandates")
    payment_intents = relationship("PaymentIntent", back_populates="mandate")

    def __repr__(self) -> str:
        return f"<Mandate id={self.id!r} status={self.status!r} cap={self.max_cap}>"


class Vendor(Base):
    """Commercial counterparties, allowlist verification status, and historical risk."""

    __tablename__ = "vendors"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    is_allowlisted = Column(Boolean, default=False, nullable=False)
    risk_rating = Column(Float, default=0.0, nullable=False)
    dispute_rate = Column(Float, default=0.0, nullable=False)
    paypal_merchant_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")
    contracts = relationship("VendorContract", back_populates="vendor")
    payment_intents = relationship("PaymentIntent", back_populates="vendor")

    def __repr__(self) -> str:
        return f"<Vendor id={self.id!r} allowlisted={self.is_allowlisted}>"


class PurchaseOrder(Base):
    """Pre-negotiated baseline purchase orders for deterministic 3-way matching."""

    __tablename__ = "purchase_orders"

    id = Column(String(64), primary_key=True, index=True)
    vendor_id = Column(String(64), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    items = Column(JSON, nullable=False, default=list)
    terms = Column(String(64), default="Net-30", nullable=False)
    contract_ref = Column(String(64), nullable=True)
    status = Column(String(32), default="OPEN", nullable=False)  # OPEN, MATCHED, CLOSED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="purchase_orders")
    payment_intents = relationship("PaymentIntent", back_populates="purchase_order")

    def __repr__(self) -> str:
        return f"<PurchaseOrder id={self.id!r} amount={self.amount} {self.currency}>"


class VendorContract(Base):
    """Master services agreements and SLAs referenced by purchase orders."""

    __tablename__ = "vendor_contracts"

    id = Column(String(64), primary_key=True, index=True)
    vendor_id = Column(String(64), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    terms = Column(Text, nullable=False)
    sla_details = Column(Text, nullable=False)
    signed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="contracts")

    def __repr__(self) -> str:
        return f"<VendorContract id={self.id!r} vendor_id={self.vendor_id!r}>"


class PaymentIntent(Base):
    """Core stateful payment intent traversing the canonical 12-state lifecycle."""

    __tablename__ = "payment_intents"

    id = Column(String(64), primary_key=True, index=True)
    mandate_id = Column(String(64), ForeignKey("mandates.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(String(64), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    category = Column(String(64), nullable=False, index=True)
    invoice_ref = Column(String(64), nullable=False, index=True)
    po_ref = Column(String(64), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    line_items = Column(JSON, nullable=True, default=list)
    status = Column(String(32), default="PROPOSED", nullable=False, index=True)
    po_match_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    risk_breakdown = Column(JSON, nullable=True)
    policy_evaluation_reasons = Column(JSON, nullable=True, default=list)
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)
    paypal_order_id = Column(String(64), nullable=True, index=True)
    paypal_capture_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    mandate = relationship("Mandate", back_populates="payment_intents")
    agent = relationship("Agent", back_populates="payment_intents")
    vendor = relationship("Vendor", back_populates="payment_intents")
    purchase_order = relationship("PurchaseOrder", back_populates="payment_intents")
    approvals = relationship("ApprovalRecord", back_populates="payment_intent", cascade="all, delete-orphan")
    transactions = relationship("TransactionRecord", back_populates="payment_intent", cascade="all, delete-orphan")
    disputes = relationship("DisputeRecord", back_populates="payment_intent", cascade="all, delete-orphan")
    evidence_nodes = relationship("EvidenceNode", back_populates="payment_intent", cascade="all, delete-orphan")
    evidence_edges = relationship("EvidenceEdge", back_populates="payment_intent", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PaymentIntent id={self.id!r} status={self.status!r} amount={self.amount}>"


class ApprovalRecord(Base):
    """Immutable audit trail of human approver (CFO / Analyst) decisions."""

    __tablename__ = "approval_records"

    id = Column(String(64), primary_key=True, index=True)
    intent_id = Column(String(64), ForeignKey("payment_intents.id", ondelete="CASCADE"), nullable=False, index=True)
    approver_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision = Column(String(32), nullable=False)  # APPROVED, REJECTED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payment_intent = relationship("PaymentIntent", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")

    def __repr__(self) -> str:
        return f"<ApprovalRecord id={self.id!r} decision={self.decision!r}>"


class TransactionRecord(Base):
    """Settled and reconciled PayPal authorizations and captures."""

    __tablename__ = "transaction_records"

    id = Column(String(64), primary_key=True, index=True)
    intent_id = Column(String(64), ForeignKey("payment_intents.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    paypal_order_id = Column(String(64), nullable=False, index=True)
    paypal_capture_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), default="CAPTURED", nullable=False)  # AUTHORIZED, CAPTURED, REFUNDED, RECONCILED
    raw_response = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payment_intent = relationship("PaymentIntent", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<TransactionRecord id={self.id!r} capture_id={self.paypal_capture_id!r}>"


class DisputeRecord(Base):
    """PayPal customer disputes, Evidence Readiness scores, and auto-defense status."""

    __tablename__ = "dispute_records"

    id = Column(String(64), primary_key=True, index=True)  # e.g. "PP-D-99412"
    transaction_id = Column(String(64), nullable=True, index=True)
    intent_id = Column(String(64), ForeignKey("payment_intents.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    reason = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="OPEN", nullable=False)  # OPEN, UNDER_REVIEW, EVIDENCE_SUBMITTED, RESOLVED_BUYER, RESOLVED_SELLER
    evidence_package = Column(JSON, nullable=True)
    readiness_score = Column(Float, nullable=True)
    defense_narrative = Column(Text, nullable=True)
    sla_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    payment_intent = relationship("PaymentIntent", back_populates="disputes")

    def __repr__(self) -> str:
        return f"<DisputeRecord id={self.id!r} status={self.status!r} readiness={self.readiness_score}>"


class AuditBlock(Base):
    """Cryptographic SHA-256 Merkle hash-chained ledger block for immutable auditing."""

    __tablename__ = "audit_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_index = Column(Integer, unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False, index=True)
    actor = Column(String(64), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    merkle_root = Column(String(64), nullable=False)
    block_hash = Column(String(64), nullable=False, unique=True)
    details = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditBlock #{self.block_index} event={self.event_type!r} hash={self.block_hash[:8]}...>"


class WebhookEvent(Base):
    """Incoming PayPal webhook registry for cryptographic signature check and replay deduplication."""

    __tablename__ = "webhook_events"

    event_id = Column(String(128), primary_key=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    status = Column(String(32), default="PROCESSED", nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<WebhookEvent id={self.event_id!r} type={self.event_type!r}>"


class EvidenceNode(Base):
    """Causal Evidence Graph node representing pre- and post-payment verifiable facts."""

    __tablename__ = "evidence_nodes"

    id = Column(String(64), primary_key=True, index=True)
    intent_id = Column(String(64), ForeignKey("payment_intents.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type = Column(String(64), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    properties = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payment_intent = relationship("PaymentIntent", back_populates="evidence_nodes")

    def __repr__(self) -> str:
        return f"<EvidenceNode id={self.id!r} type={self.node_type!r}>"


class EvidenceEdge(Base):
    """Causal Evidence Graph edge linking facts in the 18-node dispute proof mesh."""

    __tablename__ = "evidence_edges"

    id = Column(String(64), primary_key=True, index=True)
    intent_id = Column(String(64), ForeignKey("payment_intents.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("evidence_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = Column(String(64), ForeignKey("evidence_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_type = Column(String(64), nullable=False, index=True)
    properties = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payment_intent = relationship("PaymentIntent", back_populates="evidence_edges")

    def __repr__(self) -> str:
        return f"<EvidenceEdge {self.source_id} -[{self.edge_type}]-> {self.target_id}>"


def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all relational tables in the configured database engine."""
    Base.metadata.create_all(bind=engine)
