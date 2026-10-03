/**
 * NIRBHAR — Solver Cut Definitions
 * Lives inside src/solver/mip/cuts/ — strictly sovereign, no imports from src/verify.
 */

export interface CutRecord {
  kind: 'GMI' | 'CMIR' | 'COVER';
  /** Constraint: coeffs · x >= rhs (or coeffs · x <= rhs depending on representation) */
  coeffs: Float64Array;
  rhs: number;
  lpValue: number;
  sourceRow?: number;
}
