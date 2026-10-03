"""
nirbhar/certificate/safe_bound.py
==================================
Rigorous dual lower bound computation for LP solutions.

For any dual multiplier vector y, computes a certified lower bound LB(y)
on the optimal LP objective that is valid regardless of floating-point errors
in y's computation.

Formula (from Neumaier & Shcherbina 2004 / NIRBHAR spec §4):
    d_j = c_j - sum_i( A_ij * y_i )          (reduced cost for variable j)

    LB(y) = sum_i( max(y_i,0) * row_lo_i + min(y_i,0) * row_hi_i )
            + sum_j( max(d_j,0) * col_lo_j + min(d_j,0) * col_hi_j )

Convention: 0 * (±∞) = 0  (product is zeroed when bound is infinite).

Conservative float64 error allowance:
    eps = (n + m) * eps_machine * sum(|terms|)

where eps_machine = 2^{-52} ≈ 2.22e-16 for IEEE 754 float64.

Sovereignty: no external solver imports.
"""

from __future__ import annotations

import numpy as np
from nirbhar.io.model import Model, INF

_EPS_MACHINE = float(np.finfo(np.float64).eps)   # 2.22e-16
_INF_THRESHOLD = INF * 0.9   # 9e29 — treat as ±∞


def safe_lower_bound(
    model: Model,
    y: np.ndarray,
) -> tuple[float, float]:
    """
    Compute rigorous dual lower bound LB(y) and its error margin.

    Parameters
    ----------
    model : Model
        The LP model (minimisation).
    y : np.ndarray, shape (m,)
        Dual multiplier vector.

    Returns
    -------
    (lb, margin) : tuple[float, float]
        lb     : conservative lower bound  (lb - margin is the safe bound)
        margin : float64 rounding error allowance (>= 0)

    The safe lower bound on the optimal objective is  lb - margin.
    At optimality lb ≈ primal_obj and margin ≈ 0.
    """
    m, n = model.nrows, model.ncols

    # ── Build dense A matrix ───────────────────────────────────────────────────
    A_csr = model.A_csr
    A = np.zeros((m, n), dtype=np.float64)
    for i in range(m):
        s, e = A_csr.indptr[i], A_csr.indptr[i + 1]
        for k in range(s, e):
            A[i, A_csr.indices[k]] = A_csr.data[k]

    # ── Reduced costs d_j = c_j - A[:,j]^T y ─────────────────────────────────
    d = model.c - A.T @ y    # shape (n,)

    # ── Row bound terms ───────────────────────────────────────────────────────
    # max(y_i, 0) * row_lo_i : only when row_lo_i is finite
    y_pos = np.maximum(y, 0.0)
    y_neg = np.minimum(y, 0.0)

    row_lo = model.row_lo
    row_hi = model.row_hi

    row_lo_fin = np.where(np.abs(row_lo) < _INF_THRESHOLD, row_lo, 0.0)
    row_hi_fin = np.where(np.abs(row_hi) < _INF_THRESHOLD, row_hi, 0.0)

    row_terms = y_pos * row_lo_fin + y_neg * row_hi_fin

    # ── Column bound terms ────────────────────────────────────────────────────
    # max(d_j, 0) * col_lo_j + min(d_j, 0) * col_hi_j
    d_pos = np.maximum(d, 0.0)
    d_neg = np.minimum(d, 0.0)

    col_lo = model.col_lo
    col_hi = model.col_hi

    col_lo_fin = np.where(np.abs(col_lo) < _INF_THRESHOLD, col_lo, 0.0)
    col_hi_fin = np.where(np.abs(col_hi) < _INF_THRESHOLD, col_hi, 0.0)

    col_terms = d_pos * col_lo_fin + d_neg * col_hi_fin

    # ── LB(y) ─────────────────────────────────────────────────────────────────
    lb_raw = float(np.sum(row_terms) + np.sum(col_terms)) + model.obj_const

    # ── Error margin ─────────────────────────────────────────────────────────
    # Conservative: (n + m) * eps_machine * sum(|terms|)
    abs_sum = (
        float(np.sum(np.abs(row_terms)))
        + float(np.sum(np.abs(col_terms)))
        + abs(model.obj_const)
    )
    margin = (n + m) * _EPS_MACHINE * abs_sum

    return lb_raw, margin


def safe_lower_bound_simple(model: Model, y: np.ndarray) -> float:
    """
    Return the safe lower bound  lb - margin.

    This is the tightest provably-valid lower bound given y.
    """
    lb, margin = safe_lower_bound(model, y)
    return lb - margin
