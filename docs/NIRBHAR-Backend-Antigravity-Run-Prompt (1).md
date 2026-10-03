# NIRBHAR Backend: Antigravity Run Prompt (Python solver core)

> **How to use:** Unzip `nirbhar-sample-pack.zip` into the repo's `data/` folder first. In Antigravity use Planning mode, paste everything below the line, and attach `NIRBHAR-Complete-Idea.md` and `NirbharDraft.pdf` (the SIH deck). Ask the agent to stop for your review at the end of each phase in section 11 and to paste the real `pytest` summary each time.

---

# ROLE

You are a senior numerical-optimization engineer and Python performance engineer. Build the **real NIRBHAR solver core** (Smart India Hackathon 2026, PS SIH26119, Team Vernils, for MRPL): an India-owned, from-scratch **certified hybrid CPU-GPU solver** for LP, MILP, QP and convex MIQP. There is no frontend in this job. The deliverables are a Python package, a separate verifier package, a CLI, a Python API, a benchmark harness, and a test suite that proves the claims in the deck.

Source of truth: the attached idea document (section numbers written as "doc §n") and the deck. Where this prompt and the doc disagree, stop and ask me. The deck's one-line promise, which every design decision must serve: **"The solver that proves its answers."**

# 1. WHAT "DONE" MEANS (PS deliverables, mapped to this build)

1. Parse MPS (fixed and free, with RANGES, all bound types, integer markers, `OBJSENSE`) and QPS (`QUADOBJ`/`QMATRIX`), keeping the **original model untouched**.
2. Solve **LP, MILP, QP and convex MIQP** with engines written in this repo: revised simplex (dual + primal), Mehrotra interior point, **JAX HPR** first-order engine (LP, QP, batched), crossover, certified branch-and-cut.
3. **Hybrid dispatch:** after presolve each model goes to the engine that measurably wins; the engines **race at the root** and the first result that passes the safe-bound check wins.
4. **Certified answers:** every solve returns a certificate with a rigorous bound; "OPTIMAL" is reported only when the certified gap is within tolerance **and** the separate verifier says PASS.
5. **Independent verifier** as its own package that re-reads the **original** model and never imports the solver.
6. **Robustness:** a controller that logs every escalation (no silent loops), plus a `naive_mode` textbook configuration used to show where an unhardened solver fails.
7. **Explainability:** binding constraints, shadow prices, reduced costs, and (for infeasible models) an irreducible conflicting set, in plain language.
8. **Parallelism:** GIL-free Numba threads (multi-core), JAX batching (scenario batches), concurrent root race.
9. **Plug-in interfaces** (engine, presolver, propagator, branching rule, node selector, heuristic, cut generator, model class) used by NIRBHAR's own components.
10. **Benchmarks and honesty:** Netlib LPs, MIPLIB 3 MILPs, QP/MIQP packs, stress suite; baselines (HiGHS, MPAX) live **only** in `bench/`; losses and residual failures are published.
11. **Refinery-shaped proof point:** a synthetic MRPL-like model (labelled synthetic) solved as LP, MILP, QP and a scenario batch.
12. **CLI and Python API** producing a human report plus `certificate.json`.

# 2. HARD RULES (the deck's "three hard rules" plus project rules)

1. **No approximate prune.** A branch-and-bound node is pruned only when its **safe lower bound** (section 7) is at least `UB - tol`. A weak or unverified bound keeps the node open. A node is declared infeasible only with a verified Farkas ray; otherwise it stays open and is flagged.
2. **Verify on the original model.** The verifier re-reads the original MPS text (hash-checked), never the presolved or scaled model. All stopping tests in every engine are evaluated in **original, unscaled** space.
3. **Cuts are derived, not trusted.** Every cut carries a derivation record (row multipliers, bounds used, rounding, complementation) that the verifier re-derives in exact rational arithmetic. Cuts are built with safe aggregation and directed rounding.
4. **Sovereignty.** `nirbhar/` and `nirbhar_verify/` import **no solver library** and no SciPy/CVXPY/OR-Tools/PuLP/Pyomo/HiGHS/MPAX. Allowed: Python stdlib, NumPy, Numba, JAX. SciPy, `highspy` and MPAX are allowed **only** in `bench/` and `tests/`. Enforced by `tools/check_imports.py` in CI (AST scan, fails the build).
5. **Verifier isolation.** `nirbhar_verify/` imports nothing from `nirbhar/` (enforced by the same script). It has its own MPS reader, its own bound code and its own cut re-derivation. Exact mode uses `fractions.Fraction`.
6. **No fake results.** No hardcoded objectives, timings, or "naive fails" outcomes. If a demo instance does not behave as intended, change the instance by a **written rule** and log it in `docs/instances.md`, never the reported numbers.
7. **Honesty wording.** Never write "GPU-native". Say "certified hybrid CPU-GPU solver core". GPU use is reported only if a GPU device actually ran and was timed; the certificate records the real device. First-order answers are labelled `CERTIFIED_APPROXIMATE` unless polished to a basis. Never claim parity with CPLEX/Gurobi/Xpress; report the ratio to HiGHS and publish losses.
8. **Determinism.** Fixed seeds everywhere; a `--deterministic` mode (fixed thread count, fixed merge order) must give identical objective values run to run.
9. **CPU path is complete.** No deliverable may require a GPU. JAX runs on CPU, GPU or TPU from the same code.

