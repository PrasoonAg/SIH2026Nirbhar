import { describe, it, expect } from 'vitest';
import { ModelBuilder } from '../src/solver/io/model';
import { presolve } from '../src/solver/presolve/presolve';
import { dualSimplexSolve } from '../src/solver/lp/dualSimplex';

describe('Presolve & Postsolve', () => {
  it('eliminates fixed variable and postsolves accurately', () => {
    // min -x2 s.t. x1 + x2 <= 6, x1 in [2, 2], x2 in [0, 10]
    // Optimal: x1 = 2, x2 = 4, obj = -4
    const builder = new ModelBuilder();
    builder.name = 'FIXED_VAR';
    const x1 = builder.addCol('x1');
    const x2 = builder.addCol('x2');
    builder.setColBound(x1, 'FX', 2.0);
    builder.setColBound(x2, 'UP', 10.0);
    builder.setObjCoeff(x2, -1.0);

    const r1 = builder.addRow('r1', 'L');
    builder.setRhs(r1, 6.0, 'L');
    builder.setEntry(r1, x1, 1.0);
    builder.setEntry(r1, x2, 1.0);

    const model = builder.build();
    const pResult = presolve(model);

    expect(pResult.stats.colsRemoved).toBe(1);
    expect(pResult.presolvedModel.nCols).toBe(1);

    // Solve reduced model
    const redResult = dualSimplexSolve(pResult.presolvedModel);
    expect(redResult.status).toBe('OPTIMAL');

    // Postsolve to original space
    const full = pResult.postsolve(redResult.x, redResult.y, redResult.rc);
    expect(full.x[0]).toBeCloseTo(2.0, 4);
    expect(full.x[1]).toBeCloseTo(4.0, 4);
  });

  it('detects infeasible empty row in presolve', () => {
    const builder = new ModelBuilder();
    builder.name = 'EMPTY_ROW_INFEAS';
    builder.addCol('x1');
    const r1 = builder.addRow('r1', 'G');
    builder.setRhs(r1, 10.0, 'G'); // 0 >= 10 is impossible

    const model = builder.build();
    const pResult = presolve(model);
    expect(pResult.isInfeasible).toBe(true);
  });

  it('tightens bounds using singleton row and eliminates row', () => {
    // min -x1 s.t. 2*x1 <= 6 (implies x1 <= 3)
    const builder = new ModelBuilder();
    builder.name = 'SINGLETON_ROW';
    const x1 = builder.addCol('x1');
    builder.setColBound(x1, 'UP', 100.0);
    builder.setObjCoeff(x1, -1.0);

    const r1 = builder.addRow('r1', 'L');
    builder.setRhs(r1, 6.0, 'L');
    builder.setEntry(r1, x1, 2.0);

    const model = builder.build();
    const pResult = presolve(model);

    expect(pResult.stats.boundsTightened).toBe(1);
    expect(pResult.stats.rowsRemoved).toBe(1);
    expect(pResult.presolvedModel.colHi[0]).toBeCloseTo(3.0, 4);
    expect(pResult.presolvedModel.nRows).toBe(0); // Row was eliminated
  });
});
