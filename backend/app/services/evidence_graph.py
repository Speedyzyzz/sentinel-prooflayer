"""Causal Evidence Property Graph Engine for Sentinel & ProofLayer.

Implements all 18 verifiable node types and 13 directed edge types:
- Node Types: AGENT_MANDATE, PAYMENT_INTENT, POLICY_DECISION, APPROVAL_RECORD,
  VENDOR, PURCHASE_ORDER, CONTRACT, INVOICE, PAYPAL_ORDER, PAYPAL_CAPTURE,
  PAYPAL_REFUND, SHIPMENT, DELIVERY_CONFIRMATION, CUSTOMER_SESSION,
  SUPPORT_TICKET, DISPUTE, EVIDENCE_DOCUMENT, EVIDENCE_CLAIM.
- Edge Types: AUTHORIZED_BY, VALIDATED_BY, REFERENCES, MATCHES, PAID_BY,
  CAPTURED_AS, REFUNDED_BY, DISPUTED_BY, REQUIRES, SUPPORTS, CONTRADICTS,
  CITES, OCCURRED_AT.

Supports bidirectional traversal, sub-graph extraction, and database hydration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.orm import Session

from app.database import EvidenceEdge as DBEvidenceEdge, EvidenceNode as DBEvidenceNode


class InvalidGraphElementError(Exception):
    """Raised when an unrecognized node type or edge type is added to the graph."""
    def __init__(self, message: str):
        super().__init__(message)


class CausalGraph:
    """In-memory and persistent property graph engine for dispute auto-defense."""

    NODE_TYPES: Set[str] = {
        "AGENT_MANDATE",
        "PAYMENT_INTENT",
        "POLICY_DECISION",
        "APPROVAL_RECORD",
        "VENDOR",
        "PURCHASE_ORDER",
        "CONTRACT",
        "INVOICE",
        "PAYPAL_ORDER",
        "PAYPAL_CAPTURE",
        "PAYPAL_REFUND",
        "SHIPMENT",
        "DELIVERY_CONFIRMATION",
        "CUSTOMER_SESSION",
        "SUPPORT_TICKET",
        "DISPUTE",
        "EVIDENCE_DOCUMENT",
        "EVIDENCE_CLAIM",
    }

    EDGE_TYPES: Set[str] = {
        "AUTHORIZED_BY",
        "VALIDATED_BY",
        "REFERENCES",
        "MATCHES",
        "PAID_BY",
        "CAPTURED_AS",
        "REFUNDED_BY",
        "DISPUTED_BY",
        "REQUIRES",
        "SUPPORTS",
        "CONTRADICTS",
        "CITES",
        "OCCURRED_AT",
    }

    def __init__(self, intent_id: Optional[str] = None):
        self.intent_id = intent_id
        self._nodes: Dict[str, Dict[str, Any]] = {}
        # source_id -> list of edge dicts
        self._outgoing: Dict[str, List[Dict[str, Any]]] = {}
        # target_id -> list of edge dicts
        self._incoming: Dict[str, List[Dict[str, Any]]] = {}
        self._edges: List[Dict[str, Any]] = []

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        properties: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Add a factual evidence node to the graph."""
        if node_type not in self.NODE_TYPES:
            raise InvalidGraphElementError(f"Invalid node type '{node_type}'. Must be one of: {sorted(self.NODE_TYPES)}")

        props = properties or {}
        node = {
            "id": node_id,
            "intent_id": self.intent_id or props.get("intent_id", ""),
            "node_type": node_type,
            "label": label,
            "properties": props,
            "created_at": created_at or datetime.utcnow(),
        }
        self._nodes[node_id] = node
        if node_id not in self._outgoing:
            self._outgoing[node_id] = []
        if node_id not in self._incoming:
            self._incoming[node_id] = []
        return node

    def add_edge(
        self,
        edge_id: str,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Add a causal relationship edge between two existing nodes."""
        if edge_type not in self.EDGE_TYPES:
            raise InvalidGraphElementError(f"Invalid edge type '{edge_type}'. Must be one of: {sorted(self.EDGE_TYPES)}")

        if source_id not in self._nodes:
            raise InvalidGraphElementError(f"Source node '{source_id}' does not exist in graph.")
        if target_id not in self._nodes:
            raise InvalidGraphElementError(f"Target node '{target_id}' does not exist in graph.")

        edge_props = properties or {}
        edge = {
            "id": edge_id,
            "intent_id": self.intent_id or edge_props.get("intent_id", ""),
            "source_id": source_id,
            "target_id": target_id,
            "edge_type": edge_type,
            "properties": edge_props,
            "created_at": created_at or datetime.utcnow(),
        }
        self._edges.append(edge)
        self._outgoing[source_id].append(edge)
        self._incoming[target_id].append(edge)
        return edge

    def has_node(self, node_id: str) -> bool:
        """Check whether a given node exists in the graph."""
        return node_id in self._nodes

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve node dictionary by ID."""
        return self._nodes.get(node_id)

    def find_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """Filter nodes by node type."""
        return [node for node in self._nodes.values() if node["node_type"] == node_type]

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """Retrieve neighboring nodes connected via incoming/outgoing edges."""
        neighbors: List[Dict[str, Any]] = []
        if direction in ("out", "both") and node_id in self._outgoing:
            for edge in self._outgoing[node_id]:
                target = self._nodes.get(edge["target_id"])
                if target and target not in neighbors:
                    neighbors.append(target)
        if direction in ("in", "both") and node_id in self._incoming:
            for edge in self._incoming[node_id]:
                source = self._nodes.get(edge["source_id"])
                if source and source not in neighbors:
                    neighbors.append(source)
        return neighbors

    def get_edges(self) -> List[Dict[str, Any]]:
        """Return all edges in the graph."""
        return list(self._edges)

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Return all nodes in the graph."""
        return list(self._nodes.values())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize property graph to JSON-friendly payload."""
        return {
            "intent_id": self.intent_id or "",
            "nodes": [
                {
                    "id": n["id"],
                    "intent_id": n.get("intent_id", self.intent_id or ""),
                    "node_type": n["node_type"],
                    "label": n["label"],
                    "properties": n["properties"],
                    "created_at": n["created_at"].isoformat() if isinstance(n["created_at"], datetime) else str(n["created_at"]),
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "id": e["id"],
                    "intent_id": e.get("intent_id", self.intent_id or ""),
                    "source_id": e["source_id"],
                    "target_id": e["target_id"],
                    "edge_type": e["edge_type"],
                    "properties": e["properties"],
                    "created_at": e["created_at"].isoformat() if isinstance(e["created_at"], datetime) else str(e["created_at"]),
                }
                for e in self._edges
            ],
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
        }

    # -----------------------------------------------------------------------
    # Database Hydration & Persistence
    # -----------------------------------------------------------------------

    @classmethod
    def from_db(cls, db: Session, intent_id: str) -> CausalGraph:
        """Hydrate CausalGraph from database tables for a given intent."""
        graph = cls(intent_id=intent_id)

        db_edges = db.query(DBEvidenceEdge).filter(DBEvidenceEdge.intent_id == intent_id).all()
        edge_node_ids = set()
        for edge in db_edges:
            edge_node_ids.add(edge.source_id)
            edge_node_ids.add(edge.target_id)

        query = db.query(DBEvidenceNode).filter(DBEvidenceNode.intent_id == intent_id)
        if edge_node_ids:
            query = db.query(DBEvidenceNode).filter(
                (DBEvidenceNode.intent_id == intent_id) | (DBEvidenceNode.id.in_(edge_node_ids))
            )
        db_nodes = query.all()

        for node in db_nodes:
            graph.add_node(
                node_id=node.id,
                node_type=node.node_type,
                label=node.label,
                properties=node.properties or {},
                created_at=node.created_at,
            )

        for edge in db_edges:
            if graph.has_node(edge.source_id) and graph.has_node(edge.target_id):
                graph.add_edge(
                    edge_id=edge.id,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    edge_type=edge.edge_type,
                    properties=edge.properties or {},
                    created_at=edge.created_at,
                )

        return graph

    def save_to_db(self, db: Session, intent_id: Optional[str] = None) -> None:
        """Persist in-memory graph to evidence_nodes and evidence_edges tables."""
        target_intent = intent_id or self.intent_id
        if not target_intent:
            return

        # Insert or update nodes
        for node in self._nodes.values():
            existing_node = db.query(DBEvidenceNode).filter(DBEvidenceNode.id == node["id"]).first()
            if not existing_node:
                db_node = DBEvidenceNode(
                    id=node["id"],
                    intent_id=target_intent,
                    node_type=node["node_type"],
                    label=node["label"],
                    properties=node["properties"],
                    created_at=node["created_at"] if isinstance(node["created_at"], datetime) else datetime.utcnow(),
                )
                db.add(db_node)

        db.flush()

        # Insert or update edges
        for edge in self._edges:
            existing_edge = db.query(DBEvidenceEdge).filter(DBEvidenceEdge.id == edge["id"]).first()
            if not existing_edge:
                db_edge = DBEvidenceEdge(
                    id=edge["id"],
                    intent_id=target_intent,
                    source_id=edge["source_id"],
                    target_id=edge["target_id"],
                    edge_type=edge["edge_type"],
                    properties=edge["properties"],
                    created_at=edge["created_at"] if isinstance(edge["created_at"], datetime) else datetime.utcnow(),
                )
                db.add(db_edge)

        db.commit()
