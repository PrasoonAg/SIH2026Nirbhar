/**
 * NIRBHAR Showcase — CSR/CSC sparse matrix operations.
 * Provides sparse-dense products, transposition, extraction, and
 * submatrix selection needed by the LP and IPM engines.
 */

import type { CSR, CSC } from '../io/model.js';

// ─── Type re-exports so callers don't need to touch io/model ───────────────
export type { CSR, CSC };

// ─── Basic sparse-dense products ───────────────────────────────────────────

/** y = A * x  (CSR form, x dense length A.n, y dense length A.m) */
export function csrMulVec(A: CSR, x: Float64Array, y?: Float64Array): Float64Array {
  const out = y ?? new Float64Array(A.m);
  for (let i = 0; i < A.m; i++) {
    let s = 0;
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) s += A.Av[k] * x[A.Ai[k]];
    out[i] = s;
  }
  return out;
}

/** y = Aᵀ * x  (CSR form; x dense length A.m, y dense length A.n) */
export function csrMulVecT(A: CSR, x: Float64Array, y?: Float64Array): Float64Array {
  const out = y ?? new Float64Array(A.n);
  out.fill(0);
  for (let i = 0; i < A.m; i++) {
    const xi = x[i];
    if (xi === 0) continue;
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) out[A.Ai[k]] += A.Av[k] * xi;
  }
  return out;
}

/** y = A * x  (CSC form; x dense length A.n, y dense length A.m) */
export function cscMulVec(A: CSC, x: Float64Array, y?: Float64Array): Float64Array {
  const out = y ?? new Float64Array(A.m);
  out.fill(0);
  for (let j = 0; j < A.n; j++) {
    const xj = x[j];
    if (xj === 0) continue;
    for (let k = A.Cp[j]; k < A.Cp[j + 1]; k++) out[A.Ci[k]] += A.Cv[k] * xj;
  }
  return out;
}

/** y = Aᵀ * x  (CSC form; x dense length A.m, y dense length A.n) */
export function cscMulVecT(A: CSC, x: Float64Array, y?: Float64Array): Float64Array {
  const out = y ?? new Float64Array(A.n);
  for (let j = 0; j < A.n; j++) {
    let s = 0;
    for (let k = A.Cp[j]; k < A.Cp[j + 1]; k++) s += A.Cv[k] * x[A.Ci[k]];
    out[j] = s;
  }
  return out;
}

// ─── Transpose ─────────────────────────────────────────────────────────────

/** Build CSC from CSR (= CSR of Aᵀ) */
export function csrToCSC(A: CSR): CSC {
  const { m, n, Ap, Ai, Av } = A;
  const nnz = Ap[m];
  const colCounts = new Int32Array(n);
  for (let k = 0; k < nnz; k++) colCounts[Ai[k]]++;
  const Cp = new Int32Array(n + 1);
  for (let j = 0; j < n; j++) Cp[j + 1] = Cp[j] + colCounts[j];
  const Ci = new Int32Array(nnz);
  const Cv = new Float64Array(nnz);
  const pos = Cp.slice(0, n);
  for (let i = 0; i < m; i++) {
    for (let k = Ap[i]; k < Ap[i + 1]; k++) {
      const j = Ai[k];
      const p = pos[j]++;
      Ci[p] = i;
      Cv[p] = Av[k];
    }
  }
  return { m: n, n: m, Cp, Ci, Cv };
}

/** Build CSR from CSC (= CSC of Aᵀ) */
export function cscToCSR(A: CSC): CSR {
  const { m, n, Cp, Ci, Cv } = A;
  const nnz = Cp[n];
  const rowCounts = new Int32Array(m);
  for (let k = 0; k < nnz; k++) rowCounts[Ci[k]]++;
  const Ap = new Int32Array(m + 1);
  for (let i = 0; i < m; i++) Ap[i + 1] = Ap[i] + rowCounts[i];
  const Ai = new Int32Array(nnz);
  const Av = new Float64Array(nnz);
  const pos = Ap.slice(0, m);
  for (let j = 0; j < n; j++) {
    for (let k = Cp[j]; k < Cp[j + 1]; k++) {
      const i = Ci[k];
      const p = pos[i]++;
      Ai[p] = j;
      Av[p] = Cv[k];
    }
  }
  return { m: n, n: m, Ap, Ai, Av };
}

// ─── Submatrix / row extraction ─────────────────────────────────────────────

/**
 * Extract rows listed in `rowSet` (sorted ascending) from a CSR matrix.
 * Returns a new CSR with `rowSet.length` rows.
 */
export function csrSelectRows(A: CSR, rowSet: ArrayLike<number>): CSR {
  const nRows = rowSet.length;
  const aiArr: number[] = [];
  const avArr: number[] = [];
  const Ap = new Int32Array(nRows + 1);
  for (let ii = 0; ii < nRows; ii++) {
    const i = rowSet[ii];
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) {
      aiArr.push(A.Ai[k]);
      avArr.push(A.Av[k]);
    }
    Ap[ii + 1] = aiArr.length;
  }
  return { m: nRows, n: A.n, Ap, Ai: new Int32Array(aiArr), Av: new Float64Array(avArr) };
}

