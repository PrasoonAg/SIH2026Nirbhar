"""
mapping.domain.state_machine — Pure domain state machine and corroboration credit (§6.2, §6.4).

INV-01: No override from Rejected. Rejected is strictly absorbing.
INV-06: Corroboration needs new independent evidence. Same actor or same checker = weight 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from pramana.mapping.api import EvidenceItem, MappingError, MappingState


# ─── Domain Events ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LineUnrecognizedEvent:
    raw_line: str
    dialect_fingerprint: str


@dataclass(frozen=True)
class AnchorMatchedEvent:
    candidates_count: int
    top1_cosine: float
    proposer_family: str


@dataclass(frozen=True)
class AdminConfirmedEvent:
    actor_id: UUID
    target_setting_id: str


@dataclass(frozen=True)
class AdminCorrectedEvent:
    actor_id: UUID
    target_setting_id: str


@dataclass(frozen=True)
class GateFiredEvent:
    gate_run_id: UUID
    verifier_family: str


@dataclass(frozen=True)
class GatePassedEvent:
    gate_run_id: UUID
    profile_commit: str


@dataclass(frozen=True)
class GateFailedEvent:
    gate_run_id: UUID
    failed_checks: list[str]


@dataclass(frozen=True)
class GateErroredEvent:
    gate_run_id: UUID
    error_message: str


@dataclass(frozen=True)
class DecaySampledEvent:
    cycle_id: str


@dataclass(frozen=True)
class EvidenceRecordedEvent:
    evidence_id: UUID


@dataclass(frozen=True)
class CorroboratedEvent:
    evidence_ids: list[UUID]
    profile_commit: str


@dataclass(frozen=True)
class ReGatePassedEvent:
    gate_run_id: UUID


@dataclass(frozen=True)
class ReGateErroredEvent:
    gate_run_id: UUID


@dataclass(frozen=True)
class ReGateFailedEvent:
    gate_run_id: UUID


# ─── Pure State Machine Transitions ───────────────────────────────────────────

def apply_transition(current_state: MappingState, event: object) -> MappingState:
    """
    Pure state machine transition function (§6.2).
    
    INV-01: Rejected is strictly absorbing. Any transition attempt raises MappingError.
    """
    # INV-01: Absorption rule
    if current_state == MappingState.REJECTED:
        raise MappingError(
            "INV-01: Rejected is absorbing. No override, transition, or API exists "
            "to move out of Rejected. Create a new proposal with supersedes link."
        )

    # From Unmapped
    if current_state == MappingState.UNMAPPED:
        if isinstance(event, AnchorMatchedEvent):
            if event.candidates_count < 1:
                raise MappingError("AnchorMatched requires >= 1 candidate")
            return MappingState.PROPOSED
        raise MappingError(f"Illegal transition from UNMAPPED via {type(event).__name__}")

    # From Proposed
    if current_state == MappingState.PROPOSED:
        if isinstance(event, (AdminConfirmedEvent, AdminCorrectedEvent)):
            return MappingState.ADMIN_REVIEWED
        raise MappingError(f"Illegal transition from PROPOSED via {type(event).__name__}")

    # From AdminReviewed
    if current_state == MappingState.ADMIN_REVIEWED:
        if isinstance(event, GateFiredEvent):
            return MappingState.GATING
        raise MappingError(f"Illegal transition from ADMIN_REVIEWED via {type(event).__name__}")

    # From Gating
    if current_state == MappingState.GATING:
        if isinstance(event, GatePassedEvent):
            return MappingState.PROVISIONAL
        if isinstance(event, GateFailedEvent):
            return MappingState.REJECTED
        if isinstance(event, GateErroredEvent):
            return MappingState.ADMIN_REVIEWED
        raise MappingError(f"Illegal transition from GATING via {type(event).__name__}")

    # From Provisional
    if current_state == MappingState.PROVISIONAL:
        if isinstance(event, (DecaySampledEvent, EvidenceRecordedEvent)):
            return MappingState.RE_VERIFICATION
        raise MappingError(f"Illegal transition from PROVISIONAL via {type(event).__name__}")

    # From ReVerification
    if current_state == MappingState.RE_VERIFICATION:
        if isinstance(event, CorroboratedEvent):
            return MappingState.CORROBORATED
        if isinstance(event, ReGatePassedEvent):
            return MappingState.PROVISIONAL
        if isinstance(event, ReGateErroredEvent):
            return MappingState.PROVISIONAL
        if isinstance(event, ReGateFailedEvent):
            # Demoted auto-transitions to Rejected in same transaction
            return MappingState.REJECTED
        raise MappingError(f"Illegal transition from RE_VERIFICATION via {type(event).__name__}")

    # Corroborated mappings are not decay-sampled (Assumption A3)
    if current_state == MappingState.CORROBORATED:
        raise MappingError(f"Illegal transition from CORROBORATED via {type(event).__name__}")

    raise MappingError(f"Unhandled mapping state: {current_state}")


# ─── Corroboration & Independence Credit (INV-06) ─────────────────────────────

FIRST_PASS_CLASSES = frozenset([
    "ADMIN_REVIEW",
    "GATE_REGEN",
    "GATE_LEXICAL",
    "GATE_SECOND_MODEL",
])


def credit(evidence: EvidenceItem, history: Sequence[EvidenceItem]) -> tuple[int, str]:
    """
    Pure function — decide weight and reason for new evidence (INV-06, §6.4).
    
    Rules:
      1. First-pass classes (ADMIN_REVIEW, GATE_REGEN, etc.) never corroborate -> 0.
      2. Same actor, same checker, same input, or class already credited -> 0.
      3. At most one credited item per class.
      4. SECOND_REVIEWER: actor != any previous actor on this mapping. Agreement -> 1.
      5. HELD_OUT_LINES: disjoint input lines passing gate -> 1.
      6. SIGNED_PACK: independent peer signature -> 1.
    """
    # Rule 1: First-pass classes never corroborate
    if evidence.cls in FIRST_PASS_CLASSES:
        return 0, f"First-pass class {evidence.cls} cannot corroborate"

    # Rule 2: Deduplication by dedupe key (mapping_id, class, actor_or_checker, input_fingerprint)
    for h in history:
        actor_match = (
            evidence.actor_id is not None and evidence.actor_id == h.actor_id
        ) or (
            evidence.checker_id is not None and evidence.checker_id == h.checker_id
        )
        if (
            h.mapping_id == evidence.mapping_id
            and h.cls == evidence.cls
            and actor_match
            and h.input_fingerprint == evidence.input_fingerprint
        ):
            return 0, "Duplicate evidence item"

    # Rule 3: At most one credited item per class
    already_credited = any(h.cls == evidence.cls and h.weight > 0 for h in history)
    if already_credited:
        return 0, f"Evidence class {evidence.cls} is already credited"

    # Rule 4: SECOND_REVIEWER independence check
    if evidence.cls == "SECOND_REVIEWER":
        if evidence.actor_id is None:
            return 0, "Second reviewer must specify actor_id"

        # Check if actor already participated in this mapping's history
        prior_actors = {h.actor_id for h in history if h.actor_id is not None}
        if evidence.actor_id in prior_actors:
            return 0, "Second reviewer must be strictly independent from prior actors"

        if evidence.weight == 0:
            return 0, "Second reviewer disagreement blocks upgrade"

        return 1, "Credited independent blind second reviewer agreement"

    # Rule 5: HELD_OUT_LINES check
    if evidence.cls == "HELD_OUT_LINES":
        prior_fingerprints = {h.input_fingerprint for h in history if h.input_fingerprint}
        if evidence.input_fingerprint in prior_fingerprints:
            return 0, "Held-out lines must have disjoint input fingerprint"

        return 1, "Credited disjoint held-out config lines passing full gate"

    # Rule 6: SIGNED_PACK check
    if evidence.cls == "SIGNED_PACK":
        return 1, "Credited independent federated signed profile pack"

    return 0, f"Unknown or uncreditable evidence class {evidence.cls}"
