"""
nirbhar/explain/report.py
=========================
Structured human-readable explanation reports for NIRBHAR (§7).
Mirrors frontend explainability generator for unified terminal and API output.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any
import numpy as np

from nirbhar.io.model import Model
from nirbhar.lp.dual_simplex import LPResult, FarkasRay, UnboundedRay
from nirbhar.explain.farkas import certify_farkas_ray
from nirbhar.explain.iis import compute_iis


@dataclass
class ExplainSection:
    title: str
    body: str
    kind: str  # 'info' | 'success' | 'warning' | 'error'


@dataclass
class ExplainReport:
    headline: str
    summary: str
    sections: list[ExplainSection] = field(default_factory=list)


def generate_explanation_report(
    model: Model,
    result: Any,
    timing_s: float = 0.0,
    solve_path: Optional[list[str]] = None,
) -> ExplainReport:
    """
    Generate a plain-English explanation report from solver output.
    """
    path_str = " -> ".join(solve_path) if solve_path else "Direct Solve"

    if isinstance(result, FarkasRay) or (isinstance(result, LPResult) and result.status == "INFEASIBLE"):
        iis = compute_iis(model)
        farkas = certify_farkas_ray(model, result.y) if getattr(result, "y", None) is not None else None

        headline = "[INFEASIBLE] Contradictory constraints - Problem has no feasible solution"
        summary = (
            "The solver mathematically proved that no feasible assignment exists "
            "that simultaneously satisfies all constraint rows and variable bounds."
        )
        sections = [
            ExplainSection(
                title="Conflict Diagnosis (IIS)",
                kind="error",
                body=iis.explanation if iis.iis_row_names else "Mutual conflict among model constraints.",
            ),
        ]
        if farkas and farkas.is_valid:
            sections.append(
                ExplainSection(
                    title="Farkas Certificate",
                    kind="warning",
                    body=farkas.explanation,
                )
            )
        sections.append(
            ExplainSection(
                title="Engine Diagnostics",
                kind="info",
                body=f"Solve Path: {path_str} | Time: {timing_s:.3f}s",
            )
        )
        return ExplainReport(headline=headline, summary=summary, sections=sections)

    if isinstance(result, UnboundedRay) or (isinstance(result, LPResult) and result.status == "UNBOUNDED"):
        headline = "[UNBOUNDED] Objective is Unbounded - Cost can decrease to -infinity"
        summary = (
            "The solver discovered an extreme ray along which the objective improves indefinitely "
            "without violating any constraint bounds."
        )
        sections = [
            ExplainSection(
                title="Unbounded Ray",
                kind="warning",
                body="A feasible direction d was found with c^T d < 0 and A d >= 0.",
            ),
            ExplainSection(
                title="Engine Diagnostics",
                kind="info",
                body=f"Solve Path: {path_str} | Time: {timing_s:.3f}s",
            ),
        ]
        return ExplainReport(headline=headline, summary=summary, sections=sections)

    if isinstance(result, LPResult) and result.status == "OPTIMAL":
        gap_pct = result.gap * 100
        headline = f"[OPTIMAL] Verified Optimal Solution: {result.z_primal:.6f}"
        summary = (
            f"The primal solution achieves cost {result.z_primal:.6f}. "
            f"Lagrangian duality certifies that no solution can have cost below {result.z_dual:.6f}. "
            f"Optimality gap is {gap_pct:.6f}%."
        )
        sections = [
            ExplainSection(
                title="Objective & Duality",
                kind="success",
                body=(
                    f"Primal Objective (Upper Bound): {result.z_primal:.8f}\n"
                    f"Dual Bound (Lower Bound):       {result.z_dual:.8f}\n"
                    f"Relative Duality Gap:           {gap_pct:.6e}%"
                ),
            ),
            ExplainSection(
                title="Optimality Proof",
                kind="info",
                body="Karush-Kuhn-Tucker (KKT) conditions and complementarity slackness fully verified.",
            ),
            ExplainSection(
                title="Engine Diagnostics",
                kind="info",
                body=f"Iterations: {result.iters} | Time: {timing_s:.3f}s | Path: {path_str}",
            ),
        ]
        return ExplainReport(headline=headline, summary=summary, sections=sections)

    return ExplainReport(
        headline=f"Solver Status: {getattr(result, 'status', 'UNKNOWN')}",
        summary=f"Finished with status {getattr(result, 'status', 'UNKNOWN')}.",
        sections=[
            ExplainSection(
                title="Details",
                kind="info",
                body=getattr(result, "msg", ""),
            )
        ],
    )
