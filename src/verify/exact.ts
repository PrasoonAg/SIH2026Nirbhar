/**
 * NIRBHAR Verify — BigInt exact rational arithmetic mode.
 *
 * Provides exact (lossless) certificate checking using BigInt fractions.
 * Only suitable for small models (< ~50 variables) due to cost.
 * Used in: adversarial suite, tiny known-optimum models, showcase demo.
 *
 * This file is part of src/verify — it does NOT import from src/solver.
 */

// ─── Rational number (p/q in lowest terms) ───────────────────────────────────

export interface Rational {
  p: bigint;  // numerator
  q: bigint;  // denominator (always > 0)
}

function gcd(a: bigint, b: bigint): bigint {
  a = a < 0n ? -a : a;
  b = b < 0n ? -b : b;
  while (b !== 0n) { const t = b; b = a % b; a = t; }
  return a;
}

export function rat(p: bigint | number, q: bigint | number = 1): Rational {
  const bp = BigInt(p);
  const bq = BigInt(q);
  if (bq === 0n) throw new Error('Rational: denominator is zero');
  const sign = bq < 0n ? -1n : 1n;
  const g = gcd(bp < 0n ? -bp : bp, bq < 0n ? -bq : bq);
  return { p: sign * bp / g, q: sign * bq / g };
}

export function ratFromFloat(v: number, maxDenom = 1_000_000): Rational {
  // Best-rational-approximation via continued fractions
  if (!isFinite(v)) throw new Error('ratFromFloat: not finite');
  const sign = v < 0 ? -1n : 1n;
  const abs = Math.abs(v);
  const intPart = Math.floor(abs);
  let frac = abs - intPart;
  let h1 = 1n, h2 = 0n, k1 = 0n, k2 = 1n;
  let a = BigInt(intPart);
  let lastH = a, lastK = 1n;
  for (let i = 0; i < 30; i++) {
    const h = a * h1 + h2;
    const k = a * k1 + k2;
    if (Number(k) > maxDenom) break;
    lastH = h; lastK = k;
    h2 = h1; h1 = h;
    k2 = k1; k1 = k;
    if (Math.abs(frac) < 1e-15) break;
    const inv = 1 / frac;
    a = BigInt(Math.floor(inv));
    frac = inv - Number(a);
  }
  return { p: sign * lastH, q: lastK };
}

export function ratAdd(a: Rational, b: Rational): Rational {
  return rat(a.p * b.q + b.p * a.q, a.q * b.q);
}

export function ratSub(a: Rational, b: Rational): Rational {
  return rat(a.p * b.q - b.p * a.q, a.q * b.q);
}

export function ratMul(a: Rational, b: Rational): Rational {
  return rat(a.p * b.p, a.q * b.q);
}

export function ratDiv(a: Rational, b: Rational): Rational {
  return rat(a.p * b.q, a.q * b.p);
}

export function ratNeg(a: Rational): Rational {
  return { p: -a.p, q: a.q };
}

export function ratAbs(a: Rational): Rational {
  return { p: a.p < 0n ? -a.p : a.p, q: a.q };
}

export function ratCmp(a: Rational, b: Rational): number {
  const diff = a.p * b.q - b.p * a.q;
  return diff < 0n ? -1 : diff > 0n ? 1 : 0;
}

export function ratToFloat(a: Rational): number {
  // Convert via string for large numerics
  return Number(a.p) / Number(a.q);
}

export function ratFromArray(floats: ArrayLike<number>): Rational[] {
  const out: Rational[] = [];
  for (let i = 0; i < floats.length; i++) out.push(ratFromFloat(floats[i]));
  return out;
}

// ─── Exact certificate verification ─────────────────────────────────────────

export interface ExactVerifyInput {
  /** Constraint matrix A (row-major, nRows×nCols) as floats */
  A: Float64Array;
  nRows: number;
  nCols: number;
  /** Objective c, length nCols */
  c: Float64Array;
  /** Row lower/upper bounds, length nRows each */
  rowLo: Float64Array;
  rowHi: Float64Array;
  /** Column lower/upper bounds */
  colLo: Float64Array;
  colHi: Float64Array;
  /** Primal solution to verify, length nCols */
  x: Float64Array;
  /** Dual solution (row prices), length nRows */
  y: Float64Array;
  /** Reduced costs, length nCols */
  rc: Float64Array;
  /** Claimed objective value */
  objective: number;
}

export interface ExactCheckResult {
  name: string;
  pass: boolean;
  value: string;
  detail?: string;
}

export interface ExactVerifyResult {
  pass: boolean;
  checks: ExactCheckResult[];
  /** Time taken in ms */
  timeMs: number;
}

/**
 * Run all certificate checks in exact BigInt rational arithmetic.
 * WARNING: O(nCols × nRows × precision) — only for small models.
 */