# 3. TECH STACK (chosen from the deck's "Technologies to be used")

| Deck component | Choice for this build | Where it is used |
|---|---|---|
| Language and compiler | **Python 3.11/3.12** orchestrates; **Numba** `@njit(cache=True, nogil=True)` for all hot loops (GIL-free threads) | simplex, LU, IPM kernels, B&B inner loops, propagation, cuts |
| Array and GPU | **NumPy** arrays; **JAX with `jax_enable_x64=True`**: one code path for CPU, GPU and TPU | HPR-LP, HPR-QP, batched HPR, batched strong branching (P1) |
| Own sparse linear algebra | CSR/CSC classes, **LU with Markowitz pivoting** (hypersparse solves), **Cholesky**, **LDL^T**, iterative refinement, 1-norm condition estimate | simplex basis, IPM normal equations, QP KKT |
| Solver engines | Dual + primal simplex, Mehrotra IPM, HPR, HPR-QP, crossover, branch-and-cut | `nirbhar/lp`, `ipm`, `qp`, `mip` |
| Certificate and verify | Safe bounds, float64 + margin or exact rational, **separate verifier package** | `nirbhar/certificate`, `nirbhar_verify` |
| Benchmarks and QA | **pytest**; baselines **HiGHS (`highspy`)** and **MPAX** inside `bench/` only; datasets Netlib, MIPLIB, Mittelmann (as time allows) | `bench/`, `tests/` |
| Guard | CI import check ("inside the solver: no solver library; SciPy only in bench/ and tests/") | `tools/check_imports.py` |

Not used (so nobody adds them): FastAPI, Torch, CVXPY, SciPy inside the solver, Cython, C++ extensions. If you want a service wrapper later, use stdlib `http.server` (P2, section 9, item 16). Pin versions in `requirements.txt`; `requirements-bench.txt` holds `highspy`, `scipy`, `mpax`.

**JAX/Numba notes.** Enable x64 before any JAX import. Keep Numba functions allocation-free in loops and test with `NUMBA_DISABLE_JIT=1` in CI for coverage. Never share mutable NumPy state between threads; each worker owns its arrays. For sparse mat-vec in JAX use your own CSR with `jax.ops.segment_sum` (do not depend on `jax.experimental.sparse`).

# 4. REPOSITORY LAYOUT

```
nirbhar/
  io/          mps.py qps.py model.py writer.py
  sparse/      csr.py csc.py ops.py
  linalg/      lu_markowitz.py lu_update.py cholesky.py ldlt.py refine.py condest.py
  presolve/    scaling.py reductions.py postsolve.py stack.py
  lp/          dual_simplex.py primal_simplex.py basis.py hpr.py hpr_batch.py crossover.py
  ipm/         mehrotra.py
  qp/          hpr_qp.py ipm_qp.py bounds.py
  mip/         bb.py propagate.py branching.py nodesel.py heuristics.py reduced_cost_fix.py parallel_tree.py
  cuts/        gmi.py cmir.py cover.py pool.py derivation.py
  robust/      controller.py switches.py naive_mode.py
  explain/     duals.py ranging.py iis.py report.py
  extend/      registry.py interfaces.py
  certificate/ safe_bound.py builder.py schema.py
  industrial/  refinery.py lotsizing.py transport.py unit_commit.py facility.py known_opt.py
  dispatch.py  race.py  api.py  cli.py
nirbhar_verify/  mps_min.py verify.py exact.py cuts_check.py rays.py cli.py     # imports NOTHING from nirbhar/
bench/         harness.py baselines.py crossover_scale.py stress.py reliability.py report.py gpu_run.py
tests/         (see section 10)
data/          (unzipped sample pack: netlib/ milp/ qp/ miqp/ stress/ infeas/ manifest.json)
tools/         check_imports.py
docs/          instances.md KNOWN_LIMITS.md ARCHITECTURE.md
```

# 5. SAMPLE DATA PACK (real files, reference values measured)

`data/manifest.json` lists every model: file, class, rows, cols, nnz, integers, `reference_objective`, how it was obtained, `split` (tune | report | stress | status), tier and SHA-256. **Build the test suite and benchmark harness from the manifest** so new files can be added without code changes. Reference optima were measured with HiGHS 1.15.1 (1 thread) and spot-checked against the published Netlib/MIPLIB values. **Do not hand-type any model data.**

Tolerance: relative objective error `|obj - ref| / max(1, |ref|) <= 1e-6` (use `1e-4` only for HPR before polish, and label it `CERTIFIED_APPROXIMATE`). Tiers: **T1** tiny (must pass in Phase 1-2), **T2** small-medium, **T3** stretch.

### 5.1 Netlib LPs (tune = tune only, report = never tuned on)

