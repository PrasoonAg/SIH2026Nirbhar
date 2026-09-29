"""
ledger.domain.chain — Pure domain logic for SHA-256 forward-linked ledger (INV-12).

R3: No framework in domain/.
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID

from pramana.ledger.api import LedgerEntry, LedgerError


def create_entry(
    sequence: int,
    mapping_id: UUID,
    actor_id: UUID,
    event_kind: str,
    payload: dict,
    prev_hash: str = "",
) -> LedgerEntry:
    """Create a new LedgerEntry and compute its SHA-256 forward link hash."""
    entry = LedgerEntry(
        sequence=sequence,
        mapping_id=mapping_id,
        actor_id=actor_id,
        event_kind=event_kind,
        payload=payload,
        prev_hash=prev_hash,
    )
    entry.entry_hash = entry.compute_hash()
    return entry


def verify_chain(entries: Sequence[LedgerEntry]) -> bool:
    """
    Verify the cryptographic forward hash-chain of ledger entries (INV-12).
    
    Returns True iff:
      1. Every entry's entry_hash matches its recomputed canonical content hash.
      2. The first entry has prev_hash == "" (or None).
      3. Every subsequent entry's prev_hash exactly equals the preceding entry's entry_hash.
      4. Sequence numbers strictly increment by 1 starting from 1.
    """
    if not entries:
        return True

    prev_hash = ""
    for idx, entry in enumerate(entries):
        expected_seq = idx + 1
        if entry.sequence != expected_seq:
            return False

        # Verify prev_hash link
        if idx == 0:
            if entry.prev_hash not in ("", None):
                return False
        else:
            if entry.prev_hash != prev_hash:
                return False

        # Verify content integrity
        recomputed = entry.compute_hash()
        if entry.entry_hash != recomputed:
            return False

        prev_hash = entry.entry_hash

    return True
