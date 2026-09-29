"""
pipeline.router — FastAPI router for audit jobs.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from pramana.pipeline.api import JobStatus
from pramana.shared_kernel.api import NotFoundError

router = APIRouter(prefix="/audits", tags=["audits"])


# ─── Request / response schemas ───────────────────────────────────────────────

class StartAuditRequest(BaseModel):
    artifact_id: str
    device_id: str
    profile_commit: str = "HEAD"


class FindingResponse(BaseModel):
    check_id: str
    status: str
    trust: str
    blast_radius_flag: bool
    evidence_line_refs: list[dict]


class TwoNumberScore(BaseModel):
    """
    Two-number score (INV-07). Always both figures together.
    Verified excludes Provisional checks; Provisional-Inclusive includes them.
    Provisional-dependence shows how much evaluated weight rests on Provisional mappings.
    No single combined figure exists in this schema.
    """
    verified: str | None
    provisional_inclusive: str | None
    provisional_dependence: str | None
    verified_numerator: int | None
    verified_denominator: int | None
    provisional_inclusive_numerator: int | None
    provisional_inclusive_denominator: int | None


class JobResponse(BaseModel):
    job_id: str
    artifact_id: str
    device_id: str
    profile_commit: str
    status: str
    progress: int
    error: str | None = None
    vendor_id: str | None = None
    score: TwoNumberScore | None = None
    findings: list[FindingResponse] | None = None
    total_lines: int | None = None
    recognized_lines: int | None = None
    unrecognized_lines: int | None = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a compliance audit",
)
async def start_audit(request: StartAuditRequest) -> JobResponse:
    """
    Submit a config artifact for compliance auditing.
    Phase 1: runs synchronously and returns DONE immediately.
    Phase 4+: returns PENDING and polls GET /audits/{job_id}.
    """
    from pramana.pipeline.service import get_pipeline_service
    pipeline_svc = get_pipeline_service()

    job = pipeline_svc.start_audit(
        artifact_id=request.artifact_id,
        device_id=request.device_id,
        profile_commit=request.profile_commit,
    )

    return _job_to_response(job)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get audit job status and result",
)
async def get_audit(job_id: str) -> JobResponse:
    """
    Return the current status of an audit job.
    When status=done, the result includes both scores and all findings.
    """
    from pramana.pipeline.service import get_pipeline_service
    pipeline_svc = get_pipeline_service()

    try:
        job = pipeline_svc.get_job(job_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")

    return _job_to_response(job)


def _job_to_response(job) -> JobResponse:  # type: ignore[no-untyped-def]
    """Convert a Job domain object to a JobResponse schema."""
    score = None
    findings = None
    vendor_id = None
    total_lines = recognized_lines = unrecognized_lines = None

    if job.status == JobStatus.DONE and job.result:
        r = job.result
        score = TwoNumberScore(
            verified=r.get("verified_score"),
            provisional_inclusive=r.get("provisional_inclusive_score"),
            provisional_dependence=r.get("provisional_dependence"),
            verified_numerator=r.get("verified_numerator"),
            verified_denominator=r.get("verified_denominator"),
            provisional_inclusive_numerator=r.get("provisional_inclusive_numerator"),
            provisional_inclusive_denominator=r.get("provisional_inclusive_denominator"),
        )
        findings = [
            FindingResponse(
                check_id=f["check_id"],
                status=f["status"],
                trust=f["trust"],
                blast_radius_flag=f.get("blast_radius_flag", False),
                evidence_line_refs=f.get("evidence_line_refs", []),
            )
            for f in r.get("findings", [])
        ]
        vendor_id = r.get("vendor_id")
        total_lines = r.get("total_lines")
        recognized_lines = r.get("recognized_lines")
        unrecognized_lines = r.get("unrecognized_lines")

    return JobResponse(
        job_id=job.job_id,
        artifact_id=job.artifact_id,
        device_id=job.device_id,
        profile_commit=job.profile_commit,
        status=job.status.value,
        progress=job.progress,
        error=job.error,
        vendor_id=vendor_id,
        score=score,
        findings=findings,
        total_lines=total_lines,
        recognized_lines=recognized_lines,
        unrecognized_lines=unrecognized_lines,
    )
