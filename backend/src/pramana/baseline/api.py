"""
baseline.api — NormalizedBaseline and related types.

Public surface for the baseline module.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence


# ─── Provenance ───────────────────────────────────────────────────────────────

class Provenance(str, Enum):
    """How an observation's setting_id was determined."""
    DETERMINISTIC = "deterministic"   # Hand-written grammar recognized it
    PROPOSED = "proposed"             # AI proposer → gate passed


# ─── Line reference ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LineRef:
    """Pointer back to a specific line in the source artifact."""
    artifact_sha256: str
    line_no: int
    byte_span: tuple[int, int]


# ─── Observation ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Observation:
    """
    One parsed setting observation from a config file.

    `setting_id` is "__raw__" until a mapping is resolved (Phase 1 → compliance).
    `typed_value` is the token list for Cisco IOS; structured dict for others.
    """
    setting_id: str
    typed_value: Any
    scope: str
    provenance: Provenance
    line_ref: LineRef
    mapping_id: str | None  # None until proposer → gate assigns one


# ─── Unrecognized line ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class UnrecognizedLine:
    """A config line the parser could not classify."""
    raw: str
    line_no: int
    byte_span: tuple[int, int]
    reason: str


# ─── Normalized baseline ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class NormalizedBaseline:
    """
    Vendor-normalized view of a config artifact.
    Immutable after creation (frozen dataclass).
    """
    vendor_id: str
    observations: tuple[Observation, ...]
    unrecognized: tuple[UnrecognizedLine, ...]

    @property
    def recognized_count(self) -> int:
        return len(self.observations)

    @property
    def unrecognized_count(self) -> int:
        return len(self.unrecognized)


# ─── Mapping Specification (§6.1) ───────────────────────────────────────────

from pramana.baseline.domain.mapping_spec import (
    Fragment,
    MappingSpec,
    SlotType,
    Token,
    match,
    render,
)

__all__ = [
    "Provenance",
    "LineRef",
    "Observation",
    "UnrecognizedLine",
    "NormalizedBaseline",
    "SlotType",
    "Token",
    "MappingSpec",
    "Fragment",
    "match",
    "render",
]
