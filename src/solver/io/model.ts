/**
 * NIRBHAR Showcase — Immutable Model type
 * Represents an LP / MILP / QP / MIQP in the NIRBHAR internal format.
 * CSR storage for A; CSC also maintained for column pricing.
 */

export const INF = 1e30;   // "infinity" sentinel — use for unbounded bounds
export const NEG_INF = -1e30;

/** Row type as parsed from MPS */
export type RowType = 'N' | 'L' | 'G' | 'E';

/** Variable integrality */
export const CONTINUOUS = 0;
export const INTEGER    = 1;
export const BINARY     = 2;

/** Sparse matrix in CSR format */
export interface CSR {
  m: number;
  n: number;
  Ap: Int32Array;    // row pointers, length m+1
  Ai: Int32Array;    // column indices, length nnz
  Av: Float64Array;  // values, length nnz
}

/** Sparse matrix in CSC format */
export interface CSC {
  m: number;
  n: number;
  Cp: Int32Array;    // col pointers, length n+1
  Ci: Int32Array;    // row indices, length nnz
  Cv: Float64Array;  // values, length nnz
}

/** Optional quadratic objective matrix (upper triangular, symmetric) */
export interface QMatrix {
  Qp: Int32Array;    // col pointers (CSC upper tri), length n+1
  Qi: Int32Array;    // row indices
  Qv: Float64Array;  // values (each off-diagonal stored once)
  isDiagonal: boolean;
  isPosSemiDef: boolean | null;  // null = not checked
}

/** Immutable NIRBHAR model */
export interface Model {
  readonly name: string;
  readonly sense: 'min' | 'max';
  readonly objConstant: number;   // constant added to objective

  // Dimensions (excluding objective row)
  readonly nRows: number;         // m
  readonly nCols: number;         // n

  // Objective (length n)
  readonly c: Float64Array;

  // Constraint matrix
  readonly A: CSR;
  readonly At: CSC;  // transpose, for column pricing
  readonly nnz: number;

  // Row bounds: rowLo[i] ≤ Ax[i] ≤ rowHi[i]
  // For E rows: rowLo[i] == rowHi[i]
  // For L rows: rowLo[i] = -INF, rowHi[i] = rhs
  // For G rows: rowLo[i] = rhs, rowHi[i] = INF
  readonly rowLo: Float64Array;
  readonly rowHi: Float64Array;

  // Column bounds
  readonly colLo: Float64Array;   // default 0
  readonly colHi: Float64Array;   // default INF

  // Integrality: CONTINUOUS | INTEGER | BINARY
  readonly integrality: Uint8Array;

  // Names
  readonly rowNames: string[];
  readonly colNames: string[];
  readonly objRowName: string;

  // Optional quadratic term ½ x^T Q x
  readonly Q?: QMatrix;

  // Metadata
  readonly sha256?: string;
  readonly sourceText?: string;
  readonly parseErrors?: string[];
}

/** Mutable builder, freeze to get Model */
export class ModelBuilder {
  name = 'untitled';
  sense: 'min' | 'max' = 'min';
  objConstant = 0;
  objRowName = 'OBJ';

  private rows: Array<{ lo: number; hi: number; name: string; type: RowType }> = [];
  private cols: Array<{ lo: number; hi: number; integ: number; name: string }> = [];
  private entries: Array<{ row: number; col: number; val: number }> = [];
  private cObj: Map<number, number> = new Map();
  private Q?: QMatrix;
  sha256?: string;
  sourceText?: string;
  parseErrors: string[] = [];

  addRow(name: string, type: RowType): number {
    const idx = this.rows.length;
    let lo: number, hi: number;
    switch (type) {
      case 'L': lo = NEG_INF; hi = 0; break;
      case 'G': lo = 0; hi = INF; break;
      case 'E': lo = 0; hi = 0; break;
      default:  lo = NEG_INF; hi = INF; break;
    }
    this.rows.push({ lo, hi, name, type });
    return idx;
  }

  addCol(name: string): number {
    const idx = this.cols.length;
    this.cols.push({ lo: 0, hi: INF, integ: CONTINUOUS, name });
    return idx;
  }

  setEntry(row: number, col: number, val: number) {
    this.entries.push({ row, col, val });
  }

