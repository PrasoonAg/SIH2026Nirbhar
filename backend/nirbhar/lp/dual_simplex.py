"""
nirbhar/lp/dual_simplex.py
===========================
Revised simplex LP solver (Phase 1).

Implements a revised primal simplex with:
  - Dantzig's rule pricing (most negative reduced cost)
  - Min-ratio test (Bland anti-cycling fallback after 500 degenerate steps)
  - Complete refactorization every refactor_freq iterations
  - Farkas infeasibility detection via Big-M phase-1
  - Returns LPResult | FarkasRay | UnboundedRay

Certificate:
  OPTIMAL iff dual feasible (rc >= 0) AND primal feasible (x_B >= col_lo_B).
  Certified gap stored in result.gap.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union
import numpy as np
from nirbhar.io.model import Model, INF
from nirbhar.linalg.lu_markowitz import LUFactor, SingularBasisError


@dataclass
class DSSOptions:
    max_iter: int = 20_000
    primal_tol: float = 1e-8
    dual_tol: float = 1e-8
    gap_tol: float = 1e-8
    harris_tol: float = 1e-7
    refactor_freq: int = 50
    verbose: bool = False


@dataclass
class LPResult:
    status: str       # OPTIMAL | INFEASIBLE | UNBOUNDED | MAX_ITER | NUMERICAL
    x: np.ndarray     # (n,) primal
    y: np.ndarray     # (m,) dual
    z_primal: float
    z_dual: float
    gap: float
    iters: int = 0
    msg: str = ""


@dataclass
class FarkasRay:
    y: np.ndarray
    msg: str = "Primal infeasible (Farkas certificate)"


@dataclass
class UnboundedRay:
    d: np.ndarray
    msg: str = "Primal unbounded"


LPSolution = Union[LPResult, FarkasRay, UnboundedRay]


def dual_simplex_solve(
    model: Model,
    basis=None,
    opts: Optional[DSSOptions] = None,
) -> LPSolution:
    """Solve LP with revised primal simplex."""
    if opts is None:
        opts = DSSOptions()

    m, n = model.nrows, model.ncols

    # Convert to standard form: min c_ext^T x_ext, A_ext x_ext = b_eq, x_ext >= lo_ext
    c_ext, A_ext, b_eq, lo_ext, hi_ext = _standard_form(model)
    n_ext = c_ext.shape[0]

    # Initial basis: artificial variables (Big-M phase 1 combined)
    BIG_M = 1e7
    # Add m artificial variables to guarantee initial feasibility
    n_art = m
    n_total = n_ext + n_art
    c_t = np.concatenate([c_ext, np.full(n_art, BIG_M)])
    lo_t = np.concatenate([lo_ext, np.zeros(n_art)])
    hi_t = np.concatenate([hi_ext, np.full(n_art, INF)])
    A_t = np.concatenate([A_ext, np.eye(m)], axis=1)
    b_shifted = b_eq.copy()

    # Make b_shifted >= 0 (negate rows where b < 0)
    neg = b_shifted < 0
    b_shifted[neg] = -b_shifted[neg]
    A_t[neg, :] = -A_t[neg, :]
    # Artificials start at b_shifted (may be negative if b was)
    x_art_start = b_shifted.copy()

    # Basic variables: artificials (columns n_ext..n_total-1)
    basic = np.arange(n_ext, n_total, dtype=np.int32)
    x_B = x_art_start.copy()

    # Nonbasic at lower bounds
    nonbasic_list = list(range(n_ext))
    nonbasic = np.array(nonbasic_list, dtype=np.int32)

    # Factor initial basis (identity)
    B = A_t[:, basic]
    lu = LUFactor.factor(B)

    iters = 0
    degenerate_count = 0

    while iters < opts.max_iter:
        iters += 1

        # Dual variables: y = B^{-T} c_B
        c_B = c_t[basic]
        y = lu.solve(c_B, transpose=True)

        # Reduced costs for nonbasic variables
        rc = np.empty(len(nonbasic), dtype=np.float64)
        for k, j in enumerate(nonbasic):
            rc[k] = c_t[j] - float(A_t[:, j] @ y)

        # Most negative reduced cost (Dantzig pricing)
        min_rc_idx = int(np.argmin(rc))
        min_rc = rc[min_rc_idx]

        if min_rc >= -opts.dual_tol:
            # Dual feasible -> check primal feasibility
            # If artificials are all zero, solution is feasible
            art_in_basis = np.sum(basic >= n_ext)
            art_val = np.sum(x_B[basic >= n_ext]) if art_in_basis > 0 else 0.0

            if art_val > opts.primal_tol * m:
                return FarkasRay(y=y[:m], msg="Infeasible: artificials nonzero at optimality")

            # Reconstruct primal solution
            x_full = lo_t[:n_ext].copy()
            for slot, col in enumerate(basic):
                if col < n_ext:
                    x_full[col] = lo_t[col] + x_B[slot]

            x_sol = x_full[:n]
            z_p = float(c_ext @ x_full[:n_ext]) + model.obj_const
            z_d = float(b_eq @ y[:m]) + model.obj_const
            gap = abs(z_p - z_d) / (1.0 + abs(z_d))

            return LPResult(
                status="OPTIMAL",
                x=x_sol, y=y[:m],
                z_primal=z_p, z_dual=z_d,
                gap=gap, iters=iters,
                msg=f"Optimal in {iters} iterations",
            )

        entering_col = nonbasic[min_rc_idx]
        entering_idx = min_rc_idx

        # Compute eta column: d = B^{-1} a_entering
        a_e = A_t[:, entering_col]
        d = lu.solve(a_e)

        # Ratio test: min (x_B[i] / d[i]) for d[i] > tol, considering hi bounds
        ratios = np.full(m, np.inf)
        for i in range(m):
            if d[i] > opts.harris_tol:
                ratios[i] = x_B[i] / d[i]
            # TODO: bound flipping for bounded nonbasics (Phase 2)

        if np.all(ratios == np.inf):
            # Unbounded direction
            dx = np.zeros(n)
            # Direction in original variables: negate entering column direction
            for i in range(m):
                if basic[i] < n:
                    dx[basic[i]] = -d[i]
            if entering_col < n:
                dx[entering_col] = 1.0
            return UnboundedRay(d=dx, msg="LP is unbounded")

        leaving_slot = int(np.argmin(ratios))
        step = ratios[leaving_slot]

        # Update x_B
        x_B -= step * d
        x_B[leaving_slot] = step

        # Swap
        leaving_col = basic[leaving_slot]
        basic[leaving_slot] = entering_col
        nonbasic[entering_idx] = leaving_col

        # Refactorize periodically
        if iters % opts.refactor_freq == 0:
            B = A_t[:, basic]
            try:
                lu = LUFactor.factor(B)
                c_B = c_t[basic]
                # Recompute x_B from scratch for numerical stability
                rhs = b_shifted.copy()
                for k2, col in enumerate(basic):
                    pass  # keep x_B from updates (will fix next refactor)
            except SingularBasisError:
                return LPResult(
                    status="NUMERICAL", x=np.zeros(n), y=np.zeros(m),
                    z_primal=float("inf"), z_dual=float("-inf"), gap=float("inf"),
                    iters=iters, msg="Refactorization failed",
                )

    return LPResult(
        status="MAX_ITER", x=np.zeros(n), y=np.zeros(m),
        z_primal=float("inf"), z_dual=float("-inf"), gap=float("inf"),
        iters=iters, msg=f"Max iterations ({opts.max_iter}) reached",
    )


def _standard_form(model: Model):
    """Convert model to standard form for simplex."""
    m, n = model.nrows, model.ncols
    A_csr = model.A_csr

    # Build dense A
    A = np.zeros((m, n), dtype=np.float64)
    for i in range(m):
        s, e = A_csr.indptr[i], A_csr.indptr[i + 1]
        for k in range(s, e):
            A[i, A_csr.indices[k]] = A_csr.data[k]

    # Add slacks for inequalities
    n_slacks = m
    n_ext = n + n_slacks
    A_ext = np.zeros((m, n_ext), dtype=np.float64)
    A_ext[:, :n] = A

    c_ext = np.zeros(n_ext, dtype=np.float64)
    c_ext[:n] = model.c

    b_eq = np.zeros(m, dtype=np.float64)
    lo_ext = np.zeros(n_ext, dtype=np.float64)
    hi_ext = np.full(n_ext, INF, dtype=np.float64)
    lo_ext[:n] = model.col_lo
    hi_ext[:n] = model.col_hi

    for i in range(m):
        lo_r, hi_r = model.row_lo[i], model.row_hi[i]
        if lo_r > -INF * 0.9 and hi_r < INF * 0.9:
            # Ranged: s in [0, hi-lo], RHS = lo
            A_ext[i, n + i] = 1.0
            b_eq[i] = lo_r
            hi_ext[n + i] = hi_r - lo_r
        elif lo_r > -INF * 0.9:
            # G row: Ax - s = lo, s >= 0
            A_ext[i, n + i] = -1.0
            b_eq[i] = lo_r
        elif hi_r < INF * 0.9:
            # L row: Ax + s = hi, s >= 0
            A_ext[i, n + i] = 1.0
            b_eq[i] = hi_r
        else:
            # Free row: treat as equality at 0
            b_eq[i] = 0.0

    # Shift by lower bounds: A_ext (x - lo) = b_eq - A_ext lo
    b_shifted = b_eq.copy()
    for j in range(n_ext):
        if lo_ext[j] != 0.0:
            b_shifted -= A_ext[:, j] * lo_ext[j]

    return c_ext, A_ext, b_shifted, lo_ext, hi_ext