| name | rows x cols | nnz | reference optimum (min) | split | tier |
|---|---|---|---|---|---|
| 25fv47 | 821 x 1571 | 10400 | 5501.845888 | report | T3 |
| adlittle | 56 x 97 | 383 | 225494.9632 | report | T1 |
| afiro | 27 x 32 | 83 | -464.7531429 | tune | T1 |
| bandm | 305 x 472 | 2494 | -158.6280185 | report | T2 |
| beaconfd | 173 x 262 | 3375 | 33592.48581 | report | T2 |
| blend | 74 x 83 | 491 | -30.81214985 | report | T1 |
| brandy | 220 x 249 | 2148 | 1518.509896 | report | T2 |
| degen2 | 444 x 534 | 3978 | -1435.178 | report | T2 |
| e226 | 223 x 282 | 2578 | -11.63892907 | tune | T2 |
| forplan | 161 x 421 | 4563 | -664.2189613 | report | T2 |
| israel | 174 x 142 | 2269 | -896644.8219 | report | T2 |
| kb2 | 43 x 41 | 286 | -1749.90013 | tune | T1 |
| lotfi | 153 x 308 | 1078 | -25.26470606 | tune | T2 |
| recipe | 91 x 180 | 663 | -266.616 | report | T1 |
| sc105 | 105 x 103 | 280 | -52.20206121 | tune | T1 |
| sc50a | 50 x 48 | 130 | -64.57507706 | tune | T1 |
| sc50b | 50 x 48 | 118 | -70 | tune | T1 |
| scagr25 | 471 x 500 | 1554 | -14753433.06 | report | T2 |
| scagr7 | 129 x 140 | 420 | -2331389.824 | tune | T2 |
| scfxm1 | 330 x 457 | 2589 | 18416.75903 | report | T2 |
| scorpion | 388 x 358 | 1426 | 1878.124823 | report | T2 |
| scsd1 | 77 x 760 | 2388 | 8.666666674 | report | T1 |
| sctap1 | 300 x 480 | 1692 | 1412.25 | report | T2 |
| share1b | 117 x 225 | 1151 | -76589.31858 | report | T1 |
| share2b | 96 x 79 | 694 | -415.7322407 | report | T1 |
| stocfor1 | 117 x 111 | 447 | -41131.97622 | report | T1 |

`25fv47` (821 x 1571) is T3 stretch. Do not tune parameters on `report` instances.

### 5.2 MIPLIB 3 MILPs (all minimisation)

| name | rows x cols | ints | reference optimum (min) | HiGHS time / nodes | tier |
|---|---|---|---|---|---|
| bell3a | 123 x 133 | 71 | 878430.316 | 0.406s / 215 | T1 |
| bell5 | 91 x 104 | 58 | 8966406.492 | 0.598s / 1076 | T1 |
| dcmulti | 290 x 548 | 75 | 188182 | 1.333s / 15 | T3 |
| egout | 98 x 141 | 55 | 568.1007 | 0.014s / 1 | T1 |
| enigma | 21 x 100 | 100 | 0 | 0.175s / 1 | T1 |
| fixnet6 | 478 x 878 | 378 | 3983 | 3.372s / 1 | T3 |
| flugpl | 18 x 18 | 11 | 1201500 | 0.099s / 89 | T1 |
| gt2 | 29 x 188 | 188 | 21166 | 0.046s / 1 | T1 |
| khb05250 | 101 x 1350 | 24 | 106940226 | 0.304s / 1 | T3 |
| lseu | 28 x 89 | 89 | 1120 | 0.236s / 7 | T1 |
| misc03 | 96 x 160 | 159 | 3360 | 0.507s / 27 | T1 |
| mod008 | 6 x 319 | 319 | 307 | 0.855s / 7 | T1 |
| p0033 | 16 x 33 | 33 | 3089 | 0.022s / 1 | T1 |
| p0201 | 133 x 201 | 201 | 7615 | 0.817s / 5 | T3 |
| rgn | 24 x 180 | 100 | 82.19999924 | 0.251s / 1 | T1 |
| stein27 | 118 x 27 | 27 | 18 | 0.698s / 1434 | T1 |
| stein45 | 331 x 45 | 45 | 30 | 24.918s / 36405 | T3 |
| vpm1 | 234 x 378 | 168 | 20 | 0.029s / 1 | T1 |

T1 must reach proven optimality with the certified tree. T3 (`stein45`, `fixnet6`, `dcmulti`, `khb05250`, `p0201`) are stretch: report status, gap, nodes and time honestly even if the node/time limit hits (`OPTIMAL_WITHIN_GAP` with the true proven gap, or `TIME_LIMIT`). HiGHS times above are only for calibration.

### 5.3 QP and MIQP (generated; convex)

| name | class | rows x cols | ints | Q | reference optimum | how obtained |
|---|---|---|---|---|---|---|
| adlittle_qp_sparse | QP | 56 x 97 | 0 | 97 | 232956.7387 | HiGHS QP + Clarabel |
| afiro_qp_diag | QP | 27 x 32 | 0 | 32 | 70.6475082 | HiGHS QP + Clarabel |
| kb2_qp_sparse | QP | 43 x 41 | 0 | 41 | -0.1446220142 | HiGHS QP + Clarabel |
| sc50a_qp_diag | QP | 50 x 48 | 0 | 48 | -0.004431826858 | HiGHS QP + Clarabel |
| share2b_qp_diag | QP | 96 x 79 | 0 | 79 | 312.4618237 | HiGHS QP + Clarabel |
| uc_miqp_3x4 | MIQP | 40 x 36 | 12 | 36 | 21908.806 | brute force over 4096 assignments |
| uc_miqp_4x3 | MIQP | 39 x 36 | 12 | 36 | 22400.985 | brute force over 4096 assignments |

