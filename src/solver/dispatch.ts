/**
 * NIRBHAR Engine Dispatcher
 * Routes solve requests to the appropriate engine worker.
 * 
 * Phase 1 engines:
 *   'dual-simplex' → dualSimplex.ts (LP only)
 * 
 * Phase 2+ engines (stubs for now):
 *   'ipm'          → Interior-point method (QP, LP)
 *   'hpr-family'   → Halpern-anchored PDHG first-order (LP, QP, batch)
 *   'branch-cut'   → Branch-and-cut (MILP, MIQP)
 *
 * Dispatch rules (Phase 1):
 *   LP  → dual-simplex (any size, prototype limit ~500 rows)
 *   MILP → branch-cut (not yet implemented)
 *   QP  → ipm (not yet implemented)
 *   MIQP → branch-cut (not yet implemented)
 *
 * Workers are created lazily and kept alive for the session.
 */

import type { Model } from './io/model';
import type { SolveOptions, EngineResult } from './lp/dualSimplex';
import { dualSimplexSolve } from './lp/dualSimplex';
import { ipmSolve } from './ipm/ipm';
import { hprSolve } from './lp/hpr';
import { branchAndCutSolve } from './mip/bb';
import { presolve } from './presolve/presolve';

export type EngineId = 'dual-simplex' | 'ipm' | 'hpr-family' | 'branch-cut';

export interface DispatchRequest {
  model: Model;
  engine?: EngineId;          // auto-select if omitted
  options?: SolveOptions;
}

export interface DispatchResult extends EngineResult {
  engine: EngineId;
  engineLabel: string;        // human-readable label for UI
}

/** Automatically select the best available engine for a model */
export function selectEngine(model: Model): EngineId {
  const hasIntegers = model.integrality.some(v => v !== 0);
  const hasQ = !!model.Q;

  if (hasIntegers && hasQ) return 'branch-cut';   // MIQP
  if (hasIntegers)          return 'branch-cut';   // MILP
  if (hasQ)                 return 'ipm';           // QP (Phase 2)
  return 'dual-simplex';                            // LP
}

/** Human-readable engine labels */
export const ENGINE_LABELS: Record<EngineId, string> = {
  'dual-simplex': 'Dual Simplex — Two-Phase Industrial Core',
  'ipm':          'Interior-Point Method (Mehrotra Predictor-Corrector)',
  'hpr-family':   'HPR-Family (First-Order GPU/JIT Engine)',
  'branch-cut':   'Deterministic Branch-and-Cut (Certified MILP Tree)',
};

/** Dispatch and solve synchronously (used in tests and CLI API) */
export async function dispatch(req: DispatchRequest): Promise<DispatchResult> {
  const engine = req.engine ?? selectEngine(req.model);
  const label  = ENGINE_LABELS[engine];

  let targetModel = req.model;
  let postsolveFn: ((x: Float64Array, y: Float64Array, rc: Float64Array) => { x: Float64Array; y: Float64Array; rc: Float64Array }) | null = null;
  const escalations: string[] = [];

  if (req.options?.presolve) {
    const p = presolve(req.model);
    if (p.isInfeasible) {
      const x = new Float64Array(req.model.nCols);
      const y = new Float64Array(req.model.nRows);
      const rc = new Float64Array(req.model.nCols);
      return {
        status: 'INFEASIBLE_CERTIFIED',
        objective: Infinity,
        lowerBound: -Infinity,
        gap: Infinity,
        x, y, rc,
        iterations: 0,
        timeMs: 0,
        maxPrimalViol: 0,
        maxDualViol: 0,
        escalations: [p.infeasibilityReason ?? 'Infeasibility detected in presolve'],
        solvePathComponents: ['presolve-infeasible'],
        engine,
        engineLabel: label,
      };
    }
    if (p.stats.rowsRemoved > 0 || p.stats.colsRemoved > 0 || p.stats.boundsTightened > 0) {
      targetModel = p.presolvedModel;
      postsolveFn = p.postsolve;
      escalations.push(`Presolve: removed ${p.stats.rowsRemoved} rows, ${p.stats.colsRemoved} cols, tightened ${p.stats.boundsTightened} bounds`);
    }
  }

  let result: EngineResult;
  switch (engine) {
    case 'dual-simplex': {
      result = dualSimplexSolve(targetModel, req.options ?? {});
      break;
    }

    case 'ipm': {
      result = ipmSolve(targetModel, req.options ?? {});
      break;
    }

    case 'hpr-family': {
      result = hprSolve(targetModel, req.options ?? {});
      break;
    }

    case 'branch-cut': {
      result = branchAndCutSolve(targetModel, req.options ?? {});
      break;
    }
  }

  if (postsolveFn) {
    const full = postsolveFn(result.x, result.y, result.rc);
    result = {
      ...result,
      x: full.x,
      y: full.y,
      rc: full.rc,
      escalations: [...result.escalations, ...escalations],
      solvePathComponents: ['presolve', ...result.solvePathComponents, 'postsolve'],
    };
  }

  return { ...result, engine, engineLabel: label };
}

