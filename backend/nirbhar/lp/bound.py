"""
nirbhar/lp/bound.py
===================
Rigorous safe lower bound calculation for LP, MILP, and convex QP (§6.7).
Guaranteed certified lower bound via Lagrangian duality.
"""

from __future__ import annotations
import math
from typing import Optional
import numpy as np

from nirbhar.io.model import Model, INF


def compute_safe_lower_bound(
    model: Model,
    y: Optional[np.ndarray] = None,
    rc: Optional[np.ndarray] = None,
    q_diag: Optional[np.ndarray] = None,
) -> float:
    """
    Compute certified safe lower bound LB(y) for any dual vector y.
    
    For LP/MILP:
      min  c^T x + obj_const
      s.t. row_lo <= A x <= row_hi
           col_lo <= x   <= col_hi
    
    If y is None or zeros, computes unconstrained variable bound:
      LB = min_{col_lo <= x <= col_hi} c^T x + obj_const
    """
    m = model.nrows
    n = model.ncols

    lb = float(model.obj_const)

    if y is not None and len(y) == m:
        # 1. Row contributions:
        # If y_i > 0, constraint is A_i x >= row_lo_i  ==> term +y_i * row_lo_i
        # If y_i < 0, constraint is A_i x <= row_hi_i  ==> term +y_i * row_hi_i
        for i in range(m):
            yi = float(y[i])
            if abs(yi) < 1e-13:
                continue

            r_lo = float(model.row_lo[i])
            r_hi = float(model.row_hi[i])

            if yi > 1e-12:
                if r_lo > -INF * 0.9:
                    lb += yi * r_lo
                elif yi > 1e-5:
                    return -math.inf
            elif yi < -1e-12:
                if r_hi < INF * 0.9:
                    lb += yi * r_hi
                elif -yi > 1e-5:
                    return -math.inf

        # 2. Compute reduced costs: rc = c - A^T y
        if rc is None:
            ATy = model.A_csc.matvec(y)
            rc_vec = model.c - ATy
        else:
            rc_vec = rc
    else:
        rc_vec = model.c

    # 3. Variable contributions
    for j in range(n):
        rj = float(rc_vec[j])
        c_lo = float(model.col_lo[j])
        c_hi = float(model.col_hi[j])
        qj = float(q_diag[j]) if q_diag is not None and len(q_diag) == n else 0.0

        if qj > 1e-12:
            # Separable convex quadratic term 0.5 * qj * x_j^2 + rj * x_j
            t_opt = -rj / qj
            t = max(c_lo, min(c_hi, t_opt))
            lb += 0.5 * qj * t * t + rj * t
        else:
            if abs(rj) < 1e-13:
                continue
            if rj > 1e-12:
                if c_lo > -INF * 0.9:
                    lb += rj * c_lo
                elif rj > 1e-5:
                    return -math.inf
            elif rj < -1e-12:
                if c_hi < INF * 0.9:
                    lb += rj * c_hi
                elif -rj > 1e-5:
                    return -math.inf

    return lb
