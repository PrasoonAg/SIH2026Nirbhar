import { describe, it, expect } from 'vitest';
import { parseMPS } from '../src/solver/io/mps';
import { hprSolve } from '../src/solver/lp/hpr';
import { branchAndCutSolve, bruteForceSmallMILP } from '../src/solver/mip/bb';

const SAMPLE_LP = `NAME          TINY_LP
ROWS
 N  obj
 L  c1
 L  c2
COLUMNS
    x1  obj  -1.0  c1   1.0
    x1  c2    2.0
    x2  obj  -2.0  c1   1.0
    x2  c2    1.0
RHS
    rhs  c1   4.0  c2   6.0
BOUNDS
ENDATA`;

const SAMPLE_KNAPSACK_MILP = `NAME          KNAPSACK_MILP
ROWS
 N  obj
 L  capacity
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    x1        obj       -10.0  capacity  5.0
    x2        obj       -8.0   capacity  4.0
    x3        obj       -5.0   capacity  3.0
    MARK0001  'MARKER'                 'INTDEG'
RHS
    rhs       capacity  7.0
BOUNDS
 UP bnd       x1        1.0
 UP bnd       x2        1.0
 UP bnd       x3        1.0
ENDATA`;

describe('HPR-Family First-Order Solver', () => {
  it('solves TINY_LP within tolerance', () => {
    const { model } = parseMPS(SAMPLE_LP);
    const res = hprSolve(model, { maxIter: 1000, tol: 1e-4 });
    expect(['OPTIMAL', 'CERTIFIED_APPROXIMATE']).toContain(res.status);
    expect(res.objective).toBeCloseTo(-8.0, 1);
    expect(res.lowerBound).toBeLessThanOrEqual(-7.9);
  });
});

describe('Branch-and-Cut Solver', () => {
  it('solves 0-1 knapsack MILP and closes gap', () => {
    const { model } = parseMPS(SAMPLE_KNAPSACK_MILP);
    const res = branchAndCutSolve(model, { useCuts: true });
    expect(res.status).toBe('OPTIMAL');
    expect(res.objective).toBeCloseTo(-13.0, 2);
    expect(res.gap).toBeLessThanOrEqual(1e-4);
  });

  it('matches brute-force enumeration on small MILPs', () => {
    const { model } = parseMPS(SAMPLE_KNAPSACK_MILP);
    const bins = [0, 1, 2];
    const bfObj = bruteForceSmallMILP(model, bins);
    const res = branchAndCutSolve(model);
    expect(res.objective).toBeCloseTo(bfObj, 2);
  });
});
