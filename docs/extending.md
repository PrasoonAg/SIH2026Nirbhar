# NIRBHAR — Plug-in Architecture & Developer Extension Guide
### Smart India Hackathon 2026 | Problem Statement SIH26119 | Team Vernils (MRPL)

> *"The solver that proves its answers."*

This document provides the reference guide for extending NIRBHAR through its 8 modular plug-in interfaces (§8 of `NIRBHAR-Complete-Idea.md`). NIRBHAR is architected so that internal algorithms (dual simplex, interior point, HPR, cuts, presolvers) and user-contributed extensions register through the **same registry** without modifying the core engine loops.

---

## 1. The 8 Plug-in Interfaces (§8)

| # | Interface | Purpose | Built-in Implementations |
|---|---|---|---|
| 1 | `Engine` | Core solver algorithms | `dual-simplex` (Markowitz sparse LU), `ipm` (Mehrotra predictor-corrector), `hpr` (first-order Halpern PDHG) |
| 2 | `Presolver` | Problem reduction routines | Singletons, dual fixing, forcing rows, duplicate rows, big-M tightening, probing |
| 3 | `Propagator` | Bound tightening during B&B | Activity-based bounds propagation with directed rounding |
| 4 | `BranchingRule` | Variable selection at fractional nodes | `most-fractional`, `reliability-branching`, `pseudocost-lite` |
| 5 | `NodeSelector` | Search tree node exploration strategy | `best-bound`, `best-estimate + plunging`, `depth-first` |
| 6 | `Heuristic` | Fast primal incumbent discovery | Simple rounding, diving (fractional/guided/coefficient), feasibility pump, RINS |
| 7 | `CutGenerator` | Valid inequality generation | `gmi` (safe aggregation), `c-mir` (greedy aggregation), `extended-cover` |
| 8 | `ModelClass` | Problem classification and relaxation builder | `LP`, `MILP`, `ConvexQP`, `ConvexMIQP`, `NonConvexNLP` |

---

## 2. Central Registry (`src/solver/extend/registry.ts`)

The central singleton `PluginRegistry` manages registered components:

```typescript
import { PluginRegistry } from '../solver/extend/registry';

const registry = PluginRegistry.get();
```

---

## 3. Worked Example: Adding a Custom Branching Rule

Requirement from §8 and §11.1:
> *"The worked example adds a second branching rule without touching `bb.ts` or `branching.ts`."*

### Step 1: Implement `BranchingRulePlugin`

```typescript
import type { BranchingRulePlugin } from '../solver/extend/registry';
import type { Model } from '../solver/io/model';

export const LowestIndexBranchingRule: BranchingRulePlugin = {
  name: 'lowest-index-fractional',
  description: 'Deterministic lowest-index selection for reproducible debugging and verification',
  selectVariable: (model: Model, x: Float64Array, fractionalIndices: number[]) => {
    // Select the first fractional variable in natural index order
    return fractionalIndices[0];
  }
};
```

### Step 2: Register with `PluginRegistry`

```typescript
import { PluginRegistry } from '../solver/extend/registry';
import { LowestIndexBranchingRule } from './lowestIndexRule';

// Register the custom rule
PluginRegistry.get().registerBranchingRule(LowestIndexBranchingRule);
```

### Step 3: Use in Branch-and-Cut

When solving a mixed-integer model, specify the registered rule name:

```typescript
import { branchAndCutSolve } from '../solver/mip/bb';

const result = branchAndCutSolve(model, {
  branchingRule: 'lowest-index-fractional',
  maxNodes: 500,
  useCuts: true
});
```

### Step 4: Audit Verification in the Certificate

The resulting certificate automatically records the registered plug-in inside `solve_path`:

```json
{
  "kind": "MILP_OPTIMAL",
  "version": "1.0",
  "solve_path": [
    "presolve-8-pass",
    "root-dual-simplex",
    "cut-loop-gmi-cmir",
    "branch-and-cut",
    "branching:lowest-index-fractional",
    "safe-bound-cert"
  ],
  "objectiveUB": 3089.0,
  "lowerBound": 3089.0,
  "gap": 0.0
}
```

---

## 4. Worked Example: Extending `ModelClass` for Non-Convex Problems

To handle problem classes beyond convex LP/QP, implement `ModelClassPlugin`:

```typescript
import type { ModelClassPlugin } from '../solver/extend/registry';

export const BilinearPoolingModelClass: ModelClassPlugin = {
  className: 'BilinearPoolingNLP',
  convex: false,
  relaxationFamily: 'TangentRelaxation',
  buildRelaxation: (rawProblem) => {
    // Construct outer-approximation McCormick envelopes
    return buildMcCormickRelaxation(rawProblem);
  },
  computeLagrangianBound: () => -Infinity,
  // Strictly enforce honest status reporting: non-convex optimization returns LOCAL_ONLY
  allowedStatuses: ['LOCAL_ONLY', 'UNSUPPORTED']
};

PluginRegistry.get().registerModelClass(BilinearPoolingModelClass);
```

When an optimization run terminates on this class, NIRBHAR guarantees that the certificate status is set to `LOCAL_ONLY` rather than a misleading `OPTIMAL` without a global duality proof.

---

## 5. Sovereignty Invariant for Contributors

All contributions to `src/solver/**` and `src/verify/**` must obey:
1. **Zero third-party numeric/solver packages** (no `mathjs`, `glpk`, `highs`, `numeric.js`).
2. **Strict air-gap isolation:** `src/verify/**` must never import from `src/solver/**`.
3. Verified automatically via:
   ```bash
   npm run check-imports
   ```
