/**
 * NIRBHAR Certificate Schema
 * Every solve result carries a machine-checkable certificate.
 * 
 * For LP OPTIMAL:
 *   - Primal point x with Ax-b and bound residuals
 *   - Dual vector y, reduced costs rc
 *   - LB(y): safe lower bound ≤ true optimal
 *   - Gap = |UB - LB| / (1 + |UB|)
 * 
 * For LP INFEASIBLE:
 *   - Farkas ray: vector d s.t. A d ≤ 0 (or ≥), b^T d > 0 — certifies infeasibility
 *
 * For LP UNBOUNDED:
 *   - Recession direction: d s.t. Ad = 0, c^T d < 0, d ≥ 0 — certifies unboundedness
 *
 * Version: 1.0 (Phase 1)
 */

/** Problem class */
export type ProblemClass = 'LP' | 'MILP' | 'QP' | 'MIQP';

/** Certificate version */
export const CERT_VERSION = '1.0';

/** Residual block: how well does the solution satisfy the constraints? */
export interface ResidualBlock {
  maxRowViol: number;       // max |Ax - b| / (1 + |b|) row violation
  maxBoundViol: number;     // max bound violation for x
  maxDualViol: number;      // max reduced-cost sign violation
  infeasibilityNorm: number; // Frobenius norm of all violations
}

/** LP Optimal Certificate */
export interface CertLP {
  kind: 'LP_OPTIMAL';
  version: typeof CERT_VERSION;
  modelName: string;
  modelSHA256?: string;
  timestamp: string;        // ISO 8601
  engine: string;           // e.g. "dualSimplex-v1"
  
  // Numerical result
  objectiveUB: number;      // primal objective (= c^T x + constant)
  lowerBound: number;       // LB(y) ≤ true optimal (computed from dual y)
  gap: number;              // |UB - LB| / (1 + |UB|)
  
  // Solution arrays (sparse-ish: JSON-serialisable)
  x: number[];              // primal solution (nCols)
  y: number[];              // dual variables (nRows)
  rc: number[];             // reduced costs (nCols)
  
  // Residuals
  residuals: ResidualBlock;
  
  // Timing & iterations
  solveTimeMs: number;
  iterations: number;
  
  // Path taken
  solvePathComponents: string[];
  escalations: string[];
  
  // Human-readable explanation seed
  explanationHints: string[];
}

/** LP Infeasibility Certificate (Farkas ray) */
export interface CertLPInfeasible {
  kind: 'LP_INFEASIBLE';
  version: typeof CERT_VERSION;
  modelName: string;
  modelSHA256?: string;
  timestamp: string;
  engine: string;
  
  // Farkas ray: y s.t. A^T y ≤ 0, b^T y > 0 (dual ray)
  farkasRay?: number[];     // dual ray (nRows), null if not computed
  farkasCheck?: {           // verification values
    AtY_maxPositive: number;  // should be ≤ 0
    bTy: number;              // should be > 0
  };
  
  // IIS (irreducible infeasible subset) — computed separately
  iisRows?: string[];
  iisCols?: string[];
  
  solveTimeMs: number;
  iterations: number;
  escalations: string[];
}

/** LP Unboundedness Certificate */
export interface CertLPUnbounded {
  kind: 'LP_UNBOUNDED';
  version: typeof CERT_VERSION;
  modelName: string;
  modelSHA256?: string;
  timestamp: string;
  engine: string;
  
  // Recession direction: d s.t. Ad = 0, c^T d < 0, d ≥ 0
  recessionDir?: number[];  // nCols
  recessionCheck?: {
    cTd: number;            // should be < 0
    AdMax: number;          // should be ≈ 0
  };
  
  solveTimeMs: number;
  iterations: number;
  escalations: string[];
}

/** MILP Certificate (from Branch-and-Cut) */
export interface CertMILP {
  kind: 'MILP_OPTIMAL';
  version: typeof CERT_VERSION;
  modelName: string;
  modelSHA256?: string;
  timestamp: string;
  engine: string;
  
  objectiveUB: number;      // best incumbent
  objectiveLB: number;      // dual bound from B&C
  gap: number;
  
  x: number[];
  y: number[];              // LP relaxation duals at root
  
  // B&C statistics
  bcStats: {
    nodes: number;
    cutRounds: number;
    cutsAdded: number;
    branchingVar?: string;
  };
  
  // LP relaxation certificate at root
  lpRelaxCert?: CertLP;
  
  residuals: ResidualBlock;
  solveTimeMs: number;
  escalations: string[];
}

/** Union type for all certificate kinds */
export type Certificate = CertLP | CertLPInfeasible | CertLPUnbounded | CertMILP;

/** Verification result from the independent verifier */
export interface VerifyResult {
  pass: boolean;
  mode: 'float64' | 'bigint-rational';
  checks: VerifyCheck[];
  maxError: number;
  timestamp: string;
}

export interface VerifyCheck {
  name: string;
  pass: boolean;
  value: number | string;
  threshold?: number;
  detail?: string;
}

/** Serialise a certificate to JSON string */
export function serialiseCert(cert: Certificate): string {
  return JSON.stringify(cert, (_, v) => {
    // Round numbers to 15 significant digits to avoid spurious precision in JSON
    if (typeof v === 'number' && isFinite(v)) {
      return parseFloat(v.toPrecision(15));
    }
    return v;
  }, 2);
}

/** Parse a certificate from JSON string. Throws on invalid JSON. */
export function parseCert(json: string): Certificate {
  const obj = JSON.parse(json) as Certificate;
  if (!obj.kind || !obj.version) throw new Error('Not a valid NIRBHAR certificate');
  return obj;
}
