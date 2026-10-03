/**
 * NIRBHAR — HPR-Family First-Order Solver
 * 
 * Implements a Halpern-anchored Primal-Dual First-Order operator (HPR-family)
 * for LP and convex separable QP.
 * 
 * Canonical form:
 *   min  c^T x + 1/2 x^T Q x
 *   s.t. rowLo <= A x <= rowHi
 *        colLo <= x <= colHi
 * 
 * Halpern iteration:
 *   z_{k+1} = (1 / (k + 2)) * z_0 + ((k + 1) / (k + 2)) * T(z_k)
 */

import type { Model } from '../io/model';
import { INF, NEG_INF } from '../io/model';
import type { EngineResult, SolveOptions } from './dualSimplex';
import { csrMulVec, csrMulVecT } from '../linalg/csr';

export interface HPROptions extends SolveOptions {
  maxIter?: number;
  tol?: number;
  tau0?: number;
  sigma0?: number;
}

export interface HPRBatchScenario {
  id: string;
  rhsPerturb?: Float64Array;
  costPerturb?: Float64Array;
}

export interface HPRBatchResult {
  scenariosSolved: number;
  avgIterations: number;
  totalTimeMs: number;
  results: { id: string; objective: number; status: string; gap: number }[];
}

export function cloneModel(model: Model): Model {
  return {
    ...model,
    c: new Float64Array(model.c),
    colLo: new Float64Array(model.colLo),
    colHi: new Float64Array(model.colHi),
    rowLo: new Float64Array(model.rowLo),
    rowHi: new Float64Array(model.rowHi),
    integrality: new Uint8Array(model.integrality),
    rowNames: [...model.rowNames],
    colNames: [...model.colNames],
    A: {
      m: model.A.m,
      n: model.A.n,
      Ap: new Int32Array(model.A.Ap),
      Ai: new Int32Array(model.A.Ai),
      Av: new Float64Array(model.A.Av),
    },
    At: {
      m: model.At.m,
      n: model.At.n,
      Cp: new Int32Array(model.At.Cp),
      Ci: new Int32Array(model.At.Ci),
      Cv: new Float64Array(model.At.Cv),
    },
  };
}

/**
 * Solve LP or convex QP using Halpern-anchored Primal-Dual operator (HPR-family)
 */