QP files are a Netlib LP plus a PSD `Q` in a `QUADOBJ` section, objective `c'x + 0.5 x'Qx`, one triangle of Q listed. `Q` is PSD up to rounding (min eigenvalue about -5e-16), so the PSD check must use a tolerance. MIQP files are 3 x 4 and 4 x 3 unit-commitment models with quadratic fuel cost; the reference is a full enumeration of the 4096 binary assignments.

### 5.4 Stress and status suite (stated before results are seen)

| name | rows x cols | true optimum (exact) | what HiGHS defaults return | category |
|---|---|---|---|---|
| adlittle_rescaled_1e3 | 56 x 97 | 225494.9632 | 225494.9632 | S2-illconditioned-1e3 |
| adlittle_rescaled_1e6 | 56 x 97 | 225494.9632 | 181016.4841 | S2-illconditioned-1e6 |
| afiro_rescaled_1e3 | 27 x 32 | -464.7531429 | -464.7531429 | S2-illconditioned-1e3 |
| afiro_rescaled_1e6 | 27 x 32 | -464.7531429 | -464.7531429 | S2-illconditioned-1e6 |
| beale_cycling | 3 x 7 | -1.25 | -1.25 | S1-degenerate |
| kb2_rescaled_1e3 | 43 x 41 | -1749.90013 | -1749.90013 | S2-illconditioned-1e3 |
| kb2_rescaled_1e6 | 43 x 41 | -1749.90013 | -1749.543615 | S2-illconditioned-1e6 |
| sc50a_rescaled_1e3 | 50 x 48 | -64.57507706 | -64.57507706 | S2-illconditioned-1e3 |
| sc50a_rescaled_1e6 | 50 x 48 | -64.57507706 | -52.36656596 | S2-illconditioned-1e6 |
| galenet | 8 x 8 | status INFEASIBLE_CERTIFIED | - | status |
| tiny_infeasible | 3 x 2 | status INFEASIBLE_CERTIFIED | - | status |
| tiny_unbounded | 1 x 2 | status UNBOUNDED_CERTIFIED | - | status |

* **S1 degenerate:** `beale_cycling` (the classic Beale LP). A textbook primal simplex (Dantzig pricing, lowest-index ties) cycles on it. Verify this in your own `naive_mode`; if it does not cycle in your implementation, report that honestly and rely on S2.
* **S2 ill-conditioned:** rows and columns rescaled by factors drawn from `[1e-3, 1e3]` (1e3 tier) or `[1e-6, 1e6]` (1e6 tier). The optimum is **exactly** the original model's optimum, so the reference is exact. Measured fact: HiGHS with default settings returns "Optimal" with a **wrong** objective on `sc50a`, `adlittle` and `kb2` at the 1e6 tier (right column above). So: on the 1e6 tier the hardened solver must either match the true optimum **and** pass the verifier, or return an honest weaker status (`CERTIFIED_APPROXIMATE`, `NUMERICAL_ISSUE`). **A wrong `OPTIMAL` is a failed test.** The verifier must reject a wrong answer even when the solver claims optimal.
* **Status models:** `galenet` (a real Netlib infeasible LP), `tiny_infeasible`, `tiny_unbounded`: expected `INFEASIBLE_CERTIFIED` / `UNBOUNDED_CERTIFIED`, with the ray re-checked by the verifier.
* **S3 weak relaxation / S4 wide coefficient range:** generated by `industrial/lotsizing.py` and `industrial/transport.py` (fixed-charge, big-M); rule written in `docs/instances.md`.

### 5.5 Parser traps (test these explicitly)

`dcmulti.mps` has an `IMPORTANCES` block **after** `ENDATA` (must be ignored). `forplan` uses RANGES. `misc03` has an `FR` bound. `recipe`, `egout`, `flugpl`, `vpm1` use `FX`/`LO`. MPS bound types `MI`, `PL`, `LI`, `UI`, negative `UP` with zero lower bound, `BV`, RANGES on E rows (sign of R decides), objective-row RHS (objective constant, sign flipped), `OBJSENSE MAX`, free-format files: none are in the pack, so write small inline-snippet unit tests for each.

# 6. MODULE SPECIFICATIONS

Each module ends with **Accept** (a pytest that must pass). Correctness first on small models, then speed.

**M1. Parser and model (`io`).** Immutable `Model`: `c`, `A` (CSR + CSC), row lo/hi, col lo/hi, integrality, optional `Q` (upper triangle), names, sense, constant, SHA-256 of the original text. Errors carry line number and reason. A writer exports MPS/QPS (round-trip). **Accept:** every manifest model parses with rows/cols/nnz/integers equal to the manifest; round-trip preserves the objective; malformed files give line-numbered errors.

**M2. Sparse and linear algebra (`sparse`, `linalg`).** CSR/CSC ops in Numba. LU with Markowitz pivoting and threshold partial pivoting, hypersparse triangular solves, product-form/Forrest-Tomlin updates with refactorization triggers (eta length, growth estimate, residual check); Cholesky and LDL^T for IPM/QP (with regularization); iterative refinement; Hager 1-norm condition estimate. (Phase 1 may start with dense LU for bases up to a few hundred rows; replace by sparse LU in Phase 2 and say so in `KNOWN_LIMITS.md`.) **Accept:** residual tests on random and Netlib-derived bases; sparse LU matches dense LU to 1e-10.

