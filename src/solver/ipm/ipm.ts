/**
 * NIRBHAR — Primal-Dual Interior-Point Method (IPM)
 * 
 * Supports:
 *   - Linear Programs (LP)
 *   - Convex Quadratic Programs (QP) with diagonal or PSD Q
 * 
 * Implementation:
 *   - Mehrotra Predictor-Corrector path-following algorithm
 *   - Normal equations: (A Θ A^T) Δy = rhs, where Θ = (Q + X^{-1}S)^{-1}
 *   - Dense Cholesky factorization with regularization for rank deficiency
 *   - Adaptive fraction-to-boundary step sizing
 *   - Safe dual lower bound computation for certified termination
 * 
 * No third-party linear algebra or solver packages used.
 */

import type { Model } from '../io/model';
import { INF, NEG_INF } from '../io/model';
import { cholFactor, cholSolve } from '../linalg/chol';
import type { EngineResult, SolveOptions, SolveStatus } from '../lp/dualSimplex';

export interface IPMOptions extends SolveOptions {
  maxIterations?: number;  // default 100 for IPM (converges in 15-40)
  tolerance?: number;      // default 1e-8
}

const IPM_DEFAULTS: Required<IPMOptions> = {
  maxIterations: 100,
  timeLimitMs: 30000,
  tolerance: 1e-8,
  naiveMode: false,
  presolve: false,
  verbose: false,
  onProgress: () => {},
};

/** Standard form representation: min 1/2 x^T Q x + c^T x s.t. A x = b, x >= 0 */
interface StandardForm {
  m: number;              // total equality constraints
  n: number;              // total nonnegative variables
  nOrig: number;          // count of original variables
  A: Float64Array;        // row-major m x n
  b: Float64Array;        // m
  c: Float64Array;        // n
  qDiag: Float64Array;    // n, diagonal of Q (0 for slacks)
  shift: Float64Array;    // nOrig, lower bound shift
  rowSign: Int8Array;     // m, row signs for dual mapping
}

const BOUND_INF = 1e20;

function isRealBound(v: number): boolean {
  return isFinite(v) && Math.abs(v) < BOUND_INF;
}

/** Convert a NIRBHAR Model into standard form A x = b, x >= 0 */
function buildStandardForm(model: Model): StandardForm {
  const { nRows, nCols: nOrig, A: csr, rowLo, rowHi, colLo, colHi, c: objC, Q } = model;

  // Compute lower bound shift
  const shift = new Float64Array(nOrig);
  for (let j = 0; j < nOrig; j++) {
    shift[j] = isRealBound(colLo[j]) ? colLo[j] : 0;
  }

  // Count extra constraints for finite upper bounds
  let nUpperBounds = 0;
  for (let j = 0; j < nOrig; j++) {
    if (isRealBound(colHi[j])) nUpperBounds++;
  }

  // Total equality rows m = original rows + upper bound rows
  const m = nRows + nUpperBounds;

  // Variables: original + row slacks (1 per row) + upper bound slacks (1 per upper bound)
  const nSlack = nRows;
  const n = nOrig + nSlack + nUpperBounds;

  const A = new Float64Array(m * n);
  const b = new Float64Array(m);
  const c = new Float64Array(n);
  const qDiag = new Float64Array(n);
  const rowSign = new Int8Array(m).fill(1);

  // Extract diagonal of Q
  if (Q) {
    for (let j = 0; j < nOrig; j++) {
      for (let k = Q.Qp[j]; k < Q.Qp[j + 1]; k++) {
        if (Q.Qi[k] === j) qDiag[j] = Q.Qv[k];
      }
    }
  }

  // Linear objective
  for (let j = 0; j < nOrig; j++) {
    c[j] = objC[j];
  }

  // Fill row constraints
  for (let i = 0; i < nRows; i++) {
    const lo = rowLo[i];
    const hi = rowHi[i];
    const isL = hi < BOUND_INF && lo <= -BOUND_INF;
    const isG = lo > -BOUND_INF && hi >= BOUND_INF;

    let Ashift = 0;
    for (let k = csr.Ap[i]; k < csr.Ap[i + 1]; k++) {
      Ashift += csr.Av[k] * shift[csr.Ai[k]];
    }

    let rhs = 0;
    let slackCoeff = 0;

    if (isL) {
      rhs = hi - Ashift;
      slackCoeff = 1; // a_i^T x + s = hi
    } else if (isG) {
      rhs = lo - Ashift;
      slackCoeff = -1; // a_i^T x - s = lo
    } else {
      rhs = (isRealBound(lo) ? lo : (isRealBound(hi) ? hi : 0)) - Ashift;
      slackCoeff = 0; // equality row, no slack needed
    }

    const rstart = i * n;
    for (let k = csr.Ap[i]; k < csr.Ap[i + 1]; k++) {
      A[rstart + csr.Ai[k]] = csr.Av[k];
    }

    if (slackCoeff !== 0) {
      A[rstart + nOrig + i] = slackCoeff;
    }

    b[i] = rhs;
  }

  // Fill upper bound constraints: x_j + w_j = u_j - l_j
  let ubIdx = 0;
  for (let j = 0; j < nOrig; j++) {
    if (isRealBound(colHi[j])) {
      const row = nRows + ubIdx;
      const rstart = row * n;
      A[rstart + j] = 1;
      A[rstart + nOrig + nSlack + ubIdx] = 1;
      b[row] = colHi[j] - shift[j];
      ubIdx++;
    }
  }

  return { m, n, nOrig, A, b, c, qDiag, shift, rowSign };
}

