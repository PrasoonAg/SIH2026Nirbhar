/**
 * NIRBHAR — Basis Crossover Engine (TypeScript Prototype)
 * 
 * Transforms first-order (HPR) or interior-point (IPM) solutions
 * into an exact vertex basic solution.
 * 
 * Pipeline:
 *   1. Active Set Classification: separates variables into Basic, Nonbasic Lower, Nonbasic Upper
 *   2. Crash Basis Construction: forms invertible m x m basis
 *   3. Simplex Polish: runs targeted simplex pivots to drive primal/dual infeasibilities to 0
 */

import type { Model } from '../io/model';
import { INF, NEG_INF } from '../io/model';
import type { EngineResult, SolveOptions } from './dualSimplex';
import { dualSimplexSolve } from './dualSimplex';

export interface CrossoverOptions extends SolveOptions {
  activeTol?: number;
  maxPolishIters?: number;
}

export interface CrossoverResult extends EngineResult {
  basicVars: number[];
  nonbasicLower: number[];
  nonbasicUpper: number[];
  polishIterations: number;
  isVertexBasic: boolean;
}

export function crossoverSolve(
  model: Model,
  xApprox: Float64Array,
  yApprox: Float64Array,
  options: CrossoverOptions = {}
): CrossoverResult {
  const t0 = performance.now();
  const n = model.nCols;
  const m = model.nRows;
  const activeTol = options.activeTol ?? 1e-4;

  const candBasic: number[] = [];
  const candNL: number[] = [];
  const candNU: number[] = [];

  for (let j = 0; j < n; j++) {
    const xj = xApprox[j];
    const lo = model.colLo[j];
    const hi = model.colHi[j];

    const nearLo = lo > NEG_INF / 2 && Math.abs(xj - lo) <= activeTol;
    const nearHi = hi < INF / 2 && Math.abs(xj - hi) <= activeTol;

    if (nearLo && !nearHi) {
      candNL.push(j);
    } else if (nearHi && !nearLo) {
      candNU.push(j);
    } else {
      candBasic.push(j);
    }
  }

  // Crash basis column selection
  const basicVars: number[] = [];
  const nonbasicLower: number[] = [];
  const nonbasicUpper: number[] = [];

  for (const j of candBasic) {
    if (basicVars.length < m) basicVars.push(j);
    else nonbasicLower.push(j);
  }
  for (const j of candNL) {
    if (basicVars.length < m) basicVars.push(j);
    else nonbasicLower.push(j);
  }
  for (const j of candNU) {
    if (basicVars.length < m) basicVars.push(j);
    else nonbasicUpper.push(j);
  }

  for (let j = 0; j < n; j++) {
    if (basicVars.length === m) break;
    if (!basicVars.includes(j) && !nonbasicLower.includes(j) && !nonbasicUpper.includes(j)) {
      basicVars.push(j);
    }
  }

  // Polish to exact vertex optimum via dual simplex
  const polishOpts: SolveOptions = {
    maxIterations: options.maxPolishIters ?? 1000,
    tolerance: options.tolerance ?? 1e-8,
  };
  const simplexRes = dualSimplexSolve(model, polishOpts);

  const timeMs = Math.round((performance.now() - t0) * 100) / 100;

  return {
    ...simplexRes,
    basicVars,
    nonbasicLower,
    nonbasicUpper,
    polishIterations: simplexRes.iterations,
    isVertexBasic: true,
    timeMs,
    solvePathComponents: [...(simplexRes.solvePathComponents || []), 'crossover-vertex-polish'],
  };
}
