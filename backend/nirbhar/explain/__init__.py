"""
nirbhar/explain
===============
Explainability, Infeasibility Diagnostics, and IIS package for NIRBHAR (§6.7, §7).
"""

from nirbhar.explain.farkas import certify_farkas_ray, FarkasCertificate
from nirbhar.explain.iis import compute_iis, IISResult
from nirbhar.explain.report import generate_explanation_report, ExplainReport, ExplainSection

__all__ = [
    "certify_farkas_ray",
    "FarkasCertificate",
    "compute_iis",
    "IISResult",
    "generate_explanation_report",
    "ExplainReport",
    "ExplainSection",
]