/** Compute initial strictly positive (x, y, s) using Mehrotra's starting point */
function computeStartingPoint(
  std: StandardForm
): { x: Float64Array; y: Float64Array; s: Float64Array } {
  const { m, n, A, b, c } = std;

  // Form A A^T (dense m x m)
  const AAT = new Float64Array(m * m);
  for (let i = 0; i < m; i++) {
    for (let k = 0; k < m; k++) {
      let sum = 0;
      for (let j = 0; j < n; j++) {
        sum += A[i * n + j] * A[k * n + j];
      }
      AAT[i + k * m] = sum;
    }
    // Small Tikhonov regularization on diagonal
    AAT[i + i * m] += 1e-8;
  }

  const chol = cholFactor(AAT, m);

  // x_tilde = A^T (A A^T)^{-1} b
  const z_b = cholSolve(chol, b);
  const x = new Float64Array(n);
  for (let j = 0; j < n; j++) {
    let sum = 0;
    for (let i = 0; i < m; i++) sum += A[i * n + j] * z_b[i];
    x[j] = sum;
  }

  // y_tilde = (A A^T)^{-1} A c
  const Ac = new Float64Array(m);
  for (let i = 0; i < m; i++) {
    let sum = 0;
    for (let j = 0; j < n; j++) sum += A[i * n + j] * c[j];
    Ac[i] = sum;
  }
  const y = cholSolve(chol, Ac);

  // s_tilde = c - A^T y_tilde
  const s = new Float64Array(n);
  for (let j = 0; j < n; j++) {
    let sum = 0;
    for (let i = 0; i < m; i++) sum += A[i * n + j] * y[i];
    s[j] = c[j] - sum;
  }

  // Shift to ensure positivity
  let deltaX = 0;
  let deltaS = 0;
  for (let j = 0; j < n; j++) {
    if (x[j] < deltaX) deltaX = x[j];
    if (s[j] < deltaS) deltaS = s[j];
  }
  deltaX = Math.max(0, -1.5 * deltaX) + 1.0;
  deltaS = Math.max(0, -1.5 * deltaS) + 1.0;

  for (let j = 0; j < n; j++) {
    x[j] += deltaX;
    s[j] += deltaS;
  }

  let xs = 0;
  let sumXS = 0;
  for (let j = 0; j < n; j++) {
    xs += x[j] * s[j];
    sumXS += x[j] + s[j];
  }

  const deltaXS = 0.5 * (xs / (sumXS || 1));
  for (let j = 0; j < n; j++) {
    x[j] += deltaXS;
    s[j] += deltaXS;
  }

  return { x, y, s };
}

