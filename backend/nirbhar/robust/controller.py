"""
nirbhar/robust/controller.py
=============================
Phase 2 M12: Robustness Controller — escalation table for LP solver failures.

Escalation levels (applied sequentially):
  Level 0: Plain two-phase simplex (DSSOptions defaults)
  Level 1: Stall detected → Bland anti-cycling (reduce max_degenerate)
  Level 2: Numerical issues → tighter harris_tol + more frequent refactor
  Level 3: Scaling (Ruiz presolve) → presolve then simplex
  Level 4: IPM fallback (Mehrotra) → use as primary solver

naive_mode: Uses only Level 0 (unprotected textbook simplex).
Used to demonstrate where a solver without robustness features fails.

Also provides:
  - SolverResult with the escalation level used
  - dispatch_solve(): tries levels until OPTIMAL or exhausted

Sovereignty: no external solver imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from nirbhar.io.model import Model
from nirbhar.lp.dual_simplex import (
    dual_simplex_solve, DSSOptions, LPResult, FarkasRay, UnboundedRay
)


import time

@dataclass
class RobustOptions:
    max_level: int = 4          # 0=naive, 1=Bland, 2=tight, 3=presolve, 4=IPM
    naive_mode: bool = False    # if True, only use Level 0 (no robustness)
    verbose: bool = False
    time_limit_s: float = 300.0


@dataclass
class SolverResult:
    inner: object               # LPResult | FarkasRay | UnboundedRay
    level_used: int             # escalation level that produced result
    attempts: int
    status: str


def dispatch_solve(
    model: Model,
    opts: Optional[RobustOptions] = None,
) -> SolverResult:
    """
    Try escalating robustness levels until OPTIMAL or all levels exhausted.

    Parameters
    ----------
    model : Model
    opts  : RobustOptions

    Returns
    -------
    SolverResult
    """
    if opts is None:
        opts = RobustOptions()

    max_level = 0 if opts.naive_mode else opts.max_level
    attempts = 0
    result = None
    t0 = time.perf_counter()

    for level in range(max_level + 1):
        elapsed = time.perf_counter() - t0
        if elapsed > opts.time_limit_s:
            break
        attempts += 1
        if opts.verbose:
            print(f"[Robust] Trying level {level}...")

        rem_time = max(0.1, opts.time_limit_s - elapsed)
        result = _solve_at_level(model, level, opts, time_limit_s=rem_time)

        # Accept OPTIMAL and INFEASIBLE immediately
        if isinstance(result, (FarkasRay, UnboundedRay)):
            return SolverResult(inner=result, level_used=level,
                                attempts=attempts, status=result.status)

        if isinstance(result, LPResult):
            if result.status == "OPTIMAL":
                return SolverResult(inner=result, level_used=level,
                                    attempts=attempts, status="OPTIMAL")
            if result.status == "INFEASIBLE":
                return SolverResult(inner=result, level_used=level,
                                    attempts=attempts, status="INFEASIBLE")
            # Otherwise: MAX_ITER, NUMERICAL -> escalate

    # All levels exhausted
    return SolverResult(
        inner=result,
        level_used=max_level,
        attempts=attempts,
        status=getattr(result, "status", "FAILED"),
    )


def _solve_at_level(model: Model, level: int, opts: RobustOptions, time_limit_s: float = float("inf")) -> object:
    """Apply one escalation level and return result."""
    base_iter = min(1500, max(500, 5 * model.nrows))

    if level == 0:
        # -- Level 0: Standard two-phase simplex -------------------------------
        dss_opts = DSSOptions(
            max_iter=base_iter,
            refactor_freq=40,
            max_degenerate=150,
            verbose=opts.verbose,
            time_limit_s=time_limit_s,
        )
        return dual_simplex_solve(model, opts=dss_opts)

    elif level == 1:
        # -- Level 1: Bland anti-cycling (max_degenerate=0) -------------------
        dss_opts = DSSOptions(
            max_iter=base_iter,
            refactor_freq=30,
            max_degenerate=0,   # Always use Bland
            harris_tol=1e-9,
            verbose=opts.verbose,
            time_limit_s=time_limit_s,
        )
        return dual_simplex_solve(model, opts=dss_opts)

    elif level == 2:
        # -- Level 2: Tighter numerics + more frequent refactor ----------------
        dss_opts = DSSOptions(
            max_iter=base_iter,
            refactor_freq=20,
            max_degenerate=50,
            harris_tol=1e-9,
            primal_tol=1e-10,
            dual_tol=1e-10,
            verbose=opts.verbose,
            time_limit_s=time_limit_s,
        )
        return dual_simplex_solve(model, opts=dss_opts)

    elif level == 3:
        # ── Level 3: Ruiz scaling presolve then simplex ───────────────────────
        try:
            from nirbhar.presolve.presolve import presolve, postsolve, PresolveOptions
            ps_opts = PresolveOptions(
                max_scaling_rounds=20,
                do_singleton_rows=True,
                do_fixed_vars=True,
            )
            ps = presolve(model, ps_opts)
            dss_opts = DSSOptions(
                max_iter=base_iter,
                refactor_freq=30,
                max_degenerate=50,
                verbose=opts.verbose,
                time_limit_s=time_limit_s,
            )
            inner = dual_simplex_solve(ps.model, opts=dss_opts)

            if isinstance(inner, LPResult) and inner.status == "OPTIMAL":
                # Postsolve: recover original solution
                x_orig, y_orig = postsolve(ps, inner.x, inner.y)
                z_p = float(model.c @ x_orig) + model.obj_const
                z_d = float(inner.z_dual)
                gap = abs(z_p - z_d) / (1.0 + abs(z_d))
                return LPResult(
                    status="OPTIMAL", x=x_orig, y=y_orig,
                    z_primal=z_p, z_dual=z_d, gap=gap,
                    iters=inner.iters, msg=f"Presolve+Simplex: {inner.msg}",
                )
            return inner
        except Exception as e:
            # Fallback: simplex without presolve
            dss_opts = DSSOptions(max_iter=base_iter, verbose=opts.verbose, time_limit_s=time_limit_s)
            return dual_simplex_solve(model, opts=dss_opts)

    elif level == 4:
        # ── Level 4: Mehrotra IPM ─────────────────────────────────────────────
        try:
            from nirbhar.ipm.mehrotra import mehrotra_ipm, IPMOptions
            ipm_opts = IPMOptions(
                max_iter=150,
                tol_feas=1e-8,
                tol_gap=1e-8,
                verbose=opts.verbose,
            )
            return mehrotra_ipm(model, opts=ipm_opts)
        except Exception as e:
            return LPResult(
                status="NUMERICAL", x=np.zeros(model.ncols), y=np.zeros(model.nrows),
                z_primal=float("inf"), z_dual=float("-inf"), gap=float("inf"),
                iters=0, msg=f"IPM failed: {e}",
            )

    else:
        dss_opts = DSSOptions(max_iter=200_000, verbose=opts.verbose)
        return dual_simplex_solve(model, opts=dss_opts)
