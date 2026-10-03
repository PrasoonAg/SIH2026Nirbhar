/**
 * NIRBHAR — Gomory Mixed-Integer (GMI) Cuts (§6.9)
 */

import type { Model } from '../../io/model';
import { INF } from '../../io/model';
import type { CutRecord } from './types';

export interface GMICutOptions {
  minFractionality?: number;
  maxCuts?: number;
}

export function generateGMICuts(
  model: Model,
  xLP: Float64Array,
  options: GMICutOptions = {}
): CutRecord[] {
  const minFrac = options.minFractionality ?? 0.05;
  const maxCuts = options.maxCuts ?? 10;
  const cuts: CutRecord[] = [];
  const n = model.nCols;
  const m = model.nRows;

  for (let j = 0; j < n; j++) {
    if (model.integrality[j] === 0) continue;

    const val = xLP[j];
    const floorVal = Math.floor(val);
    const frac = val - floorVal;

    if (frac < minFrac || frac > 1 - minFrac) continue;

    const coeffs = new Float64Array(n);
    let derived = false;
    let sourceRowIndex = -1;

    for (let i = 0; i < m; i++) {
      const rowStart = model.A.Ap[i];
      const rowEnd = model.A.Ap[i + 1];
      let hasVar = false;
      let a_ij = 0;

      for (let p = rowStart; p < rowEnd; p++) {
        if (model.A.Ai[p] === j) {
          hasVar = true;
          a_ij = model.A.Av[p];
          break;
        }
      }

      if (hasVar && Math.abs(a_ij) > 1e-4) {
        sourceRowIndex = i;
        const b = model.rowHi[i] < INF ? model.rowHi[i] : model.rowLo[i];
        if (!isFinite(b)) continue;

        const rhsDiv = b / Math.abs(a_ij);
        const f0 = rhsDiv - Math.floor(rhsDiv);
        if (f0 < 0.02 || f0 > 0.98) continue;
        let cutRhs = Math.floor(rhsDiv);

        for (let p = rowStart; p < rowEnd; p++) {
          const col = model.A.Ai[p];
          const a = model.A.Av[p] / Math.abs(a_ij);
          const isInt = model.integrality[col] !== 0;

          if (isInt) {
            const fa = a - Math.floor(a);
            coeffs[col] = Math.floor(a) + (fa > f0 ? (fa - f0) / (1 - f0) : 0);
          } else {
            coeffs[col] = a < 0 ? a / (1 - f0) : 0;
          }
        }

        for (let k = 0; k < n; k++) coeffs[k] = -coeffs[k];
        cutRhs = -cutRhs;

        let lpVal = 0;
        for (let k = 0; k < n; k++) lpVal += coeffs[k] * xLP[k];

        if (lpVal < cutRhs - 1e-6) {
          cuts.push({
            kind: 'GMI',
            coeffs,
            rhs: cutRhs,
            lpValue: lpVal,
            sourceRow: sourceRowIndex,
          });
          derived = true;
          break;
        }
      }
    }

    if (cuts.length >= maxCuts) break;
  }

  return cuts;
}
