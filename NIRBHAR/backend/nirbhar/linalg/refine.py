"""
nirbhar/linalg/refine.py
==========================
Iterative refinement for LU solves.

After computing x = B^{-1} b, compute residual r = b - B x,
then solve B delta = r, update x += delta.
Typically 1-2 steps are sufficient.

Phase 1: dense; Phase 2: sparse with mixed precision.
"""

from __future__ import annotations
import numpy as np
from nirbhar.linalg.lu_markowitz import LUFactor


def iterative_refine(
    lu: LUFactor,
    B: np.ndarray,
    b: np.ndarray,
    x0: np.ndarray,
    steps: int = 2,
    tol: float = 1e-10,
) -> np.ndarray:
    """
    Refine solution x0 of B x = b.

    Parameters
    ----------
    lu   : LUFactor for B
    B    : original basis matrix (needed to compute residual)
    b    : right-hand side
    x0   : initial solution estimate
    steps: max refinement steps
    tol  : stop if relative residual < tol

    Returns
    -------
    Refined x
    """
    x = x0.copy()
    b_norm = np.linalg.norm(b, np.inf) + 1e-300

    for _ in range(steps):
        r = b - B @ x
        rel = np.linalg.norm(r, np.inf) / b_norm
        if rel < tol:
            break
        dx = lu.solve(r)
        x = x + dx

    return x