/**
 * Extract columns listed in `colSet` from a CSR matrix.
 * Returns a new CSR with same number of rows but only `colSet.length` columns.
 * colSet must be sorted ascending; a reverse map is built internally.
 */
export function csrSelectCols(A: CSR, colSet: ArrayLike<number>): CSR {
  const nCols = colSet.length;
  // Build reverse map: original col → new col index (-1 = not selected)
  const colMap = new Int32Array(A.n).fill(-1);
  for (let jj = 0; jj < nCols; jj++) colMap[colSet[jj]] = jj;

  const aiArr: number[] = [];
  const avArr: number[] = [];
  const Ap = new Int32Array(A.m + 1);
  for (let i = 0; i < A.m; i++) {
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) {
      const jnew = colMap[A.Ai[k]];
      if (jnew >= 0) { aiArr.push(jnew); avArr.push(A.Av[k]); }
    }
    Ap[i + 1] = aiArr.length;
  }
  return { m: A.m, n: nCols, Ap, Ai: new Int32Array(aiArr), Av: new Float64Array(avArr) };
}

// ─── Dense basis matrix extraction ─────────────────────────────────────────

/**
 * Extract a dense m×m column-major basis matrix B from CSR matrix A_csr
 * using `basisCols[j]` as the j-th column of B.
 * A_csr has m rows, nCols columns.
 */
export function extractDenseBasis(
  A: CSR,
  m: number,
  basisCols: ArrayLike<number>,
): Float64Array {
  const B = new Float64Array(m * m);
  // Iterate over every row, pick basis column entries
  for (let i = 0; i < m; i++) {
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) {
      const j = A.Ai[k];
      // Linear search through basisCols (small m in prototype)
      for (let jj = 0; jj < m; jj++) {
        if (basisCols[jj] === j) {
          B[i + jj * m] += A.Av[k];
          break;
        }
      }
    }
  }
  return B;
}

/**
 * More efficient basis extraction using a pre-built colToBasisIdx map.
 * colToBasisIdx[j] = jj (basis column index) or -1.
 */
export function extractDenseBasisFast(
  A: CSR,
  m: number,
  colToBasisIdx: Int32Array,
): Float64Array {
  const B = new Float64Array(m * m);
  for (let i = 0; i < m; i++) {
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) {
      const jj = colToBasisIdx[A.Ai[k]];
      if (jj >= 0) B[i + jj * m] += A.Av[k];
    }
  }
  return B;
}

// ─── 1-norm & inf-norm ──────────────────────────────────────────────────────

/** 1-norm of a dense vector */
export function norm1(v: Float64Array): number {
  let s = 0;
  for (let i = 0; i < v.length; i++) s += Math.abs(v[i]);
  return s;
}

/** inf-norm of a dense vector */
export function normInf(v: Float64Array): number {
  let s = 0;
  for (let i = 0; i < v.length; i++) { const a = Math.abs(v[i]); if (a > s) s = a; }
  return s;
}

/** 2-norm of a dense vector */
export function norm2(v: Float64Array): number {
  let s = 0;
  for (let i = 0; i < v.length; i++) s += v[i] * v[i];
  return Math.sqrt(s);
}

// ─── Dot product ────────────────────────────────────────────────────────────

export function dot(a: Float64Array, b: Float64Array): number {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}

// ─── Dense diagonal matrix D operations ────────────────────────────────────

/**
 * Scale columns of A (CSR) by diagonal d: returns new CSR A * diag(d).
 * (Used for row/column scaling in presolve and IPM.)
 */
export function csrScaleCols(A: CSR, d: Float64Array): CSR {
  const nnz = A.Ap[A.m];
  const Av2 = new Float64Array(nnz);
  for (let i = 0; i < A.m; i++) {
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) {
      Av2[k] = A.Av[k] * d[A.Ai[k]];
    }
  }
  return { m: A.m, n: A.n, Ap: A.Ap, Ai: A.Ai, Av: Av2 };
}

/**
 * Scale rows of A (CSR) by diagonal d: returns new CSR diag(d) * A.
 */
export function csrScaleRows(A: CSR, d: Float64Array): CSR {
  const nnz = A.Ap[A.m];
  const Av2 = new Float64Array(nnz);
  for (let i = 0; i < A.m; i++) {
    const di = d[i];
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) Av2[k] = A.Av[k] * di;
  }
  return { m: A.m, n: A.n, Ap: A.Ap, Ai: A.Ai, Av: Av2 };
}

// ─── Residual helpers ───────────────────────────────────────────────────────

/**
 * Compute residual r = b - A*x (CSR).
 * Both b and r are length A.m.
 */
export function csrResidual(A: CSR, x: Float64Array, b: Float64Array): Float64Array {
  const r = new Float64Array(b);
  for (let i = 0; i < A.m; i++) {
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) r[i] -= A.Av[k] * x[A.Ai[k]];
  }
  return r;
}

// ─── Sparse identity ────────────────────────────────────────────────────────

/** Build the m×m identity matrix as CSR. */
export function csrIdentity(m: number): CSR {
  const Ap = new Int32Array(m + 1);
  const Ai = new Int32Array(m);
  const Av = new Float64Array(m);
  for (let i = 0; i < m; i++) { Ap[i] = i; Ai[i] = i; Av[i] = 1; }
  Ap[m] = m;
  return { m, n: m, Ap, Ai, Av };
}