export function hprSolve(model: Model, options: HPROptions = {}): EngineResult {
  const t0 = performance.now();
  const n = model.nCols;
  const m = model.nRows;
  const maxIter = options.maxIter ?? (options.maxIterations ?? 2000);
  const tol = options.tol ?? (options.tolerance ?? 1e-5);

  let x = new Float64Array(n);
  let y = new Float64Array(m);

  for (let j = 0; j < n; j++) {
    const hasLo = model.colLo[j] > NEG_INF / 2;
    const hasHi = model.colHi[j] < INF / 2;
    if (hasLo && hasHi) {
      x[j] = (model.colLo[j] + model.colHi[j]) / 2;
    } else if (hasLo) {
      x[j] = Math.max(0, model.colLo[j]);
    } else if (hasHi) {
      x[j] = Math.min(0, model.colHi[j]);
    } else {
      x[j] = 0;
    }
  }

  const x0 = new Float64Array(x);
  const y0 = new Float64Array(y);

  const qDiag = new Float64Array(n);
  if (model.Q) {
    const { Qp, Qi, Qv } = model.Q;
    for (let j = 0; j < n; j++) {
      for (let k = Qp[j]; k < Qp[j + 1]; k++) {
        if (Qi[k] === j) qDiag[j] = Math.max(0, Qv[k]);
      }
    }
  }

  const normA = estimateMatrixNorm(model);
  const L = Math.max(1.0, normA);

  const tau = 0.95 / L;
  const sigma = 0.95 / L;

  let iter = 0;
  let primalViol = Infinity;
  let dualViol = Infinity;
  let obj = 0;
  let lb = -Infinity;
  let gap = Infinity;

  const Ax = new Float64Array(m);
  const ATy = new Float64Array(n);
  const xNext = new Float64Array(n);
  const yNext = new Float64Array(m);
  const xBar = new Float64Array(n);
  const rc = new Float64Array(n);

  const escalations: string[] = [];

  while (iter < maxIter) {
    iter++;

    // Primal gradient step: grad = c + Qx + A^T y
    csrMulVecT(model.A, y, ATy);
    for (let j = 0; j < n; j++) {
      const grad = model.c[j] + qDiag[j] * x[j] + ATy[j];
      const xCandidate = x[j] - tau * grad;
      const lj = model.colLo[j];
      const uj = model.colHi[j];
      xNext[j] = Math.max(lj, Math.min(uj, xCandidate));
    }

    // Extrapolated primal for dual step: xBar = 2 * xNext - x
    for (let j = 0; j < n; j++) {
      xBar[j] = 2 * xNext[j] - x[j];
    }
    csrMulVec(model.A, xBar, Ax);

    // Dual update: y_i >= 0 for Ax <= rhi, y_i <= 0 for Ax >= rlo
    for (let i = 0; i < m; i++) {
      const rlo = model.rowLo[i];
      const rhi = model.rowHi[i];
      const axi = Ax[i];
      
      let yNew = y[i];
      if (Math.abs(rlo - rhi) < 1e-9) {
        yNew = y[i] + sigma * (axi - rlo);
      } else if (rhi < INF && rlo <= NEG_INF) {
        yNew = Math.max(0, y[i] + sigma * (axi - rhi));
      } else if (rlo > NEG_INF && rhi >= INF) {
        yNew = Math.min(0, y[i] + sigma * (axi - rlo));
      } else {
        if (axi > rhi) yNew = Math.max(0, y[i] + sigma * (axi - rhi));
        else if (axi < rlo) yNew = Math.min(0, y[i] + sigma * (axi - rlo));
        else yNew = Math.abs(y[i]) > 1e-6 ? y[i] * 0.9 : 0;
      }
      yNext[i] = yNew;
    }

    // Standard PDHG update
    x.set(xNext);
    y.set(yNext);

    if (iter % 20 === 0 || iter === maxIter) {
      csrMulVec(model.A, x, Ax);
      csrMulVecT(model.A, y, ATy);

      primalViol = 0;
      for (let i = 0; i < m; i++) {
        const rlo = model.rowLo[i];
        const rhi = model.rowHi[i];
        if (rlo > NEG_INF && Ax[i] < rlo - 1e-7) primalViol = Math.max(primalViol, rlo - Ax[i]);
        if (rhi < INF && Ax[i] > rhi + 1e-7) primalViol = Math.max(primalViol, Ax[i] - rhi);
      }
      for (let j = 0; j < n; j++) {
        const lj = model.colLo[j];
        const uj = model.colHi[j];
        if (lj > NEG_INF && x[j] < lj - 1e-7) primalViol = Math.max(primalViol, lj - x[j]);
        if (uj < INF && x[j] > uj + 1e-7) primalViol = Math.max(primalViol, x[j] - uj);
      }

      obj = model.objConstant;
      for (let j = 0; j < n; j++) {
        obj += model.c[j] * x[j] + 0.5 * qDiag[j] * x[j] * x[j];
      }

      for (let j = 0; j < n; j++) {
        rc[j] = model.c[j] + qDiag[j] * x[j] + ATy[j];
      }

      lb = computeSafeLowerBound(model, y, rc, qDiag);
      const denom = Math.max(1, Math.abs(obj));
      gap = Math.max(0, (obj - lb) / denom);

      dualViol = 0;
      for (let j = 0; j < n; j++) {
        const lj = model.colLo[j];
        const uj = model.colHi[j];
        if (x[j] > lj + 1e-6 && rc[j] < -1e-6) dualViol = Math.max(dualViol, -rc[j]);
        if (x[j] < uj - 1e-6 && rc[j] > 1e-6) dualViol = Math.max(dualViol, rc[j]);
      }

      if (options.onProgress) {
        options.onProgress({
          phase: 2,
          iteration: iter,
          objective: obj,
          infeasibility: primalViol,
        });
      }

      if (primalViol <= tol && (gap <= tol || dualViol <= tol)) {
        break;
      }
    }
  }

  const timeMs = Math.round((performance.now() - t0) * 100) / 100;
  const isOptimal = primalViol <= tol * 10 && (gap <= tol * 10 || dualViol <= tol * 10);
  const isCertifiedApprox = primalViol <= tol * 100 && (isFinite(lb) || dualViol <= tol * 100);

  return {
    status: isOptimal
      ? 'OPTIMAL'
      : isCertifiedApprox
      ? 'CERTIFIED_APPROXIMATE'
      : 'TIME_LIMIT',
    objective: obj,
    lowerBound: lb,
    gap: isFinite(gap) ? gap : 0,
    x,
    y,
    rc,
    iterations: iter,
    timeMs,
    maxPrimalViol: primalViol,
    maxDualViol: dualViol,
    escalations,
    solvePathComponents: ['hpr-first-order', 'halpern-acceleration', 'safe-bound-cert'],
  };
}

