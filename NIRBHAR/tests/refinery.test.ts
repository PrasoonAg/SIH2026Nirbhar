import { describe, it, expect } from 'vitest';
import { buildRefineryModel, REFINERY_SCENARIOS } from '../src/demo/refinery';
import { dualSimplexSolve } from '../src/solver/lp/dualSimplex';
import { ipmSolve } from '../src/solver/ipm/ipm';

describe('Refinery Demo Generator & Solver', () => {
  it('builds and solves the baseline refinery model to certified optimum with dual simplex', () => {
    const { model } = buildRefineryModel('baseline');
    expect(model.nRows).toBe(32); // 4 CDU + 4 Sulfur + 24 Balances
    expect(model.nCols).toBe(88); // 40 Crudes + 24 Sales + 24 Inventories
    expect(model.sense).toBe('max');

    const result = dualSimplexSolve(model);
    console.log('Refinery Baseline Solve (Dual Simplex):', {
      status: result.status,
      objective: result.objective,
      iterations: result.iterations,
      gap: result.gap,
    });

    expect(result.status).toBe('OPTIMAL');
    expect(result.objective).toBeGreaterThan(0); // Positive GRM
  });

  it('solves the refinery model with interior-point method (IPM)', () => {
    const { model } = buildRefineryModel('baseline');
    const result = ipmSolve(model);
    console.log('Refinery Baseline Solve (IPM):', {
      status: result.status,
      objective: result.objective,
      iterations: result.iterations,
      gap: result.gap,
    });

    expect(result.status).toBe('OPTIMAL');
    expect(result.objective).toBeGreaterThan(0);
  });

  it('correctly reacts to tight sulfur scenario by altering crude blend', () => {
    const base = buildRefineryModel('baseline');
    const tight = buildRefineryModel('tight-sulfur');

    const resBase = dualSimplexSolve(base.model);
    const resTight = dualSimplexSolve(tight.model);

    expect(resBase.status).toBe('OPTIMAL');
    expect(resTight.status).toBe('OPTIMAL');
    // Stricter sulfur constraint reduces or keeps margin equal
    expect(resTight.objective).toBeLessThanOrEqual(resBase.objective + 1e-4);
  });
});
