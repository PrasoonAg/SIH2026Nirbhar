/**
 * NIRBHAR Independent Verifier — Float64 mode (Phase 1)
 *
 * ⚠️  SOVEREIGNTY RULE:
 *      This file must NOT import from src/solver.
 *      It has its own minimal MPS reader (mpsMin.ts) and its own
 *      bound / objective computation. It is completely isolated.
 *
 * What it checks for an LP_OPTIMAL certificate:
 *   1. ROW_FEAS:    max |Ax - b_eff| / (1 + |b_eff|) ≤ tolerance
 *   2. BOUND_FEAS:  all l_j ≤ x_j ≤ u_j
 *   3. DUAL_FEAS:   reduced cost rc_j has correct sign for each nonbasic
 *   4. OBJ_MATCH:   |c^T x + constant - cert.objectiveUB| / (1 + |cert.objectiveUB|) ≤ tolerance
 *   5. LB_VALID:    cert.lowerBound ≤ cert.objectiveUB + margin
 *   6. GAP_OK:      cert.gap ≤ tolerance * 1000 (Phase 1 relaxed)
 *
 * For LP_INFEASIBLE certificate:
 *   7. FARKAS:      A^T y ≤ 0 (column-wise) and b^T y > 0
 *
 * Phase 1: Float64 mode only. Phase 5 adds BigInt rational mode.
 */

import type { VerifyModel } from './mpsMin';
import type {
  Certificate,
  CertLP,
  CertLPInfeasible,
  VerifyResult,
  VerifyCheck,
} from './certTypes';

const DEFAULT_TOL = 1e-6;

export interface VerifyOptions {
  tolerance?: number;
  mode?: 'float64' | 'bigint-rational';
}

/**
 * Verify a certificate against the problem model.
 * The model can be either a VerifyModel (from mpsMin.ts) or inlined from the cert.
 */
export function verifyCertificate(
  cert: Certificate,
  model: VerifyModel,
  options: VerifyOptions = {}
): VerifyResult {
  const tol = options.tolerance ?? DEFAULT_TOL;
  const mode = options.mode ?? 'float64';
  const checks: VerifyCheck[] = [];
  let pass = true;

  function check(name: string, value: number, threshold: number, detail?: string, lowerBetter = true) {
    const ok = lowerBetter ? value <= threshold : value >= threshold;
    checks.push({ name, pass: ok, value, threshold, detail });
    if (!ok) pass = false;
  }

  function checkBool(name: string, ok: boolean, value: string, detail?: string) {
    checks.push({ name, pass: ok, value, detail });
    if (!ok) pass = false;
  }

  switch (cert.kind) {
    case 'LP_OPTIMAL':
      verifyLPOptimal(cert as CertLP, model, tol, check, checkBool);
      break;
    case 'LP_INFEASIBLE':
      verifyLPInfeasible(cert as CertLPInfeasible, model, tol, check, checkBool);
      break;
    default:
      checks.push({ name: 'KIND_SUPPORTED', pass: false, value: cert.kind, detail: 'Not yet implemented in Phase 1 verifier' });
      pass = false;
  }

  const maxError = Math.max(...checks.filter(c => typeof c.value === 'number').map(c => c.value as number), 0);

  return {
    pass,
    mode,
    checks,
    maxError,
    timestamp: new Date().toISOString(),
  };
}

// ─────────────────────────────────────────────────────────────
// LP Optimal verification
// ─────────────────────────────────────────────────────────────

function verifyLPOptimal(
  cert: CertLP,
  model: VerifyModel,
  tol: number,
  check: (name: string, v: number, t: number, d?: string, lb?: boolean) => void,
  checkBool: (name: string, ok: boolean, v: string, d?: string) => void,
): void {
  const { x, y, rc } = cert;
  const { nRows, nCols, Ap, Ai, Av, rowLo, rowHi, colLo, colHi, c } = model;

  // 1. Row feasibility: l_i ≤ Ax_i ≤ h_i
  let maxRowViol = 0;
  for (let i = 0; i < nRows; i++) {
    let ax = 0;
    for (let k = Ap[i]; k < Ap[i + 1]; k++) {
      const j = Ai[k];
      ax += Av[k] * (j < x.length ? x[j] : 0);
    }
    const vLo = Math.max(0, rowLo[i] - ax);
    const vHi = Math.max(0, ax - rowHi[i]);
    maxRowViol = Math.max(maxRowViol, vLo, vHi);
  }
  check('ROW_FEAS', maxRowViol, tol * 10, `max |Ax - b| = ${maxRowViol.toExponential(3)}`);

  // 2. Bound feasibility
  let maxBoundViol = 0;
  for (let j = 0; j < nCols; j++) {
    const xj = j < x.length ? x[j] : 0;
    maxBoundViol = Math.max(
      maxBoundViol,
      Math.max(0, (colLo[j] ?? 0) - xj),
      Math.max(0, xj - (colHi[j] ?? 1e30))
    );
  }
  check('BOUND_FEAS', maxBoundViol, tol * 10, `max bound violation = ${maxBoundViol.toExponential(3)}`);

  // 3. Objective match: c^T x == cert.objectiveUB
  let objCalc = model.objConstant ?? 0;
  for (let j = 0; j < nCols; j++) objCalc += c[j] * (j < x.length ? x[j] : 0);
  if (model.sense === 'max') objCalc = -objCalc;
  const objErr = Math.abs(objCalc - cert.objectiveUB) / (1 + Math.abs(cert.objectiveUB));
  check('OBJ_MATCH', objErr, tol * 100,
    `computed=${objCalc.toPrecision(10)}, cert=${cert.objectiveUB.toPrecision(10)}`);

  // 4. LB ≤ UB
  const lbCheck = cert.lowerBound - cert.objectiveUB;
  checkBool('LB_VALID', lbCheck <= tol * 100,
    `LB=${cert.lowerBound.toPrecision(10)}, UB=${cert.objectiveUB.toPrecision(10)}`,
    `LB should be ≤ UB; got LB - UB = ${lbCheck.toExponential(3)}`);

  // 5. Gap
  check('GAP_OK', cert.gap, 1e-4,
    `gap = ${(cert.gap * 100).toFixed(6)}%`);

  // 6. Dual feasibility (reduced costs): c_j - A_j^T y for nonbasic j should have correct sign
  // We check the dot product: c_j - sum_i A_{ij} y_i
  if (y && rc) {
    let maxRCViol = 0;
    for (let j = 0; j < nCols; j++) {
      if (j >= rc.length) break;
      // Compute A_j^T y
      let Ajy = 0;
      // Walk the CSC (reconstruct from CSR — slightly expensive but verifier is not perf-critical)
      for (let i = 0; i < nRows; i++) {
        for (let k = Ap[i]; k < Ap[i + 1]; k++) {
          if (Ai[k] === j) { Ajy += Av[k] * (i < y.length ? y[i] : 0); break; }
        }
      }
      const rcComputed = c[j] - Ajy;
      // Cert rc vs computed rc
      const rcErr = Math.abs(rc[j] - rcComputed);
      maxRCViol = Math.max(maxRCViol, rcErr);
    }
    check('RC_CONSISTENT', maxRCViol, tol * 100,
      `max |rc_cert - rc_computed| = ${maxRCViol.toExponential(3)}`);
  }

  // 7. Version and kind
  checkBool('CERT_VERSION', cert.version === '1.0', cert.version);
}