function notImplemented(
  engine: EngineId,
  label: string,
  model: Model,
  options?: SolveOptions
): DispatchResult {
  const x = new Float64Array(model.nCols);
  const y = new Float64Array(model.nRows);
  const rc = new Float64Array(model.nCols);
  return {
    status: 'UNSUPPORTED',
    objective: Infinity,
    lowerBound: -Infinity,
    gap: Infinity,
    x, y, rc,
    iterations: 0,
    timeMs: 0,
    maxPrimalViol: Infinity,
    maxDualViol: Infinity,
    escalations: [`Engine "${engine}" not yet implemented (future phase)`],
    solvePathComponents: [`stub:${engine}`],
    engine,
    engineLabel: label,
  };
}

/** Engine metadata for the Architecture page and Sovereignty panel */
export const ENGINE_METADATA = [
  {
    id: 'dual-simplex' as EngineId,
    label: 'Dual Simplex',
    description: 'Bounded two-phase revised simplex with dense LU refactorization. Phase 1/2 with big-M artificials.',
    problemClass: ['LP'],
    phase: 'Phase 1',
    status: 'active',
    usesGPU: false,
    usesThirdParty: false,
    algorithm: 'Primal simplex with Phase 1 feasibility and Phase 2 optimization via Dantzig pricing',
  },
  {
    id: 'ipm' as EngineId,
    label: 'Interior-Point Method',
    description: 'Homogeneous self-dual IPM with dense Cholesky normal equations. Suited for LP and QP.',
    problemClass: ['LP', 'QP'],
    phase: 'Phase 2',
    status: 'planned',
    usesGPU: false,
    usesThirdParty: false,
    algorithm: 'Homogeneous self-dual IPM; dense Cholesky via LDL^T',
  },
  {
    id: 'hpr-family' as EngineId,
    label: 'HPR-Family First-Order',
    description: 'Halpern-anchored PDHG-type primal-dual first-order operator. Suited for large LP/QP and batch scenarios.',
    problemClass: ['LP', 'QP'],
    phase: 'Phase 3',
    status: 'planned',
    usesGPU: false,
    usesThirdParty: false,
    algorithm: 'Halpern-anchored PDHG (HPR-family); Chambolle-Pock type iterations with adaptive step size',
  },
  {
    id: 'branch-cut' as EngineId,
    label: 'Branch-and-Cut',
    description: 'Certified branch-and-cut with Farkas prune, Gomory cuts, and brute-force cross-check.',
    problemClass: ['MILP', 'MIQP'],
    phase: 'Phase 3',
    status: 'planned',
    usesGPU: false,
    usesThirdParty: false,
    algorithm: 'LP-based B&C; Gomory cuts; strong branching; Farkas dual at each node',
  },
] as const;
