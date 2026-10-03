"""
nirbhar/mip/heuristics.py
=========================
Primal heuristics and integer feasibility checks (§6.8).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

from nirbhar.io.model import Model, INF


@dataclass
class HeuristicIncumbent:
    x: np.ndarray
    objective: float
    heuristic_name: str


def is_integer_feasible(model: Model, x: np.ndarray, tol: float = 1e-4) -> bool:
    """Check if all designated integer variables take integer values within tolerance."""
    integrality = model.integrality
    if integrality is None:
        return True

    for j in range(model.ncols):
        if integrality[j] != 0:
            val = float(x[j])
            dist = abs(val - round(val))
            if dist > tol:
                return False
    return True


def try_rounding_heuristic(model: Model, x_lp: np.ndarray) -> Optional[HeuristicIncumbent]:
    """
    Attempt simple rounding heuristic on fractional integer variables.
    Returns feasible incumbent if rounding satisfies all constraints.
    """
    integrality = model.integrality
    if integrality is None or not np.any(integrality):
        return None

    x_cand = x_lp.copy()
    for j in range(model.ncols):
        if integrality[j] != 0:
            x_cand[j] = round(float(x_cand[j]))
            x_cand[j] = max(float(model.col_lo[j]), min(float(model.col_hi[j]), float(x_cand[j])))

    # Check linear constraints Ax in [row_lo, row_hi]
    A_csr = model.A_csr
    m = model.nrows
    for i in range(m):
        s, e = A_csr.indptr[i], A_csr.indptr[i + 1]
        ax_i = float(A_csr.data[s:e] @ x_cand[A_csr.indices[s:e]]) if e > s else 0.0

        r_lo = float(model.row_lo[i])
        r_hi = float(model.row_hi[i])

        if r_lo > -INF * 0.9 and ax_i < r_lo - 1e-6:
            return None
        if r_hi < INF * 0.9 and ax_i > r_hi + 1e-6:
            return None

    obj = float(model.c @ x_cand) + model.obj_const
    return HeuristicIncumbent(
        x=x_cand,
        objective=obj,
        heuristic_name="simple-rounding",
    )
