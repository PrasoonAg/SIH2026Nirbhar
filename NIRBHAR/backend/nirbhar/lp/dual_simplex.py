"""
nirbhar/lp/dual_simplex.py
===========================
Two-Phase Revised Primal Simplex LP solver with bounded-variable support.

Bounded-variable handling:
  - Nonbasic vars at lower bound (0) or upper bound (ub_prime)
  - Canonical row orientation: negative RHS rows are flipped so b_eq >= 0 always.
  - Phase 1: bounded-variable simplex minimizing sum of artificial variables.
  - Phase 2: bounded-variable simplex on true objective, artificials locked out.
  - Dual solution: corrected for flipped rows and bounds.

Sovereignty: no scipy / cvxpy / highspy / etc. imports.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union, Tuple
import time
import numpy as np
from nirbhar.io.model import Model, INF
from nirbhar.linalg.lu_markowitz import LUFactor, SingularBasisError
from nirbhar.linalg.refine import iterative_refine


# ---------------------------------------------------------------------------
# Public option / result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DSSOptions:
    max_iter: int = 50_000
    primal_tol: float = 1e-8
    dual_tol: float = 1e-8
    gap_tol: float = 1e-8
    harris_tol: float = 1e-7
    refactor_freq: int = 50
    max_degenerate: int = 500
    verbose: bool = False
    time_limit_s: float = float("inf")

@dataclass
class LPResult:
    status: str
    x: np.ndarray
    y: np.ndarray
    z_primal: float
    z_dual: float
    gap: float
    iters: int
    msg: str = ""

@dataclass
class FarkasRay:
    status: str = "INFEASIBLE"
    y: np.ndarray = None
    msg: str = ""

@dataclass
class UnboundedRay:
    status: str = "UNBOUNDED"
    d: np.ndarray = None
    msg: str = ""


# ---------------------------------------------------------------------------
# Main solver entry point
# ---------------------------------------------------------------------------

def dual_simplex_solve(
    model: Model,
    basis=None,
    opts: Optional[DSSOptions] = None,
) -> Union[LPResult, FarkasRay, UnboundedRay]:
    """Solve LP with two-phase revised primal simplex (bounded-variable)."""
    if opts is None:
        opts = DSSOptions()

    m, n = model.nrows, model.ncols
    c_ext, A_eq, b_eq, col_lo_orig, n_ext, equality_rows, ub_ext, neg_rows = \
        _build_standard_form(model)

    n_art = m
    n_total = n_ext + n_art

    A_full = np.empty((m, n_total), dtype=np.float64)
    A_full[:, :n_ext] = A_eq
    A_full[:, n_ext:] = np.eye(m, dtype=np.float64)

    ub_all = np.full(n_total, np.inf)
    ub_all[:n_ext] = ub_ext

    # ── Phase 1: Minimize sum of artificial variables ─────────────────────────
    basic_p1 = np.arange(n_ext, n_total, dtype=np.int32)
    x_B_p1 = b_eq.copy()
    nonbasic_p1 = np.arange(n_ext, dtype=np.int32)
    at_ub_p1 = np.zeros(n_ext, dtype=bool)
    c_p1 = np.zeros(n_total, dtype=np.float64)
    c_p1[n_ext:] = 1.0

    res_p1 = _bounded_simplex_loop(
        A_full, c_p1, b_eq, basic_p1, x_B_p1, nonbasic_p1, at_ub_p1, ub_all, opts
    )

    if isinstance(res_p1, str):
        if res_p1 == "NUMERICAL":
            return LPResult(status="NUMERICAL", x=np.zeros(n), y=np.zeros(m),
                            z_primal=float("inf"), z_dual=float("-inf"),
                            gap=float("inf"), iters=0, msg="Phase 1 basis breakdown")
        return LPResult(status="MAX_ITER", x=np.zeros(n), y=np.zeros(m),
                        z_primal=float("inf"), z_dual=float("-inf"),
                        gap=float("inf"), iters=opts.max_iter, msg="Phase 1 max iterations")

    if isinstance(res_p1, UnboundedRay):
        return LPResult(status="NUMERICAL", x=np.zeros(n), y=np.zeros(m),
                        z_primal=float("inf"), z_dual=float("-inf"),
                        gap=float("inf"), iters=0, msg="Phase 1 unbounded ray")

    basic_1, x_B_1, nonbasic_1, at_ub_1, y_p1, iters_p1, status_p1 = res_p1

    if status_p1 == "MAX_ITER":
        return LPResult(status="MAX_ITER", x=np.zeros(n), y=np.zeros(m),
                        z_primal=float("inf"), z_dual=float("-inf"),
                        gap=float("inf"), iters=iters_p1, msg="Phase 1 max iterations")

    # Check infeasibility: artificial variables sum > 0 (only when Phase 1 reached an optimal vertex)
    art_mask = basic_1 >= n_ext
    art_sum = float(x_B_1[art_mask].sum()) if art_mask.any() else 0.0
    if art_sum > opts.primal_tol * max(m, 1):
        y_farkas = y_p1.copy()
        y_farkas[neg_rows] *= -1.0
        return FarkasRay(y=y_farkas, msg=f"Phase 1 infeasible (art_sum={art_sum:.2e})")

    # ── Phase 2: Optimize true objective ──────────────────────────────────────
    c_p2 = np.zeros(n_total, dtype=np.float64)
    c_p2[:n_ext] = c_ext

    # Artificials must not re-enter the basis in Phase 2 and cannot increase if basic
    allow_enter_p2 = nonbasic_1 < n_ext
    ub_all_p2 = ub_all.copy()
    ub_all_p2[n_ext:] = 0.0

    res_p2 = _bounded_simplex_loop(
        A_full, c_p2, b_eq, basic_1, x_B_1, nonbasic_1, at_ub_1, ub_all_p2, opts,
        allow_enter_mask=allow_enter_p2
    )

    if isinstance(res_p2, str):
        if res_p2 == "NUMERICAL":
            return LPResult(status="NUMERICAL", x=np.zeros(n), y=np.zeros(m),
                            z_primal=float("inf"), z_dual=float("-inf"),
                            gap=float("inf"), iters=iters_p1, msg="Phase 2 basis breakdown")
        return LPResult(status="MAX_ITER", x=np.zeros(n), y=np.zeros(m),
                        z_primal=float("inf"), z_dual=float("-inf"),
                        gap=float("inf"), iters=iters_p1 + opts.max_iter, msg="Phase 2 max iterations")

    if isinstance(res_p2, UnboundedRay):
        return UnboundedRay(d=res_p2.d[:n])

    basic_fin, x_B_fin, nonbasic_fin, at_ub_fin, y_final, iters_p2, status_p2 = res_p2

    if status_p2 == "UNBOUNDED":
        return UnboundedRay(d=np.zeros(n), msg="Problem is unbounded")

    # ── Reconstruct primal and dual solutions ─────────────────────────────────
    x_shifted = np.zeros(n_total, dtype=np.float64)
    for slot, col in enumerate(basic_fin):
        x_shifted[col] = float(x_B_fin[slot])
    for k, j in enumerate(nonbasic_fin):
        if at_ub_fin[k] and j < n:
            x_shifted[j] = float(ub_ext[j])

    x_sol = x_shifted[:n] + col_lo_orig

    # Dual solution: invert signs on rows that were flipped to make b_eq >= 0
    y_sol = y_final.copy()
    y_sol[neg_rows] *= -1.0

    z_p = float(model.c @ x_sol) + model.obj_const
    # Dual objective: b_orig @ y_sol + model.obj_const
    z_d = float(b_eq @ y_final) + model.obj_const
    gap = abs(z_p - z_d) / (1.0 + abs(z_d))

    total_iters = iters_p1 + iters_p2
    return LPResult(
        status="OPTIMAL", x=x_sol, y=y_sol,
        z_primal=z_p, z_dual=z_d, gap=gap,
        iters=total_iters,
        msg=f"Optimal in {iters_p1}+{iters_p2} iterations",
    )


# ---------------------------------------------------------------------------
# Bounded-variable simplex loop (unified for Phase 1 and Phase 2)
# ---------------------------------------------------------------------------

def _bounded_simplex_loop(
    A_full: np.ndarray,
    c_full: np.ndarray,
    b_eq: np.ndarray,
    basic: np.ndarray,
    x_B: np.ndarray,
    nonbasic: np.ndarray,
    at_ub: np.ndarray,
    ub_all: np.ndarray,
    opts: DSSOptions,
    allow_enter_mask: Optional[np.ndarray] = None,
):
    """
    Revised primal simplex with upper bounds.

    Returns:
      (basic, x_B, nonbasic, at_ub, y, iters, status)
      where status is 'OPTIMAL' or 'UNBOUNDED'
      or string 'NUMERICAL' / 'MAX_ITER' on early termination.
    """
    m, n_total = A_full.shape
    b_eff = b_eq.copy()
    for k_nb, j_nb in enumerate(nonbasic):
        if at_ub[k_nb]:
            b_eff -= A_full[:, j_nb] * ub_all[j_nb]

    try:
        lu = LUFactor.factor(A_full[:, basic])
    except SingularBasisError:
        return "NUMERICAL"

    degenerate_count = 0
    t_start = time.perf_counter()

    for iters in range(1, opts.max_iter + 1):
        if opts.time_limit_s < 1e9 and (iters % 20 == 0):
            if time.perf_counter() - t_start > opts.time_limit_s:
                return "MAX_ITER"

        c_B = c_full[basic]
        y = lu.solve(c_B, transpose=True)
        rc = c_full[nonbasic] - (A_full[:, nonbasic].T @ y)

        # Reduced cost sign convention:
        # Nonbasic at LB: entering variable increases, rc must be negative to improve.
        # Nonbasic at UB: entering variable decreases, rc must be positive to improve -> rc_eff = -rc < 0.
        rc_eff = np.where(at_ub, -rc, rc)

        if allow_enter_mask is not None:
            rc_eff = np.where(allow_enter_mask, rc_eff, np.inf)

        # Pricing
        if degenerate_count >= opts.max_degenerate:
            bland_mask = rc_eff < -opts.dual_tol
            if not bland_mask.any():
                return basic.copy(), x_B.copy(), nonbasic.copy(), at_ub.copy(), y.copy(), iters, "OPTIMAL"
            entering_slot = int(np.argmax(bland_mask))
        else:
            entering_slot = int(np.argmin(rc_eff))

        min_rc_eff = float(rc_eff[entering_slot])
        if min_rc_eff >= -opts.dual_tol:
            return basic.copy(), x_B.copy(), nonbasic.copy(), at_ub.copy(), y.copy(), iters, "OPTIMAL"

        entering_col = int(nonbasic[entering_slot])
        entering_from_ub = bool(at_ub[entering_slot])
        ub_e = float(ub_all[entering_col])

        # FTRAN
        d = lu.solve(A_full[:, entering_col])
        if entering_from_ub:
            d = -d  # variable DECREASES from UB towards LB

        # Bounded ratio test
        ub_basic = ub_all[basic]
        min_ratio = ub_e
        leaving_slot = -2
        ub_leave = False

        # LB ratio: basic[i] decreases to 0 (d[i] > 0)
        lb_mask = d > opts.harris_tol
        if lb_mask.any():
            lb_ratios = np.where(lb_mask, x_B / np.where(lb_mask, d, 1.0), np.inf)
            best_lb = int(np.argmin(lb_ratios))
            if lb_ratios[best_lb] < min_ratio - 1e-12:
                min_ratio = float(lb_ratios[best_lb])
                leaving_slot = best_lb
                ub_leave = False

        # UB ratio: basic[i] increases to ub_basic[i] (d[i] < 0, finite UB)
        ub_mask = (d < -opts.harris_tol) & (ub_basic < 1e30)
        if ub_mask.any():
            ub_ratios = np.where(ub_mask, (ub_basic - x_B) / np.where(ub_mask, -d, 1.0), np.inf)
            best_ub_r = int(np.argmin(ub_ratios))
            if ub_ratios[best_ub_r] < min_ratio - 1e-12:
                min_ratio = float(ub_ratios[best_ub_r])
                leaving_slot = best_ub_r
                ub_leave = True

        step = max(0.0, min_ratio)

        # Unbounded check
        if leaving_slot == -2 and not np.isfinite(ub_e):
            ray = np.zeros(n_total, dtype=np.float64)
            sgn = -1.0 if entering_from_ub else 1.0
            ray[entering_col] = sgn
            ray[basic] -= d * sgn
            return UnboundedRay(d=ray)

        degenerate_count = (degenerate_count + 1) if step < opts.primal_tol else 0
        x_B -= step * d

        if leaving_slot >= 0:
            leaving_col = int(basic[leaving_slot])
            leaving_ub = float(ub_all[leaving_col])
            entering_val = (ub_e - step) if entering_from_ub else step

            x_B[leaving_slot] = entering_val
            basic[leaving_slot] = entering_col
            nonbasic[entering_slot] = leaving_col

            if ub_leave:
                at_ub[entering_slot] = True
                b_eff -= A_full[:, leaving_col] * leaving_ub
            else:
                at_ub[entering_slot] = False

            if entering_from_ub:
                b_eff += A_full[:, entering_col] * ub_e

            if allow_enter_mask is not None:
                # Update allow_enter for the newly nonbasic variable
                allow_enter_mask[entering_slot] = (leaving_col < (n_total - m))
        else:
            # Entering var hits its own bound and flips
            if np.isfinite(ub_e) and step >= ub_e - opts.primal_tol:
                if not entering_from_ub:
                    at_ub[entering_slot] = True
                    b_eff -= A_full[:, entering_col] * ub_e
                else:
                    at_ub[entering_slot] = False
                    b_eff += A_full[:, entering_col] * ub_e

        # Periodic refactorisation
        if iters % opts.refactor_freq == 0:
            B = A_full[:, basic]
            try:
                lu = LUFactor.factor(B)
                b_eff_fresh = b_eq.copy()
                for k_nb, j_nb in enumerate(nonbasic):
                    if at_ub[k_nb]:
                        b_eff_fresh -= A_full[:, j_nb] * ub_all[j_nb]
                b_eff = b_eff_fresh
                x_B_cand = lu.solve(b_eff)
                x_B_cand = iterative_refine(lu, B, b_eff, x_B_cand, steps=2)
                np.maximum(x_B_cand, 0.0, out=x_B_cand)
                x_B = x_B_cand
            except SingularBasisError:
                return "NUMERICAL"
        else:
            try:
                lu = LUFactor.factor(A_full[:, basic])
            except SingularBasisError:
                return "NUMERICAL"

    return basic.copy(), x_B.copy(), nonbasic.copy(), at_ub.copy(), y.copy(), opts.max_iter, "MAX_ITER"


# ---------------------------------------------------------------------------
# Standard form builder
# ---------------------------------------------------------------------------

def _build_standard_form(model: Model):
    """
    Standard-form reduction. Row slacks handle row bounds.
    Column UBs returned as ub_prime[] for the bounded-variable simplex.
    Negative RHS rows are canonicalised (negated) so b_eq >= 0 always.
    """
    m, n = model.nrows, model.ncols
    A_csr = model.A_csr

    A = np.zeros((m, n), dtype=np.float64)
    for i in range(m):
        s, e = A_csr.indptr[i], A_csr.indptr[i + 1]
        for k in range(s, e):
            A[i, A_csr.indices[k]] = A_csr.data[k]

    row_type = np.zeros(m, dtype=np.int8)
    for i in range(m):
        lo_r, hi_r = model.row_lo[i], model.row_hi[i]
        fl, fh = lo_r > -INF * 0.9, hi_r < INF * 0.9
        if fl and fh:
            row_type[i] = 0 if abs(hi_r - lo_r) < 1e-12 else 1
        elif fh:
            row_type[i] = 1
        elif fl:
            row_type[i] = -1
        else:
            row_type[i] = 2

    equality_rows = (row_type == 0) | (row_type == 2)
    col_lo_orig = np.clip(model.col_lo.copy(), -INF, INF)

    # Shifted upper bounds
    ub_prime = np.full(n, np.inf)
    for j in range(n):
        hi_j, lo_j = model.col_hi[j], col_lo_orig[j]
        if hi_j < INF * 0.9 and lo_j > -INF * 0.9:
            ub_prime[j] = max(0.0, hi_j - lo_j)

    n_ext = n + m
    c_ext = np.zeros(n_ext, dtype=np.float64)
    c_ext[:n] = model.c

    A_eq = np.zeros((m, n_ext), dtype=np.float64)
    A_eq[:, :n] = A
    b_eq = np.zeros(m, dtype=np.float64)

    for i in range(m):
        lo_r, hi_r = model.row_lo[i], model.row_hi[i]
        rt = row_type[i]
        if rt == 1:
            A_eq[i, n + i] = 1.0; b_eq[i] = hi_r
        elif rt == -1:
            A_eq[i, n + i] = -1.0; b_eq[i] = lo_r
        elif rt == 0:
            b_eq[i] = lo_r
        else:
            b_eq[i] = 0.0

    for j in range(n):
        lj = col_lo_orig[j]
        if abs(lj) > 1e-300:
            b_eq -= A_eq[:, j] * lj

    # Canonicalise negative RHS: flip rows so b_eq >= 0 always
    neg_rows = b_eq < 0
    A_eq[neg_rows] *= -1.0
    b_eq[neg_rows] *= -1.0

    ub_ext = np.full(n_ext, np.inf)
    ub_ext[:n] = ub_prime
    for i in range(m):
        lo_r, hi_r = model.row_lo[i], model.row_hi[i]
        fl, fh = lo_r > -INF * 0.9, hi_r < INF * 0.9
        if fl and fh and abs(hi_r - lo_r) >= 1e-12:
            ub_ext[n + i] = max(0.0, hi_r - lo_r)

    return c_ext, A_eq, b_eq, col_lo_orig, n_ext, equality_rows, ub_ext, neg_rows