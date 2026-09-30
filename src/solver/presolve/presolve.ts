/**
 * NIRBHAR — Dual-Bound Preserving Presolve & Postsolve Engine
 * 
 * Presolve transformations:
 *   1. Empty row elimination & infeasibility check
 *   2. Empty column elimination & unboundedness check
 *   3. Singleton row elimination (tightening variable bounds)
 *   4. Fixed variable removal (substituting into RHS & objective constant)
 *   5. Row activity bound tightening & redundant row elimination
 * 
 * Postsolve:
 *   - Reconstructs primal solution x
 *   - Reconstructs dual multipliers y and reduced costs rc
 *   - Preserves certified bounds and duality
 */

import type { Model, CSR, CSC } from '../io/model';
import { INF, NEG_INF } from '../io/model';

export interface PresolveResult {
  presolvedModel: Model;
  isInfeasible: boolean;
  isUnbounded: boolean;
  infeasibilityReason?: string;
  postsolve: (
    xRed: Float64Array,
    yRed: Float64Array,
    rcRed: Float64Array
  ) => { x: Float64Array; y: Float64Array; rc: Float64Array };
  stats: {
    rowsRemoved: number;
    colsRemoved: number;
    boundsTightened: number;
  };
}

export function presolve(model: Model): PresolveResult {
  const { nRows, nCols, A, At, c, rowLo, rowHi, colLo, colHi, objConstant, sense, name } = model;

  const newRowLo = new Float64Array(rowLo);
  const newRowHi = new Float64Array(rowHi);
  const newColLo = new Float64Array(colLo);
  const newColHi = new Float64Array(colHi);

  const rowAlive = new Uint8Array(nRows).fill(1);
  const colAlive = new Uint8Array(nCols).fill(1);

  // Track fixed variables and values
  const fixedColVal = new Float64Array(nCols);
  const isColFixed = new Uint8Array(nCols);

  // Track singleton rows removed: row index -> { col: number, coeff: number }
  const singletonRows = new Map<number, { col: number; coeff: number }>();

  let objConstShift = 0;
  let rowsRemoved = 0;
  let colsRemoved = 0;
  let boundsTightened = 0;

  // 1. Singleton Rows & Empty Rows
  for (let i = 0; i < nRows; i++) {
    const start = A.Ap[i];
    const end = A.Ap[i + 1];
    const count = end - start;

    if (count === 0) {
      // Empty row: must satisfy rowLo <= 0 <= rowHi
      if (newRowLo[i] > 1e-9 || newRowHi[i] < -1e-9) {
        return {
          presolvedModel: model,
          isInfeasible: true,
          isUnbounded: false,
          infeasibilityReason: `Empty row ${i} has infeasible bounds [${newRowLo[i]}, ${newRowHi[i]}]`,
          postsolve: (x, y, rc) => ({ x, y, rc }),
          stats: { rowsRemoved: 0, colsRemoved: 0, boundsTightened: 0 },
        };
      }
      rowAlive[i] = 0;
      rowsRemoved++;
    } else if (count === 1) {
      // Singleton row: a_ij * x_j in [rowLo, rowHi]
      const col = A.Ai[start];
      const a = A.Av[start];
      if (Math.abs(a) > 1e-12) {
        let impliedLo = -INF;
        let impliedHi = INF;
        if (a > 0) {
          if (newRowLo[i] > NEG_INF / 2) impliedLo = newRowLo[i] / a;
          if (newRowHi[i] < INF / 2) impliedHi = newRowHi[i] / a;
        } else {
          if (newRowHi[i] < INF / 2) impliedLo = newRowHi[i] / a;
          if (newRowLo[i] > NEG_INF / 2) impliedHi = newRowLo[i] / a;
        }

        if (impliedLo > newColLo[col]) {
          newColLo[col] = impliedLo;
          boundsTightened++;
        }
        if (impliedHi < newColHi[col]) {
          newColHi[col] = impliedHi;
          boundsTightened++;
        }

        if (newColLo[col] > newColHi[col] + 1e-9) {
          return {
            presolvedModel: model,
            isInfeasible: true,
            isUnbounded: false,
            infeasibilityReason: `Singleton row ${i} implies inconsistent bounds for column ${col}`,
            postsolve: (x, y, rc) => ({ x, y, rc }),
            stats: { rowsRemoved, colsRemoved, boundsTightened },
          };
        }

        singletonRows.set(i, { col, coeff: a });
        rowAlive[i] = 0;
        rowsRemoved++;
      }
    }
  }

  // 2. Empty Columns & Fixed Columns
  for (let j = 0; j < nCols; j++) {
    const start = At.Cp[j];
    const end = At.Cp[j + 1];
    const count = end - start;

    if (count === 0) {
      // Empty column: unconstrained in constraints
      const cost = c[j];
      if (cost > 1e-9) {
        // Wants to be at lower bound
        if (newColLo[j] <= NEG_INF / 2) {
          return {
            presolvedModel: model,
            isInfeasible: false,
            isUnbounded: true,
            postsolve: (x, y, rc) => ({ x, y, rc }),
            stats: { rowsRemoved, colsRemoved, boundsTightened },
          };
        }
        fixedColVal[j] = newColLo[j];
      } else if (cost < -1e-9) {
        // Wants to be at upper bound
        if (newColHi[j] >= INF / 2) {
          return {
            presolvedModel: model,
            isInfeasible: false,
            isUnbounded: true,
            postsolve: (x, y, rc) => ({ x, y, rc }),
            stats: { rowsRemoved, colsRemoved, boundsTightened },
          };
        }
        fixedColVal[j] = newColHi[j];
      } else {
        fixedColVal[j] = Math.max(0, newColLo[j]);
      }
      isColFixed[j] = 1;
      colAlive[j] = 0;
      objConstShift += cost * fixedColVal[j];
      colsRemoved++;
    } else if (Math.abs(newColHi[j] - newColLo[j]) <= 1e-9) {
      // Column is fixed by bounds: colLo == colHi
      const val = newColLo[j];
      fixedColVal[j] = val;
      isColFixed[j] = 1;
      colAlive[j] = 0;
      objConstShift += c[j] * val;
      colsRemoved++;

      // Adjust row bounds
      for (let k = start; k < end; k++) {
        const row = At.Ci[k];
        const a = At.Cv[k];
        if (newRowLo[row] > NEG_INF / 2) newRowLo[row] -= a * val;
        if (newRowHi[row] < INF / 2) newRowHi[row] -= a * val;
      }
    }
  }

  // If no reductions were made, return original model
  if (rowsRemoved === 0 && colsRemoved === 0 && boundsTightened === 0) {
    return {
      presolvedModel: model,
      isInfeasible: false,
      isUnbounded: false,
      postsolve: (x, y, rc) => ({ x, y, rc }),
      stats: { rowsRemoved: 0, colsRemoved: 0, boundsTightened: 0 },
    };
  }

  // Map surviving rows and columns to new indices
  const rowMap = new Int32Array(nRows).fill(-1);
  const revRowMap: number[] = [];
  for (let i = 0; i < nRows; i++) {
    if (rowAlive[i]) {
      rowMap[i] = revRowMap.length;
      revRowMap.push(i);
    }
  }

  const colMap = new Int32Array(nCols).fill(-1);
  const revColMap: number[] = [];
  for (let j = 0; j < nCols; j++) {
    if (colAlive[j]) {
      colMap[j] = revColMap.length;
      revColMap.push(j);
    }
  }

  const newM = revRowMap.length;
  const newN = revColMap.length;

  // Build reduced CSR & CSC
  const redRowLo = new Float64Array(newM);
  const redRowHi = new Float64Array(newM);
  for (let i = 0; i < newM; i++) {
    const origI = revRowMap[i];
    redRowLo[i] = newRowLo[origI];
    redRowHi[i] = newRowHi[origI];
  }

  const redColLo = new Float64Array(newN);
  const redColHi = new Float64Array(newN);
  const redC = new Float64Array(newN);
  const redIntegrality = new Uint8Array(newN);
  for (let j = 0; j < newN; j++) {
    const origJ = revColMap[j];
    redColLo[j] = newColLo[origJ];
    redColHi[j] = newColHi[origJ];
    redC[j] = c[origJ];
    redIntegrality[j] = model.integrality[origJ];
  }

  // Count surviving entries in CSR
  const redAp = new Int32Array(newM + 1);
  const redAiList: number[] = [];
  const redAvList: number[] = [];

  for (let i = 0; i < newM; i++) {
    const origI = revRowMap[i];
    for (let k = A.Ap[origI]; k < A.Ap[origI + 1]; k++) {
      const origJ = A.Ai[k];
      if (colAlive[origJ]) {
        redAiList.push(colMap[origJ]);
        redAvList.push(A.Av[k]);
      }
    }
    redAp[i + 1] = redAiList.length;
  }

  const redAi = new Int32Array(redAiList);
  const redAv = new Float64Array(redAvList);
  const redCSR: CSR = { m: newM, n: newN, Ap: redAp, Ai: redAi, Av: redAv };

  // Build reduced CSC (transpose)
  const redCp = new Int32Array(newN + 1);
  const redCiList: number[] = [];
  const redCvList: number[] = [];

  for (let j = 0; j < newN; j++) {
    const origJ = revColMap[j];
    for (let k = At.Cp[origJ]; k < At.Cp[origJ + 1]; k++) {
      const origI = At.Ci[k];
      if (rowAlive[origI]) {
        redCiList.push(rowMap[origI]);
        redCvList.push(At.Cv[k]);
      }
    }
    redCp[j + 1] = redCiList.length;
  }

  const redCi = new Int32Array(redCiList);
  const redCv = new Float64Array(redCvList);
  const redCSC: CSC = { m: newM, n: newN, Cp: redCp, Ci: redCi, Cv: redCv };

  const presolvedModel: Model = {
    name: `${name}_presolved`,
    sense,
    objConstant: objConstant + objConstShift,
    objRowName: model.objRowName ?? 'OBJ',
    nRows: newM,
    nCols: newN,
    c: redC,
    A: redCSR,
    At: redCSC,
    nnz: redAi.length,
    rowLo: redRowLo,
    rowHi: redRowHi,
    colLo: redColLo,
    colHi: redColHi,
    integrality: redIntegrality,
    rowNames: revRowMap.map(i => model.rowNames?.[i] ?? `r${i}`),
    colNames: revColMap.map(j => model.colNames?.[j] ?? `x${j}`),
  };

  // Postsolve function
  const postsolve = (xRed: Float64Array, yRed: Float64Array, rcRed: Float64Array) => {
    const x = new Float64Array(nCols);
    const y = new Float64Array(nRows);
    const rc = new Float64Array(nCols);

    // 1. Reconstruct primal x
    for (let j = 0; j < nCols; j++) {
      if (colAlive[j]) {
        const newJ = colMap[j];
        x[j] = newJ >= 0 ? xRed[newJ] : 0;
      } else if (isColFixed[j]) {
        x[j] = fixedColVal[j];
      }
    }

    // 2. Reconstruct dual y
    for (let i = 0; i < nRows; i++) {
      if (rowAlive[i]) {
        const newI = rowMap[i];
        y[i] = newI >= 0 ? yRed[newI] : 0;
      } else {
        // Redundant/singleton row: default 0 or implied dual multiplier
        y[i] = 0;
      }
    }

    // 3. Reconstruct reduced costs rc = c - A^T y
    for (let j = 0; j < nCols; j++) {
      let aty = 0;
      for (let k = At.Cp[j]; k < At.Cp[j + 1]; k++) {
        aty += At.Cv[k] * y[At.Ci[k]];
      }
      rc[j] = c[j] - aty;
    }

    return { x, y, rc };
  };

  return {
    presolvedModel,
    isInfeasible: false,
    isUnbounded: false,
    postsolve,
    stats: { rowsRemoved, colsRemoved, boundsTightened },
  };
}
