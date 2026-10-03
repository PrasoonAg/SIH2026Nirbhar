/**
 * NIRBHAR — Plug-in Registry & Extension Interfaces (§8, Feature F25)
 * 
 * Implements the 8 core extension interfaces:
 *   1. Engine          — Core solver algorithms (Simplex, IPM, HPR, etc.)
 *   2. Presolver       — Problem reduction routines
 *   3. Propagator      — Bound tightening and domain reduction
 *   4. BranchingRule   — Variable selection in branch-and-cut
 *   5. NodeSelector    — Search tree node exploration strategy
 *   6. Heuristic       — Primal incumbent discovery methods
 *   7. CutGenerator    — Valid inequality separation routines
 *   8. ModelClass      — Model classifications (LP, MILP, QP, MIQP, NLP)
 */

import type { Model } from '../io/model';
import type { EngineResult } from '../lp/dualSimplex';

// ─── 1. Engine Interface ──────────────────────────────────────────
export interface EnginePlugin {
  name: string;
  category: 'exact-basic' | 'interior-point' | 'first-order' | 'hybrid';
  supportsModelClass: (modelClass: string) => boolean;
  solve: (model: Model, options?: Record<string, any>) => Promise<EngineResult> | EngineResult;
}

// ─── 2. Presolver Interface ───────────────────────────────────────
export interface PresolveReductionResult {
  modifiedModel: Model;
  rowsRemoved: number;
  colsRemoved: number;
  postsolveData?: any;
}

export interface PresolverPlugin {
  name: string;
  apply: (model: Model) => PresolveReductionResult;
}

// ─── 3. Propagator Interface ──────────────────────────────────────
export interface PropagatorPlugin {
  name: string;
  propagateBounds: (
    model: Model,
    currentColLo: Float64Array,
    currentColHi: Float64Array
  ) => { changed: boolean; infeasible: boolean };
}

// ─── 4. BranchingRule Interface ───────────────────────────────────
export interface BranchingRulePlugin {
  name: string;
  description: string;
  selectVariable: (
    model: Model,
    x: Float64Array,
    fractionalIndices: number[],
    context?: any
  ) => number;
}

// ─── 5. NodeSelector Interface ────────────────────────────────────
export interface BNCNodeRef {
  id: number;
  depth: number;
  lowerBound: number;
  estimatedObj?: number;
}

export interface NodeSelectorPlugin {
  name: string;
  selectNextNode: (openNodes: BNCNodeRef[]) => number;
}

// ─── 6. Heuristic Interface ───────────────────────────────────────
export interface HeuristicPlugin {
  name: string;
  tryFindIncumbent: (
    model: Model,
    relaxationX: Float64Array,
    currentBestUB: number
  ) => Float64Array | null;
}

// ─── 7. CutGenerator Interface ────────────────────────────────────
export interface CutRecord {
  type: string;
  coefficients: { col: number; val: number }[];
  rhs: number;
  sense: 'L' | 'G';
  multipliers?: number[];
  originRows?: number[];
}

export interface CutGeneratorPlugin {
  name: string;
  separateCuts: (
    model: Model,
    x: Float64Array,
    basisInfo?: any
  ) => CutRecord[];
}

// ─── 8. ModelClass Interface ──────────────────────────────────────
export interface ModelClassPlugin {
  className: string;
  convex: boolean;
  relaxationFamily: 'LP' | 'QP' | 'SDP' | 'TangentRelaxation';
  buildRelaxation: (rawProblem: any) => Model;
  computeLagrangianBound: (model: Model, y: Float64Array) => number;
  allowedStatuses: string[];
}

// ─── Central Plug-in Registry ────────────────────────────────────
export class PluginRegistry {
  private static instance: PluginRegistry;

  private engines = new Map<string, EnginePlugin>();
  private presolvers = new Map<string, PresolverPlugin>();
  private propagators = new Map<string, PropagatorPlugin>();
  private branchingRules = new Map<string, BranchingRulePlugin>();
  private nodeSelectors = new Map<string, NodeSelectorPlugin>();
  private heuristics = new Map<string, HeuristicPlugin>();
  private cutGenerators = new Map<string, CutGeneratorPlugin>();
  private modelClasses = new Map<string, ModelClassPlugin>();

  private constructor() {
    this.registerDefaults();
  }

  public static get(): PluginRegistry {
    if (!PluginRegistry.instance) {
      PluginRegistry.instance = new PluginRegistry();
    }
    return PluginRegistry.instance;
  }

