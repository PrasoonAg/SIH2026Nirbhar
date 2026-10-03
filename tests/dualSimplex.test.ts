import { describe, it, expect } from 'vitest';
import { parseMPS } from '../src/solver/io/mps';
import { dualSimplexSolve } from '../src/solver/lp/dualSimplex';

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

const SAMPLE_AFIRO = `NAME          AFIRO
ROWS
 N  OBJ
 L  R09
 L  R10
 E  X05
 L  X21
COLUMNS
    X01  OBJ  -.02  R09   1.0
    X01  X05   1.0
    X02  R09   1.0  R10   1.0
    X02  X05   1.0
    X06  OBJ  -.01  R10   1.0
    X06  X21   1.0
    X22  OBJ  -.02  X21   1.0
    X23  R09  -1.0  X21  -1.0
    X23  OBJ   0.0
    X24  R10  -1.0  X21  -1.0
    X24  OBJ   0.0
RHS
    RHS  R09   310   R10  300
    RHS  X05   80    X21  500
BOUNDS
 UP BND  X22   400.0
 UP BND  X23   400.0
 UP BND  X24   400.0
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

const SAMPLE_INFEASIBLE = `NAME          INFEASIBLE
ROWS
 N  obj
 G  c1
 L  c2
COLUMNS
    x1  obj  1.0  c1  1.0  c2  1.0
RHS
    rhs  c1  5.0  c2  3.0
BOUNDS
ENDATA`;

describe('dualSimplexSolve', () => {
  it('solves TINY_LP correctly', () => {
    const { model, errors } = parseMPS(SAMPLE_SMALL);
    expect(errors).toHaveLength(0);
    const result = dualSimplexSolve(model);
    expect(result.status).toBe('OPTIMAL');
    expect(result.objective).toBeCloseTo(-8.0, 4);
    expect(result.x[0]).toBeCloseTo(0.0, 4);
    expect(result.x[1]).toBeCloseTo(4.0, 4);
  });

  it('detects INFEASIBLE instance', () => {
    const { model, errors } = parseMPS(SAMPLE_INFEASIBLE);
    expect(errors).toHaveLength(0);
    const result = dualSimplexSolve(model);
    expect(result.status).toBe('INFEASIBLE_CERTIFIED');
  });

  it('solves CANONICAL 3-variable LP correctly', () => {
    const { model, errors } = parseMPS(SAMPLE_CANONICAL);
    expect(errors).toHaveLength(0);
    const result = dualSimplexSolve(model);
    expect(result.status).toBe('OPTIMAL');
    expect(result.objective).toBeCloseTo(-20.0, 4);
    expect(result.x[2]).toBeCloseTo(5.0, 4);
  });

  it('solves AFIRO sample correctly', () => {
    const { model, errors } = parseMPS(SAMPLE_AFIRO);
    expect(errors).toHaveLength(0);
    const result = dualSimplexSolve(model);
    console.log('Result for AFIRO:', {
      status: result.status,
      objective: result.objective,
      iterations: result.iterations
    });
    expect(result.status).toBe('OPTIMAL');
    expect(result.objective).toBeLessThan(0);
  });
});
