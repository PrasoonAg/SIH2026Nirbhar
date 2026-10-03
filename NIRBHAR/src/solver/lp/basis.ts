/**
 * NIRBHAR Showcase — LP Basis management
 *
 * Maintains the basis B (set of basic variable indices), the LU factorization
 * of the basis matrix, and provides refactorization and eta-file-style updates.
 *
 * In this prototype, we use DENSE LU (suitable for bases ≤ ~500 rows).
 * The basis matrix B is m×m; columns come from [A | I_slack].
 */

import type { Model } from '../io/model.js';
import { luFactor, luSolve, luSolveTranspose } from '../linalg/lu.js';
import type { LUFactor } from '../linalg/lu.js';
import { condestFast } from '../linalg/condest.js';

// ─── Status of a variable ───────────────────────────────────────────────────

export const AT_LOWER   = 0;  // nonbasic at lower bound
export const AT_UPPER   = 1;  // nonbasic at upper bound
export const BASIC      = 2;  // basic variable
export const FIXED      = 3;  // fixed (lo == hi), treated as nonbasic at lower
export const SUPERBASIC = 4;  // superbasic (primal simplex escalation)
export const FREE_BASIC = 5;  // free basic variable

export type VarStatus = 0 | 1 | 2 | 3 | 4 | 5;

// ─── Extended problem: original vars + row slacks ───────────────────────────
//
// Column j in the extended problem:
//   j < nCols   → original structural variable
//   j >= nCols  → slack for row (j - nCols)
//
// For row i:
//   L ≤ a_i^T x ≤ H
//   Introduce slack s_i: a_i^T x - s_i = 0, L ≤ s_i ≤ H (sign convention)
//   (so s_i absorbs the row type)

export interface BasisState {
  /** m: number of constraint rows */
  m: number;
  /** n: number of structural columns */
  n: number;
  /** nExt = n + m: extended column count */
  nExt: number;

  /** Which extended variable occupies basis position i (length m) */
  basisVar: Int32Array;

  /** Status of every extended variable (length nExt) */
  status: Uint8Array;

  /** Primal values of all extended variables (length nExt) */
  x: Float64Array;

  /** Dual multipliers (row prices) π, length m */
  pi: Float64Array;

  /** Reduced costs for all extended variables, length nExt */
  rc: Float64Array;

  /** LU factorization of current basis matrix */
  lu: LUFactor;

  /** Dense column-major basis matrix (m×m) — kept for refactorization */
  B: Float64Array;

  /** 1-norm condition estimate of current basis */
  condEst: number;

  /** Number of simplex pivots since last full refactorization */
  pivotsSinceRefact: number;

  /** Refactorization threshold */
  refactThreshold: number;
}

// ─── Build the extended A matrix (with identity slack columns) ───────────────

/**
 * For a model with m rows and n cols, build the dense m × (n+m)
 * extended matrix [A | I_slack].  Row-major output.
 */
export function buildExtendedRowMajor(model: Model): Float64Array {
  const { nRows: m, nCols: n, A } = model;
  const nExt = n + m;
  const ext = new Float64Array(m * nExt);
  // Fill A part
  for (let i = 0; i < m; i++) {
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) {
      ext[i * nExt + A.Ai[k]] = A.Av[k];
    }
  }
  // Fill identity slack part
  for (let i = 0; i < m; i++) ext[i * nExt + n + i] = 1.0;
  return ext;
}

// ─── Extract dense basis matrix ─────────────────────────────────────────────

export function extractBasisDense(
  extRowMajor: Float64Array,
  m: number,
  nExt: number,
  basisVar: Int32Array,
): Float64Array {
  const B = new Float64Array(m * m); // column-major
  for (let j = 0; j < m; j++) {
    const col = basisVar[j];
    for (let i = 0; i < m; i++) {
      B[i + j * m] = extRowMajor[i * nExt + col];
    }
  }
  return B;
}

// ─── Initialise basis: all slacks basic ─────────────────────────────────────

/**
 * Crash-start basis: put all slack variables (n..n+m-1) into the basis.
 * This is always feasible for the augmented system.
 */
