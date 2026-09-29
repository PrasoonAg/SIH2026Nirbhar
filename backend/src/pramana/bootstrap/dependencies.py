"""
bootstrap.dependencies — singleton service instances (Phase 1 DI container).

In Phase 1: simple module-level singletons.
Phase 4+: replace with proper DI (e.g. FastAPI Depends + lifespan).
"""
from __future__ import annotations

from pramana.compliance.domain.engine import ComplianceServiceImpl
from pramana.compliance.domain.seed_checks import SEED_CHECKS_PHASE2
from pramana.ingest.service import IngestServiceImpl
from pramana.parsing.service import ParsingServiceImpl
from pramana.pipeline.service import PipelineServiceImpl

# ── Singletons ────────────────────────────────────────────────────────────────
_ingest_svc = IngestServiceImpl()
_parsing_svc = ParsingServiceImpl()
_compliance_svc = ComplianceServiceImpl(SEED_CHECKS_PHASE2)
_pipeline_svc = PipelineServiceImpl(
    ingest_svc=_ingest_svc,
    parsing_svc=_parsing_svc,
    compliance_svc=_compliance_svc,
)


def get_ingest_service() -> IngestServiceImpl:
    return _ingest_svc


def get_pipeline_service() -> PipelineServiceImpl:
    return _pipeline_svc


def get_parsing_service() -> ParsingServiceImpl:
    return _parsing_svc


def get_compliance_service() -> ComplianceServiceImpl:
    return _compliance_svc
