"""
reporting — public API surface.

Layer:  L5
Track:  5
Tier:   1  (signing T3)

Exports:
  Report model, Jinja2 template rendering, WeasyPrint PDF, signing hook.
  One template renders both HTML preview and PDF (never two definitions).
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pramana.shared_kernel.api import PramanaError


@dataclass(frozen=True)
class ReportData:
    """
    Canonical JSON object for a per-device report.
    Its SHA-256 is printed in the PDF footer.
    """
    report_id: UUID
    device_id: UUID
    audit_id: UUID
    payload: dict[str, object]   # fully serialisable


class ReportingError(PramanaError):
    """Report generation failure."""


class ReportingService:
    """
    Generate HTML preview and WeasyPrint PDF for a device audit.
    STUB — full implementation in Phase 7.
    """

    def build_report_data(self, audit_id: UUID, device_id: UUID) -> ReportData:  # noqa: ARG002
        raise NotImplementedError("Phase 7")

    def render_html(self, report: ReportData) -> str:  # noqa: ARG002
        raise NotImplementedError("Phase 7")

    def render_pdf(self, report: ReportData) -> bytes:  # noqa: ARG002
        raise NotImplementedError("Phase 7")


__all__ = ["ReportData", "ReportingError", "ReportingService"]
