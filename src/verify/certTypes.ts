/**
 * NIRBHAR Verify — Local certificate type definitions.
 *
 * These types MIRROR src/solver/certificate/schema.ts exactly.
 * They are duplicated here so that src/verify has NO imports from src/solver.
 *
 * ⚠️  SOVEREIGNTY RULE: This file must not import from src/solver.
 *
 * If you modify schema.ts, also update this file accordingly.
 */

export type ProblemClass = 'LP' | 'MILP' | 'QP' | 'MIQP';

export const CERT_VERSION = '1.0' as const;

export interface ResidualBlock {
  maxRowViol: number;
  maxBoundViol: number;
  maxDualViol: number;
  infeasibilityNorm: number;
}

export interface CertLP {
  kind: 'LP_OPTIMAL';
  version: typeof CERT_VERSION;
  modelName: string;
  modelSHA256?: string;
  timestamp: string;
  engine: string;
  objectiveUB: number;
  lowerBound: number;
  gap: number;
  x: number[];
  y: number[];
  rc: number[];
  residuals: ResidualBlock;
  solveTimeMs: number;
  iterations: number;
  solvePathComponents: string[];
  escalations: string[];
  explanationHints: string[];
}

export interface CertLPInfeasible {
  kind: 'LP_INFEASIBLE';
  version: typeof CERT_VERSION;
  modelName: string;
  modelSHA256?: string;
  timestamp: string;
  engine: string;
  farkasRay?: number[];
  farkasCheck?: {
    AtY_maxPositive: number;
    bTy: number;
  };
  iisRows?: string[];
  iisCols?: string[];
  solveTimeMs: number;
  iterations: number;
  escalations: string[];
}

export interface CertLPUnbounded {
  kind: 'LP_UNBOUNDED';
  version: typeof CERT_VERSION;
  modelName: string;
  modelSHA256?: string;
  timestamp: string;
  engine: string;
  recessionDir?: number[];
  recessionCheck?: {
    cTd: number;
    AdMax: number;
  };
  solveTimeMs: number;
  iterations: number;
  escalations: string[];
}

export interface CertMILP {
  kind: 'MILP_OPTIMAL';
  version: typeof CERT_VERSION;
  modelName: string;
  modelSHA256?: string;
  timestamp: string;
  engine: string;
  objectiveUB: number;
  objectiveLB: number;
  gap: number;
  x: number[];
  y: number[];
  bcStats: {
    nodes: number;
    cutRounds: number;
    cutsAdded: number;
    branchingVar?: string;
  };
  lpRelaxCert?: CertLP;
  residuals: ResidualBlock;
  solveTimeMs: number;
  escalations: string[];
}

export type Certificate = CertLP | CertLPInfeasible | CertLPUnbounded | CertMILP;

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
