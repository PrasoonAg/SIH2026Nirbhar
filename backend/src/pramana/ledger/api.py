"""
ledger — public API surface.

Layer:  L1
Track:  2
Tier:   1

Exports:
  Append-only SHA-256 forward-linked ledger and chain verification.
  Every state transition is ledgered in the same DB transaction as the change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pramana.shared_kernel.api import PramanaError, sha256_bytes, canonical_json


@dataclass
class LedgerEntry:
    """One immutable ledger record.

    Fields:
        sequence: monotonically increasing per-mapping counter.
        entry_id: globally unique.
        mapping_id: foreign reference (opaque UUID).
        actor_id: who triggered the transition.
        event_kind: string tag (e.g. 'AnchorMatched', 'GateFired').
        payload: arbitrary JSON-serialisable dict.
        prev_hash: SHA-256 of the previous entry's canonical bytes (or '' for the first).
        entry_hash: SHA-256 of this entry's canonical bytes (set after creation).
        occurred_at: UTC timestamp.
    """

    sequence: int
    mapping_id: UUID
    actor_id: UUID
    event_kind: str
    payload: dict[str, Any]
    prev_hash: str
    entry_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    entry_hash: str = field(default="")

    def compute_hash(self) -> str:
        """Return the SHA-256 of this entry's canonical bytes."""
        data = canonical_json({
            "entry_id": str(self.entry_id),
            "sequence": self.sequence,
            "mapping_id": str(self.mapping_id),
            "actor_id": str(self.actor_id),
            "event_kind": self.event_kind,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "occurred_at": self.occurred_at.isoformat(),
        })
        return sha256_bytes(data)


class LedgerError(PramanaError):
    """Ledger integrity failure (chain broken or tampered)."""


class LedgerPort:
    """Protocol for the ledger storage adapter (implemented in adapters/)."""

    def append(self, entry: LedgerEntry) -> LedgerEntry:  # noqa: ARG002
        """Persist entry; returns entry with entry_hash set. Must be inside the caller's transaction."""
        raise NotImplementedError

    def verify_chain(self, mapping_id: UUID) -> bool:  # noqa: ARG002
        """Re-hash every entry for *mapping_id* and check forward links."""
        raise NotImplementedError

    def entries_for(self, mapping_id: UUID) -> list[LedgerEntry]:  # noqa: ARG002
        raise NotImplementedError


from pramana.ledger.domain.chain import create_entry, verify_chain

__all__ = ["LedgerEntry", "LedgerError", "LedgerPort", "create_entry", "verify_chain"]

