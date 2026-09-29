"""
mapping — public API surface.

Layer:  L3
Track:  2
Tier:   1  (decay T2)

Exports:
  Mapping aggregate + state machine, spec induction, evidence + corroboration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from pramana.shared_kernel.api import PramanaError, DomainEvent
from pramana.proposer.api import Proposal


class MappingState(str, Enum):
    UNMAPPED = "Unmapped"
    PROPOSED = "Proposed"
    ADMIN_REVIEWED = "AdminReviewed"
    GATING = "Gating"           # transient — same transaction as gate run
    PROVISIONAL = "Provisional"
    RE_VERIFICATION = "ReVerification"
    CORROBORATED = "Corroborated"
    DEMOTED = "Demoted"         # transient — auto-transitions to Rejected
    REJECTED = "Rejected"       # absorbing (INV-01)


class MappingError(PramanaError):
    """State machine violation or mapping persistence failure."""


@dataclass(frozen=True)
class EvidenceItem:
    """One corroboration evidence item (§6.4)."""
    evidence_id: UUID
    mapping_id: UUID
    cls: str                    # "SECOND_REVIEWER", "HELD_OUT_LINES", "SIGNED_PACK"
    actor_id: UUID | None
    checker_id: str | None
    input_fingerprint: str
    payload_ref: str
    weight: int                 # 0 or 1
    reason: str


def credit(evidence: EvidenceItem, history: list[EvidenceItem]) -> tuple[int, str]:
    """
    Pure function — decide weight and reason for new evidence (INV-06).
    Same actor, same checker, same input, or class already credited → weight 0.
    """
    from pramana.mapping.domain.state_machine import credit as _credit
    return _credit(evidence, history)


@dataclass
class Mapping:
    """
    Aggregate root for the trust lifecycle state machine.
    All transitions are pure domain methods; adapters handle persistence.
    """
    mapping_id: UUID
    vendor_id: str
    state: MappingState
    dialect_fingerprint: str
    proposal: Proposal | None = None
    spec: object | None = None          # MappingSpec; typed as object to avoid circular import
    evidence_items: list[EvidenceItem] = field(default_factory=list)
    supersedes: UUID | None = None

    def transition(self, event: object) -> MappingState:
        """
        Apply *event* and transition state.
        Rejected is absorbing — raises MappingError if attempted (INV-01).
        """
        from pramana.mapping.domain.state_machine import apply_transition
        self.state = apply_transition(self.state, event)
        return self.state


class MappingRepository:
    """Protocol for the mapping persistence adapter."""

    def get(self, mapping_id: UUID) -> Mapping:  # noqa: ARG002
        raise NotImplementedError

    def save(self, mapping: Mapping) -> None:  # noqa: ARG002
        raise NotImplementedError

    def list_by_state(self, state: MappingState) -> list[Mapping]:  # noqa: ARG002
        raise NotImplementedError


from pramana.mapping.domain.induce import induce_spec

__all__ = [
    "MappingState",
    "MappingError",
    "EvidenceItem",
    "credit",
    "Mapping",
    "MappingRepository",
    "induce_spec",
]

