"""
nirbhar/qp/outer_approx.py
==========================
Kelley's Outer-Approximation algorithm for Convex Mixed-Integer Quadratic Programs (MIQP) (§6.10).

Formulation:
    min  c^T x + 1/2 x^T Q x + obj_const
    s.t. row_lo <= A x <= row_hi
         col_lo <= x   <= col_hi
         x_j in Z  for j in Integrals

Solves via outer-approximation tangent cuts:
    theta - (Q x^k)^T x >= -1/2 (x^k)^T Q x^k
"""

from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Optional, List
import numpy as np

from nirbhar.io.model import Model, INF, build_csr, build_csc
from nirbhar.lp.dual_simplex import LPResult
from nirbhar.mip.bb import branch_and_cut_solve, BCOptions, BCResult
from nirbhar.mip.heuristics import is_integer_feasible
from nirbhar.qp.mehrotra_qp import qp_solve, QPOptions
from nirbhar.qp.psd import check_psd


@dataclass
class MIQPOptions:
    max_iter: int = 25
    gap_tol: float = 1e-4
    time_limit_s: float = 30.0
    verbose: bool = False


@dataclass
class MIQPResult:
    status: str
    objective: float
    lower_bound: float
    gap: float
    x: np.ndarray
    iterations: int
    time_s: float
    cuts_generated: int
    msg: str = ""


