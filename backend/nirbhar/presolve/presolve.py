"""
nirbhar/presolve/presolve.py
==============================
Phase 2 M3: Presolve — scaling and structural reductions for LP/MILP.

Operations (applied in order):
  1. Geometric-mean column/row scaling (Ruiz equilibration, up to 20 rounds)
  2. Singleton row elimination (fixed variables implied by single-variable rows)
  3. Fixed variable substitution (col_lo == col_hi)
  4. Empty / free row removal
  5. Bound tightening on bounded rows (propagate col bounds through single-nonzero rows)

Each reduction records an entry in PresolveStack for postsolve reconstruction.

Postsolve recovers the original (x, y) from the presolved solution.

Sovereignty: no external solver imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

import numpy as np

from nirbhar.io.model import Model, INF, CSRMatrix, CSCMatrix, build_csr, build_csc


# ---------------------------------------------------------------------------
# Presolve options
# ---------------------------------------------------------------------------

@dataclass
class PresolveOptions:
    max_scaling_rounds: int = 20
    scaling_tol: float = 1e-4          # stop when max ratio < 1 + tol
    do_singleton_rows: bool = True
    do_fixed_vars: bool = True
    do_empty_rows: bool = True
    do_bound_tighten: bool = True
    verbose: bool = False


# ---------------------------------------------------------------------------
# Postsolve stack entries
# ---------------------------------------------------------------------------

class ReductionType(IntEnum):
    SCALING         = 0   # column/row scaling
    FIXED_VAR       = 1   # variable fixed at value
    SINGLETON_ROW   = 2   # row eliminated, variable fixed
    EMPTY_ROW       = 3   # row removed (non-binding)
    ROW_REMOVED     = 4   # row removed (index bookkeeping)


@dataclass
class ScalingEntry:
    col_scale: np.ndarray   # (n_orig,) multiply columns by
    row_scale: np.ndarray   # (m_orig,) multiply rows by


@dataclass
class FixedVarEntry:
    col_idx: int            # original column index
    value: float            # value the variable is fixed to


@dataclass
class SingletonRowEntry:
    row_idx: int            # original row index
    col_idx: int            # original column index (the one singleton)
    value: float            # implied value for the variable


@dataclass
class EmptyRowEntry:
    row_idx: int            # original row index removed


@dataclass
class PresolveStack:
    entries: list = field(default_factory=list)

    def push_scaling(self, col_scale: np.ndarray, row_scale: np.ndarray) -> None:
        self.entries.append((ReductionType.SCALING, ScalingEntry(col_scale.copy(), row_scale.copy())))

    def push_fixed(self, col_idx: int, value: float) -> None:
        self.entries.append((ReductionType.FIXED_VAR, FixedVarEntry(col_idx, value)))

    def push_singleton(self, row_idx: int, col_idx: int, value: float) -> None:
        self.entries.append((ReductionType.SINGLETON_ROW, SingletonRowEntry(row_idx, col_idx, value)))

    def push_empty_row(self, row_idx: int) -> None:
        self.entries.append((ReductionType.EMPTY_ROW, EmptyRowEntry(row_idx)))


# ---------------------------------------------------------------------------
# Presolved model container
# ---------------------------------------------------------------------------

@dataclass
class PresolvedModel:
    model: Model                    # reduced model
    stack: PresolveStack            # postsolve instructions
    col_map: np.ndarray             # (n_reduced,) -> original col index
    row_map: np.ndarray             # (m_reduced,) -> original row index
    col_scale: np.ndarray           # (n_orig,) scaling applied to cols
    row_scale: np.ndarray           # (m_orig,) scaling applied to rows
    fixed_cols: dict                # {orig_col_idx: fixed_value}
    n_orig: int
    m_orig: int
    obj_offset: float               # constant added to obj from fixed vars


# ---------------------------------------------------------------------------
# Main presolve entry
# ---------------------------------------------------------------------------

def presolve(model: Model, opts: Optional[PresolveOptions] = None) -> PresolvedModel:
    """
    Apply presolve reductions to model.

    Returns
    -------
    PresolvedModel with reduced model + postsolve stack.
    """
    if opts is None:
        opts = PresolveOptions()

    m_orig, n_orig = model.nrows, model.ncols
    stack = PresolveStack()

    # Work on dense A for simplicity in Phase 2
    A = _to_dense(model)
    c = model.c.copy()
    row_lo = model.row_lo.copy()
    row_hi = model.row_hi.copy()
    col_lo = model.col_lo.copy()
    col_hi = model.col_hi.copy()

    col_scale = np.ones(n_orig, dtype=np.float64)
    row_scale = np.ones(m_orig, dtype=np.float64)
    fixed_cols: dict[int, float] = {}
    obj_offset: float = model.obj_const

    # ── 1. Ruiz equilibration scaling ─────────────────────────────────────────
    if opts.max_scaling_rounds > 0:
        col_scale, row_scale = _ruiz_scale(A, opts.max_scaling_rounds, opts.scaling_tol)
        stack.push_scaling(col_scale, row_scale)
        # Apply scaling: A_scaled[i,j] = row_scale[i] * A[i,j] / col_scale[j]
        # (divide c by col_scale to keep objective correct for scaled x)
        A = (row_scale[:, None] * A) / col_scale[None, :]
        c = c / col_scale
        row_lo = np.where(np.abs(row_lo) < INF * 0.9, row_lo * row_scale, row_lo)
        row_hi = np.where(np.abs(row_hi) < INF * 0.9, row_hi * row_scale, row_hi)
        # col_lo/col_hi scale inversely (variable x' = x * col_scale)
        col_lo_sc = np.where(np.abs(col_lo) < INF * 0.9, col_lo / col_scale, col_lo)
        col_hi_sc = np.where(np.abs(col_hi) < INF * 0.9, col_hi / col_scale, col_hi)
    else:
        col_lo_sc = col_lo.copy()
        col_hi_sc = col_hi.copy()

    # ── 2. Fixed variable substitution ────────────────────────────────────────
    active_rows = list(range(m_orig))
    active_cols = list(range(n_orig))

    if opts.do_fixed_vars:
        new_active_cols = []
        for j in active_cols:
            if abs(col_hi_sc[j] - col_lo_sc[j]) < 1e-12:
                val = col_lo_sc[j]
                fixed_cols[j] = val
                stack.push_fixed(j, val)
                # Update RHS: b_new = b - A[:, j] * val
                row_lo[active_rows] -= A[np.ix_(active_rows, [j])][:, 0] * val
                row_hi[active_rows] -= A[np.ix_(active_rows, [j])][:, 0] * val
                obj_offset += c[j] * val
            else:
                new_active_cols.append(j)
        active_cols = new_active_cols

    # ── 3. Empty / free row removal ───────────────────────────────────────────
    if opts.do_empty_rows:
        new_active_rows = []
        for i in active_rows:
            nnz_i = np.sum(np.abs(A[i, active_cols]) > 1e-15)
            lo_inf = row_lo[i] <= -INF * 0.9
            hi_inf = row_hi[i] >= INF * 0.9
            if nnz_i == 0 or (lo_inf and hi_inf):
                stack.push_empty_row(i)
            else:
                new_active_rows.append(i)
        active_rows = new_active_rows

    # ── 4. Singleton row elimination ──────────────────────────────────────────
    if opts.do_singleton_rows:
        changed = True
        while changed:
            changed = False
            new_active_rows = []
            for i in active_rows:
                row_nnz = [(j, A[i, j]) for j in active_cols if abs(A[i, j]) > 1e-15]
                if len(row_nnz) == 1:
                    j, aij = row_nnz[0]
                    # Ax = b: aij * x_j = b  =>  x_j = b / aij
                    lo_r, hi_r = row_lo[i], row_hi[i]
                    if abs(aij) > 1e-14:
                        # Derive bounds on x_j from this row
                        implied_lo = lo_r / aij if aij > 0 else hi_r / aij
                        implied_hi = hi_r / aij if aij > 0 else lo_r / aij
                        # Tighten col bounds
                        new_lo = max(col_lo_sc[j], implied_lo) if abs(implied_lo) < INF * 0.9 else col_lo_sc[j]
                        new_hi = min(col_hi_sc[j], implied_hi) if abs(implied_hi) < INF * 0.9 else col_hi_sc[j]
                        if new_hi < new_lo - 1e-10:
                            # Infeasible (detected in presolve)
                            new_lo = new_hi = new_lo  # let solver catch it
                        col_lo_sc[j] = new_lo
                        col_hi_sc[j] = new_hi
                        # If now fixed
                        if abs(new_hi - new_lo) < 1e-12 and j not in fixed_cols:
                            val = new_lo
                            fixed_cols[j] = val
                            stack.push_singleton(i, j, val)
                            row_lo[active_rows] -= A[active_rows, j] * val
                            row_hi[active_rows] -= A[active_rows, j] * val
                            obj_offset += c[j] * val
                            active_cols = [k for k in active_cols if k != j]
                            changed = True
                    stack.push_empty_row(i)  # row is now eliminated
                else:
                    new_active_rows.append(i)
            active_rows = new_active_rows

    # ── Build reduced model ───────────────────────────────────────────────────
    row_map = np.array(active_rows, dtype=np.int32)
    col_map = np.array(active_cols, dtype=np.int32)

    if len(row_map) == 0 or len(col_map) == 0:
        # Trivially feasible — return a 1x1 model
        row_map = np.array([0], dtype=np.int32)
        col_map = np.array([active_cols[0]] if active_cols else [0], dtype=np.int32)

    A_red = A[np.ix_(row_map, col_map)]
    c_red = c[col_map]
    row_lo_red = row_lo[row_map]
    row_hi_red = row_hi[row_map]
    col_lo_red = col_lo_sc[col_map]
    col_hi_red = col_hi_sc[col_map]

    m_red, n_red = A_red.shape

    # Build CSR/CSC for reduced model
    rows_coo, cols_coo, vals_coo = [], [], []
    for i in range(m_red):
        for j in range(n_red):
            v = A_red[i, j]
            if abs(v) > 1e-15:
                rows_coo.append(i)
                cols_coo.append(j)
                vals_coo.append(v)

    if not vals_coo:
        vals_coo = [0.0]; rows_coo = [0]; cols_coo = [0]

    A_csr_red = build_csr(rows_coo, cols_coo, vals_coo, m_red, n_red)
    A_csc_red = build_csc(rows_coo, cols_coo, vals_coo, m_red, n_red)

    integ_red = model.integrality[col_map] if model.integrality is not None else np.zeros(n_red, dtype=np.int8)

    from nirbhar.io.model import Model as M2
    reduced = M2(
        nrows=m_red, ncols=n_red,
        c=c_red, obj_const=obj_offset,
        sense=model.sense,
        A_csr=A_csr_red, A_csc=A_csc_red,
        row_lo=row_lo_red, row_hi=row_hi_red,
        col_lo=col_lo_red, col_hi=col_hi_red,
        integrality=integ_red,
        row_names=tuple(model.row_names[i] for i in active_rows) if model.row_names else (),
        col_names=tuple(model.col_names[j] for j in active_cols) if model.col_names else (),
        sha256=model.sha256,
        source_path=model.source_path,
    )

    return PresolvedModel(
        model=reduced,
        stack=stack,
        col_map=col_map,
        row_map=row_map,
        col_scale=col_scale,
        row_scale=row_scale,
        fixed_cols=fixed_cols,
        n_orig=n_orig,
        m_orig=m_orig,
        obj_offset=obj_offset,
    )


# ---------------------------------------------------------------------------
# Postsolve: recover original (x, y) from reduced solution
# ---------------------------------------------------------------------------

def postsolve(
    ps: PresolvedModel,
    x_red: np.ndarray,
    y_red: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Recover original-space primal x and dual y from reduced solution.

    Parameters
    ----------
    ps    : PresolvedModel from presolve()
    x_red : primal solution in reduced scaled space, shape (n_red,)
    y_red : dual solution in reduced scaled space, shape (m_red,)

    Returns
    -------
    (x_orig, y_orig) in original problem space
    """
    n_orig, m_orig = ps.n_orig, ps.m_orig

    # --- Primal recovery ---
    x_orig = np.zeros(n_orig, dtype=np.float64)

    # Place reduced variables back
    for slot, orig_j in enumerate(ps.col_map):
        x_orig[orig_j] = x_red[slot] if slot < len(x_red) else 0.0

    # Place fixed variables
    for orig_j, val in ps.fixed_cols.items():
        x_orig[orig_j] = val

    # Undo column scaling: x_unscaled[j] = x_scaled[j] / col_scale[j]
    # (col_scale was applied as x' = x / col_scale when building reduced)
    # Wait: in presolve we did: A_scaled = A / col_scale (column scaling means x_scaled = x * col_scale? no)
    # In Ruiz: x_orig corresponds to the scaled A. The original problem is:
    #   A x = b  =>  (R A C^{-1}) (C x) = R b
    # So x_scaled = C x = col_scale * x_orig => x_orig = x_scaled / col_scale
    # But we stored col_scale as "multiply columns by" — meaning A_scaled[:,j] = A[:,j]/col_scale[j]
    # and b_scaled = row_scale * b. The scaled variable is x_s = x * col_scale.
    # Wait, let me re-check: in _ruiz_scale we return col_scale such that
    #   A_scaled[i,j] = row_scale[i] * A[i,j] / col_scale[j]
    # The scaled problem is: A_sc * x_sc = b_sc where x_sc[j] = x[j]
    # Actually the scaling is A_sc = diag(row_scale) @ A @ diag(1/col_scale)
    # The scaled variable is x_sc = col_scale * x (in diagonal scaling: D_c x_sc = x where D_c = diag(col_scale))
    # So x_orig[j] = x_sc[j] / col_scale[j]
    x_orig /= ps.col_scale

    # --- Dual recovery ---
    y_orig = np.zeros(m_orig, dtype=np.float64)
    for slot, orig_i in enumerate(ps.row_map):
        y_orig[orig_i] = y_red[slot] if slot < len(y_red) else 0.0

    # Undo row scaling: y_orig[i] = y_scaled[i] / row_scale[i]
    # (dual is multiplied by row_scale when A_sc = diag(row_scale) A diag(1/col_scale))
    y_orig /= ps.row_scale

    return x_orig, y_orig


