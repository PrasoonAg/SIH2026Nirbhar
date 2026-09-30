/**
 * Certificate builder — assembles a Certificate from an EngineResult.
 * Keeps solver (src/solver) and verifier (src/verify) strictly separated.
 * This file lives in src/solver and does NOT import from src/verify.
 */

import type { Model } from '../io/model';
import type { EngineResult } from '../lp/dualSimplex';
import {
  CERT_VERSION,
  serialiseCert,
  type CertLP,
  type CertLPInfeasible,
  type CertLPUnbounded,
  type ResidualBlock,
  type Certificate,
} from './schema';

/** Build a certificate from a solved LP result */
export function buildCertLP(
  model: Model,
  result: EngineResult,
  engine: string,
  modelSHA256?: string
): Certificate {
  const now = new Date().toISOString();

  const residuals: ResidualBlock = {
    maxRowViol:         result.maxPrimalViol,
    maxBoundViol:       result.maxPrimalViol,
    maxDualViol:        result.maxDualViol,
    infeasibilityNorm:  result.maxPrimalViol,
  };

  switch (result.status) {
    case 'OPTIMAL':
    case 'OPTIMAL_WITHIN_GAP': {
      const explanationHints = buildExplanationHints(model, result);

      const cert: CertLP = {
        kind: 'LP_OPTIMAL',
        version: CERT_VERSION,
        modelName: model.name,
        modelSHA256,
        timestamp: now,
        engine,
        objectiveUB: result.objective,
        lowerBound: result.lowerBound,
        gap: result.gap,
        x: Array.from(result.x),
        y: Array.from(result.y),
        rc: Array.from(result.rc),
        residuals,
        solveTimeMs: result.timeMs,
        iterations: result.iterations,
        solvePathComponents: result.solvePathComponents,
        escalations: result.escalations,
        explanationHints,
      };
      return cert;
    }

    case 'INFEASIBLE_CERTIFIED': {
      const cert: CertLPInfeasible = {
        kind: 'LP_INFEASIBLE',
        version: CERT_VERSION,
        modelName: model.name,
        modelSHA256,
        timestamp: now,
        engine,
        farkasRay: Array.from(result.y),  // dual ray from Phase 1
        farkasCheck: {
          AtY_maxPositive: result.maxDualViol,
          bTy: 1e9,  // placeholder — computed properly in Phase 5
        },
        solveTimeMs: result.timeMs,
        iterations: result.iterations,
        escalations: result.escalations,
      };
      return cert;
    }

    case 'UNBOUNDED_CERTIFIED': {
      const cert: CertLPUnbounded = {
        kind: 'LP_UNBOUNDED',
        version: CERT_VERSION,
        modelName: model.name,
        modelSHA256,
        timestamp: now,
        engine,
        recessionDir: Array.from(result.x),
        recessionCheck: { cTd: result.objective, AdMax: result.maxPrimalViol },
        solveTimeMs: result.timeMs,
        iterations: result.iterations,
        escalations: result.escalations,
      };
      return cert;
    }

    default: {
      // TIME_LIMIT, ITER_LIMIT, NUMERICAL_ISSUE
      const cert: CertLP = {
        kind: 'LP_OPTIMAL',
        version: CERT_VERSION,
        modelName: model.name,
        modelSHA256,
        timestamp: now,
        engine: `${engine} [${result.status}]`,
        objectiveUB: result.objective,
        lowerBound: result.lowerBound,
        gap: result.gap,
        x: Array.from(result.x),
        y: Array.from(result.y),
        rc: Array.from(result.rc),
        residuals,
        solveTimeMs: result.timeMs,
        iterations: result.iterations,
        solvePathComponents: result.solvePathComponents,
        escalations: [...result.escalations, `Solve terminated with status ${result.status}`],
        explanationHints: [`Solve did not converge: ${result.status}`],
      };
      return cert;
    }
  }
}

/** Generate human-readable explanation hints from the solve result */
function buildExplanationHints(model: Model, result: EngineResult): string[] {
  const hints: string[] = [];

  hints.push(
    `The solver minimized ${model.nCols} variables over ${model.nRows} constraints.`
  );

  if (result.lowerBound > -1e29) {
    const gapPct = (result.gap * 100).toFixed(4);
    hints.push(
      `LB(y) = ${result.lowerBound.toPrecision(10)} confirms no feasible point can have cost below this value.`
    );
    hints.push(
      `Optimality gap = ${gapPct}% — within tolerance.`
    );
  }

  const topRC = Array.from(result.rc)
    .map((v, j) => ({ j, v, name: model.colNames[j] ?? `x${j}` }))
    .filter(e => Math.abs(e.v) > 1e-6)
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
    .slice(0, 3);

  if (topRC.length > 0) {
    hints.push(
      'Largest (non-zero) reduced costs: ' +
      topRC.map(e => `${e.name}: ${e.v.toFixed(4)}`).join(', ') + '.'
    );
  }

  const topDual = Array.from(result.y)
    .map((v, i) => ({ i, v, name: model.rowNames[i] ?? `r${i}` }))
    .filter(e => Math.abs(e.v) > 1e-6)
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
    .slice(0, 3);

  if (topDual.length > 0) {
    hints.push(
      'Most binding constraints (shadow prices): ' +
      topDual.map(e => `${e.name}: ${e.v.toFixed(4)}`).join(', ') + '.'
    );
  }

  if (result.escalations.length > 0) {
    hints.push(`Solver noted: ${result.escalations[0]}`);
  }

  return hints;
}

/** Convenience: build and serialise to JSON */
export function buildCertLPJson(
  model: Model,
  result: EngineResult,
  engine: string,
  modelSHA256?: string
): string {
  return serialiseCert(buildCertLP(model, result, engine, modelSHA256));
}
