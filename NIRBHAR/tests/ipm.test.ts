import { describe, it, expect } from 'vitest';
import { parseMPS } from '../src/solver/io/mps';
import { ipmSolve } from '../src/solver/ipm/ipm';
import { ModelBuilder } from '../src/solver/io/model';

const SAMPLE_SMALL = `NAME          TINY_LP
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

const SAMPLE_CANONICAL = `NAME          CANONICAL
ROWS
 N  OBJ
 L  R1
 L  R2
COLUMNS
    X1  OBJ  -2.0  R1  3.0  R2  2.0
    X2  OBJ  -3.0  R1  2.0  R2  5.0
    X3  OBJ  -4.0  R1  1.0  R2  3.0
RHS
    RHS  R1  10.0  R2  15.0
BOUNDS
ENDATA`;

describe('ipmSolve', () => {
  it('solves TINY_LP with interior-point method', () => {
    const { model, errors } = parseMPS(SAMPLE_SMALL);
    expect(errors).toHaveLength(0);
    const result = ipmSolve(model);
    console.log('IPM Result for TINY_LP:', {
      status: result.status,
      objective: result.objective,
      iterations: result.iterations,
      x: Array.from(result.x)
    });
    expect(result.status).toBe('OPTIMAL');
    expect(result.objective).toBeCloseTo(-8.0, 2);
    expect(result.x[0]).toBeCloseTo(0.0, 2);
    expect(result.x[1]).toBeCloseTo(4.0, 2);
  });

  it('solves CANONICAL LP with interior-point method', () => {
    const { model, errors } = parseMPS(SAMPLE_CANONICAL);
    expect(errors).toHaveLength(0);
    const result = ipmSolve(model);
    console.log('IPM Result for CANONICAL:', {
      status: result.status,
      objective: result.objective,
      iterations: result.iterations,
      x: Array.from(result.x)
    });
    expect(result.status).toBe('OPTIMAL');
    expect(result.objective).toBeCloseTo(-20.0, 2);
    expect(result.x[2]).toBeCloseTo(5.0, 2);
  });

  it('solves convex Quadratic Program (QP) with interior-point method', () => {
    // min 1/2 (x1^2 + x2^2) - x1 - x2 s.t. x1 + x2 <= 1, x1 >= 0, x2 >= 0
    // Optimum: x1 = 0.5, x2 = 0.5, obj = -0.75
    const builder = new ModelBuilder();
    builder.name = 'MIN_QP';
    const x1 = builder.addCol('x1');
    const x2 = builder.addCol('x2');
    builder.setObjCoeff(x1, -1.0);
    builder.setObjCoeff(x2, -1.0);

    const r1 = builder.addRow('r1', 'L');
    builder.setRhs(r1, 1.0, 'L');
    builder.setEntry(r1, x1, 1.0);
    builder.setEntry(r1, x2, 1.0);

    // Q diagonal: Q_00 = 1, Q_11 = 1
    builder.setQ({
      Qp: new Int32Array([0, 1, 2]),
      Qi: new Int32Array([0, 1]),
      Qv: new Float64Array([1.0, 1.0]),
      isDiagonal: true,
      isPosSemiDef: true,
    });

    const model = builder.build();
    const result = ipmSolve(model);
    console.log('IPM Result for QP:', {
      status: result.status,
      objective: result.objective,
      iterations: result.iterations,
      x: Array.from(result.x)
    });

    expect(result.status).toBe('OPTIMAL');
    expect(result.objective).toBeCloseTo(-0.75, 2);
    expect(result.x[0]).toBeCloseTo(0.5, 2);
    expect(result.x[1]).toBeCloseTo(0.5, 2);
  });
});
