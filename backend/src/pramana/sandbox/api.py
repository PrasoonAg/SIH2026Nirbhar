"""
sandbox — public API surface.

Layer:  L5
Track:  3
Tier:   2

Exports:
  Scratch copy, apply remediation, re-audit, delta.
  simulate() measures the actual delta by running a real re-audit.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pramana.shared_kernel.api import PramanaError


@dataclass(frozen=True)
class RemediationDelta:
    """Before/after for BOTH scores after applying the remediation patch."""
    device_audit_id: UUID
    check_id: str
    verified_before: str | None
    verified_after: str | None
    provisional_before: str | None
    provisional_after: str | None
    resolved_findings: list[str]
    regressions: list[str]       # newly failing checks


class SandboxError(PramanaError):
    """Simulation failure."""


class SandboxService:
    """
    T2 — Simulation Sandbox.
    simulate() = apply remediation to an in-memory scratch copy, then re-audit.
    STUB — full implementation in Phase 8.
    """

    def simulate(
        self,
        device_audit_id: UUID,
        check_id: str,
    ) -> RemediationDelta:  # noqa: ARG002
        raise NotImplementedError("Phase 8 (T2)")


__all__ = ["RemediationDelta", "SandboxError", "SandboxService"]