**M3. Scaling, presolve, postsolve (`presolve`).** Geometric-mean then Ruiz scaling (simplex/IPM); Ruiz about 10 iterations (HPR). Reductions, each with an on/off switch and a postsolve record: empty rows/columns, fixed variables, duplicate rows/columns, singleton rows to bounds, forcing and redundant rows, activity-based bound tightening, dual fixing, doubleton aggregation, integer rounding, **big-M coefficient tightening**, probing (MILP). Every step logged. Postsolve rebuilds primal, duals and basis in original space. **Accept:** presolve, solve, postsolve yields a point feasible in the original model with the same objective (1e-6) on all T1/T2 Netlib and T1 MILP models.

**M4. Simplex (`lp`).** Bounded **dual simplex** with warm start `solve(model, basis=None, bound_overrides=None, added_rows=None)` returning status, x, y, z, basis, or a Farkas/unbounded ray. Dual steepest-edge with Devex fallback, Harris two-pass ratio test with **bound flipping**, cost perturbation with primal cleanup, basis-hash cycle detection, Bland's rule as last resort, singular-basis recovery by slack swap. **Primal simplex** for cleanup and as an escalation alternative. **Accept:** all T1/T2 Netlib models match the reference (1e-6); `afiro`, `sc50a`, `kb2` also in `naive_mode` (they should pass); warm-started re-solves use measurably fewer iterations than cold.

**M5. Interior point (`ipm`).** Mehrotra predictor-corrector for LP and convex QP (Q = 0 is the LP case): normal equations with sparse Cholesky, LDL^T on the regularized augmented system for general Q, proximal regularization, adaptive step length, divergence tests producing candidate Farkas/improving rays (accepted only if the safe check confirms). **Accept:** T1/T2 Netlib and all five QPs match the reference.

**M6. HPR engines (`lp/hpr.py`, `qp/hpr_qp.py`, `lp/hpr_batch.py`), JAX.** Halpern Peaceman-Rachford first-order method for LP and convex QP with restarts, one product with `A` and one with `A^T` per iteration, bound projections, residual checks every K iterations on **unscaled** KKT residuals. **Read the papers before coding** (HPR-LP arXiv:2408.12179, HPR-QP arXiv:2507.02470, GPU first-order relationships arXiv:2509.23903, batched first-order LP in MIP arXiv:2601.21990) and write `docs/hpr_notes.md` stating exactly what you implemented and any deviation from the paper; never claim equivalence you have not checked. Batched variant: state arrays shape `(n, B)`, per-column restart and step state, converged columns masked out. **Accept:** matches Netlib T1 references to 1e-4 unpolished and 1e-6 after crossover; batch of B scenarios equals B independent solves; the same code runs on CPU and, if present, GPU.

**M7. Crossover (`lp/crossover.py`).** From an HPR/IPM point: classify variables by distance to bounds and complementarity, build a crash basis, finish with dual simplex, remove shifts with primal simplex. Report whether the result is a basic optimal solution or `CERTIFIED_APPROXIMATE`. **Accept:** polish turns HPR output on T1/T2 into a basic optimal solution with the reference objective; time(engine + polish) is recorded against cold simplex.

**M8. Safe bounds and certificate (`certificate`).** See section 7. **Accept:** property test, for hundreds of random `y`, `LB(y) <= true optimum` on LP, separable QP and general QP; Farkas check returns True only for truly infeasible models.

**M9. Verifier (`nirbhar_verify`).** CLI and API: `verify(model_path, certificate_or_solution)`. Checks: model SHA-256 vs certificate; bound/row violations (abs and rel); integrality; recomputed objective; recomputed `LB(y)` and gap; Farkas/unbounded rays; re-derived cuts; reduced-cost fixings. `exact=True` converts every float to `Fraction` and returns exact objective and bound (and, for small LPs, an **exact basis proof**: solve `B x_B = b`, `B^T y = c_B` in rationals, confirm primal and dual feasibility). **Accept:** PASS on every honest solve; float and exact modes agree within the stated margin.

**M10. Certified branch-and-cut (`mip`, `cuts`).** Implement doc §6.8:
* root LP via the race, then the **root cut loop** (GMI, c-MIR, extended cover on knapsack rows; efficacy, parallelism and density filters; aging) with warm-started dual simplex re-solves; root heuristics;
* open-node pool; node selection `best-bound | best-estimate + plunging | depth-first`; activity-based propagation with safe rounding; **reduced-cost fixing certified through the term-wise split of `LB(y)`**;
* node LPs by warm-started dual simplex from the parent basis; infeasible nodes proven by Farkas ray (else kept open and flagged `unverified_infeasible`);
* branching `most-fractional | pseudocost | strong | reliability`; heuristics: rounding, diving (fractional/guided/coefficient), feasibility pump, RINS; every incumbent is re-verified before it is accepted;
* global bound = minimum over open nodes' safe bounds; gap formula as doc §6.8; counters mirror the certificate's `mip` block.
Cut derivation records (multipliers, bounds used, complementation flags, delta, cover set) go to the certificate. **Accept:** every T1 MILP reaches the reference optimum with verifier PASS; **brute-force parity** on 50 seeded random MILPs with <= 12 binaries; **cut-validity property test**: no known optimum is violated by any generated cut; no node is ever pruned without a recorded safe bound.

