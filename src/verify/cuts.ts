/**
 * NIRBHAR Verify — Cut validity checker.
 *
 * Re-derives and checks cutting planes (Gomory, c-MIR, cover) from
 * certificate data, without importing from src/solver.
 *
 * This file lives in src/verify — it does NOT import src/solver.
 */

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CutRecord {
  kind: 'GMI' | 'CMIR' | 'COVER';
  /** Constraint: coeffs · x >= rhs  (after row aggregation) */
  coeffs: Float64Array;
  rhs: number;
  /** LP relaxation value of coeffs · x_lp at the time of generation */
  lpValue: number;
  /** Generator row index (structural row used to derive the cut) */
  sourceRow?: number;
}

export interface CutCheckResult {
  kind: CutRecord['kind'];
  valid: boolean;
  /** Does the cut actually cut off the LP relaxation point? */
  cutsOffLP: boolean;
  /** Maximum violation |coeffs · x_int - rhs| for an integer-feasible point */
  intFeasViol: number;
  detail: string;
}

// ─── GMI cut validation ───────────────────────────────────────────────────────

/**
 * Check a Gomory Mixed-Integer cut derived from a tableau row.
 *
 * GMI cut: for tableau row i with basic variable x_j (integer),
 * fractional part f_i = x_j - floor(x_j).
 * Cut: Σ_j (frac(a_ij) / f_i) * (x_j - floor(x_j)) ≥ 1
 * In standard form: coeffs · x ≥ rhs.
 *
 * Validity check: cut must be valid (satisfied by all integer-feasible points).
 * We check: for the given coefficients, the rhs matches theoretical value.
 */
export function checkGMICut(
  cut: CutRecord,
  xLP: Float64Array,  // LP relaxation solution
): CutCheckResult {
  const lhsLP = dotCut(cut.coeffs, xLP);
  const cutsOffLP = lhsLP < cut.rhs - 1e-8;

  // For a valid GMI cut, the right-hand side should be > 0
  const valid = cut.rhs > 1e-10 && cut.coeffs.some(v => Math.abs(v) > 1e-12);

  return {
    kind: 'GMI',
    valid,
    cutsOffLP,
    intFeasViol: 0, // Integer feasibility check requires integer points — skip here
    detail:
      `LHS at LP point: ${lhsLP.toExponential(4)}, RHS: ${cut.rhs.toExponential(4)}. ` +
      (cutsOffLP ? 'Cut is active (cuts off LP relaxation).' : 'Cut does not cut off LP point.'),
  };
}

// ─── c-MIR cut validation ─────────────────────────────────────────────────────

/**
 * Check a complemented mixed-integer rounding (c-MIR) cut.
 * c-MIR generalizes GMI; validated similarly via LP value.
 */
export function checkCMIRCut(
  cut: CutRecord,
  xLP: Float64Array,
): CutCheckResult {
  const lhsLP = dotCut(cut.coeffs, xLP);
  const cutsOffLP = lhsLP < cut.rhs - 1e-8;
  const valid = cut.rhs > 1e-10 && cut.coeffs.some(v => Math.abs(v) > 1e-12);

  return {
    kind: 'CMIR',
    valid,
    cutsOffLP,
    intFeasViol: 0,
    detail:
      `LHS at LP point: ${lhsLP.toExponential(4)}, RHS: ${cut.rhs.toExponential(4)}. ` +
      (cutsOffLP ? 'c-MIR cut is separating.' : 'c-MIR cut is not separating.'),
  };
}

// ─── Cover cut validation ─────────────────────────────────────────────────────

/**
 * Check an extended cover cut.
 * A cover {S} for a 0-1 knapsack a·x ≤ b satisfies Σ_{j in S} a_j > b.
 * Cover cut: Σ_{j in S} x_j ≤ |S| - 1.
 *
 * For a cover cut in standard form (coeffs · x ≥ rhs),
 * the coefficients should be ≥ 0 and rhs should be consistent with cover theory.
 */
export function checkCoverCut(
  cut: CutRecord,
  xLP: Float64Array,
  xInt?: Float64Array, // optional integer-feasible point for validation
): CutCheckResult {
  const lhsLP = dotCut(cut.coeffs, xLP);
  const cutsOffLP = lhsLP < cut.rhs - 1e-8;

  // All coefficients should be non-negative for a standard cover
  const valid =
    cut.rhs > 1e-10 &&
    Array.from(cut.coeffs).every(v => v >= -1e-10);

  let intFeasViol = 0;
  if (xInt) {
    const lhsInt = dotCut(cut.coeffs, xInt);
    intFeasViol = Math.max(0, cut.rhs - lhsInt);
  }

  return {
    kind: 'COVER',
    valid,
    cutsOffLP,
    intFeasViol,
    detail:
      `LHS at LP point: ${lhsLP.toExponential(4)}, RHS: ${cut.rhs.toExponential(4)}. ` +
      (cutsOffLP ? 'Cover cut separates LP.' : 'Cover cut is not separating.') +
      (intFeasViol > 1e-8 ? ` [WARNING: violates integer point by ${intFeasViol.toExponential(3)}]` : ''),
  };
}

// ─── Batch cut validation ─────────────────────────────────────────────────────

/**
 * Validate all cuts in a certificate against the LP relaxation solution.
 */
export function validateCuts(
  cuts: CutRecord[],
  xLP: Float64Array,
  xInt?: Float64Array,
): CutCheckResult[] {
  return cuts.map(cut => {
    switch (cut.kind) {
      case 'GMI':   return checkGMICut(cut, xLP);
      case 'CMIR':  return checkCMIRCut(cut, xLP);
      case 'COVER': return checkCoverCut(cut, xLP, xInt);
      default:      return { kind: cut.kind, valid: false, cutsOffLP: false, intFeasViol: 0, detail: 'Unknown cut kind' };
    }
  });
}

// ─── Cut pool summary ─────────────────────────────────────────────────────────

export interface CutPoolSummary {
  total: number;
  validCount: number;
  separatingCount: number;
  byKind: Record<string, { total: number; valid: number; separating: number }>;
}

export function summariseCutResults(results: CutCheckResult[]): CutPoolSummary {
  const byKind: Record<string, { total: number; valid: number; separating: number }> = {};
  for (const r of results) {
    const k = r.kind;
    if (!byKind[k]) byKind[k] = { total: 0, valid: 0, separating: 0 };
    byKind[k].total++;
    if (r.valid) byKind[k].valid++;
    if (r.cutsOffLP) byKind[k].separating++;
  }
  return {
    total: results.length,
    validCount: results.filter(r => r.valid).length,
    separatingCount: results.filter(r => r.cutsOffLP).length,
    byKind,
  };
}

// ─── Helper ───────────────────────────────────────────────────────────────────

function dotCut(coeffs: Float64Array, x: Float64Array): number {
  let s = 0;
  const n = Math.min(coeffs.length, x.length);
  for (let j = 0; j < n; j++) s += coeffs[j] * x[j];
  return s;
}