  setObjCoeff(col: number, val: number) {
    this.cObj.set(col, (this.cObj.get(col) ?? 0) + val);
  }

  setRhs(rowIdx: number, rhs: number, type: RowType) {
    const r = this.rows[rowIdx];
    if (!r) return;
    switch (type) {
      case 'L': r.lo = NEG_INF; r.hi = rhs; break;
      case 'G': r.lo = rhs; r.hi = INF; break;
      case 'E': r.lo = rhs; r.hi = rhs; break;
    }
  }

  applyRange(rowIdx: number, range: number, type: RowType) {
    const r = this.rows[rowIdx];
    if (!r) return;
    const absRange = Math.abs(range);
    if (type === 'L') {
      // rhs - |range| ≤ a^T x ≤ rhs
      r.lo = r.hi - absRange;
    } else if (type === 'G') {
      // rhs ≤ a^T x ≤ rhs + |range|
      r.hi = r.lo + absRange;
    } else if (type === 'E') {
      // range > 0: rhs ≤ a^T x ≤ rhs + range
      // range < 0: rhs + range ≤ a^T x ≤ rhs
      if (range >= 0) { r.hi = r.lo + range; }
      else { const old = r.lo; r.lo = old + range; r.hi = old; }
    }
  }

  setColBound(col: number, type: string, val: number) {
    const c = this.cols[col];
    if (!c) return;
    switch (type) {
      case 'LO': c.lo = val; break;
      case 'UP': c.hi = val; break;
      case 'FX': c.lo = val; c.hi = val; break;
      case 'FR': c.lo = NEG_INF; c.hi = INF; break;
      case 'MI': c.lo = NEG_INF; break;
      case 'PL': c.hi = INF; break;
      case 'BV': c.lo = 0; c.hi = 1; c.integ = BINARY; break;
      case 'LI': c.lo = val; c.integ = INTEGER; break;
      case 'UI': c.hi = val; c.integ = INTEGER; break;
    }
  }

  setQ(Q: QMatrix) { this.Q = Q; }

  build(): Model {
    const m = this.rows.length;
    const n = this.cols.length;

    // Build CSR for A (excluding objective row which was already removed)
    const entriesPerRow: Array<Array<{ col: number; val: number }>> = Array.from({ length: m }, () => []);
    for (const e of this.entries) {
      if (e.row >= 0 && e.row < m && e.col >= 0 && e.col < n) {
        entriesPerRow[e.row].push({ col: e.col, val: e.val });
      }
    }

    // Sort and sum duplicates
    const nnzEstimate = this.entries.length;
    const Ap = new Int32Array(m + 1);
    const aiArr: number[] = [];
    const avArr: number[] = [];

    for (let i = 0; i < m; i++) {
      const rowEntries = entriesPerRow[i];
      rowEntries.sort((a, b) => a.col - b.col);
      // Merge duplicates
      const merged: { col: number; val: number }[] = [];
      for (const e of rowEntries) {
        if (merged.length > 0 && merged[merged.length - 1].col === e.col) {
          merged[merged.length - 1].val += e.val;
        } else {
          merged.push({ ...e });
        }
      }
      for (const e of merged) {
        if (e.val !== 0) {
          aiArr.push(e.col);
          avArr.push(e.val);
        }
      }
      Ap[i + 1] = aiArr.length;
    }
    Ap[0] = 0;

    const nnz = aiArr.length;
    const Ai = new Int32Array(aiArr);
    const Av = new Float64Array(avArr);

    // Build CSC (transpose)
    const colCounts = new Int32Array(n);
    for (let k = 0; k < nnz; k++) colCounts[Ai[k]]++;
    const Cp = new Int32Array(n + 1);
    for (let j = 0; j < n; j++) Cp[j + 1] = Cp[j] + colCounts[j];
    const Ci = new Int32Array(nnz);
    const Cv = new Float64Array(nnz);
    const colPos = Cp.slice(0, n);
    for (let i = 0; i < m; i++) {
      for (let k = Ap[i]; k < Ap[i + 1]; k++) {
        const j = Ai[k];
        const pos = colPos[j]++;
        Ci[pos] = i;
        Cv[pos] = Av[k];
      }
    }

    // Objective
    const c = new Float64Array(n);
    for (const [col, val] of this.cObj) {
      if (col >= 0 && col < n) c[col] = val;
    }

    // Row bounds
    const rowLo = new Float64Array(m);
    const rowHi = new Float64Array(m);
    for (let i = 0; i < m; i++) {
      rowLo[i] = this.rows[i].lo;
      rowHi[i] = this.rows[i].hi;
    }

    // Column bounds
    const colLo = new Float64Array(n);
    const colHi = new Float64Array(n);
    const integrality = new Uint8Array(n);
    for (let j = 0; j < n; j++) {
      colLo[j] = this.cols[j].lo;
      colHi[j] = this.cols[j].hi;
      integrality[j] = this.cols[j].integ;
    }

    return Object.freeze({
      name: this.name,
      sense: this.sense,
      objConstant: this.objConstant,
      nRows: m,
      nCols: n,
      c,
      A: { m, n, Ap, Ai, Av },
      At: { m: n, n: m, Cp, Ci, Cv },
      nnz,
      rowLo,
      rowHi,
      colLo,
      colHi,
      integrality,
      rowNames: this.rows.map(r => r.name),
      colNames: this.cols.map(c => c.name),
      objRowName: this.objRowName,
      Q: this.Q,
      sha256: this.sha256,
      sourceText: this.sourceText,
      parseErrors: [...this.parseErrors],
    } as Model);
  }
}

