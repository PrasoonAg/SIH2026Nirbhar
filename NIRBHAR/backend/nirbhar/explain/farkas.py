"""
nirbhar/explain/farkas.py
=========================
Farkas certificate extraction and certification for infeasible models (§6.7, §7).

Proves that no assignment can satisfy row and variable bounds:
    A^T y = r_y
    farkas_val(y) = y^T (row bounds) + r_y^T (col bounds) > 0
Contradicting 0 >= farkas_val(y) for any feasible point.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional
import numpy as np

from nirbhar.io.model import Model, INF
from nirbhar.lp.dual_simplex import FarkasRay, LPResult


@dataclass
class FarkasCertificate:
    is_valid: bool
    y: np.ndarray
    farkas_value: float
    max_dual_violation: float
    explanation: str


def certify_farkas_ray(
    model: Model,
    ray: np.ndarray,
    tol: float = 1e-6,
) -> FarkasCertificate:
    """
    Verify and certify a Farkas ray y for the given model.
    """
    m, n = model.nrows, model.ncols
    y = np.asarray(ray, dtype=np.float64).flatten()
    if len(y) != m:
        return FarkasCertificate(
            is_valid=False,
            y=y,
            farkas_value=-math.inf,
            max_dual_violation=math.inf,
            explanation=f"Farkas ray dimension mismatch: got {len(y)}, expected {m}",
        )

    # Normalize ray to prevent scaling artifacts
    norm_y = float(np.linalg.norm(y))
    if norm_y > 1e-12:
        y = y / norm_y
    else:
        return FarkasCertificate(
            is_valid=False,
            y=y,
            farkas_value=0.0,
            max_dual_violation=0.0,
            explanation="Trivial zero ray cannot certify infeasibility",
        )

    # r_y = A^T y
    ATy = model.A_csc.matvec(y)

    farkas_val = 0.0

    # 1. Row bound contributions
    for i in range(m):
        yi = float(y[i])
        if abs(yi) < 1e-12:
            continue
        r_lo = float(model.row_lo[i])
        r_hi = float(model.row_hi[i])

        if yi > 1e-9:
            if r_lo > -INF * 0.9:
                farkas_val += yi * r_lo
            else:
                return FarkasCertificate(
                    is_valid=False,
                    y=y,
                    farkas_value=-math.inf,
                    max_dual_violation=abs(yi),
                    explanation=f"Ray has y[{i}] > 0 on unconstrained lower bound row {i}",
                )
        elif yi < -1e-9:
            if r_hi < INF * 0.9:
                farkas_val += yi * r_hi
            else:
                return FarkasCertificate(
                    is_valid=False,
                    y=y,
                    farkas_value=-math.inf,
                    max_dual_violation=abs(yi),
                    explanation=f"Ray has y[{i}] < 0 on unconstrained upper bound row {i}",
                )

    # 2. Variable bound contributions
    max_dual_viol = 0.0
    for j in range(n):
        rj = float(ATy[j])
        if abs(rj) < 1e-12:
            continue
        c_lo = float(model.col_lo[j])
        c_hi = float(model.col_hi[j])

        # If r_j > 0, term is -r_j * x_j <= -r_j * c_lo
        # So in duality: A^T y <= 0 when x >= 0
        if rj > 1e-9:
            if c_lo > -INF * 0.9:
                farkas_val -= rj * c_lo
            else:
                max_dual_viol = max(max_dual_viol, rj)
        elif rj < -1e-9:
            if c_hi < INF * 0.9:
                farkas_val -= rj * c_hi
            else:
                max_dual_viol = max(max_dual_viol, -rj)

    is_valid = (farkas_val > tol) and (max_dual_viol <= tol)
    expl = (
        f"Certified Farkas Ray: contradiction value = {farkas_val:.4e} > 0 (proves 0 >= {farkas_val:.4e})"
        if is_valid
        else f"Farkas ray check failed: value = {farkas_val:.4e}, max dual violation = {max_dual_viol:.4e}"
    )

    return FarkasCertificate(
        is_valid=is_valid,
        y=y,
        farkas_value=farkas_val,
        max_dual_violation=max_dual_viol,
        explanation=expl,
    )
