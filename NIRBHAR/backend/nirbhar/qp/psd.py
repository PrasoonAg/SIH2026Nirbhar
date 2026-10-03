"""
nirbhar/qp/psd.py
=================
Positive Semidefinite (PSD) verification and eigenvalue certification for Q (§6.10).
Refuses non-convex quadratic forms with certified UNSUPPORTED status.
"""

from __future__ import annotations
import math
from typing import Tuple, Optional
import numpy as np

from nirbhar.io.model import Model


def check_psd(
    model: Model,
    tol: float = -1e-8,
) -> Tuple[bool, str, Optional[np.ndarray]]:
    """
    Check if the quadratic matrix Q in model is positive semidefinite (Q >= 0).
    
    Returns:
      (is_psd, message, q_diag)
    """
    if model.Q_upper is None or len(model.Q_upper) == 0:
        return True, "No quadratic objective term (pure LP)", np.zeros(model.ncols)

    n = model.ncols
    q_diag = np.zeros(n, dtype=np.float64)

    # Check if Q is purely diagonal or has off-diagonal terms
    has_off_diag = False
    for (i, j), val in model.Q_upper.items():
        if i == j:
            q_diag[i] = val
        else:
            if abs(val) > 1e-12:
                has_off_diag = True

    # 1. Quick diagonal check: if any diagonal entry is negative, Q cannot be PSD
    min_diag = float(np.min(q_diag))
    if min_diag < tol:
        return (
            False,
            f"NON_CONVEX_UNSUPPORTED: negative diagonal entry Q[{np.argmin(q_diag)}, {np.argmin(q_diag)}] = {min_diag:.4e} < 0",
            None,
        )

    # 2. If diagonal only, it is PSD since all q_jj >= tol
    if not has_off_diag:
        return True, "Convex separable quadratic objective (diagonal Q >= 0)", q_diag

    # 3. Dense / general check via symmetric matrix reconstruction and Cholesky / eigenvalues
    # Reconstruct dense Q for full PSD validation
    Q_dense = np.zeros((n, n), dtype=np.float64)
    for (i, j), val in model.Q_upper.items():
        Q_dense[i, j] = val
        Q_dense[j, i] = val

    # Eigenvalues of symmetric matrix via numpy.linalg.eigvalsh (sovereign standard numpy)
    eigenvalues = np.linalg.eigvalsh(Q_dense)
    min_eig = float(np.min(eigenvalues))

    if min_eig < tol:
        return (
            False,
            f"NON_CONVEX_UNSUPPORTED: minimum eigenvalue {min_eig:.4e} < 0",
            None,
        )

    return True, f"Convex quadratic objective verified (min eigenvalue = {min_eig:.4e} >= 0)", q_diag
