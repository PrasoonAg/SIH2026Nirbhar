/**
 * NIRBHAR Showcase — Standalone 1-norm condition number estimator.
 *
 * Uses Hager's power iteration method (LAPACK DLACON variant):
 * estimates ||A^{-1}||_1 via alternating forward/backward solves,
 * then cond₁(A) ≈ ||A||_1 * ||A^{-1}||_1.
 *
 * Reference: Hager (1984) "Condition estimates", SIAM J. Sci. Stat. Comput.
 */

import { luSolve, luSolveTranspose } from './lu.js';
import type { LUFactor } from './lu.js';

export interface CondEstResult {
  /** Estimated 1-norm condition number */
  cond1: number;
  /** Estimated ||A||_1 */
  normA1: number;
  /** Estimated ||A^{-1}||_1 */
  normAinv1: number;
}

/**
 * Estimate the 1-norm condition number of the factored matrix.
 *
 * @param lu      Pre-computed LU factors
 * @param A       Original dense column-major matrix (for ||A||_1 computation)
 * @param maxIter Power iterations (default 5 — sufficient for Hager's method)
 */
export function condest(
  lu: LUFactor,
  A: Float64Array,
  maxIter = 5,
): CondEstResult {
  const m = lu.m;
  if (m === 0) return { cond1: 1, normA1: 0, normAinv1: 0 };

  // ── Step 1: ||A||_1 = max column sum ─────────────────────────────────────
  let normA1 = 0;
  for (let j = 0; j < m; j++) {
    let colSum = 0;
    for (let i = 0; i < m; i++) colSum += Math.abs(A[i + j * m]);
    if (colSum > normA1) normA1 = colSum;
  }

  // ── Step 2: Hager's estimate of ||A^{-1}||_1 ─────────────────────────────
  // Initialise x = 1/m
  let x = new Float64Array(m).fill(1.0 / m);

  let normAinv1 = 0;
  let prevNorm = 0;

  for (let iter = 0; iter < maxIter; iter++) {
    // y = A^{-1} x
    const y = luSolve(lu, x as Float64Array);

    // Compute 1-norm of y
    let ny = 0;
    for (let i = 0; i < m; i++) ny += Math.abs(y[i]);
    normAinv1 = ny;

    if (normAinv1 <= prevNorm + 1e-10) break; // converged
    prevNorm = normAinv1;

    // z = sign(y)
    const z = new Float64Array(m);
    for (let i = 0; i < m; i++) z[i] = y[i] >= 0 ? 1 : -1;

    // w = A^{-T} z
    const w = luSolveTranspose(lu, z);

    // Find coordinate of maximum |w|
    let maxW = 0;
    let maxIdx = 0;
    for (let i = 0; i < m; i++) {
      const aw = Math.abs(w[i]);
      if (aw > maxW) { maxW = aw; maxIdx = i; }
    }

    // Next x = e_{maxIdx}
    x = new Float64Array(m);
    x[maxIdx] = 1;
  }

  const cond1 = normA1 * normAinv1;
  return { cond1, normA1, normAinv1 };
}

/**
 * Quick condition estimate using only the LU factors (without A).
 * Approximates ||A||_1 from U diagonal and column structure.
 * Less accurate but doesn't require storing A.
 */
export function condestFast(lu: LUFactor): number {
  const { LU, m } = lu;

  // ||A^{-1}||_1 approximation via 3-step power iteration
  let x = new Float64Array(m).fill(1.0 / m);
  for (let iter = 0; iter < 3; iter++) {
    const y = luSolve(lu, x as Float64Array);
    let ny = 0;
    for (let i = 0; i < m; i++) ny += Math.abs(y[i]);
    if (ny === 0) break;
    const inv = 1 / ny;
    for (let i = 0; i < m; i++) x[i] = y[i] * inv;
  }
  const normAinv1 = x.reduce((s, v) => s + Math.abs(v), 0);

  // ||A||_1 approximation from LU column sums
  let normA1 = 0;
  for (let j = 0; j < m; j++) {
    let col = 0;
    for (let i = 0; i < m; i++) col += Math.abs(LU[i + j * m]);
    if (col > normA1) normA1 = col;
  }

  return normA1 * normAinv1;
}
