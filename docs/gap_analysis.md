# NIRBHAR Gap Analysis — Prompt (4) vs Current Prototype

Generated: 2026-10-03
Checked against: Frontend Prompt (4) and Backend Prompt (1)

---

## Top-Level Status

| Category | Status |
|---|---|
| Sovereignty check-imports | PASS — 32 files, 0 violations |
| Data Pack (data/ folder) | Complete — netlib, milp, qp, miqp, stress, infeas all present |
| Core solver modules | Mostly present — qp/, robust/, parallel/, explain/ empty |
| UI pages | All 11 pages present |
| Backend Python package | Not in scope for this repo (separate deliverable) |

---

## Data Pack (data/ folder) — Complete

| Category | Required | Present |
|---|---|---|
| Netlib LPs | 26 | 26 |
| MIPLIB MILPs | 18 | 18 |
| QP variants | 5 | 5 |
| MIQP models | 2 | 2 |
| Stress/S1/S2 | 9 | 9 |
| Infeasible models | 3 | 3 |
| manifest.json | 1 | 1 |

All data files from the spec (§8 / Backend §5) are present.

---

## Source Module Coverage

### src/solver/

| Module | Files Present | Gap |
|---|---|---|
| io/ | mps.ts, model.ts | None |
| linalg/ | csr.ts, lu.ts, etc. | None |
| presolve/ | presolve.ts | None |
| lp/ | dualSimplex.ts, basis.ts, hpr.ts | Missing: hprBatch.ts, primalSimplex.ts, crossover.ts |
| ipm/ | ipm.ts | None |
| qp/ | EMPTY | Missing: hprQp.ts, bounds.ts, kelley.ts |
| mip/ | bb.ts, branching.ts, heuristics.ts, nodesel.ts, cuts/ | None |
| robust/ | EMPTY | Missing: controller.ts, switches.ts, naiveMode.ts |
| parallel/ | EMPTY | Missing: pool.ts, race.ts |
| explain/ | EMPTY | Missing: duals.ts, ranging.ts, iis.ts |
| extend/ | registry.ts | None |
| certificate/ | builder.ts, explain.ts, schema.ts | None |
| workers/ | engine.worker.ts | Missing: mip.worker.ts, batch.worker.ts, verify.worker.ts |
| dispatch.ts | Present | None |
| cli.ts | Present | None |

### src/verify/ — Complete

verify.ts, exact.ts, cuts.ts, mpsMin.ts, certTypes.ts — all present.

### src/demo/ — Incomplete

| File | Status |
|---|---|
| refinery.ts | Present |
| milpSamples.ts | Present |
| lotsizing.ts | MISSING |
| transport.ts | MISSING |
| unitCommit.ts | MISSING |
| supplyChain.ts | MISSING |

### src/bench/ — Empty

Missing: harness.ts, knownOpt.ts, stress.ts, refs.ts, highsBaseline.ts

---

## UI Pages — All Present

Home, SolveStudio, RefineryDemo, BranchCutLab, RobustnessLab, Verifier,
Benchmarks, ModelFamilies, Architecture, CliApi, PSCompliance, SelfTest (bonus)

---

## Feature Spec Gap by Priority

### P0 Features — Status

| Feature | Status |
|---|---|
| F1 Model intake | Complete |
| F2 Engine config | Complete |
| F3 Live solve + concurrent race | Partial — race needs race.ts + 3 workers |
| F4 Result + certificate | Complete |
| F6 Shadow prices + infeasibility | Incomplete — explain/ empty |
| F7 Refinery LP | Complete |
| F8 Refinery MILP | Complete |
| F9 Refinery QP | Incomplete — qp/ empty |
| F10 Scenario batch | Partial — batch.worker.ts + hprBatch.ts missing |
| F11 B&C + live tree | Complete |
| F12 Node selection + branching | Complete |
| F13 Cuts + inspector | Complete |
| F14 Brute-force check | Complete |
| F15 Robustness naive vs hardened | Incomplete — robust/ empty |
| F17 Independent verifier | Complete |
| F18 Adversarial suite | Complete |
| F19 Netlib benchmark | Complete |
| F23 Model Families | Partial — 4 generators missing |
| F25 Plug-in registry + extend | Complete |
| F26 Sovereignty panel | Complete |
| F27 CLI and API | Complete |
| F28 PS Compliance | Complete |

### P1 Features

| Feature | Status |
|---|---|
| F5 Presolve visualiser | Complete |
| F16 Stress suite table | bench/ empty |
| F20 QP/MIQP tables | Partial — needs qp/ modules |
| F21 Charts (crossover, reliability) | Complete |
| F22 Known-optimum generators | Missing — knownOpt.ts |
| F24 Architecture explorer | Complete |

---

## Must-Fix P0 Gaps (7 items)

1. src/solver/qp/hprQp.ts + bounds.ts — QP HPR engine (F9)
2. src/solver/robust/controller.ts + switches.ts + naiveMode.ts — Robustness (F15)
3. src/solver/explain/duals.ts + iis.ts — Shadow prices + IIS (F6)
4. src/solver/parallel/race.ts + pool.ts — Concurrent race (F3, F10)
5. src/solver/workers/ — Add mip.worker.ts, batch.worker.ts, verify.worker.ts
6. src/demo/ — Add lotsizing.ts, transport.ts, unitCommit.ts, supplyChain.ts (F23)
7. src/solver/lp/hprBatch.ts — Batched HPR for F10 scenario batch

## P1 Gaps

8. src/solver/lp/primalSimplex.ts — Escalation fallback
9. src/solver/lp/crossover.ts — IPM crossover polishing
10. src/solver/qp/kelley.ts — Kelley OA fallback
11. docs/ARCHITECTURE.md — Architecture diagram document

## Backend Python Package

The Backend Prompt (1) describes a separate Python package (nirbhar/ + nirbhar_verify/)
using Numba/JAX. This is NOT present in the current JavaScript/TypeScript prototype workspace.
It is a separate deliverable for a different repository. The frontend TS prototype is independent.