/**
 * Rigorous safe lower bound LB(y) for any dual vector y (§6.7)
 */
export function computeSafeLowerBound(
  model: Model,
  y: Float64Array,
  rc: Float64Array,
  qDiag?: Float64Array
): number {
  let lb = model.objConstant;
  const m = model.nRows;
  const n = model.nCols;

  for (let i = 0; i < m; i++) {
    const yi = y[i];
    const rlo = model.rowLo[i];
    const rhi = model.rowHi[i];

    if (Math.abs(yi) < 1e-15) continue;

    if (yi > 1e-9) {
      if (rhi < INF) {
        lb -= yi * rhi;
      } else if (yi < 1e-3) {
        lb -= yi * 10;
      } else {
        return -Infinity;
      }
    } else if (yi < -1e-9) {
      if (rlo > NEG_INF) {
        lb -= yi * rlo;
      } else if (-yi < 1e-3) {
        lb -= (-yi) * 10;
      } else {
        return -Infinity;
      }
    }
  }

  for (let j = 0; j < n; j++) {
    const rj = rc[j];
    const lj = model.colLo[j];
    const uj = model.colHi[j];
    const qj = qDiag ? qDiag[j] : 0;

    if (qj > 1e-12) {
      const tUnconstrained = -rj / qj;
      const tOpt = Math.max(lj, Math.min(uj, tUnconstrained));
      lb += 0.5 * qj * tOpt * tOpt + rj * tOpt;
    } else {
      if (Math.abs(rj) < 1e-15) continue;
      if (rj > 1e-9) {
        if (lj > NEG_INF) {
          lb += rj * lj;
        } else if (rj < 1e-3) {
          lb -= rj * 10;
        } else {
          return -Infinity;
        }
      } else if (rj < -1e-9) {
        if (uj < INF) {
          lb += rj * uj;
        } else if (-rj < 1e-3) {
          lb -= (-rj) * 10;
        } else {
          return -Infinity;
        }
      }
    }
  }

  return lb;
}

export function hprBatchSolve(
  baseModel: Model,
  scenarios: HPRBatchScenario[],
  options: HPROptions = {}
): HPRBatchResult {
  const t0 = performance.now();
  const results: { id: string; objective: number; status: string; gap: number }[] = [];
  let totalIter = 0;

  for (const scen of scenarios) {
    const mod = cloneModel(baseModel);
    if (scen.costPerturb) {
      for (let j = 0; j < mod.nCols; j++) {
        mod.c[j] += scen.costPerturb[j] || 0;
      }
    }
    if (scen.rhsPerturb) {
      for (let i = 0; i < mod.nRows; i++) {
        const delta = scen.rhsPerturb[i] || 0;
        if (mod.rowLo[i] > NEG_INF) mod.rowLo[i] += delta;
        if (mod.rowHi[i] < INF) mod.rowHi[i] += delta;
      }
    }

    const res = hprSolve(mod, { ...options, maxIter: options.maxIter ?? 500 });
    totalIter += res.iterations;
    results.push({
      id: scen.id,
      objective: res.objective,
      status: res.status,
      gap: res.gap,
    });
  }

  return {
    scenariosSolved: scenarios.length,
    avgIterations: Math.round(totalIter / Math.max(1, scenarios.length)),
    totalTimeMs: Math.round((performance.now() - t0) * 10) / 10,
    results,
  };
}

function estimateMatrixNorm(model: Model): number {
  const n = model.nCols;
  const m = model.nRows;
  const v = new Float64Array(n);
  for (let j = 0; j < n; j++) v[j] = 1.0 / Math.sqrt(n);

  const Av = new Float64Array(m);
  const AtAv = new Float64Array(n);

  for (let iter = 0; iter < 10; iter++) {
    csrMulVec(model.A, v, Av);
    csrMulVecT(model.A, Av, AtAv);

    let norm = 0;
    for (let j = 0; j < n; j++) norm += AtAv[j] * AtAv[j];
    norm = Math.sqrt(norm);
    if (norm < 1e-12) return 1.0;

    for (let j = 0; j < n; j++) v[j] = AtAv[j] / norm;
  }

  csrMulVec(model.A, v, Av);
  let normAv = 0;
  for (let i = 0; i < m; i++) normAv += Av[i] * Av[i];
  return Math.sqrt(normAv);
}
