"""
ingest.router — FastAPI router for config file upload.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from pramana.ingest.api import Artifact, IngestError, ZipGuardError

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ─── Response schemas ─────────────────────────────────────────────────────────

class ArtifactResponse(BaseModel):
    artifact_id: str
    sha256: str
    filename: str
    size_bytes: int
    vendor_hint: str | None = None

    model_config = {"from_attributes": True}


class ZipIngestResponse(BaseModel):
    artifacts: list[ArtifactResponse]
    count: int


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/file",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a single config file",
)
async def upload_file(
    file: UploadFile = File(...),
    vendor_hint: str | None = Form(default=None),
    device_id: str | None = Form(default=None),
) -> ArtifactResponse:
    """
    Upload a single configuration file.
    Returns a content-addressed artifact record.
    Identical content is deduplicated by SHA-256.
    """
    # Import at call time to get the request-scoped service (injected by bootstrap)
    from pramana.ingest.service import get_ingest_service
    ingest_svc = get_ingest_service()

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        artifact = ingest_svc.ingest_bytes(
            raw,
            filename=file.filename or "upload.cfg",
            device_id=device_id,
            vendor_hint=vendor_hint,
        )
    except IngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ArtifactResponse(
        artifact_id=artifact.artifact_id,
        sha256=artifact.sha256,
        filename=artifact.filename,
        size_bytes=artifact.size_bytes,
        vendor_hint=artifact.vendor_hint,
    )


@router.post(
    "/zip",
    response_model=ZipIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a ZIP archive of config files",
)
async def upload_zip(
    file: UploadFile = File(...),
) -> ZipIngestResponse:
    """
    Upload a ZIP archive. All members are stored as individual artifacts.
    ZIP guards enforced (INV-11, §12): max members, max size, ratio, no traversal.
    """
    from pramana.ingest.service import get_ingest_service
    ingest_svc = get_ingest_service()

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        artifacts = ingest_svc.ingest_zip(raw, filename=file.filename or "upload.zip")
    except ZipGuardError as exc:
        raise HTTPException(status_code=422, detail=f"ZIP guard: {exc}") from exc
    except IngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ZipIngestResponse(
        artifacts=[
            ArtifactResponse(
                artifact_id=a.artifact_id,
                sha256=a.sha256,
                filename=a.filename,
                size_bytes=a.size_bytes,
                vendor_hint=a.vendor_hint,
            )
            for a in artifacts
        ],
        count=len(artifacts),
    )
