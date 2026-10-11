"""Append-Only SHA-256 Merkle Chain Audit Ledger & Cryptographic Verifier.

Implements:
1. Canonical JSON serialization and payload hashing.
2. SHA-256 block hash chaining and rolling Merkle root calculation.
3. Genesis block initialization.
4. verify_chain(blocks) returning (is_valid, message, tampered_block_index)
   capable of pinpointing the exact corrupted block index upon tampering.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.orm import Session

from app.database import AuditBlock


def canonical_json(data: Optional[Dict[str, Any]]) -> str:
    """Produce deterministic canonical JSON string for cryptographic hashing."""
    if data is None:
        data = {}
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_payload_hash(data: Optional[Dict[str, Any]]) -> str:
    """Calculate SHA-256 digest of canonical JSON payload."""
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def compute_block_hash(
    block_index: int,
    timestamp_str: str,
    event_type: str,
    actor: str,
    payload_hash: str,
    prev_hash: str,
    merkle_root: str,
) -> str:
    """Compute overall SHA-256 block digest from chained components."""
    preimage = f"{block_index}:{timestamp_str}:{event_type}:{actor}:{payload_hash}:{prev_hash}:{merkle_root}"
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


class AuditLedgerService:
    """Cryptographic audit ledger service for Sentinel mandate and payment events."""

    GENESIS_PREV_HASH = "0" * 64

    @classmethod
    def initialize_genesis_block(cls, db: Session) -> AuditBlock:
        """Create and persist the immutable Genesis Block (index 0) if not present."""
        existing_genesis = db.query(AuditBlock).filter(AuditBlock.block_index == 0).first()
        if existing_genesis:
            return existing_genesis

        ts = datetime(2026, 1, 1, 0, 0, 0)
        ts_str = ts.isoformat()
        payload_data: Dict[str, Any] = {"system": "Sentinel-ProofLayer-Genesis", "version": "1.0.0"}
        payload_hash = compute_payload_hash(payload_data)
        prev_hash = cls.GENESIS_PREV_HASH
        merkle_root = hashlib.sha256(payload_hash.encode("utf-8")).hexdigest()
        block_hash = compute_block_hash(
            block_index=0,
            timestamp_str=ts_str,
            event_type="GENESIS",
            actor="system",
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            merkle_root=merkle_root,
        )

        genesis_block = AuditBlock(
            block_index=0,
            timestamp=ts,
            event_type="GENESIS",
            entity_type="SYSTEM",
            entity_id="sentinel_genesis",
            actor="system",
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            merkle_root=merkle_root,
            block_hash=block_hash,
            details=payload_data,
        )
        db.add(genesis_block)
        db.commit()
        db.refresh(genesis_block)
        return genesis_block

    @classmethod
    def append_block(
        cls,
        db: Session,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> AuditBlock:
        """Append a new tamper-evident audit block to the cryptographic chain."""
        # Ensure genesis exists
        latest_block = db.query(AuditBlock).order_by(AuditBlock.block_index.desc()).first()
        if not latest_block:
            latest_block = cls.initialize_genesis_block(db)

        next_index = latest_block.block_index + 1
        ts = timestamp or datetime.utcnow()
        ts_str = ts.isoformat()
        payload_dict = details or {}
        payload_hash = compute_payload_hash(payload_dict)
        prev_hash = latest_block.block_hash
        merkle_root = hashlib.sha256((latest_block.merkle_root + payload_hash).encode("utf-8")).hexdigest()
        block_hash = compute_block_hash(
            block_index=next_index,
            timestamp_str=ts_str,
            event_type=event_type,
            actor=actor,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            merkle_root=merkle_root,
        )

        new_block = AuditBlock(
            block_index=next_index,
            timestamp=ts,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            merkle_root=merkle_root,
            block_hash=block_hash,
            details=payload_dict,
        )
        db.add(new_block)
        db.commit()
        db.refresh(new_block)
        return new_block

    @classmethod
    def verify_chain(
        cls,
        blocks: List[Union[AuditBlock, Dict[str, Any]]],
    ) -> Tuple[bool, str, Optional[int]]:
        """Verify complete cryptographic integrity of the audit chain.

        Returns:
            Tuple of (is_valid, message, tampered_block_index)
        """
        if not blocks:
            return True, "Empty ledger is valid", None

        # Sort blocks by index to ensure sequential verification
        sorted_blocks = sorted(
            blocks,
            key=lambda b: b.block_index if isinstance(b, AuditBlock) else b.get("block_index", 0),
        )

        for i, block in enumerate(sorted_blocks):
            # Extract attributes whether ORM or dict
            if isinstance(block, AuditBlock):
                idx = block.block_index
                ts = block.timestamp
                event_type = block.event_type
                actor = block.actor
                payload_hash = block.payload_hash
                prev_hash = block.prev_hash
                merkle_root = block.merkle_root
                block_hash = block.block_hash
                details = block.details
            else:
                idx = block.get("block_index", i)
                ts = block.get("timestamp")
                event_type = block.get("event_type", "")
                actor = block.get("actor", "")
                payload_hash = block.get("payload_hash", "")
                prev_hash = block.get("prev_hash", "")
                merkle_root = block.get("merkle_root", "")
                block_hash = block.get("block_hash", "")
                details = block.get("details", {})

            ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)

            # 1. Verify payload hash integrity
            expected_payload_hash = compute_payload_hash(details)
            if payload_hash != expected_payload_hash:
                return False, f"Payload hash mismatch at block {idx}", idx

            # 2. Verify previous hash chaining
            if idx == 0:
                if prev_hash != cls.GENESIS_PREV_HASH:
                    return False, f"Invalid genesis previous hash at block 0", 0
            else:
                prev_b = sorted_blocks[i - 1]
                prev_b_hash = prev_b.block_hash if isinstance(prev_b, AuditBlock) else prev_b.get("block_hash")
                if prev_hash != prev_b_hash:
                    return (
                        False,
                        f"Chain broken: block {idx} previous_hash does not match block {idx - 1} block_hash",
                        idx,
                    )

            # 3. Verify Merkle root rolling calculation
            if idx == 0:
                expected_merkle_root = hashlib.sha256(expected_payload_hash.encode("utf-8")).hexdigest()
            else:
                prev_b = sorted_blocks[i - 1]
                prev_b_merkle = prev_b.merkle_root if isinstance(prev_b, AuditBlock) else prev_b.get("merkle_root")
                expected_merkle_root = hashlib.sha256(
                    (prev_b_merkle + expected_payload_hash).encode("utf-8")
                ).hexdigest()

            if merkle_root != expected_merkle_root:
                return False, f"Merkle root mismatch at block {idx}", idx

            # 4. Verify block hash calculation
            expected_block_hash = compute_block_hash(
                block_index=idx,
                timestamp_str=ts_str,
                event_type=event_type,
                actor=actor,
                payload_hash=expected_payload_hash,
                prev_hash=prev_hash,
                merkle_root=expected_merkle_root,
            )
            if block_hash != expected_block_hash:
                return False, f"Block hash tampering detected at block {idx}", idx

        return True, f"Ledger verified ({len(sorted_blocks)} blocks intact)", None