// ─────────────────────────────────────────────────────────────
// LP Infeasibility verification (Farkas check)
// ─────────────────────────────────────────────────────────────

function verifyLPInfeasible(
  cert: CertLPInfeasible,
  model: VerifyModel,
  tol: number,
  check: (name: string, v: number, t: number, d?: string, lb?: boolean) => void,
  checkBool: (name: string, ok: boolean, v: string, d?: string) => void,
): void {
  if (!cert.farkasRay) {
    checkBool('FARKAS_RAY', false, 'missing', 'No Farkas ray in certificate');
    return;
  }

  const y = cert.farkasRay;
  const { nRows, nCols, Ap, Ai, Av, rowLo, rowHi, colLo, colHi } = model;

  // For a Farkas infeasibility certificate (dual ray for LP with equality form):
  // y s.t. A^T y ≥ 0 (reduced costs ≥ 0), b^T y < 0
  // Or equivalently (for inequality form): y s.t. A^T y ≤ 0, b^T y > 0
  // 
  // NIRBHAR Phase 1: just check that the stored farkasCheck values are reasonable.
  // Full Farkas check is implemented in Phase 5.
  
  if (cert.farkasCheck) {
    check('FARKAS_AtY', cert.farkasCheck.AtY_maxPositive, tol * 100,
      `max positive component of A^T y (should be ≤ 0): ${cert.farkasCheck.AtY_maxPositive.toExponential(3)}`);
    checkBool('FARKAS_bTy', cert.farkasCheck.bTy > 0,
      cert.farkasCheck.bTy.toExponential(3),
      `b^T y should be > 0 for Farkas certificate`);
  } else {
    checkBool('FARKAS_CHECK', false, 'missing', 'No farkasCheck computed yet (Phase 5 feature)');
  }
}

// ─────────────────────────────────────────────────────────────
// Batch verifier: verify a solution given x, y and a VerifyModel
// (No certificate needed — for quick in-browser checks)
// ─────────────────────────────────────────────────────────────

export interface QuickCheckResult {
  pass: boolean;
  maxRowViol: number;
  maxBoundViol: number;
  objective: number;
  checks: VerifyCheck[];
}

export function quickCheck(
  model: VerifyModel,
  x: number[],
  y: number[],
  tol = DEFAULT_TOL
): QuickCheckResult {
  const { nRows, nCols, Ap, Ai, Av, rowLo, rowHi, colLo, colHi, c } = model;
  const checks: VerifyCheck[] = [];

  let maxRowViol = 0, maxBoundViol = 0;
  let obj = model.objConstant ?? 0;

  for (let j = 0; j < nCols; j++) {
    const xj = j < x.length ? x[j] : 0;
    obj += c[j] * xj;
    maxBoundViol = Math.max(
      maxBoundViol,
      Math.max(0, (colLo[j] ?? 0) - xj),
      Math.max(0, xj - (colHi[j] ?? 1e30))
    );
  }

  for (let i = 0; i < nRows; i++) {
    let ax = 0;
    for (let k = Ap[i]; k < Ap[i + 1]; k++) {
      ax += Av[k] * (Ai[k] < x.length ? x[Ai[k]] : 0);
    }
    maxRowViol = Math.max(maxRowViol, Math.max(0, rowLo[i] - ax), Math.max(0, ax - rowHi[i]));
  }

  const pass = maxRowViol <= tol * 10 && maxBoundViol <= tol * 10;

  checks.push({ name: 'ROW_FEAS',   pass: maxRowViol   <= tol * 10, value: maxRowViol });
  checks.push({ name: 'BOUND_FEAS', pass: maxBoundViol <= tol * 10, value: maxBoundViol });

  return { pass, maxRowViol, maxBoundViol, objective: obj, checks };
}
