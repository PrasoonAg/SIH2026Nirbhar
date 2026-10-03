/**
 * NIRBHAR — Complemented Mixed-Integer Rounding (c-MIR) Cuts (§6.9)
 */

import type { Model } from '../../io/model';
import { INF } from '../../io/model';
import type { CutRecord } from './types';

export interface CMIROptions {
  maxCuts?: number;
  scales?: number[];
}

export function generateCMIRCuts(
  model: Model,
  xLP: Float64Array,
  options: CMIROptions = {}
): CutRecord[] {
  const maxCuts = options.maxCuts ?? 6;
  const scales = options.scales ?? [1.0, 0.5, 2.0, 0.25];
  const cuts: CutRecord[] = [];
  const n = model.nCols;
  const m = model.nRows;

  for (let i = 0; i < m && cuts.length < maxCuts; i++) {
    const rowUpper = model.rowHi[i];
    if (rowUpper >= INF) continue;

    const rowStart = model.A.Ap[i];
    const rowEnd = model.A.Ap[i + 1];
    let hasInt = false;
    for (let p = rowStart; p < rowEnd; p++) {
      if (model.integrality[model.A.Ai[p]] !== 0) {
        hasInt = true;
        break;
      }
    }
    if (!hasInt) continue;

    for (const delta of scales) {
      const bScaled = rowUpper * delta;
      const f = bScaled - Math.floor(bScaled);
      if (f < 0.05 || f > 0.95) continue;

      const coeffs = new Float64Array(n);

      for (let p = rowStart; p < rowEnd; p++) {
        const j = model.A.Ai[p];
        const aScaled = model.A.Av[p] * delta;
        const isInt = model.integrality[j] !== 0;

        if (isInt) {
          const fa = aScaled - Math.floor(aScaled);
          coeffs[j] = Math.floor(aScaled) + (fa > f ? (fa - f) / (1 - f) : 0);
        } else {
          coeffs[j] = aScaled < 0 ? aScaled / (1 - f) : 0;
        }
      }

      const rhs = -Math.floor(bScaled);
      for (let j = 0; j < n; j++) {
        coeffs[j] = -coeffs[j];
      }

      let lpVal = 0;
      for (let j = 0; j < n; j++) lpVal += coeffs[j] * xLP[j];

      if (lpVal < rhs - 1e-5) {
        cuts.push({
          kind: 'CMIR',
          coeffs,
          rhs,
          lpValue: lpVal,
          sourceRow: i,
        });
        break;
      }
    }
  }

  return cuts;
}
