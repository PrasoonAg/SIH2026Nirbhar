/**
 * NIRBHAR — Branching Strategies (§6.8)
 */

import type { Model } from '../io/model';

export type BranchingStrategy = 'most-fractional' | 'pseudocost' | 'reliability';

export interface PseudocostData {
  upCost: Float64Array;
  downCost: Float64Array;
  upCount: Int32Array;
  downCount: Int32Array;
}

export function initPseudocosts(nCols: number): PseudocostData {
  return {
    upCost: new Float64Array(nCols).fill(1.0),
    downCost: new Float64Array(nCols).fill(1.0),
    upCount: new Int32Array(nCols),
    downCount: new Int32Array(nCols),
  };
}

export interface BranchDecision {
  varIndex: number;
  varName: string;
  fractionalValue: number;
  branchPoint: number;
}

export function selectBranchingVariable(
  model: Model,
  x: Float64Array,
  strategy: BranchingStrategy = 'most-fractional',
  pseudocosts?: PseudocostData
): BranchDecision | null {
  const n = model.nCols;
  let bestIdx = -1;
  let bestScore = -Infinity;
  let bestFrac = 0;

  for (let j = 0; j < n; j++) {
    if (model.integrality[j] === 0) continue;

    const val = x[j];
    const floorVal = Math.floor(val);
    const frac = val - floorVal;

    if (frac < 1e-4 || frac > 1 - 1e-4) continue;

    let score = 0;
    if (strategy === 'most-fractional') {
      score = 0.5 - Math.abs(frac - 0.5);
    } else if (strategy === 'pseudocost' && pseudocosts) {
      const upScore = (1 - frac) * pseudocosts.upCost[j];
      const downScore = frac * pseudocosts.downCost[j];
      score = Math.max(1e-4, downScore) * Math.max(1e-4, upScore);
    } else if (strategy === 'reliability' && pseudocosts) {
      const count = Math.min(pseudocosts.upCount[j], pseudocosts.downCount[j]);
      if (count < 4) {
        score = 100.0 + (0.5 - Math.abs(frac - 0.5));
      } else {
        const upScore = (1 - frac) * pseudocosts.upCost[j];
        const downScore = frac * pseudocosts.downCost[j];
        score = Math.max(1e-4, downScore) * Math.max(1e-4, upScore);
      }
    } else {
      score = 0.5 - Math.abs(frac - 0.5);
    }

    if (score > bestScore) {
      bestScore = score;
      bestIdx = j;
      bestFrac = val;
    }
  }

  if (bestIdx === -1) return null;

  return {
    varIndex: bestIdx,
    varName: model.colNames[bestIdx] || `x${bestIdx + 1}`,
    fractionalValue: bestFrac,
    branchPoint: Math.floor(bestFrac),
  };
}