/** Deep clone an immutable Model into a new mutable or modified Model */
export function cloneModel(model: Model): Model {
  return {
    ...model,
    c: new Float64Array(model.c),
    colLo: new Float64Array(model.colLo),
    colHi: new Float64Array(model.colHi),
    rowLo: new Float64Array(model.rowLo),
    rowHi: new Float64Array(model.rowHi),
    integrality: new Uint8Array(model.integrality),
    rowNames: [...model.rowNames],
    colNames: [...model.colNames],
    A: {
      m: model.A.m,
      n: model.A.n,
      Ap: new Int32Array(model.A.Ap),
      Ai: new Int32Array(model.A.Ai),
      Av: new Float64Array(model.A.Av),
    },
    At: {
      m: model.At.m,
      n: model.At.n,
      Cp: new Int32Array(model.At.Cp),
      Ci: new Int32Array(model.At.Ci),
      Cv: new Float64Array(model.At.Cv),
    },
  };
}

/** Compute row-wise Ax and check bounds — returns max violation */
export function computeRowViolation(model: Model, x: Float64Array): number {
  const { A, rowLo, rowHi } = model;
  let maxViol = 0;
  for (let i = 0; i < model.nRows; i++) {
    let ax = 0;
    for (let k = A.Ap[i]; k < A.Ap[i + 1]; k++) ax += A.Av[k] * x[A.Ai[k]];
    const vLo = Math.max(0, rowLo[i] - ax);
    const vHi = Math.max(0, ax - rowHi[i]);
    maxViol = Math.max(maxViol, vLo, vHi);
  }
  return maxViol;
}

/** Compute bound violation */
export function computeBoundViolation(model: Model, x: Float64Array): number {
  let maxViol = 0;
  for (let j = 0; j < model.nCols; j++) {
    maxViol = Math.max(maxViol,
      Math.max(0, model.colLo[j] - x[j]),
      Math.max(0, x[j] - model.colHi[j])
    );
  }
  return maxViol;
}

/** Compute objective value c^T x (+ objConstant, + ½ x^T Q x if QP) */
export function computeObjective(model: Model, x: Float64Array): number {
  let obj = model.objConstant;
  for (let j = 0; j < model.nCols; j++) obj += model.c[j] * x[j];
  if (model.Q) {
    const { Qp, Qi, Qv } = model.Q;
    for (let j = 0; j < model.nCols; j++) {
      for (let k = Qp[j]; k < Qp[j + 1]; k++) {
        const i = Qi[k];
        const v = 0.5 * Qv[k] * x[i] * x[j];
        obj += (i === j) ? v : 2 * v;  // symmetric: each off-diag stored once
      }
    }
  }
  if (model.sense === 'max') obj = -obj;
  return obj;
}