**M11. Convex QP and MIQP (`qp`, `mip`).** PSD check by Cholesky attempt with tolerance; non-PSD `Q` returns `UNSUPPORTED` with the reason (never solved as if convex). QP bound: closed-form separable Lagrangian bound for diagonal `Q`; tangent (outer-approximation) bound for general convex `Q`. Kelley fallback (epigraph variables + tangent rows with warm-started dual simplex) is P1. MIQP: branch-and-cut on certified QPs; two independent node paths (Kelley/LP vs IPM) must agree. **Accept:** all five QPs match the reference with bound <= primal; both MIQPs match the brute-force optimum; non-convex `Q` returns `UNSUPPORTED`.

**M12. Robustness controller and `naive_mode` (`robust`).** Health monitors per engine and the escalation table: stall -> perturb -> Devex/steepest-edge -> Bland; singular basis -> tighter refactorization -> slack swap -> rescale; inaccurate solves -> refinement; simplex failing -> IPM -> crossover; IPM failing -> regularization -> simplex/HPR; node LP failure -> alternate engine -> keep node open with the parent's safe bound; final `CERTIFIED_APPROXIMATE` or `NUMERICAL_ISSUE`. Every escalation is written to the certificate's `escalations[]` (symptom, detection, response, iteration). Hardening switches individually toggleable. `naive_mode` is a fair textbook configuration (no scaling, exact costs, textbook ratio test, Dantzig/largest-infeasibility pricing, refactor only when forced, no recovery; IPM without scaling or regularization and a fixed step; B&C with most-fractional, no presolve/cuts/heuristics), **not** a sabotaged one. A solve the verifier rejects counts as a failure. **Accept:** stress suite results as in 5.4; per-mechanism ablation ("one mechanism off at a time") table produced from real runs, including **residual hardened failures** (if none: "none observed on this suite").

**M13. Dispatcher, race, parallelism (`dispatch.py`, `race.py`).** Rules (doc §4.1): class and size decide; small LP -> dual simplex; root of a MIP -> **concurrent race** (simplex + IPM + HPR) where the **first result passing the safe-bound gap check wins**, losers are cancelled and their partial results discarded, never mixed; diagonal Q -> IPM; non-PSD Q -> `UNSUPPORTED`; GPU used only if present **and** a measured threshold says it wins. Thresholds come from a calibration file written by `bench/crossover_scale.py`; the dispatcher prints the reason for every choice. Multi-core via Numba `prange`/threads; scenario batches via worker pool or batched HPR. Parallel tree search (P1): shared incumbent, deterministic merge order. **Accept:** race result equals sequential result; scenario batch results equal independent solves to 1e-6; deterministic mode reproduces objectives exactly.

**M14. Explainability (`explain`).** Binding constraints, shadow prices and reduced costs in plain sentences; cost and RHS ranging from the optimal basis (verified by re-solving at the endpoints); state whether duals come from a basis (exact) or from an unpolished first-order solve (approximate). Infeasible models: Farkas ray, then **deletion filter** to an irreducible conflicting set, re-checked by the verifier. **Accept:** `galenet` returns an irreducible set (removing any one member makes it feasible); shadow prices on `afiro`/`sc50a` match finite-difference re-solves.

**M15. Plug-in registry (`extend`).** The eight interfaces: `Engine`, `Presolver`, `Propagator`, `BranchingRule`, `NodeSelector`, `Heuristic`, `CutGenerator`, `ModelClass`. **NIRBHAR's own components register through the same registry.** Ship one worked extension: a second `BranchingRule` added **without editing `bb.py`**. A `ModelClass` demo: a convex NLP via tangent relaxations, and a non-convex (bilinear pooling) example that returns `LOCAL_ONLY`, never `OPTIMAL`. **Accept:** registering the custom rule changes branching decisions and the certificate's `solve_path` names it.

**M16. Industrial generators (`industrial`).** Seeded, exportable to MPS/QPS, all tagged `SYNTHETIC - not MRPL data`: refinery (10 crudes, 4 periods, 6 products, CDU capacity, sulfur limit, inventory; LP; MILP with campaign/changeover binaries, big-M links, minimum run length; QP with a convex price-risk term; an over-constrained variant that is infeasible with a 3-row conflict; a scenario generator with perturbed prices/availability/demand), capacitated multi-item lot-sizing, transportation (+ fixed charge), unit commitment (MILP, MIQP, economic-dispatch QP), facility location, **known-optimum LP and QP generators** (built backwards from a primal-dual or KKT point). **Accept:** known-optimum generators reproduce their optimum to 1e-6; refinery LP/MILP/QP solve with verifier PASS; the infeasible variant returns `INFEASIBLE_CERTIFIED` with the designed conflict computed (not printed).

**M17. CLI and API (`cli.py`, `api.py`).**
```
nirbhar solve MODEL [--engine auto|dual|primal|ipm|hpr|race] [--presolve on|off] [--naive]
                    [--cuts on|off] [--verify float|exact] [--tol 1e-6] [--time-limit S]
                    [--threads N] [--deterministic] [--out cert.json]
nirbhar verify CERT.json MODEL            # runs nirbhar_verify only
nirbhar explain CERT.json MODEL
nirbhar bench netlib|miplib|qp|stress|scale|batch [--baseline highs]
nirbhar models                            # lists data/manifest.json
```
Python API: `nirbhar.load(path)`, `nirbhar.solve(model, **opts)`, `nirbhar.verify(model, cert, exact=False)`. Output: a readable report and `certificate.json`. **P2 bridge:** `nirbhar export-fixtures DIR` writes real run results (certificates, convergence traces, timings, tree events) as JSON so a UI or demo video can show genuine backend numbers; an optional stdlib `http.server` wrapper may serve the same JSON. **Accept:** `nirbhar solve data/netlib/afiro.mps --engine race --verify exact` prints a result, writes a certificate, and the verifier says PASS.

