/**
 * NIRBHAR — Primal Heuristics (§6.8)
 */

import type { Model } from '../io/model';
import { INF, NEG_INF } from '../io/model';
import { csrMulVec } from '../linalg/csr';

export interface HeuristicIncumbent {
  x: Float64Array;
  objective: number;
  heuristicName: string;
}

export function tryRoundingHeuristic(model: Model, xLP: Float64Array): HeuristicIncumbent | null {
  const n = model.nCols;
  const m = model.nRows;
  const xCandidate = new Float64Array(xLP);

  for (let j = 0; j < n; j++) {
    if (model.integrality[j] !== 0) {
      xCandidate[j] = Math.round(xCandidate[j]);
      xCandidate[j] = Math.max(model.colLo[j], Math.min(model.colHi[j], xCandidate[j]));
    }
  }

  const Ax = new Float64Array(m);
  csrMulVec(model.A, xCandidate, Ax);

  for (let i = 0; i < m; i++) {
    const rlo = model.rowLo[i];
    const rhi = model.rowHi[i];
    if (rlo > NEG_INF && Ax[i] < rlo - 1e-6) return null;
    if (rhi < INF && Ax[i] > rhi + 1e-6) return null;
  }

  let obj = model.objConstant;
  for (let j = 0; j < n; j++) {
    obj += model.c[j] * xCandidate[j];
  }

  return {
    x: xCandidate,
    objective: obj,
    heuristicName: 'simple-rounding',
  };
}

export function isIntegerFeasible(model: Model, x: Float64Array, tol = 1e-4): boolean {
  for (let j = 0; j < model.nCols; j++) {
    if (model.integrality[j] !== 0) {
      const val = x[j];
      const dist = Math.abs(val - Math.round(val));
      if (dist > tol) return false;
    }
  }
  return true;
}
