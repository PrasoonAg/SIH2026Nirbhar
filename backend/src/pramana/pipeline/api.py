"""
pipeline.api — Public surface for the pipeline module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


# ─── Job lifecycle ────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    """Background audit job record."""
    job_id: str
    artifact_id: str
    device_id: str
    profile_commit: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0          # 0–100
    error: str | None = None
    result: dict[str, Any] | None = None


# ─── Audit result ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuditResult:
    """
    Fully resolved audit result for one device (INV-07 / INV-08).
    Two scores, always together. All findings carry trust class.
    """
    job_id: str
    device_id: str
    artifact_id: str
    profile_commit: str
    vendor_id: str

    # Two-number score (INV-07)
    verified_score: str | None        # formatted "71.4" or None
    provisional_inclusive_score: str | None
    provisional_dependence: str | None
    verified_numerator: int | None
    verified_denominator: int | None
    provisional_inclusive_numerator: int | None
    provisional_inclusive_denominator: int | None

    # Findings (INV-08)
    findings: tuple[dict[str, Any], ...]

    # Metadata
    total_lines: int
    recognized_lines: int
    unrecognized_lines: int


# ─── Error ────────────────────────────────────────────────────────────────────

class PipelineError(Exception):
    """Orchestration failure."""


# ─── Port protocol ────────────────────────────────────────────────────────────

class PipelineService(Protocol):
    """Port — implemented in pipeline/service.py (injected by bootstrap)."""

    def start_audit(
        self,
        artifact_id: str,
        device_id: str,
        profile_commit: str = "HEAD",
    ) -> Job:
        """Start an audit job and return immediately with the job record."""
        ...

    def get_job(self, job_id: str) -> Job:
        """Return the current status of a job."""
        ...

    def run_audit_sync(
        self,
        artifact_id: str,
        device_id: str,
        profile_commit: str = "HEAD",
    ) -> AuditResult:
        """Run an audit synchronously (for testing and CLI). Returns result directly."""
        ...
