/**
 * Dense LU factorization with partial pivoting (Gaussian elimination).
 * Suitable for bases up to ~500×500 in prototype (dense LU; sparse in production).
 *
 * A = P * L * U   where P is a row permutation
 * Stored in-place: diagonal = U diagonal; below diagonal = L (without 1s on diagonal)
 *
 * The matrix is stored column-major (Fortran order) for cache efficiency during BLAS-like ops.
 */

export interface LUFactor {
  /** Dense m×m LU (column-major). Lower triangle is L (unit diagonal), upper is U. */
  LU: Float64Array;
  /** Row pivot permutation: row piv[i] of original A is now row i */
  piv: Int32Array;
  /** Matrix dimension */
  m: number;
  /** Log of |det| — useful for conditioning */
  logAbsDet: number;
  /** Singular (rank-deficient) flag */
  singular: boolean;
}

const EPS_SINGULAR = 1e-14;

/**
 * Factor A (column-major, m×m) into LU in-place.
 * A is MODIFIED — on return it holds the LU factors.
 */
export function luFactor(A: Float64Array, m: number): LUFactor {
  const piv = new Int32Array(m);
  for (let i = 0; i < m; i++) piv[i] = i;

  let logAbsDet = 0;
  let singular = false;

  for (let k = 0; k < m; k++) {
    // Find pivot row (max absolute value in column k, rows k..m-1)
    let maxVal = Math.abs(A[k + k * m]);
    let maxRow = k;
    for (let i = k + 1; i < m; i++) {
      const v = Math.abs(A[i + k * m]);
      if (v > maxVal) { maxVal = v; maxRow = i; }
    }

    // Swap rows k and maxRow in A and piv
    if (maxRow !== k) {
      piv[k] = maxRow;
      // Swap entire rows (all columns)
      for (let j = 0; j < m; j++) {
        const tmp = A[k + j * m];
        A[k + j * m] = A[maxRow + j * m];
        A[maxRow + j * m] = tmp;
      }
    } else {
      piv[k] = k;
    }

    const diag = A[k + k * m];
    if (Math.abs(diag) < EPS_SINGULAR) {
      singular = true;
      logAbsDet = -Infinity;
      // Do NOT abort — keep factoring (will produce zeros in L)
      continue;
    }

    logAbsDet += Math.log(Math.abs(diag));
    const invDiag = 1.0 / diag;

    // Compute L entries for column k (rows below k)
    for (let i = k + 1; i < m; i++) {
      A[i + k * m] *= invDiag;
    }

    // Update trailing submatrix (Schur complement)
    for (let j = k + 1; j < m; j++) {
      const akj = A[k + j * m];
      if (akj === 0) continue;
      for (let i = k + 1; i < m; i++) {
        A[i + j * m] -= A[i + k * m] * akj;
      }
    }
  }

  return { LU: A, piv, m, logAbsDet, singular };
}

/**
 * Solve A x = b using pre-computed LU factors.
 * Returns a NEW Float64Array x.
 */
export function luSolve(lu: LUFactor, b: Float64Array): Float64Array {
  const { LU, piv, m } = lu;
  const x = new Float64Array(b);

  // Apply row permutations (forward)
  for (let k = 0; k < m; k++) {
    if (piv[k] !== k) {
      const tmp = x[k]; x[k] = x[piv[k]]; x[piv[k]] = tmp;
    }
  }

  // Forward substitution: L y = x (L has 1s on diagonal)
  for (let k = 0; k < m; k++) {
    for (let i = k + 1; i < m; i++) {
      x[i] -= LU[i + k * m] * x[k];
    }
  }

  // Back substitution: U x = y
  for (let k = m - 1; k >= 0; k--) {
    const diag = LU[k + k * m];
    if (Math.abs(diag) < EPS_SINGULAR) { x[k] = 0; continue; }
    x[k] /= diag;
    for (let i = 0; i < k; i++) {
      x[i] -= LU[i + k * m] * x[k];
    }
  }

  return x;
}

/**
 * Solve A^T x = b using pre-computed LU factors.
 * Returns a NEW Float64Array x.
 */
export function luSolveTranspose(lu: LUFactor, b: Float64Array): Float64Array {
  const { LU, piv, m } = lu;
  const x = new Float64Array(b);

  // Forward substitution with U^T: U^T y = b
  for (let k = 0; k < m; k++) {
    const diag = LU[k + k * m];
    if (Math.abs(diag) < EPS_SINGULAR) { x[k] = 0; continue; }
    x[k] /= diag;
    for (let i = k + 1; i < m; i++) {
      x[i] -= LU[k + i * m] * x[k];
    }
  }

  // Back substitution with L^T: L^T x = y
  for (let k = m - 1; k >= 0; k--) {
    for (let j = k + 1; j < m; j++) {
      x[k] -= LU[j + k * m] * x[j];
    }
  }

  // Apply inverse row permutation (reverse)
  for (let k = m - 1; k >= 0; k--) {
    if (piv[k] !== k) {
      const tmp = x[k]; x[k] = x[piv[k]]; x[piv[k]] = tmp;
    }
  }

  return x;
}

/**
 * Extract the m×m basis matrix from the extended coefficient matrix.
 * basisCols[i] = column index in the full extended matrix.
 * A_ext: m × nExt coefficient matrix (row-major: row i starts at i*nExt).
 * Returns a NEW Float64Array[m*m] column-major.
 */
export function extractBasisMatrix(
  A_ext: Float64Array,
  m: number,
  nExt: number,
  basisCols: Int32Array
): Float64Array {
  const B = new Float64Array(m * m);
  for (let j = 0; j < m; j++) {
    const col = basisCols[j];
    for (let i = 0; i < m; i++) {
      B[i + j * m] = A_ext[i * nExt + col];
    }
  }
  return B;
}

/**
 * 1-norm condition estimate (Hager's method, simplified 2-iteration version).
 * lu: factored LU; returns estimated condition number.
 */
export function condest(lu: LUFactor): number {
  const m = lu.m;
  if (m === 0) return 1;

  // Estimate ||A^{-1}|| via a few power iterations
  let x = new Float64Array(m).fill(1.0 / m);
  for (let iter = 0; iter < 3; iter++) {
    const y = luSolve(lu, x);
    const norm = y.reduce((s, v) => s + Math.abs(v), 0);
    if (norm === 0) break;
    const inv = 1.0 / norm;
    for (let i = 0; i < m; i++) x[i] = y[i] * inv;
  }
  const normAinv = x.reduce((s, v) => s + Math.abs(v), 0);

  // Estimate ||A|| as max column sum (column-major LU)
  // Rough estimate: use the U diagonal product
  let normA = 0;
  for (let j = 0; j < m; j++) {
    let colSum = 0;
    for (let i = 0; i < m; i++) colSum += Math.abs(lu.LU[i + j * m]);
    normA = Math.max(normA, colSum);
  }

  return normA * normAinv;
}
