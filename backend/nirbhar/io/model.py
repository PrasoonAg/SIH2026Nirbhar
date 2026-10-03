"""
nirbhar/io/model.py
===================
Immutable Model dataclass.  Every engine, verifier, and test operates on this
single canonical representation.  Fields are set at parse time and never mutated.

Class: Model
  c           : np.ndarray (n,)         objective coefficients (minimisation)
  A_csr       : CSRMatrix               constraint matrix, row-major
  A_csc       : CSCMatrix               constraint matrix, column-major
  row_lo      : np.ndarray (m,)         row lower bounds (-inf = -1e30)
  row_hi      : np.ndarray (m,)         row upper bounds (+inf = +1e30)
  col_lo      : np.ndarray (n,)         variable lower bounds
  col_hi      : np.ndarray (n,)         variable upper bounds
  integrality : np.ndarray (n,) int8    0=continuous, 1=general integer, 2=binary
  Q_upper     : dict[tuple,float]|None  upper triangle of Q (for QP/MIQP)
  row_names   : list[str]
  col_names   : list[str]
  obj_name    : str
  sense       : str                     'min' or 'max'
  obj_const   : float                   objective constant (from RHS of objective row)
  sha256      : str                     hex digest of the original MPS/QPS bytes
  source_path : str | None              path from which the model was parsed
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# Sentinel for ±infinity in bounds
INF = 1e30


@dataclass(frozen=True)
class CSRMatrix:
    """Compressed Sparse Row matrix (immutable view)."""
    data: np.ndarray     # nonzero values
    indices: np.ndarray  # column indices
    indptr: np.ndarray   # row pointer
    shape: tuple[int, int]

    @property
    def nnz(self) -> int:
        return int(self.data.shape[0])

    @property
    def nrows(self) -> int:
        return self.shape[0]

    @property
    def ncols(self) -> int:
        return self.shape[1]

    def matvec(self, x: np.ndarray) -> np.ndarray:
        """y = A @ x  (dense x → dense y)."""
        y = np.zeros(self.nrows, dtype=np.float64)
        for i in range(self.nrows):
            for k in range(self.indptr[i], self.indptr[i + 1]):
                y[i] += self.data[k] * x[self.indices[k]]
        return y

    def to_dense(self) -> np.ndarray:
        A = np.zeros(self.shape, dtype=np.float64)
        for i in range(self.nrows):
            for k in range(self.indptr[i], self.indptr[i + 1]):
                A[i, self.indices[k]] = self.data[k]
        return A


@dataclass(frozen=True)
class CSCMatrix:
    """Compressed Sparse Column matrix (immutable view)."""
    data: np.ndarray     # nonzero values
    indices: np.ndarray  # row indices
    indptr: np.ndarray   # column pointer
    shape: tuple[int, int]

    @property
    def nnz(self) -> int:
        return int(self.data.shape[0])

    @property
    def nrows(self) -> int:
        return self.shape[0]

    @property
    def ncols(self) -> int:
        return self.shape[1]

    def matvec(self, x: np.ndarray) -> np.ndarray:
        """y = A^T @ x via CSC (effectively A^T matvec)."""
        y = np.zeros(self.ncols, dtype=np.float64)
        for j in range(self.ncols):
            for k in range(self.indptr[j], self.indptr[j + 1]):
                y[j] += self.data[k] * x[self.indices[k]]
        return y

    def to_dense(self) -> np.ndarray:
        A = np.zeros(self.shape, dtype=np.float64)
        for j in range(self.ncols):
            for k in range(self.indptr[j], self.indptr[j + 1]):
                A[self.indices[k], j] = self.data[k]
        return A


def build_csr(rows: list[int], cols: list[int], vals: list[float],
              nrows: int, ncols: int) -> CSRMatrix:
    """Build a CSRMatrix from COO triplets."""
    data = np.array(vals, dtype=np.float64)
    row_arr = np.array(rows, dtype=np.int32)
    col_arr = np.array(cols, dtype=np.int32)

    nnz = len(data)
    # Sort by row then col
    order = np.lexsort((col_arr, row_arr))
    data = data[order]
    col_arr = col_arr[order]
    row_arr = row_arr[order]

    indptr = np.zeros(nrows + 1, dtype=np.int32)
    for r in row_arr:
        indptr[r + 1] += 1
    np.cumsum(indptr, out=indptr)

    return CSRMatrix(data=data, indices=col_arr, indptr=indptr,
                     shape=(nrows, ncols))


def build_csc(rows: list[int], cols: list[int], vals: list[float],
              nrows: int, ncols: int) -> CSCMatrix:
    """Build a CSCMatrix from COO triplets."""
    data = np.array(vals, dtype=np.float64)
    row_arr = np.array(rows, dtype=np.int32)
    col_arr = np.array(cols, dtype=np.int32)

    order = np.lexsort((row_arr, col_arr))
    data = data[order]
    row_arr = row_arr[order]
    col_arr = col_arr[order]

    indptr = np.zeros(ncols + 1, dtype=np.int32)
    for c in col_arr:
        indptr[c + 1] += 1
    np.cumsum(indptr, out=indptr)

    return CSCMatrix(data=data, indices=row_arr, indptr=indptr,
                     shape=(nrows, ncols))


@dataclass(frozen=True)
class Model:
    """Immutable optimisation model.  Never mutated after construction."""
    # Dimensions
    nrows: int          # m — number of constraint rows
    ncols: int          # n — number of variables

    # Objective  (always stored as minimisation internally)
    c: np.ndarray       # shape (n,)
    obj_const: float    # objective row RHS constant (sign-flipped from MPS)
    sense: str          # 'min' or 'max' (original sense; c is already flipped if max)

    # Constraint matrix
    A_csr: CSRMatrix
    A_csc: CSCMatrix

    # Bounds
    row_lo: np.ndarray  # shape (m,)  -INF = unconstrained below
    row_hi: np.ndarray  # shape (m,)  +INF = unconstrained above
    col_lo: np.ndarray  # shape (n,)
    col_hi: np.ndarray  # shape (n,)

    # Integrality: 0=continuous, 1=general integer, 2=binary
    integrality: np.ndarray  # shape (n,) int8

    # Optional quadratic term  Q_upper[(i,j)] = q_ij  (i <= j)
    Q_upper: Optional[dict] = field(default=None, compare=False)

    # Names
    row_names: tuple = field(default_factory=tuple)
    col_names: tuple = field(default_factory=tuple)
    obj_name: str = "obj"

    # Provenance
    sha256: str = ""
    source_path: Optional[str] = None

    # ------------------------------------------------------------------ #
    @property
    def nnz(self) -> int:
        return self.A_csr.nnz

    @property
    def n_integers(self) -> int:
        return int(np.count_nonzero(self.integrality))

    @property
    def is_lp(self) -> bool:
        return self.n_integers == 0 and self.Q_upper is None

    @property
    def is_milp(self) -> bool:
        return self.n_integers > 0 and self.Q_upper is None

    @property
    def is_qp(self) -> bool:
        return self.n_integers == 0 and self.Q_upper is not None

    @property
    def is_miqp(self) -> bool:
        return self.n_integers > 0 and self.Q_upper is not None

    @property
    def problem_class(self) -> str:
        if self.is_miqp:
            return "MIQP"
        if self.is_milp:
            return "MILP"
        if self.is_qp:
            return "QP"
        return "LP"

    def summary(self) -> str:
        return (
            f"{self.problem_class}  rows={self.nrows}  cols={self.ncols}  "
            f"nnz={self.nnz}  integers={self.n_integers}  "
            f"sense={self.sense}  sha256={self.sha256[:8]}..."
        )


def sha256_of(text: str | bytes) -> str:
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()
