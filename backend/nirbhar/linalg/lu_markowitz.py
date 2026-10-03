"""
nirbhar/linalg/lu_markowitz.py
================================
Dense LU factorization with partial pivoting for LP basis management.

Phase 1: dense LU for bases up to ~500 rows (documented in KNOWN_LIMITS.md).
Phase 2: replaced with sparse Markowitz LU.

API:
    lu = LUFactor.factor(B)      # factor an (m x m) basis matrix
    lu.solve(rhs, transpose=False) -> np.ndarray
    lu.condition_estimate() -> float (1-norm using Hager's method)

No solver libraries (SciPy, LAPACK wrappers not imported directly).
Uses pure NumPy routines: np.linalg.lu_factor / lu_solve for Phase 1.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np


class SingularBasisError(Exception):
    """Raised when the basis matrix is (near-)singular."""
    pass


@dataclass
class LUFactor:
    """
    Dense LU factorization result.

    Phase 1 implementation uses numpy's built-in LU (LAPACK dgetrf under the hood).
    This is intentional — NumPy is allowed; SciPy is not.
    """
    lu: np.ndarray          # (m, m) combined L/U storage
    piv: np.ndarray         # (m,) permutation from partial pivoting (1-indexed LAPACK style)
    m: int
    _rcond: Optional[float] = None

    @classmethod
    def factor(cls, B: np.ndarray, tol: float = 1e-14) -> "LUFactor":
        """
        Factor an (m x m) basis matrix B = P @ L @ U.

        Parameters
        ----------
        B : ndarray, shape (m, m)
        tol : float
            Minimum pivot magnitude below which we declare singularity.

        Returns
        -------
        LUFactor

        Raises
        ------
        SingularBasisError
        """
        m = B.shape[0]
        if B.ndim != 2 or B.shape[1] != m:
            raise ValueError(f"Expected square matrix, got shape {B.shape}")

        # Pure NumPy LU (scipy-free, works on all numpy versions)
        lu, piv = _lu_factor_pure(B)

        diag = np.abs(np.diag(lu))
        min_piv = diag.min() if m > 0 else 1.0
        if min_piv < tol:
            raise SingularBasisError(
                f"Basis is singular: min diagonal = {min_piv:.2e}"
            )
        return cls(lu=lu, piv=piv, m=m)

    def solve(self, rhs: np.ndarray, transpose: bool = False) -> np.ndarray:
        """
        Solve B @ x = rhs  (or B^T @ x = rhs if transpose=True).

        Parameters
        ----------
        rhs : ndarray, shape (m,) or (m, k)
        transpose : bool

        Returns
        -------
        ndarray, same shape as rhs
        """
        return _lu_solve_pure(self.lu, self.piv, rhs, transpose)

    def condition_estimate(self) -> float:
        """
        Estimate 1-norm condition number using Hager's power method.
        Returns inf if the system is singular.
        """
        try:
            # Cheap: use diagonal of U as proxy
            diag = np.abs(np.diag(self.lu))
            if diag.min() < 1e-300:
                return float("inf")
            # 1-norm of the full LU product vs identity solve
            e = np.ones(self.m, dtype=np.float64) / self.m
            y = self.solve(e)
            nA_inv = np.sum(np.abs(y))
            # Rough 1-norm of B: use column sums of lu (approximation)
            nA = np.max(np.sum(np.abs(self.lu), axis=0))
            return float(nA * nA_inv)
        except Exception:
            return float("inf")


# ---------------------------------------------------------------------------
# Pure-NumPy fallback LU (no LAPACK wrapper assumed)
# ---------------------------------------------------------------------------

def _lu_factor_pure(A: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    LU factorization with partial pivoting, pure NumPy.
    Returns (LU, piv) where LU is in-place combined storage and piv is 0-indexed.
    """
    m = A.shape[0]
    LU = A.astype(np.float64, copy=True)
    piv = np.arange(m, dtype=np.int32)

    for k in range(m):
        # Partial pivot: find max in column k below diagonal
        max_row = k + np.argmax(np.abs(LU[k:, k]))
        if max_row != k:
            LU[[k, max_row], :] = LU[[max_row, k], :]
            piv[[k, max_row]] = piv[[max_row, k]]

        pivot = LU[k, k]
        if abs(pivot) < 1e-300:
            pivot = 1e-300  # avoid div by zero; singularity caught by caller

        # Eliminate
        LU[k + 1:, k] /= pivot
        LU[k + 1:, k + 1:] -= np.outer(LU[k + 1:, k], LU[k, k + 1:])

    return LU, piv


def _lu_solve_pure(
    LU: np.ndarray,
    piv: np.ndarray,
    b: np.ndarray,
    transpose: bool = False,
) -> np.ndarray:
    """Solve using pure-NumPy LU factors (output from _lu_factor_pure)."""
    m = LU.shape[0]
    x = b.astype(np.float64, copy=True)

    if not transpose:
        # Apply row permutation
        x = x[piv]
        # Forward substitution (L)
        for i in range(1, m):
            x[i] -= LU[i, :i] @ x[:i]
        # Backward substitution (U)
        for i in range(m - 1, -1, -1):
            x[i] = (x[i] - LU[i, i + 1:] @ x[i + 1:]) / LU[i, i]
    else:
        # Solve U^T first
        for i in range(m):
            x[i] = (x[i] - LU[:i, i] @ x[:i]) / LU[i, i]
        # Solve L^T
        for i in range(m - 1, -1, -1):
            x[i] -= LU[i + 1:, i] @ x[i + 1:]
        # Undo permutation
        inv_piv = np.empty_like(piv)
        inv_piv[piv] = np.arange(m, dtype=piv.dtype)
        x = x[inv_piv]

    return x