**M18. Benchmark harness (`bench`).** Netlib table (tune vs report), MIPLIB table, QP/MIQP table, stress table; **baselines HiGHS and MPAX run only here**; metrics: solved/total, shifted geometric mean of time (shift 10 s), median and worst ratio to HiGHS, time-to-first-incumbent, root gap closed by cuts, nodes; **crossover-size chart data** from a scale ladder of generated transportation LPs (32x32, 100x100, 316x316, 1000x1000 lanes) for simplex, IPM, HPR (+ HiGHS) **with timeouts recorded as timeouts, not dropped**; scenario-batch scaling (sequential vs pool vs batched HPR, break-even batch size); reliability table listing every failure by name; `bench/gpu_run.py` that runs the HPR benchmark on whatever device exists and records the device, FP64 throughput observed, and time (it must also run on a free Colab/Kaggle GPU; consumer GPUs have low FP64, so report FP32 vs FP64 honestly). **Accept:** `python -m bench.report` regenerates all tables as Markdown and CSV from raw run logs; losses to HiGHS appear.

# 7. SAFE BOUNDS AND CERTIFICATE

For `min c'x` s.t. `rl <= Ax <= ru`, `l <= x <= u`, and **any** `y` (clipped so that no term multiplies an infinite bound):

```
d  = c - A'y
LB(y) = sum_r ( max(y_r,0) * rl_r + min(y_r,0) * ru_r )  +  sum_j ( max(d_j,0) * l_j + min(d_j,0) * u_j )
```

with the convention `0 * inf = 0`; any `y_r > 0` with `rl_r = -inf` (or the analogous case) makes the bound `-inf`, so clip `y` instead. This is a valid lower bound for every `y`, which is what makes it safe. Float64 evaluation adds a conservative error allowance proportional to `(n+m) * eps * sum |terms|`; exact mode evaluates in `Fraction`. Separable convex QP (diagonal `Q`, `q_j > 0`): replace the `x_j` term by the closed-form minimum of `d_j x + 0.5 q_j x^2` over `[l_j, u_j]`. General convex QP: linearize at a point `x0` (`f(x) >= f(x0) + grad f(x0)'(x - x0)`) and apply the LP bound. Infeasibility proof: with `c = 0`, a `y` with `LB(y) > 0`. Unboundedness proof: a feasible point plus a recession ray `r` with `c'r < 0` and all row/bound conditions satisfied. Reduced-cost fixing: for a column with `d_j > 0`, if `LB(y) + d_j (u_j - l_j) > UB` then `x_j` can be fixed at `l_j` (mirror for `d_j < 0`).

**Certificate (`certificate.json`)**: follow doc §7 exactly; minimum fields: `schema_version`, `status`, `model{name, sha256, class, rows, cols, nnz, integers}`, `objective`, `bound{value, arithmetic: "float64+margin"|"exact-rational", evaluated_on: "original-model"}`, `gap{abs, rel}`, `violations{row, bound, integrality}`, `hardware{cpu, threads, gpu: "none" | device name, jax_backend, fp64_used}`, `solve_path[]` (every registered component that ran, including plug-ins), `escalations[]`, `mip{nodes, open, pruned_by_safe_bound, infeasible_with_farkas, kept_open_due_to_weak_bound, fixed_by_reduced_cost, incumbent_updates, cuts[{type, efficacy, derivation}]}`, `timing_s{parse, presolve, dispatch, engine, crossover, tree, postsolve, verify}`, `duals`, `explanation`, `verifier{verdict, mode, version}`. **Status taxonomy:** `OPTIMAL`, `OPTIMAL_WITHIN_GAP`, `CERTIFIED_APPROXIMATE`, `INFEASIBLE_CERTIFIED`, `UNBOUNDED_CERTIFIED`, `TIME_LIMIT`, `NUMERICAL_ISSUE`, `UNSUPPORTED`, `LOCAL_ONLY`. `OPTIMAL` requires gap within tolerance **and** verifier PASS; otherwise the honest weaker status.

# 8. PERFORMANCE EXPECTATIONS (honest targets, not claims)

Python + Numba is not C++. Targets for a competent first version: all T1 Netlib models solve in seconds; T2 in under a minute with sparse LU; T1 MILP prove optimality within the time limit, with HiGHS node and time numbers above as calibration only. Do not tune toward a benchmark by editing instances. Anything beyond that (for example hundreds of thousands of variables on a GPU) is a **production target**: measure what you can, label the rest, and never put an unmeasured number in a report.

# 9. DESIGN DETAILS THAT MATTER

