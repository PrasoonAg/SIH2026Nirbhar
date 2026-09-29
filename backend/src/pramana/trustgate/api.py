"""
trustgate — public API surface.

Layer:  L2
Track:  2
Tier:   1  (self-audit harness T2)

INV-02: trustgate NEVER imports proposer and vice versa.
INV-03: Gate = AND of three checks. All three always run.

Exports:
  3 checks, gate orchestrator, family guard, GateReport, self-audit seam.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from pramana.shared_kernel.api import ModelCard, PramanaError


class CheckVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CheckResult:
    name: str
    verdict: CheckVerdict
    metrics: dict[str, object]
    artifacts: dict[str, object]
    checker_id: str
    duration_ms: float


class GateOutcome(str, Enum):
    PASSED = "PASSED"       # all three PASS
    FAILED = "FAILED"       # any FAIL (FAIL dominates ERROR)
    ERRORED = "ERRORED"     # >= 1 ERROR, no FAIL → mapping stays AdminReviewed


@dataclass(frozen=True)
class GateReport:
    """
    Persisted gate run record (§6.3).
    Identical inputs → identical reports apart from timestamps and durations.
    """
    gate_run_id: UUID
    mapping_id: UUID
    gate_config_hash: str   # SHA-256 of gate_config.yaml
    proposer_card: ModelCard
    verifier_card: ModelCard
    check_results: tuple[CheckResult, ...]
    outcome: GateOutcome


class TrustGateError(PramanaError):
    """Infrastructure failure during a gate run (maps to ERROR, not FAIL)."""


class TrustGateService:
    """
    Orchestrate all three checks for a candidate mapping.
    STUB — full implementation in Phase 4.
    """

    def run_gate(
        self,
        mapping_id: UUID,
        support_lines: list[bytes],
    ) -> GateReport:  # noqa: ARG002
        raise NotImplementedError("Phase 4")


class VerifierPort:
    """Protocol for the second-model adapter (different family from MiniLM)."""

    def rank(
        self,
        line_bytes: bytes,
        candidates: list[str],
    ) -> list[float]:  # noqa: ARG002
        """Return normalised scores in the same order as *candidates*."""
        raise NotImplementedError


__all__ = [
    "CheckVerdict",
    "CheckResult",
    "GateOutcome",
    "GateReport",
    "TrustGateError",
    "TrustGateService",
    "VerifierPort",
]