def outer_approximation_miqp(
    model: Model,
    opts: Optional[MIQPOptions] = None,
) -> MIQPResult:
    """
    Solve convex MIQP using Kelley's Outer-Approximation with tangent cuts.
    """
    t0 = time.perf_counter()
    options = opts or MIQPOptions()

    is_psd, psd_msg, q_diag = check_psd(model)
    if not is_psd:
        return MIQPResult(
            status="UNSUPPORTED",
            objective=math.nan,
            lower_bound=math.nan,
            gap=math.nan,
            x=np.zeros(model.ncols),
            iterations=0,
            time_s=time.perf_counter() - t0,
            cuts_generated=0,
            msg=psd_msg,
        )

    n_orig = model.ncols
    m_orig = model.nrows

    # 1. Solve initial continuous relaxation QP
    rel_res = qp_solve(model, QPOptions(max_iter=100))
    if rel_res.status != "OPTIMAL":
        return MIQPResult(
            status=rel_res.status,
            objective=rel_res.z_primal,
            lower_bound=rel_res.z_dual,
            gap=rel_res.gap,
            x=rel_res.x,
            iterations=0,
            time_s=time.perf_counter() - t0,
            cuts_generated=0,
            msg=f"Continuous QP relaxation failed: {rel_res.status}",
        )

    x0 = rel_res.x
    # If continuous relaxation is already integer feasible, optimal!
    if is_integer_feasible(model, x0):
        obj0 = float(model.c @ x0 + 0.5 * (x0 * q_diag) @ x0) + model.obj_const
        return MIQPResult(
            status="OPTIMAL",
            objective=obj0,
            lower_bound=obj0,
            gap=0.0,
            x=x0,
            iterations=0,
            time_s=time.perf_counter() - t0,
            cuts_generated=0,
            msg="Continuous relaxation is integer feasible",
        )

    # 2. Build Master MILP with auxiliary variable theta:
    # Variables: [x_1, ..., x_n, theta]
    # theta index = n_orig
    # Master objective: min c^T x + theta + obj_const
    c_master = np.zeros(n_orig + 1, dtype=np.float64)
    c_master[:n_orig] = model.c
    c_master[n_orig] = 1.0  # + theta

    col_lo_master = np.zeros(n_orig + 1, dtype=np.float64)
    col_hi_master = np.zeros(n_orig + 1, dtype=np.float64)
    col_lo_master[:n_orig] = model.col_lo
    col_hi_master[:n_orig] = model.col_hi
    col_lo_master[n_orig] = 0.0      # 1/2 x^T Q x >= 0 since Q is PSD
    col_hi_master[n_orig] = INF

    integrality_master = np.zeros(n_orig + 1, dtype=np.int8)
    if model.integrality is not None:
        integrality_master[:n_orig] = model.integrality
    integrality_master[n_orig] = 0   # theta is continuous

    col_names_master = list(model.col_names) + ["theta"]

    # Initial tangent cuts list: (coeffs of size n_orig+1, rhs)
    # theta - (Q x^k)^T x >= -1/2 (x^k)^T Q x^k
    tangent_cuts: list[tuple[np.ndarray, float]] = []

    def make_tangent_cut(xk: np.ndarray) -> tuple[np.ndarray, float]:
        q_xk = q_diag * xk
        # Coeffs for [x; theta]: [-q_xk; 1.0] @ [x; theta] >= -0.5 * (xk * q_xk)
        cut_coeffs = np.zeros(n_orig + 1, dtype=np.float64)
        cut_coeffs[:n_orig] = -q_xk
        cut_coeffs[n_orig] = 1.0
        cut_rhs = float(-0.5 * np.sum(xk * q_xk))
        return cut_coeffs, cut_rhs

    tangent_cuts.append(make_tangent_cut(x0))

    best_ub = math.inf
    best_x: Optional[np.ndarray] = None
    global_lb = rel_res.z_primal
    final_gap = math.inf
    it = 0

    for it in range(1, options.max_iter + 1):
        if (time.perf_counter() - t0) > options.time_limit_s:
            break

        # Construct Master MILP Model
        n_cuts = len(tangent_cuts)
        m_master = m_orig + n_cuts

        row_lo_master = np.empty(m_master, dtype=np.float64)
        row_hi_master = np.empty(m_master, dtype=np.float64)
        row_lo_master[:m_orig] = model.row_lo
        row_hi_master[:m_orig] = model.row_hi

        for c_idx, (coeffs, rhs) in enumerate(tangent_cuts):
            r = m_orig + c_idx
            row_lo_master[r] = rhs
            row_hi_master[r] = INF

        rows_coo = []
        cols_coo = []
        vals_coo = []

        # Original matrix rows
        for i in range(m_orig):
            s_i, e_i = model.A_csr.indptr[i], model.A_csr.indptr[i + 1]
            if e_i > s_i:
                rows_coo.extend([i] * (e_i - s_i))
                cols_coo.extend(model.A_csr.indices[s_i:e_i].tolist())
                vals_coo.extend(model.A_csr.data[s_i:e_i].tolist())

        # Tangent cut rows
        for c_idx, (coeffs, _) in enumerate(tangent_cuts):
            r = m_orig + c_idx
            for j in range(n_orig + 1):
                v = float(coeffs[j])
                if abs(v) > 1e-12:
                    rows_coo.append(r)
                    cols_coo.append(j)
                    vals_coo.append(v)

        master_csr = build_csr(rows_coo, cols_coo, vals_coo, m_master, n_orig + 1)
        master_csc = build_csc(rows_coo, cols_coo, vals_coo, m_master, n_orig + 1)

        row_names_master = list(model.row_names) + [f"tangent_cut_{k+1}" for k in range(n_cuts)]

        master_model = Model(
            nrows=m_master,
            ncols=n_orig + 1,
            c=c_master,
            obj_const=model.obj_const,
            sense=model.sense,
            A_csr=master_csr,
            A_csc=master_csc,
            row_lo=row_lo_master,
            row_hi=row_hi_master,
            col_lo=col_lo_master.copy(),
            col_hi=col_hi_master.copy(),
            integrality=integrality_master,
            Q_upper=None,  # Master problem is an MILP!
            row_names=tuple(row_names_master),
            col_names=tuple(col_names_master),
            obj_name=model.obj_name,
            sha256=model.sha256,
            source_path=model.source_path,
        )

        # Solve Master MILP
        milp_res = branch_and_cut_solve(master_model, BCOptions(max_nodes=100, use_cuts=False))

        if milp_res.status not in ("OPTIMAL", "OPTIMAL_WITHIN_GAP"):
            break

        xk = milp_res.x[:n_orig]
        thetak = float(milp_res.x[n_orig])
        lb_k = milp_res.objective
        global_lb = max(global_lb, lb_k)

        # Evaluate true QP objective at integer solution xk
        true_obj_k = float(model.c @ xk + 0.5 * (xk * q_diag) @ xk) + model.obj_const
        if true_obj_k < best_ub:
            best_ub = true_obj_k
            best_x = xk.copy()

        denom = max(1.0, abs(best_ub))
        final_gap = abs(best_ub - global_lb) / denom

        if options.verbose:
            print(f"MIQP OA it={it}: LB={global_lb:.6f}, UB={best_ub:.6f}, gap={final_gap:.2e}")

        if final_gap <= options.gap_tol:
            break

        # Generate new tangent cut at xk
        tangent_cuts.append(make_tangent_cut(xk))

    is_optimal = math.isfinite(best_ub) and final_gap <= options.gap_tol
    status = "OPTIMAL" if is_optimal else ("FEASIBLE" if math.isfinite(best_ub) else "TIME_LIMIT")

    return MIQPResult(
        status=status,
        objective=best_ub,
        lower_bound=global_lb,
        gap=final_gap if math.isfinite(final_gap) else 0.0,
        x=best_x if best_x is not None else x0,
        iterations=it,
        time_s=time.perf_counter() - t0,
        cuts_generated=len(tangent_cuts),
        msg=f"Outer-Approximation: {status} in {it} iterations",
    )
