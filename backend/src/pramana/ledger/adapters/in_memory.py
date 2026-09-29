"""
ledger.adapters.in_memory — In-memory ledger repository adapter for testing and lightweight runtime.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List
from uuid import UUID

from pramana.ledger.api import LedgerEntry, LedgerPort
from pramana.ledger.domain.chain import verify_chain


class InMemoryLedgerAdapter(LedgerPort):
    """Stores ledger entries in-memory partitioned by mapping_id."""

    def __init__(self) -> None:
        self._chains: Dict[UUID, List[LedgerEntry]] = defaultdict(list)

    def append(self, entry: LedgerEntry) -> LedgerEntry:
        """Append entry with proper hash computation to the mapping chain."""
        chain = self._chains[entry.mapping_id]
        if not entry.entry_hash:
            entry.entry_hash = entry.compute_hash()
        chain.append(entry)
        return entry

    def verify_chain(self, mapping_id: UUID) -> bool:
        """Verify the integrity of mapping_id's forward hash-chain."""
        chain = self._chains.get(mapping_id, [])
        return verify_chain(chain)

    def entries_for(self, mapping_id: UUID) -> list[LedgerEntry]:
        """Return shallow copy of all entries for mapping_id ordered by sequence."""
        return list(self._chains.get(mapping_id, []))
