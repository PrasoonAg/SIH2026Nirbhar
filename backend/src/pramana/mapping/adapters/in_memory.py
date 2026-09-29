"""
mapping.adapters.in_memory — In-memory repository adapter for Mapping aggregates.
"""
from __future__ import annotations

from typing import Dict, List
from uuid import UUID

from pramana.mapping.api import Mapping, MappingError, MappingRepository, MappingState


class InMemoryMappingRepository(MappingRepository):
    """Stores Mapping aggregates in an in-memory dictionary."""

    def __init__(self) -> None:
        self._store: Dict[UUID, Mapping] = {}

    def get(self, mapping_id: UUID) -> Mapping:
        if mapping_id not in self._store:
            raise MappingError(f"Mapping {mapping_id} not found")
        return self._store[mapping_id]

    def save(self, mapping: Mapping) -> None:
        self._store[mapping.mapping_id] = mapping

    def list_by_state(self, state: MappingState) -> list[Mapping]:
        return [m for m in self._store.values() if m.state == state]