  // Register built-in default implementations
  private registerDefaults(): void {
    // Default Branching Rules
    this.registerBranchingRule({
      name: 'most-fractional',
      description: 'Branches on variable furthest from nearest integer (max |x_j - round(x_j)|)',
      selectVariable: (_model, x, frac) => {
        let bestVar = frac[0];
        let maxDist = -1;
        for (const j of frac) {
          const dist = Math.abs(x[j] - Math.round(x[j]));
          if (dist > maxDist) {
            maxDist = dist;
            bestVar = j;
          }
        }
        return bestVar;
      }
    });

    this.registerBranchingRule({
      name: 'lowest-index-fractional',
      description: 'Deterministic lowest-index selection for reproducible debugging',
      selectVariable: (_model, _x, frac) => frac[0]
    });

    // Default Node Selectors
    this.registerNodeSelector({
      name: 'best-bound',
      selectNextNode: (nodes) => {
        let bestIdx = 0;
        let minLB = nodes[0].lowerBound;
        for (let i = 1; i < nodes.length; i++) {
          if (nodes[i].lowerBound < minLB) {
            minLB = nodes[i].lowerBound;
            bestIdx = i;
          }
        }
        return bestIdx;
      }
    });

    this.registerNodeSelector({
      name: 'depth-first',
      selectNextNode: (nodes) => {
        let bestIdx = 0;
        let maxDepth = nodes[0].depth;
        for (let i = 1; i < nodes.length; i++) {
          if (nodes[i].depth > maxDepth) {
            maxDepth = nodes[i].depth;
            bestIdx = i;
          }
        }
        return bestIdx;
      }
    });

    // Default Model Classes
    this.registerModelClass({
      className: 'LP',
      convex: true,
      relaxationFamily: 'LP',
      buildRelaxation: (m) => m,
      computeLagrangianBound: () => 0,
      allowedStatuses: ['OPTIMAL', 'INFEASIBLE_CERTIFIED', 'UNBOUNDED_CERTIFIED']
    });

    this.registerModelClass({
      className: 'MILP',
      convex: true,
      relaxationFamily: 'LP',
      buildRelaxation: (m) => m,
      computeLagrangianBound: () => 0,
      allowedStatuses: ['OPTIMAL', 'OPTIMAL_WITHIN_GAP', 'INFEASIBLE_CERTIFIED']
    });

    this.registerModelClass({
      className: 'ConvexQP',
      convex: true,
      relaxationFamily: 'QP',
      buildRelaxation: (m) => m,
      computeLagrangianBound: () => 0,
      allowedStatuses: ['OPTIMAL', 'UNSUPPORTED']
    });

    this.registerModelClass({
      className: 'NonConvexNLP',
      convex: false,
      relaxationFamily: 'TangentRelaxation',
      buildRelaxation: (m) => m,
      computeLagrangianBound: () => -Infinity,
      allowedStatuses: ['LOCAL_ONLY', 'UNSUPPORTED']
    });
  }

  // Registration methods
  public registerEngine(plugin: EnginePlugin): void {
    this.engines.set(plugin.name, plugin);
  }

  public registerPresolver(plugin: PresolverPlugin): void {
    this.presolvers.set(plugin.name, plugin);
  }

  public registerPropagator(plugin: PropagatorPlugin): void {
    this.propagators.set(plugin.name, plugin);
  }

  public registerBranchingRule(plugin: BranchingRulePlugin): void {
    this.branchingRules.set(plugin.name, plugin);
  }

  public registerNodeSelector(plugin: NodeSelectorPlugin): void {
    this.nodeSelectors.set(plugin.name, plugin);
  }

  public registerHeuristic(plugin: HeuristicPlugin): void {
    this.heuristics.set(plugin.name, plugin);
  }

  public registerCutGenerator(plugin: CutGeneratorPlugin): void {
    this.cutGenerators.set(plugin.name, plugin);
  }

  public registerModelClass(plugin: ModelClassPlugin): void {
    this.modelClasses.set(plugin.className, plugin);
  }

  // Retrieval methods
  public getEngine(name: string): EnginePlugin | undefined {
    return this.engines.get(name);
  }

  public getBranchingRule(name: string): BranchingRulePlugin | undefined {
    return this.branchingRules.get(name);
  }

  public getNodeSelector(name: string): NodeSelectorPlugin | undefined {
    return this.nodeSelectors.get(name);
  }

  public getModelClass(name: string): ModelClassPlugin | undefined {
    return this.modelClasses.get(name);
  }

  public listBranchingRules(): string[] {
    return Array.from(this.branchingRules.keys());
  }

  public listNodeSelectors(): string[] {
    return Array.from(this.nodeSelectors.keys());
  }

  public listModelClasses(): string[] {
    return Array.from(this.modelClasses.keys());
  }
}