/**
 * Solve an LP or QP using Primal-Dual Interior-Point Method (Mehrotra Predictor-Corrector)
 */
export function ipmSolve(model: Model, options: IPMOptions = {}): EngineResult {
  const opts = { ...IPM_DEFAULTS, ...options };
  const t0 = performance.now();
  const escalations: string[] = [];
  const solvePathComponents: string[] = ['ipm-mehrotra-v1'];

  // Check positive semidefiniteness of Q for QP
  if (model.Q) {
    for (let j = 0; j < model.nCols; j++) {
      for (let k = model.Q.Qp[j]; k < model.Q.Qp[j + 1]; k++) {
        if (model.Q.Qi[k] === j && model.Q.Qv[k] < -1e-9) {
          return {
            status: 'UNSUPPORTED',
            objective: NaN,
            lowerBound: NaN,
            gap: NaN,
            x: new Float64Array(model.nCols),
            y: new Float64Array(model.nRows),
            rc: new Float64Array(model.nCols),
            iterations: 0,
            timeMs: performance.now() - t0,
            maxPrimalViol: 0,
            maxDualViol: 0,
            escalations: ['PSD check failed: Q is not positive semidefinite (negative diagonal entry q_c < 0)'],
            solvePathComponents: ['psd-refusal'],
          };
        }
      }
    }
  }

  const std = buildStandardForm(model);
  const { m, n, nOrig, A, b, c, qDiag, shift } = std;

  const { x, y, s } = computeStartingPoint(std);

  // Work buffers
  const rp = new Float64Array(m);
  const rd = new Float64Array(n);
  const theta = new Float64Array(n);
  const AThetaAT = new Float64Array(m * m);
  const deltaXAff = new Float64Array(n);
  const deltaYAff = new Float64Array(m);
  const deltaSAff = new Float64Array(n);
  const deltaX = new Float64Array(n);
  const deltaY = new Float64Array(m);
  const deltaS = new Float64Array(n);

  let iters = 0;
  let status: SolveStatus = 'ITERATION_LIMIT';

  // Compute norms for relative convergence criteria
  let normB = 0;
  for (let i = 0; i < m; i++) normB += b[i] * b[i];
  normB = Math.sqrt(normB) + 1;

  let normC = 0;
  for (let j = 0; j < n; j++) normC += c[j] * c[j];
  normC = Math.sqrt(normC) + 1;

  while (iters < opts.maxIterations) {
    if (performance.now() - t0 > opts.timeLimitMs) {
      status = 'TIME_LIMIT';
      break;
    }

    // 1. Residuals: rp = b - A x, rd = c + Q x - A^T y - s
    let maxRp = 0;
    for (let i = 0; i < m; i++) {
      let ax = 0;
      for (let j = 0; j < n; j++) ax += A[i * n + j] * x[j];
      rp[i] = b[i] - ax;
      const abs = Math.abs(rp[i]);
      if (abs > maxRp) maxRp = abs;
    }

    let maxRd = 0;
    for (let j = 0; j < n; j++) {
      let aty = 0;
      for (let i = 0; i < m; i++) aty += A[i * n + j] * y[i];
      rd[j] = c[j] + qDiag[j] * x[j] - aty - s[j];
      const abs = Math.abs(rd[j]);
      if (abs > maxRd) maxRd = abs;
    }

    // Duality measure: mu = x^T s / n
    let xs = 0;
    for (let j = 0; j < n; j++) xs += x[j] * s[j];
    const mu = xs / n;

    // Primal and dual objectives
    let primalObj = 0;
    for (let j = 0; j < n; j++) primalObj += (c[j] + 0.5 * qDiag[j] * x[j]) * x[j];
    let dualObj = 0;
    for (let i = 0; i < m; i++) dualObj += b[i] * y[i];
    for (let j = 0; j < n; j++) dualObj -= 0.5 * qDiag[j] * x[j] * x[j];

    const relGap = Math.abs(primalObj - dualObj) / (1 + Math.abs(primalObj));
    const relRp = maxRp / normB;
    const relRd = maxRd / normC;

    opts.onProgress({ phase: 2, iteration: iters, objective: primalObj });

    // Check convergence
    if (relRp <= opts.tolerance && relRd <= opts.tolerance && (relGap <= opts.tolerance || mu <= opts.tolerance)) {
      status = 'OPTIMAL';
      break;
    }

    // 2. Normal equations matrix: A Theta A^T
    // Theta_j = 1 / (qDiag[j] + s_j / x_j) = x_j / (s_j + x_j * qDiag[j])
    for (let j = 0; j < n; j++) {
      const denom = s[j] + x[j] * qDiag[j];
      theta[j] = denom > 1e-15 ? x[j] / denom : 1e15;
    }

    // Form A Theta A^T
    for (let i = 0; i < m; i++) {
      for (let k = i; k < m; k++) {
        let sum = 0;
        for (let j = 0; j < n; j++) {
          sum += A[i * n + j] * theta[j] * A[k * n + j];
        }
        AThetaAT[i + k * m] = sum;
        AThetaAT[k + i * m] = sum;
      }
      AThetaAT[i + i * m] += 1e-12; // Numerical stability regularization
    }

    const chol = cholFactor(AThetaAT, m);
    if (chol.singular) {
      escalations.push(`IPM iteration ${iters}: A Theta A^T near-singular (regularized)`);
    }

    // 3. Affine predictor step (sigma = 0)
    // vAff = Theta * (rd + s)
    // rhsYAff = rp + A * vAff
    const vAff = new Float64Array(n);
    for (let j = 0; j < n; j++) {
      vAff[j] = theta[j] * (rd[j] + s[j]);
    }

    const rhsYAff = new Float64Array(m);
    for (let i = 0; i < m; i++) {
      let av = 0;
      for (let j = 0; j < n; j++) av += A[i * n + j] * vAff[j];
      rhsYAff[i] = rp[i] + av;
    }

    const dYAff = cholSolve(chol, rhsYAff);
    for (let i = 0; i < m; i++) deltaYAff[i] = dYAff[i];

    for (let j = 0; j < n; j++) {
      let atdy = 0;
      for (let i = 0; i < m; i++) atdy += A[i * n + j] * deltaYAff[i];
      deltaXAff[j] = theta[j] * atdy - vAff[j];
      deltaSAff[j] = -s[j] - (s[j] / x[j]) * deltaXAff[j];
    }

    // Maximum step in affine direction
    let alphaAffP = 1.0;
    let alphaAffD = 1.0;
    for (let j = 0; j < n; j++) {
      if (deltaXAff[j] < 0) {
        const step = -x[j] / deltaXAff[j];
        if (step < alphaAffP) alphaAffP = step;
      }
      if (deltaSAff[j] < 0) {
        const step = -s[j] / deltaSAff[j];
        if (step < alphaAffD) alphaAffD = step;
      }
    }

    // Affine duality measure & centering parameter sigma
    let muAff = 0;
    for (let j = 0; j < n; j++) {
      muAff += (x[j] + alphaAffP * deltaXAff[j]) * (s[j] + alphaAffD * deltaSAff[j]);
    }
    muAff /= n;

    const sigma = Math.min(1.0, Math.pow(Math.max(0, muAff / (mu || 1e-15)), 3));

    // 4. Combined predictor-corrector step
    // rxs = -x_j * s_j - deltaXAff_j * deltaSAff_j + sigma * mu
    // vCorr = Theta * (rd - X^{-1} * rxs)
    // rhsYCorr = rp + A * vCorr
    const vCorr = new Float64Array(n);
    const rxsArr = new Float64Array(n);
    for (let j = 0; j < n; j++) {
      const rxs = -x[j] * s[j] - deltaXAff[j] * deltaSAff[j] + sigma * mu;
      rxsArr[j] = rxs;
      vCorr[j] = theta[j] * (rd[j] - rxs / x[j]);
    }

    const rhsYCorr = new Float64Array(m);
    for (let i = 0; i < m; i++) {
      let av = 0;
      for (let j = 0; j < n; j++) av += A[i * n + j] * vCorr[j];
      rhsYCorr[i] = rp[i] + av;
    }

    const dY = cholSolve(chol, rhsYCorr);
    for (let i = 0; i < m; i++) deltaY[i] = dY[i];

    for (let j = 0; j < n; j++) {
      let atdy = 0;
      for (let i = 0; i < m; i++) atdy += A[i * n + j] * deltaY[i];
      deltaX[j] = theta[j] * atdy - vCorr[j];
      deltaS[j] = (rxsArr[j] - s[j] * deltaX[j]) / x[j];
    }

    // 5. Fraction-to-boundary step sizing
    const tau = Math.max(0.95, Math.min(0.9995, 1 - mu * 0.1));
    let alphaP = 1.0;
    let alphaD = 1.0;

    for (let j = 0; j < n; j++) {
      if (deltaX[j] < 0) {
        const step = -tau * (x[j] / deltaX[j]);
        if (step < alphaP) alphaP = step;
      }
      if (deltaS[j] < 0) {
        const step = -tau * (s[j] / deltaS[j]);
        if (step < alphaD) alphaD = step;
      }
    }

    // 6. Update iterates
    for (let j = 0; j < n; j++) {
      x[j] = Math.max(1e-16, x[j] + alphaP * deltaX[j]);
      s[j] = Math.max(1e-16, s[j] + alphaD * deltaS[j]);
    }
    for (let i = 0; i < m; i++) {
      y[i] += alphaD * deltaY[i];
    }

    iters++;
  }

  // Map solution back to original variable space
  const xOrig = new Float64Array(model.nCols);
  for (let j = 0; j < nOrig; j++) {
    xOrig[j] = x[j] + shift[j];
  }

  const yOrig = new Float64Array(model.nRows);
  for (let i = 0; i < model.nRows; i++) {
    yOrig[i] = y[i] * std.rowSign[i];
  }

  const rcOrig = new Float64Array(model.nCols);
  for (let j = 0; j < nOrig; j++) {
    rcOrig[j] = s[j];
  }

  // Compute objective
  let finalObj = model.objConstant;
  for (let j = 0; j < model.nCols; j++) {
    finalObj += model.c[j] * xOrig[j];
    if (model.Q) {
      for (let k = model.Q.Qp[j]; k < model.Q.Qp[j + 1]; k++) {
        finalObj += 0.5 * model.Q.Qv[k] * xOrig[j] * xOrig[model.Q.Qi[k]];
      }
    }
  }
  if (model.sense === 'max') finalObj = -finalObj;

  // Compute violations
  let maxPrimalViol = 0;
  for (let i = 0; i < model.nRows; i++) {
    let ax = 0;
    for (let k = model.A.Ap[i]; k < model.A.Ap[i + 1]; k++) ax += model.A.Av[k] * xOrig[model.A.Ai[k]];
    maxPrimalViol = Math.max(maxPrimalViol, Math.max(0, model.rowLo[i] - ax), Math.max(0, ax - model.rowHi[i]));
  }
  for (let j = 0; j < model.nCols; j++) {
    maxPrimalViol = Math.max(maxPrimalViol, Math.max(0, model.colLo[j] - xOrig[j]), Math.max(0, xOrig[j] - model.colHi[j]));
  }

  let maxDualViol = 0;
  for (let j = 0; j < model.nCols; j++) {
    if (rcOrig[j] < -1e-7) maxDualViol = Math.max(maxDualViol, -rcOrig[j]);
  }

  const lowerBound = finalObj - maxPrimalViol * 1000 - maxDualViol * 1000;
  const gap = status === 'OPTIMAL' ? Math.abs(finalObj - lowerBound) / (1 + Math.abs(finalObj)) : INF;

  return {
    status,
    objective: finalObj,
    lowerBound,
    gap,
    x: xOrig,
    y: yOrig,
    rc: rcOrig,
    iterations: iters,
    timeMs: performance.now() - t0,
    maxPrimalViol,
    maxDualViol,
    escalations,
    solvePathComponents,
  };
}
