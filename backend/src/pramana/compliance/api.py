"""
compliance.api — Public surface for the compliance module.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, Sequence

from pramana.baseline.api import NormalizedBaseline
from pramana.shared_kernel.api import Severity


# ─── Frameworks ───────────────────────────────────────────────────────────────

class Framework(str, Enum):
    """Compliance framework identifiers."""
    NIST = "NIST SP 800-53"
    CIS = "CIS"
    STIG = "STIG"
    ISO = "ISO/IEC 27001"


@dataclass(frozen=True)
class FrameworkRef:
    """A reference to a specific control in a compliance framework."""
    framework: Framework
    control_id: str
    title: str
    required_state: str       # "present", "absent", "configured"
    source: str
    source_version: str
    verified: bool            # False = paraphrase only, not authoritative text


# ─── Blast radius ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BlastRadiusRule:
    """Describes the operational risk of applying a remediation."""
    category: str    # "session", "acl", "routing", etc.
    level: str       # "HIGH", "MEDIUM", "LOW"
    note: str


# ─── Check ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Check:
    """
    A declarative compliance check (§8).

    `predicate` is pure declarative data — never eval'd (R9).
    """
    check_id: str
    title: str
    severity: Severity
    predicate: dict[str, Any]          # declarative: all_of / any_of / not / {setting, op, value}
    evidence_selector: dict[str, Any]
    remediation: dict[str, Any]        # vendor_id → {diff, rationale}
    blast_radius: tuple[BlastRadiusRule, ...]
    framework_refs: tuple[FrameworkRef, ...]


# ─── Finding ──────────────────────────────────────────────────────────────────

class FindingStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNEVALUATED = "unevaluated"


@dataclass(frozen=True)
class Finding:
    """
    Result of evaluating one Check against one device's baseline (INV-08).
    Always carries trust class and evidence pointers.
    """
    check_id: str
    device_id: str
    status: FindingStatus
    trust: str                         # TrustLevel value
    blast_radius_flag: bool
    unevaluated_reason: str | None
    evidence_line_refs: tuple[dict[str, Any], ...]


# ─── Port protocol ────────────────────────────────────────────────────────────

class ComplianceService(Protocol):
    """Port — implemented by ComplianceServiceImpl (injected by bootstrap)."""

    def evaluate(
        self,
        baseline: NormalizedBaseline,
        device_id: str,
        profile_commit: str,
    ) -> list[Finding]:
        ...