export function crashSlackBasis(model: Model): BasisState {
  const m = model.nRows;
  const n = model.nCols;
  const nExt = n + m;

  const basisVar = new Int32Array(m);
  const status = new Uint8Array(nExt);

  // Non-basic structural vars: set at lower bound
  for (let j = 0; j < n; j++) {
    basisVar; // placeholder
    status[j] = AT_LOWER;
  }

  // Basic slacks
  for (let i = 0; i < m; i++) {
    basisVar[i] = n + i;
    status[n + i] = BASIC;
  }

  // Primal values: slacks = row lo (which may be -INF; will be handled by phase-I)
  const x = new Float64Array(nExt);
  for (let j = 0; j < n; j++) x[j] = model.colLo[j]; // at lower bound
  // Slack s_i = a_i^T x - lo_i = 0 - lo_i initially? 
  // Actually for a_i^T x = s_i, if x_struct = lower bounds, s_i = Σ A[i,j]*x[j]
  // We set them consistently below after computing Ax
  const { A, rowLo } = model;
  for (let i = 0; i < m; i++) {
    let ax = 0;
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) ax += A.Av[k] * x[A.Ai[k]];
    // Slack s_i = Ax_i (so that a_i^T x - s_i = 0)
    x[n + i] = ax;
  }

  // Basis matrix = identity (slack columns)
  const B = new Float64Array(m * m);
  for (let i = 0; i < m; i++) B[i + i * m] = 1.0;

  const luCopy = new Float64Array(B);
  const lu = luFactor(luCopy, m);

  const pi = new Float64Array(m);
  const rc = new Float64Array(nExt);
  // rc for structural vars = c_j - π^T a_j (π=0 initially, so rc=c)
  for (let j = 0; j < n; j++) rc[j] = model.c[j];

  return {
    m, n, nExt,
    basisVar,
    status,
    x, pi, rc,
    lu,
    B,
    condEst: 1,
    pivotsSinceRefact: 0,
    refactThreshold: 50,
  };
}

// ─── Refactorize basis ───────────────────────────────────────────────────────

export function refactorizeBasis(
  bs: BasisState,
  extRowMajor: Float64Array,
): void {
  const { m, nExt, basisVar } = bs;
  const B = extractBasisDense(extRowMajor, m, nExt, basisVar);
  bs.B = B;
  const luCopy = new Float64Array(B);
  bs.lu = luFactor(luCopy, m);
  bs.condEst = condestFast(bs.lu);
  bs.pivotsSinceRefact = 0;
}

// ─── Solve with basis matrix ─────────────────────────────────────────────────

/** Solve B d = rhs (basis solve, forward) */
export function basisSolve(bs: BasisState, rhs: Float64Array): Float64Array {
  return luSolve(bs.lu, rhs);
}

/** Solve B^T π = rhs (basis transpose solve, for dual update) */
export function basisSolveT(bs: BasisState, rhs: Float64Array): Float64Array {
  return luSolveTranspose(bs.lu, rhs);
}

// ─── Dual prices update ──────────────────────────────────────────────────────

/**
 * Compute dual prices (row multipliers) π = B^{-T} c_B
 * and reduced costs rc_j = c_j - π^T a_j for all extended variables.
 */
export function updateDuals(
  bs: BasisState,
  model: Model,
  extRowMajor: Float64Array,
): void {
  const { m, n, nExt, basisVar, lu } = bs;
  // c_B vector
  const cB = new Float64Array(m);
  for (let i = 0; i < m; i++) {
    const j = basisVar[i];
    cB[i] = j < n ? model.c[j] : 0; // slacks have zero cost
  }

  // π = B^{-T} c_B
  bs.pi = luSolveTranspose(lu, cB);

  // rc_j = c_j - π^T A_j for all j
  const { pi } = bs;
  for (let j = 0; j < n; j++) {
    let piA = 0;
    // Use extended row-major to compute π^T a_j
    for (let i = 0; i < m; i++) {
      piA += pi[i] * extRowMajor[i * nExt + j];
    }
    bs.rc[j] = model.c[j] - piA;
  }
  // Slacks: rc_{n+i} = 0 - π^T e_i = -π[i]
  for (let i = 0; i < m; i++) bs.rc[n + i] = -pi[i];
}

// ─── Primal update after pivot ───────────────────────────────────────────────

/**
 * Perform a simplex pivot: entering variable `enter` (extended col)
 * replaces basic variable at position `pivotRow`.
 *
 * Updates: basisVar, status, x (primal values), pivotsSinceRefact.
 */
export function doPivot(
  bs: BasisState,
  enter: number,
  leave: number, // basic position (row index), not the column
  stepSize: number,
  enterDir: number, // +1 or -1 (entering at lower or upper)
  alphaCol: Float64Array, // B^{-1} a_enter
  extRowMajor: Float64Array,
): void {
  const { m, n, nExt, basisVar, status, x } = bs;

  // Determine leaving variable column
  const leaveCol = basisVar[leave];

  // Update primal values: x_B ← x_B - stepSize * alpha_col
  for (let i = 0; i < m; i++) {
    x[basisVar[i]] -= stepSize * enterDir * alphaCol[i];
  }

  // Entering variable enters at its new value
  const enterBound = enterDir > 0 ? 0 : 1; // which bound it was at
  x[enter] += stepSize * enterDir;

  // Update status
  status[leaveCol] = enterBound === 0 ? AT_UPPER : AT_LOWER;
  status[enter] = BASIC;

  // Update basis
  basisVar[leave] = enter;

  bs.pivotsSinceRefact++;
}
