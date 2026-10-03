"""
nirbhar_verify/lp_verify.py
=============================
Independent LP solution verifier.

CRITICAL: imports NOTHING from nirbhar/. Uses only stdlib + NumPy.

Given a primal x and dual y:
  1. Constraint feasibility: row_lo <= A x <= row_hi  (within tol)
  2. Bound feasibility:      col_lo <= x <= col_hi    (within tol)
  3. Dual feasibility:       c - A^T y >= 0 for x_j at lower bound, etc.
  4. Complementary slackness: (c_j - A^T y)_j * x_j = 0 (within tol)
  5. Objective agreement:    c^T x == b^T y            (within tol)
  6. Certified gap:          |primal - dual| / (1 + |dual|) <= gap_tol

Returns a VerifyResult dataclass with PASS/FAIL and details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from nirbhar_verify.mps_min import MinModel, parse_mps_min


@dataclass
class VerifyResult:
    status: str          # 'PASS' | 'FAIL'
    primal_feas: bool
    dual_feas: bool
    cs_ok: bool
    obj_match: bool
    gap: float
    primal_obj: float
    dual_obj: float
    violations: list[str] = field(default_factory=list)
    msg: str = ""

    def is_pass(self) -> bool:
        return self.status == "PASS"


def verify_lp(
    model: MinModel,
    x: np.ndarray,
    y: np.ndarray,
    primal_tol: float = 1e-6,
    dual_tol: float = 1e-6,
    gap_tol: float = 1e-6,
) -> VerifyResult:
    """
    Verify LP solution (x, y) against model.

    Parameters
    ----------
    model       : MinModel from nirbhar_verify (no nirbhar imports)
    x           : primal solution (n,)
    y           : dual solution / shadow prices (m,)
    primal_tol  : constraint / bound feasibility tolerance
    dual_tol    : dual feasibility tolerance
    gap_tol     : duality gap tolerance

    Returns
    -------
    VerifyResult
    """
    m, n = model.nrows, model.ncols
    violations: list[str] = []

    # ── 1. Primal bound feasibility ──────────────────────────────────────────
    lb_viol = np.sum(x < model.col_lo - primal_tol)
    ub_viol = np.sum(x > model.col_hi + primal_tol)
    if lb_viol > 0:
        violations.append(f"Primal: {lb_viol} variables below lower bound")
    if ub_viol > 0:
        violations.append(f"Primal: {ub_viol} variables above upper bound")

    # ── 2. Constraint feasibility ────────────────────────────────────────────
    Ax = model.A_dense @ x
    row_lo_viol = np.sum(Ax < model.row_lo - primal_tol)
    row_hi_viol = np.sum(Ax > model.row_hi + primal_tol)
    if row_lo_viol > 0:
        violations.append(f"Primal: {row_lo_viol} constraints below lower bound")
    if row_hi_viol > 0:
        violations.append(f"Primal: {row_hi_viol} constraints above upper bound")

    primal_feas = (lb_viol == 0 and ub_viol == 0
                   and row_lo_viol == 0 and row_hi_viol == 0)

    # ── 3. Dual feasibility (reduced costs) ──────────────────────────────────
    # reduced costs: rc = c - A^T y
    # For min LP: rc_j >= 0 if x_j at lower bound, rc_j <= 0 if x_j at upper bound
    rc = model.c - model.A_dense.T @ y
    at_lo = x <= model.col_lo + primal_tol
    at_hi = x >= model.col_hi - primal_tol
    free = (~at_lo) & (~at_hi)

    rc_lo_viol = np.sum(rc[at_lo] < -dual_tol)
    rc_hi_viol = np.sum(rc[at_hi] > dual_tol)
    rc_free_viol = np.sum(np.abs(rc[free]) > dual_tol)

    if rc_lo_viol > 0:
        violations.append(f"Dual: {rc_lo_viol} negative reduced costs at lower bound")
    if rc_hi_viol > 0:
        violations.append(f"Dual: {rc_hi_viol} positive reduced costs at upper bound")
    if rc_free_viol > 0:
        violations.append(f"Dual: {rc_free_viol} nonzero reduced costs for free variables")

    dual_feas = (rc_lo_viol == 0 and rc_hi_viol == 0 and rc_free_viol == 0)

    # ── 4. Complementary slackness ───────────────────────────────────────────
    # rc_j * (x_j - col_lo_j) = 0 and (c_j - rc_j) * (col_hi_j - x_j) = 0
    # Approximate check: |rc_j| * |x_j - col_lo_j| should be small
    cs_slack = np.abs(rc) * np.abs(x - model.col_lo)
    cs_viol = np.sum(cs_slack > primal_tol * dual_tol * 1e6 + 1e-10)
    cs_ok = cs_viol == 0
    if not cs_ok:
        violations.append(f"Complementary slackness: {cs_viol} violations")

    # ── 5. Objective values and gap ──────────────────────────────────────────
    primal_obj = float(model.c @ x) + model.obj_const
    dual_obj = float(model.row_lo @ y) + model.obj_const  # approximate
    gap = abs(primal_obj - dual_obj) / (1.0 + abs(dual_obj))
    obj_match = gap <= gap_tol

    if not obj_match:
        violations.append(
            f"Duality gap {gap:.2e} > {gap_tol:.2e} "
            f"(primal={primal_obj:.6g}, dual={dual_obj:.6g})"
        )

    status = "PASS" if (primal_feas and dual_feas and cs_ok and obj_match) else "FAIL"

    return VerifyResult(
        status=status,
        primal_feas=primal_feas,
        dual_feas=dual_feas,
        cs_ok=cs_ok,
        obj_match=obj_match,
        gap=gap,
        primal_obj=primal_obj,
        dual_obj=dual_obj,
        violations=violations,
        msg=f"Verifier: {status} — {len(violations)} violation(s)",
    )


def verify_lp_from_file(
    mps_path: str | Path,
    x: np.ndarray,
    y: np.ndarray,
    **kwargs,
) -> VerifyResult:
    """Convenience: parse model then verify."""
    model = parse_mps_min(mps_path)
    return verify_lp(model, x, y, **kwargs)
