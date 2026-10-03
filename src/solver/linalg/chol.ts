/**
 * NIRBHAR Showcase — Dense Cholesky factorization (LL^T)
 * for IPM normal equations A D A^T z = r.
 *
 * The system matrix is symmetric positive definite (SPD).
 * Storage: column-major dense m×m.
 * Only the lower triangle is used.
 */

export interface CholFactor {
  /** Lower triangle stored column-major (m×m). Upper part is garbage. */
  L: Float64Array;
  m: number;
  singular: boolean;
}

const EPS_CHOL = 1e-14;

/**
 * Cholesky factorization in-place: A → L  (L L^T = A).
 * A must be symmetric; only the lower triangle of A is read.
 * Returns {L, m, singular}.
 */
export function cholFactor(A: Float64Array, m: number): CholFactor {
  const L = new Float64Array(A); // copy; we modify L in place
  let singular = false;

  for (let j = 0; j < m; j++) {
    // Diagonal element
    let diag = L[j + j * m];
    for (let k = 0; k < j; k++) {
      const ljk = L[j + k * m];
      diag -= ljk * ljk;
    }
    if (diag < EPS_CHOL) {
      // Not positive definite — clamp to tiny positive (regularization)
      diag = EPS_CHOL;
      singular = true;
    }
    const sqrtDiag = Math.sqrt(diag);
    L[j + j * m] = sqrtDiag;
    const invSqrt = 1.0 / sqrtDiag;

    // Sub-diagonal entries in column j
    for (let i = j + 1; i < m; i++) {
      let val = L[i + j * m];
      for (let k = 0; k < j; k++) {
        val -= L[i + k * m] * L[j + k * m];
      }
      L[i + j * m] = val * invSqrt;
    }
  }

  return { L, m, singular };
}

/**
 * Solve L L^T x = b using pre-computed Cholesky factor.
 * Returns a new Float64Array.
 */
export function cholSolve(chol: CholFactor, b: Float64Array): Float64Array {
  const { L, m } = chol;
  const x = new Float64Array(b);

  // Forward substitution: L y = b
  for (let j = 0; j < m; j++) {
    for (let k = 0; k < j; k++) x[j] -= L[j + k * m] * x[k];
    const diag = L[j + j * m];
    x[j] = Math.abs(diag) < EPS_CHOL ? 0 : x[j] / diag;
  }

  // Back substitution: L^T x = y
  for (let j = m - 1; j >= 0; j--) {
    for (let k = j + 1; k < m; k++) x[j] -= L[k + j * m] * x[k];
    const diag = L[j + j * m];
    x[j] = Math.abs(diag) < EPS_CHOL ? 0 : x[j] / diag;
  }

  return x;
}

/**
 * Build A = B D B^T + ρ I (IPM normal equations) as a dense column-major matrix.
 * B is m×n (dense, column-major), D is a diagonal (length n), ρ ≥ 0 regulariser.
 */
export function buildNormalEq(
  B: Float64Array,
  m: number,
  n: number,
  D: Float64Array,
  rho = 0,
): Float64Array {
  const A = new Float64Array(m * m);
  // A = B * diag(D) * B^T
  // A[i,j] = Σ_k B[i,k]*D[k]*B[j,k]
  for (let k = 0; k < n; k++) {
    const dk = D[k];
    if (dk === 0) continue;
    for (let i = 0; i < m; i++) {
      const bik = B[i + k * m];
      if (bik === 0) continue;
      for (let j = i; j < m; j++) { // lower triangle only
        A[j + i * m] += bik * dk * B[j + k * m]; // column-major: A[row=j, col=i]
      }
    }
  }
  // Symmetrize + add ρI
  for (let i = 0; i < m; i++) {
    A[i + i * m] += rho;
    for (let j = i + 1; j < m; j++) {
      A[i + j * m] = A[j + i * m]; // mirror to upper for completeness
    }
  }
  return A;
}
