"""
pipeline.service — PipelineService implementation (Phase 1 synchronous core).

Resolves: artifact bytes → parse → compliance → score → AuditResult.
Phase 1: all checks are DETERMINISTIC (no proposer, no gate).
Phase 4: wires real profile mappings, gate, and proposer.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from pramana.compliance.api import ComplianceService, Finding, FindingStatus
from pramana.compliance.domain.engine import ComplianceServiceImpl
from pramana.compliance.domain.seed_checks import SEED_CHECKS_PHASE1
from pramana.ingest.api import IngestService
from pramana.parsing.api import ParsingService
from pramana.parsing.service import ParsingServiceImpl
from pramana.pipeline.api import AuditResult, Job, JobStatus, PipelineError, PipelineService
from pramana.scoring.api import (
    CheckOutcome,
    CheckStatus,
    ScoreComponents,
    TrustLevel,
    compute_score,
    format_score,
)
from pramana.shared_kernel.api import new_id, NotFoundError


def _finding_to_check_outcome(f: Finding, weight: int) -> CheckOutcome:
    """Convert a compliance Finding to a scoring CheckOutcome."""
    status_map = {
        FindingStatus.PASS: CheckStatus.PASS,
        FindingStatus.FAIL: CheckStatus.FAIL,
        FindingStatus.UNEVALUATED: CheckStatus.UNEVALUATED,
    }
    return CheckOutcome(
        check_id=f.check_id,
        device_id=f.device_id,
        weight=weight,
        status=status_map[f.status],
        trust=TrustLevel(f.trust),
        evidence_ids=tuple(
            str(ev.get("line_no", "")) for ev in f.evidence_line_refs
        ),
    )


class PipelineServiceImpl(PipelineService):
    """
    Phase 1 synchronous pipeline.
    Jobs are stored in memory (Phase 2: DB-backed).
    """

    def __init__(
        self,
        ingest_svc: IngestService,
        parsing_svc: ParsingService | None = None,
        compliance_svc: ComplianceService | None = None,
    ) -> None:
        self._ingest = ingest_svc
        self._parsing: ParsingService = parsing_svc or ParsingServiceImpl()
        self._compliance: ComplianceService = compliance_svc or ComplianceServiceImpl(
            SEED_CHECKS_PHASE1
        )
        # check_id → weight (from seed checks)
        self._check_weights = {c.check_id: c.severity.weight for c in SEED_CHECKS_PHASE1}
        self._jobs: dict[str, Job] = {}

    def run_audit_sync(
        self,
        artifact_id: str,
        device_id: str,
        profile_commit: str = "HEAD",
    ) -> AuditResult:
        """Run a full audit synchronously. Used by tests and CLI."""
        raw_bytes = self._ingest.read_artifact_bytes(artifact_id)
        artifact = self._ingest.get_artifact(artifact_id)

        # Parse
        parse_result = self._parsing.parse(raw_bytes, artifact.sha256)

        # Compliance
        findings = self._compliance.evaluate(
            parse_result.baseline, device_id, profile_commit
        )

        # Score
        outcomes = [
            _finding_to_check_outcome(f, self._check_weights.get(f.check_id, 1))
            for f in findings
        ]
        sc = compute_score(outcomes)
        fmt = format_score(sc)

        return AuditResult(
            job_id="sync",
            device_id=device_id,
            artifact_id=artifact_id,
            profile_commit=profile_commit,
            vendor_id=parse_result.vendor_id.value,
            verified_score=fmt["verified"],
            provisional_inclusive_score=fmt["provisional_inclusive"],
            provisional_dependence=fmt["provisional_dependence"],
            verified_numerator=sc.verified_numerator,
            verified_denominator=sc.verified_denominator,
            provisional_inclusive_numerator=sc.provisional_inclusive_numerator,
            provisional_inclusive_denominator=sc.provisional_inclusive_denominator,
            findings=tuple(
                {
                    "check_id": f.check_id,
                    "status": f.status.value,
                    "trust": f.trust,
                    "blast_radius_flag": f.blast_radius_flag,
                    "evidence_line_refs": list(f.evidence_line_refs),
                }
                for f in findings
            ),
            total_lines=parse_result.total_lines,
            recognized_lines=parse_result.recognized_lines,
            unrecognized_lines=len(parse_result.unrecognized),
        )

    def start_audit(
        self,
        artifact_id: str,
        device_id: str,
        profile_commit: str = "HEAD",
    ) -> Job:
        """Start an audit job (Phase 1: runs synchronously inline)."""
        job_id = new_id()
        job = Job(
            job_id=job_id,
            artifact_id=artifact_id,
            device_id=device_id,
            profile_commit=profile_commit,
            status=JobStatus.RUNNING,
            progress=0,
        )
        self._jobs[job_id] = job

        try:
            result = self.run_audit_sync(artifact_id, device_id, profile_commit)
            job.status = JobStatus.DONE
            job.progress = 100
            job.result = {
                "vendor_id": result.vendor_id,
                "verified_score": result.verified_score,
                "provisional_inclusive_score": result.provisional_inclusive_score,
                "provisional_dependence": result.provisional_dependence,
                "verified_numerator": result.verified_numerator,
                "verified_denominator": result.verified_denominator,
                "provisional_inclusive_numerator": result.provisional_inclusive_numerator,
                "provisional_inclusive_denominator": result.provisional_inclusive_denominator,
                "findings": list(result.findings),
                "total_lines": result.total_lines,
                "recognized_lines": result.recognized_lines,
                "unrecognized_lines": result.unrecognized_lines,
            }
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)

        return job

    def get_job(self, job_id: str) -> Job:
        if job_id not in self._jobs:
            raise NotFoundError(f"Job {job_id!r} not found")
        return self._jobs[job_id]


_default_pipeline_service: PipelineServiceImpl | None = None


def get_pipeline_service() -> PipelineServiceImpl:
    global _default_pipeline_service
    if _default_pipeline_service is None:
        from pramana.ingest.service import get_ingest_service
        _default_pipeline_service = PipelineServiceImpl(
            ingest_svc=get_ingest_service(),
        )
    return _default_pipeline_service

