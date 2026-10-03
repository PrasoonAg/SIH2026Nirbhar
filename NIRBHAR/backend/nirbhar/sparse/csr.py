"""
nirbhar/sparse/csr.py
=====================
CSR sparse matrix operations (pure NumPy — no solver libs).
The Model class uses these for A and A^T products in all engines.
"""

from __future__ import annotations
import numpy as np
from nirbhar.io.model import CSRMatrix, build_csr


def csr_matvec(A: CSRMatrix, x: np.ndarray) -> np.ndarray:
    """y = A @ x  using NumPy indexing (faster than the pure-Python version in model.py)."""
    y = np.zeros(A.nrows, dtype=np.float64)
    for i in range(A.nrows):
        s, e = A.indptr[i], A.indptr[i + 1]
        if s < e:
            y[i] = A.data[s:e] @ x[A.indices[s:e]]
    return y


def csr_transpose_matvec(A: CSRMatrix, y: np.ndarray) -> np.ndarray:
    """z = A^T @ y  (scatter implementation)."""
    z = np.zeros(A.ncols, dtype=np.float64)
    for i in range(A.nrows):
        s, e = A.indptr[i], A.indptr[i + 1]
        if s < e:
            z[A.indices[s:e]] += A.data[s:e] * y[i]
    return z


def csr_row_norms(A: CSRMatrix) -> np.ndarray:
    """L2 norms of each row."""
    norms = np.zeros(A.nrows, dtype=np.float64)
    for i in range(A.nrows):
        s, e = A.indptr[i], A.indptr[i + 1]
        if s < e:
            norms[i] = np.linalg.norm(A.data[s:e])
    return norms


def csr_col_norms(A: CSRMatrix) -> np.ndarray:
    """L2 norms of each column (from CSR — requires scatter)."""
    norms = np.zeros(A.ncols, dtype=np.float64)
    for i in range(A.nrows):
        s, e = A.indptr[i], A.indptr[i + 1]
        if s < e:
            norms[A.indices[s:e]] += A.data[s:e] ** 2
    return np.sqrt(norms)