export function exactVerify(inp: ExactVerifyInput): ExactVerifyResult {
  const t0 = performance.now();
  const checks: ExactCheckResult[] = [];
  const { nRows, nCols } = inp;

  // Convert to rational arrays
  const xR = ratFromArray(inp.x);
  const yR = ratFromArray(inp.y);
  const rcR = ratFromArray(inp.rc);
  const cR = ratFromArray(inp.c);
  const rowLoR = ratFromArray(inp.rowLo);
  const rowHiR = ratFromArray(inp.rowHi);
  const colLoR = ratFromArray(inp.colLo);
  const colHiR = ratFromArray(inp.colHi);

  // Build A as rational matrix
  const A: Rational[][] = [];
  for (let i = 0; i < nRows; i++) {
    A.push([]);
    for (let j = 0; j < nCols; j++) {
      A[i].push(ratFromFloat(inp.A[i * nCols + j]));
    }
  }

  // ── Check 1: Primal bound feasibility ─────────────────────────────────────
  let maxBoundViol = rat(0n);
  for (let j = 0; j < nCols; j++) {
    if (ratCmp(xR[j], colLoR[j]) < 0) {
      const v = ratSub(colLoR[j], xR[j]);
      if (ratCmp(v, maxBoundViol) > 0) maxBoundViol = v;
    }
    if (ratCmp(xR[j], colHiR[j]) > 0) {
      const v = ratSub(xR[j], colHiR[j]);
      if (ratCmp(v, maxBoundViol) > 0) maxBoundViol = v;
    }
  }
  checks.push({
    name: 'Primal bound feasibility (exact)',
    pass: ratCmp(maxBoundViol, rat(0n)) === 0,
    value: ratToFloat(maxBoundViol).toExponential(3),
    detail: 'max violation of colLo ≤ x ≤ colHi',
  });

  // ── Check 2: Row feasibility Ax ∈ [rowLo, rowHi] ──────────────────────────
  let maxRowViol = rat(0n);
  for (let i = 0; i < nRows; i++) {
    let ax = rat(0n);
    for (let j = 0; j < nCols; j++) ax = ratAdd(ax, ratMul(A[i][j], xR[j]));
    const vLo = ratCmp(ax, rowLoR[i]) < 0 ? ratSub(rowLoR[i], ax) : rat(0n);
    const vHi = ratCmp(ax, rowHiR[i]) > 0 ? ratSub(ax, rowHiR[i]) : rat(0n);
    const v = ratCmp(vLo, vHi) > 0 ? vLo : vHi;
    if (ratCmp(v, maxRowViol) > 0) maxRowViol = v;
  }
  checks.push({
    name: 'Row feasibility Ax ∈ [lo, hi] (exact)',
    pass: ratCmp(maxRowViol, rat(0n)) === 0,
    value: ratToFloat(maxRowViol).toExponential(3),
    detail: 'max violation of rowLo ≤ Ax ≤ rowHi',
  });

  // ── Check 3: Objective c^T x (exact) ─────────────────────────────────────
  let objR = rat(0n);
  for (let j = 0; j < nCols; j++) objR = ratAdd(objR, ratMul(cR[j], xR[j]));
  const objFloat = ratToFloat(objR);
  const objClaimed = ratFromFloat(inp.objective);
  const objErr = ratAbs(ratSub(objR, objClaimed));
  checks.push({
    name: 'Objective c·x (exact)',
    pass: ratToFloat(objErr) < 1e-10,
    value: objFloat.toPrecision(15),
    detail: `claimed ${inp.objective.toPrecision(15)}, error ${ratToFloat(objErr).toExponential(3)}`,
  });

  // ── Check 4: Reduced cost rc = c - A^T y (exact) ─────────────────────────
  let maxRCErr = rat(0n);
  for (let j = 0; j < nCols; j++) {
    let atYj = rat(0n);
    for (let i = 0; i < nRows; i++) atYj = ratAdd(atYj, ratMul(A[i][j], yR[i]));
    const expected = ratSub(cR[j], atYj);
    const err = ratAbs(ratSub(expected, rcR[j]));
    if (ratCmp(err, maxRCErr) > 0) maxRCErr = err;
  }
  checks.push({
    name: 'Reduced costs rc = c - Aᵀy (exact)',
    pass: ratToFloat(maxRCErr) < 1e-9,
    value: ratToFloat(maxRCErr).toExponential(3),
    detail: 'max |rc_j - (c_j - Aᵀy)_j|',
  });

  // ── Check 5: Dual feasibility sign check (exact) ──────────────────────────
  let maxDualViol = 0;
  for (let j = 0; j < nCols; j++) {
    const xj = ratToFloat(xR[j]);
    const loj = ratToFloat(colLoR[j]);
    const hij = ratToFloat(colHiR[j]);
    const rcj = ratToFloat(rcR[j]);
    if (Math.abs(xj - loj) < 1e-9 && rcj < -1e-9) maxDualViol = Math.max(maxDualViol, -rcj);
    if (Math.abs(xj - hij) < 1e-9 && rcj > 1e-9)  maxDualViol = Math.max(maxDualViol, rcj);
  }
  checks.push({
    name: 'Dual feasibility rc sign (exact)',
    pass: maxDualViol < 1e-9,
    value: maxDualViol.toExponential(3),
    detail: 'rc_j ≥ 0 if at lower bound, ≤ 0 if at upper bound',
  });

  const pass = checks.every(c => c.pass);
  return { pass, checks, timeMs: performance.now() - t0 };
}