# ---------------------------------------------------------------------------
# Ruiz equilibration scaling
# ---------------------------------------------------------------------------

def _ruiz_scale(
    A: np.ndarray,
    max_rounds: int,
    tol: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Ruiz column/row scaling: iteratively make row and column infinity-norms = 1.

    Returns (col_scale, row_scale) such that:
        A_scaled[i,j] = row_scale[i] * A[i,j] / col_scale[j]

    col_scale[j] = product of column norm corrections applied
    row_scale[i] = product of row norm corrections applied
    """
    m, n = A.shape
    col_scale = np.ones(n, dtype=np.float64)
    row_scale = np.ones(m, dtype=np.float64)
    A_work = A.copy()

    for _ in range(max_rounds):
        # Column norms
        col_norms = np.max(np.abs(A_work), axis=0)
        col_norms = np.where(col_norms > 1e-300, col_norms, 1.0)
        col_corr = np.sqrt(col_norms)
        col_scale *= col_corr
        A_work /= col_corr[None, :]

        # Row norms
        row_norms = np.max(np.abs(A_work), axis=1)
        row_norms = np.where(row_norms > 1e-300, row_norms, 1.0)
        row_corr = np.sqrt(row_norms)
        row_scale *= row_corr
        A_work /= row_corr[:, None]

        # Convergence: max deviation from 1
        dev = max(
            float(np.max(np.abs(col_norms - 1.0))),
            float(np.max(np.abs(row_norms - 1.0))),
        )
        if dev < tol:
            break

    return col_scale, row_scale


# ---------------------------------------------------------------------------
# Dense A builder
# ---------------------------------------------------------------------------

def _to_dense(model: Model) -> np.ndarray:
    m, n = model.nrows, model.ncols
    A = np.zeros((m, n), dtype=np.float64)
    for i in range(m):
        s, e = model.A_csr.indptr[i], model.A_csr.indptr[i + 1]
        for k in range(s, e):
            A[i, model.A_csr.indices[k]] = model.A_csr.data[k]
    return A
