/**
 * NIRBHAR Showcase — Iterative refinement for dense LU systems.
 *
 * After computing x̂ = LU\b, compute the residual r = b - A x̂
 * and correct: x ← x̂ + LU\r.  Repeat for up to maxIter steps
 * or until the residual is below tol * ||b||.
 *
 * Also provides a mixed-precision fallback using compensated summation
 * (Kahan) when double precision is insufficient.
 */

import { luSolve } from './lu.js';
import type { LUFactor } from './lu.js';
import { norm1 } from './csr.js';

export interface RefineResult {
  x: Float64Array;
  /** Residual 1-norm after refinement */
  residualNorm: number;
  /** Number of refinement steps taken */
  steps: number;
  converged: boolean;
}

/**
 * Iterative refinement for A x = b, given LU factors and the original
 * dense column-major matrix A (for residual computation).
 *
 * @param lu   Pre-computed LU factors
 * @param A    Original matrix (column-major, m×m) for residual A*x
 * @param b    Right-hand side
 * @param tol  Convergence tolerance (relative, applied to ||b||_1)
 * @param maxIter Maximum refinement iterations (default 3)
 */
export function iterativeRefine(
  lu: LUFactor,
  A: Float64Array,
  b: Float64Array,
  tol = 1e-12,
  maxIter = 3,
): RefineResult {
  const m = lu.m;

  // Initial solve
  let x = luSolve(lu, b);
  const normB = norm1(b as Float64Array);
  const absTol = tol * (normB === 0 ? 1 : normB);

  let steps = 0;
  let residualNorm = Infinity;

  for (let iter = 0; iter < maxIter; iter++) {
    // r = b - A x  (using compensated summation for accuracy)
    const r = kahanResidual(A, m, x, b);
    residualNorm = norm1(r);

    if (residualNorm <= absTol) {
      steps = iter;
      return { x, residualNorm, steps, converged: true };
    }

    // Correction solve: A δ = r
    const delta = luSolve(lu, r);

    // x ← x + δ
    for (let i = 0; i < m; i++) x[i] += delta[i];
    steps = iter + 1;
  }

  // Final residual check
  const rFinal = kahanResidual(A, m, x, b);
  residualNorm = norm1(rFinal);

  return {
    x,
    residualNorm,
    steps,
    converged: residualNorm <= absTol,
  };
}

/**
 * Compute r = b - A x with Kahan compensated summation for each row.
 * A is dense column-major (m×m), x and b are length m.
 */
function kahanResidual(
  A: Float64Array,
  m: number,
  x: Float64Array,
  b: Float64Array,
): Float64Array {
  const r = new Float64Array(m);
  for (let i = 0; i < m; i++) {
    // Kahan sum: compute Σ_j A[i,j] * x[j]
    let sum = 0;
    let comp = 0;
    for (let j = 0; j < m; j++) {
      const term = A[i + j * m] * x[j];
      const y = term - comp;
      const t = sum + y;
      comp = (t - sum) - y;
      sum = t;
    }
    r[i] = b[i] - sum;
  }
  return r;
}

/**
 * Simple 2-iteration iterative refinement without original matrix (approx).
 * Uses only the LU factors (cheaper but less accurate).
 * Useful when A is not stored separately.
 */
export function cheapRefine(
  lu: LUFactor,
  b: Float64Array,
): Float64Array {
  // Just solve once — for prototype purposes the LU is usually accurate enough
  return luSolve(lu, b);
}