1. Tolerances are relative to row/column norms and evaluated unscaled.
2. Every engine returns a `Result` with raw `x`, `y`, `z`, basis (if any), a safe bound, and a health log; nobody mixes partial results from cancelled engines.
3. Numba functions take plain arrays and return plain arrays; orchestration stays in Python.
4. Logging is structured (JSON lines) with a human summary; no `print` in library code.
5. Time limits and `KeyboardInterrupt` are honoured everywhere, with partial-result certificates.
6. Public API is typed and documented; plug-in interfaces are `Protocol`s with contract tests.
7. Memory: nothing O(n^2) dense for models above a few hundred rows except in clearly marked small-model paths.
8. Keep a `docs/ARCHITECTURE.md` that mirrors the deck's diagram (Prepare and Route, LP/QP engines, MILP certified tree, Certify, across every stage).

# 10. TEST PLAN (pytest, driven by `data/manifest.json`)

`tests/test_parser.py` (manifest counts, traps in 5.5), `test_linalg.py`, `test_presolve_postsolve.py`, `test_lp_engines.py` (each engine on tune+report T1/T2), `test_safe_bound_property.py`, `test_verifier.py`, `test_adversarial.py`, `test_milp.py` (T1 optimum, brute-force parity), `test_cuts_valid.py`, `test_qp_miqp.py`, `test_stress.py` (naive vs hardened per 5.4), `test_status_models.py`, `test_explain.py`, `test_race_parallel.py`, `test_determinism.py`, `test_plugins.py`, `test_cli.py`, `test_import_rules.py` (runs `tools/check_imports.py`).

**Adversarial suite (the "proof, not just a checker" claim):** corrupt a correct result seven ways: violate a row, flip an integer, alter the objective, supply a random `y` (must give a weaker valid bound or FAIL, never a stronger invalid one), corrupt a cut multiplier, forge an infeasibility ray, tamper with the model hash. The verifier must reject or downgrade **all seven**; the harness prints the rejection rate (target 100%).

Mark long benchmarks `@pytest.mark.slow` so `pytest -m "not slow"` runs in minutes.

# 11. BUILD ORDER AND CHECKPOINTS

Stop after each phase, run `pytest -m "not slow"` and `tools/check_imports.py`, and show me the real output. Do not start the next phase until the phase's Accept items pass.

* **Phase 0:** repo scaffold, `requirements.txt`, import-check script, manifest loader, pytest harness, CSR/CSC, **M1 parser/model/writer** (all manifest models parse).
* **Phase 1 (engine core):** dense then sparse LU (M2), **dual + primal simplex (M4)**, safe bound and certificate builder (M8), **verifier float mode (M9)**, minimal CLI `solve`/`verify`. All T1 Netlib models `OPTIMAL` + PASS.
* **Phase 2:** scaling and presolve/postsolve (M3), **Mehrotra IPM (M5)**, **robustness controller and `naive_mode` (M12)**, T2 Netlib, stress suite S1/S2, status models, explainability for infeasibility (M14).
* **Phase 3:** **JAX HPR LP/QP/batched (M6)**, crossover (M7), **dispatcher and race (M13)**, crossover-size calibration, first GPU measurement if hardware exists.
* **Phase 4:** **certified branch-and-cut (M10)**: tree, propagation, reduced-cost fixing, branching, node warm starts; T1 MILP optimal; then cuts, heuristics, brute-force and cut-validity property tests.
* **Phase 5:** **QP and MIQP (M11)**, parallel tree (P1), **exact verifier mode and adversarial suite (M9)**, VIPR-style cut re-derivation.
* **Phase 6:** shadow prices/ranging (M14), plug-in registry and worked extension (M15), industrial generators and refinery LP/MILP/QP/scenario batch (M16), full CLI/API and `export-fixtures` (M17).
* **Phase 7:** benchmark harness and report generation (M18), `docs/instances.md`, `docs/KNOWN_LIMITS.md`, `docs/hpr_notes.md`, final full test run, README (how to run, how to benchmark, how to run `bench/gpu_run.py` on a free GPU).

If time forces cuts, drop in this order: Mittelmann/MPAX baseline, parallel tree search, strong-branching on GPU, ranging, ModelClass NLP demo, extended cover cuts, Kelley fallback. **Never drop:** the safe bound, the verifier, the adversarial suite, certified pruning, the race, naive-vs-hardened on the stress suite, the Netlib and MIPLIB T1 benchmarks, and the honest reliability table.

# 12. THINGS NOT TO DO

* No solver library, SciPy, CVXPY, HiGHS or MPAX inside `nirbhar/` or `nirbhar_verify/`; no imports from `nirbhar/` into the verifier.
* No hardcoded results, canned logs, or invented baseline numbers; no editing instance data to make a test pass without a logged rule.
* No "OPTIMAL" from a first-order answer without a bound and verifier PASS; no claims of GPU use, GPU speedups, or parity with commercial solvers that were not measured on this machine and recorded in the certificate.
* Do not tune on `report` instances; do not drop failures from tables.
* Do not hand-type model data; use `data/` only.

# 13. DELIVERABLES

Working package and verifier; `pytest -m "not slow"` green and `tools/check_imports.py` green; benchmark reports (Markdown + CSV) for Netlib, MIPLIB, QP/MIQP, stress, crossover scale and scenario batch; `docs/{ARCHITECTURE,instances,KNOWN_LIMITS,hpr_notes}.md`; `README.md`. `KNOWN_LIMITS.md` must honestly list what the build does not do (for example dense paths remaining, GPU measured or not, MILP scale reached, HPR deviations from the papers).

Begin with a written plan (architecture, file tree, risks, phase schedule, and which phase-1 acceptance tests you will run first) for my approval, then start Phase 0.
