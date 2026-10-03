/**
 * NIRBHAR — Extended Cover Cuts (§6.9)
 */

import type { Model } from '../../io/model';
import { INF } from '../../io/model';
import type { CutRecord } from './types';

export interface CoverCutOptions {
  maxCuts?: number;
}

export function generateCoverCuts(
  model: Model,
  xLP: Float64Array,
  options: CoverCutOptions = {}
): CutRecord[] {
  const maxCuts = options.maxCuts ?? 6;
  const cuts: CutRecord[] = [];
  const n = model.nCols;
  const m = model.nRows;

  for (let i = 0; i < m && cuts.length < maxCuts; i++) {
    const rowUpper = model.rowHi[i];
    if (rowUpper >= INF || rowUpper <= 0) continue;

    const rowStart = model.A.Ap[i];
    const rowEnd = model.A.Ap[i + 1];

    const binCols: number[] = [];
    const binWeights: number[] = [];
    let allPosBin = true;

    for (let p = rowStart; p < rowEnd; p++) {
      const j = model.A.Ai[p];
      const val = model.A.Av[p];
      const isBinary = model.integrality[j] !== 0 && model.colLo[j] === 0 && model.colHi[j] === 1;

      if (isBinary && val > 0) {
        binCols.push(j);
        binWeights.push(val);
      } else if (val < 0) {
        allPosBin = false;
        break;
      }
    }

    if (!allPosBin || binCols.length < 2) continue;

    const indices = binCols.map((col, idx) => ({ col, weight: binWeights[idx], lp: xLP[col] }));
    indices.sort((a, b) => b.lp - a.lp);

    let sumWeight = 0;
    const coverCols: number[] = [];

    for (const item of indices) {
      coverCols.push(item.col);
      sumWeight += item.weight;
      if (sumWeight > rowUpper) {
        break;
      }
    }

    if (sumWeight > rowUpper && coverCols.length >= 2) {
      let lpSum = 0;
      for (const col of coverCols) lpSum += xLP[col];

      const maxAllowed = coverCols.length - 1;

      if (lpSum > maxAllowed + 1e-4) {
        const coeffs = new Float64Array(n);
        for (const col of coverCols) {
          coeffs[col] = -1.0;
        }
        const rhs = -maxAllowed;

        cuts.push({
          kind: 'COVER',
          coeffs,
          rhs,
          lpValue: -lpSum,
          sourceRow: i,
        });
      }
    }
  }

  return cuts;
}
