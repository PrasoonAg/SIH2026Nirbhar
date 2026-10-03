/**
 * NIRBHAR Showcase — Dense LDL^T factorization for augmented QP systems.
 *
 * Factors symmetric indefinite matrix A = L D L^T
 * where D is diagonal (possibly with negative entries).
 * Bunch-Kaufman 1×1 pivoting (diagonal only, for simplicity in prototype).
 * Column-major dense storage.
 */

export interface LDLFactor {
  /** Lower triangle of L (unit diagonal), packed column-major m×m. */
  L: Float64Array;
  /** Diagonal D, length m. */
  D: Float64Array;
  m: number;
  singular: boolean;
}

const EPS_LDL = 1e-14;

/**
 * LDL^T factorization in-place.
 * A: dense column-major m×m symmetric matrix — only lower triangle read.
 * Returns {L, D, m, singular}.
 */
export function ldlFactor(A: Float64Array, m: number): LDLFactor {
  const L = new Float64Array(A); // copy — we overwrite
  const D = new Float64Array(m);
  let singular = false;

  for (let j = 0; j < m; j++) {
    // D[j] = A[j,j] - Σ_{k<j} L[j,k]^2 * D[k]
    let dj = L[j + j * m];
    for (let k = 0; k < j; k++) {
      const ljk = L[j + k * m];
      dj -= ljk * ljk * D[k];
    }
    D[j] = dj;

    if (Math.abs(dj) < EPS_LDL) {
      singular = true;
      D[j] = (dj >= 0 ? 1 : -1) * EPS_LDL;
    }

    const invDj = 1.0 / D[j];

    // L[i,j] = (A[i,j] - Σ_{k<j} L[i,k]*D[k]*L[j,k]) / D[j]  for i > j
    for (let i = j + 1; i < m; i++) {
      let lij = L[i + j * m];
      for (let k = 0; k < j; k++) {
        lij -= L[i + k * m] * D[k] * L[j + k * m];
      }
      L[i + j * m] = lij * invDj;
    }
    // Unit diagonal
    L[j + j * m] = 1.0;
  }

  return { L, D, m, singular };
}

/**
 * Solve L D L^T x = b using pre-computed LDL factor.
 * Returns new Float64Array.
 */
export function ldlSolve(ldl: LDLFactor, b: Float64Array): Float64Array {
  const { L, D, m } = ldl;
  const x = new Float64Array(b);

  // Forward: L y = b
  for (let j = 0; j < m; j++) {
    for (let k = 0; k < j; k++) x[j] -= L[j + k * m] * x[k];
    // L has unit diagonal, so no division
  }

  // Diagonal: D z = y
  for (let j = 0; j < m; j++) {
    x[j] = Math.abs(D[j]) < EPS_LDL ? 0 : x[j] / D[j];
  }

  // Back: L^T x = z
  for (let j = m - 1; j >= 0; j--) {
    for (let k = j + 1; k < m; k++) x[j] -= L[k + j * m] * x[k];
    // L^T has unit diagonal
  }

  return x;
}

/**
 * Build the augmented QP system matrix:
 * [ Q + ρ_P I    A^T ]
 * [ A           -ρ_D I]
 * Dense column-major (m+n) × (m+n).
 *
 * Q_diag: diagonal of Q (length n), may be zero for LP.
 * A: dense m×n row-major.
 * Returns the augmented system as column-major (m+n)^2 array.
 */
export function buildAugmentedSystem(
  Q_diag: Float64Array,  // length n
  A_dense: Float64Array, // m×n row-major
  m: number,
  n: number,
  rhoP: number,
  rhoD: number,
): Float64Array {
  const sz = m + n;
  const S = new Float64Array(sz * sz);

  // Top-left n×n block: Q + ρ_P I (indices 0..n-1)
  for (let j = 0; j < n; j++) {
    S[j + j * sz] = Q_diag[j] + rhoP;
  }

  // Bottom-right m×m block: -ρ_D I (indices n..n+m-1)
  for (let i = 0; i < m; i++) {
    S[(n + i) + (n + i) * sz] = -rhoD;
  }

  // Off-diagonal blocks: A^T (top-right) and A (bottom-left)
  for (let i = 0; i < m; i++) {
    for (let j = 0; j < n; j++) {
      const aij = A_dense[i * n + j]; // row-major
      S[j + (n + i) * sz] = aij;  // top-right: col n+i, row j
      S[(n + i) + j * sz] = aij;  // bottom-left: col j, row n+i
    }
  }

  return S;
}
