/**
 * NIRBHAR — Node Selection (§6.8)
 * 
 * Supports:
 *   - 'best-bound': explores node with the lowest lower bound (minimization)
 *   - 'depth-first' / 'plunging': explores deepest child first to find incumbents rapidly
 *   - 'best-estimate': combines lower bound and expected integer degradation
 */

export interface BNode {
  id: number;
  parentId: number | null;
  depth: number;
  lowerBound: number;
  upperBound?: number;
  lpObjective: number;
  colLower: Float64Array;
  colUpper: Float64Array;
  status: 'open' | 'pruned' | 'integer' | 'infeasible';
  branchVarName?: string;
  branchDir?: 'left' | 'right';
  branchBound?: number;
  x?: Float64Array;
}

export type NodeSelectionStrategy = 'best-bound' | 'depth-first' | 'best-estimate';

/**
 * Select the next node to process from the open node pool
 */
export function selectNextNode(
  openNodes: BNode[],
  strategy: NodeSelectionStrategy = 'best-bound'
): { node: BNode; index: number } | null {
  if (openNodes.length === 0) return null;

  let bestIdx = 0;

  if (strategy === 'best-bound') {
    // Pick node with lowest lower bound
    let minBound = openNodes[0].lowerBound;
    for (let i = 1; i < openNodes.length; i++) {
      if (openNodes[i].lowerBound < minBound) {
        minBound = openNodes[i].lowerBound;
        bestIdx = i;
      }
    }
  } else if (strategy === 'depth-first') {
    // Plunging: pick deepest node; tie-break on lower bound
    let maxDepth = openNodes[0].depth;
    for (let i = 1; i < openNodes.length; i++) {
      if (
        openNodes[i].depth > maxDepth ||
        (openNodes[i].depth === maxDepth && openNodes[i].lowerBound < openNodes[bestIdx].lowerBound)
      ) {
        maxDepth = openNodes[i].depth;
        bestIdx = i;
      }
    }
  } else {
    // Best-estimate: score = lowerBound + 0.1 * depth
    let bestScore = openNodes[0].lowerBound;
    for (let i = 1; i < openNodes.length; i++) {
      const score = openNodes[i].lowerBound + 0.05 * openNodes[i].depth;
      if (score < bestScore) {
        bestScore = score;
        bestIdx = i;
      }
    }
  }

  return { node: openNodes[bestIdx], index: bestIdx };
}
