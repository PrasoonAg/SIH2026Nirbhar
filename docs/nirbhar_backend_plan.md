# NIRBHAR Backend — Phased Build Plan
## Python Certified Hybrid CPU-GPU Solver Core (SIH 2026)

> **Source of truth:** `NIRBHAR-Backend-Antigravity-Run-Prompt (1).md`
> **Data pack:** `data/` folder (already complete — 26 Netlib, 18 MILP, 5 QP, 2 MIQP, 9 stress, 3 infeas, manifest.json)
> **Repository:** A new Python package directory, separate from the TypeScript frontend prototype.

---

## Repository Root

```
nirbhar-backend/           ← new directory (separate from Prototype/)
  nirbhar/                 ← solver package (sovereignty-guarded)
  nirbhar_verify/          ← verifier package (imports NOTHING from nirbhar/)
  bench/                   ← baselines (HiGHS, MPAX allowed here only)
  tests/                   ← pytest suite
  data/ → symlink or copy of Prototype/data/
  tools/
  docs/
  requirements.txt
  requirements-bench.txt
  pyproject.toml
  README.md
```

---

## Hard Rules (Never Violate)

> [!CAUTION]
> These rules apply to every line of code across all phases. Violations break the sovereignty audit.

1. `nirbhar/` and `nirbhar_verify/` import **no solver library** — no SciPy, CVXPY, HiGHS, MPAX, OR-Tools, PuLP, Pyomo. Allowed: `stdlib`, `numpy`, `numba`, `jax`.
2. `nirbhar_verify/` imports **nothing** from `nirbhar/` — full isolation enforced by `tools/check_imports.py`.
3. `SciPy`, `highspy`, `mpax` allowed **only** in `bench/` and `tests/`.
4. **No hardcoded objectives, timings, or "naive fails" outcomes.** Every result is computed.
5. `OPTIMAL` status emitted only when certified gap ≤ tol **AND** verifier returns PASS.
6. No GPU claims unless a GPU device actually ran and was timed in the certificate.
7. Fixed seeds everywhere; `--deterministic` mode must reproduce identical objectives.

> [!IMPORTANT]
> After every phase: run `pytest -m "not slow"` + `tools/check_imports.py` and confirm PASS before proceeding.

---

## Never-Drop Items (across all phases)

- Safe bounds (`LB(y)`) and the certified gap
- The independent verifier (`nirbhar_verify/`)
- The adversarial suite (7-way corruption rejection)
- Certified pruning (no node pruned without a recorded safe bound)
- The concurrent root race
- Naive-vs-hardened on the stress suite
- Netlib and MIPLIB T1 benchmarks
- The honest reliability table

---

## Phase 0 — Scaffold, Parser, Manifest Harness

**Duration estimate: ~1–2 days**

### Goals
- Stand up the repo structure, dependency pinning, sovereignty guard, and the MPS/QPS parser.
- Everything from this phase must remain green in all subsequent phases.

### Deliverables

**Repo scaffold**
```
pyproject.toml               # package metadata, entry points
requirements.txt             # numpy, numba, jax[cpu]
requirements-bench.txt       # highspy, scipy, mpax
tools/check_imports.py       # AST-scan sovereignty guard
docs/ARCHITECTURE.md         # skeleton (fill fully in Phase 7)
docs/KNOWN_LIMITS.md         # running log of honest limitations
docs/instances.md            # instance selection rules (fill as needed)
```

**Module M1 — Parser and Model (nirbhar/io/)**
```
nirbhar/io/mps.py            # fixed+free MPS parser
nirbhar/io/qps.py            # QUADOBJ/QMATRIX extension
nirbhar/io/model.py          # immutable Model dataclass
nirbhar/io/writer.py         # MPS/QPS round-trip writer
```

**Model dataclass fields:**
`c`, `A` (CSR + CSC), `row_lo`, `row_hi`, `col_lo`, `col_hi`, `integrality`, `Q` (optional upper triangle), `names`, `sense`, `constant`, `sha256` of original text.

**Manifest loader + pytest harness**
```
tests/conftest.py            # loads data/manifest.json, parametrizes fixtures
tests/test_parser.py         # manifest counts, parser traps (§5.5)
tests/test_import_rules.py   # calls tools/check_imports.py, asserts exit 0
```

**Parser traps (must have dedicated unit tests):**
- `dcmulti.mps`: `IMPORTANCES` block after `ENDATA` → must be ignored
- `forplan.mps`: `RANGES` section
- `misc03.mps`: `FR` bound
- Inline snippets: `MI`, `PL`, `LI`, `UI`, negative `UP` with zero lower, `BV`, RANGES on E rows (sign of R decides), objective-row RHS (sign flipped), `OBJSENSE MAX`

**CSR/CSC data structures**
```
nirbhar/sparse/csr.py        # CSRMatrix: data, indices, indptr, shape + ops
nirbhar/sparse/csc.py        # CSCMatrix
nirbhar/sparse/ops.py        # spmv, spmm stubs
```

### Acceptance Tests (Phase 0)
- Every model in `data/manifest.json` parses with rows/cols/nnz/integers matching the manifest.
- Round-trip: write MPS then re-parse → same objective value.
- Malformed MPS files produce line-numbered errors.
- `tools/check_imports.py` exits 0 on the scaffold.
- `pytest -m "not slow"` green.

---

## Phase 1 — Engine Core: Simplex + Safe Bounds + Verifier

**Duration estimate: ~4–5 days**

### Goals
- All T1 Netlib LPs solved to OPTIMAL with verifier PASS.
- The fundamental solver loop is proven correct before adding complexity.

### Deliverables

**Module M2 — Sparse Linear Algebra (nirbhar/sparse/, nirbhar/linalg/)**
```
nirbhar/linalg/lu_markowitz.py   # dense LU to start; Markowitz pivot in Phase 2
nirbhar/linalg/lu_update.py      # product-form eta, refactorization triggers
nirbhar/linalg/refine.py         # iterative refinement (1-2 steps)
nirbhar/linalg/condest.py        # Hager 1-norm condition estimate
```
*Start with dense LU for bases ≤ few hundred rows. Document in KNOWN_LIMITS.md. Replace with sparse Markowitz LU in Phase 2.*

**Module M4 — Dual + Primal Simplex (nirbhar/lp/)**
```
nirbhar/lp/basis.py             # basis representation, factorization triggers
nirbhar/lp/dual_simplex.py      # warm-startable solve(model, basis, bound_overrides, added_rows)
                                 # → Result(status, x, y, z, basis) | FarkasRay | UnboundedRay
nirbhar/lp/primal_simplex.py    # for cleanup and escalation fallback
```

**Dual simplex features:**
- Dual steepest-edge with Devex fallback
- Harris two-pass ratio test with bound flipping
- Cost perturbation with primal cleanup
- Basis-hash cycle detection
- Bland's rule as last resort
- Singular-basis recovery by slack swap

**Module M8 — Safe Bounds + Certificate Builder (nirbhar/certificate/)**
```
nirbhar/certificate/safe_bound.py   # LB(y) for LP, separable QP, general QP
                                     # Farkas and unboundedness ray checks
nirbhar/certificate/builder.py      # fills all schema fields from Result
nirbhar/certificate/schema.py       # TypedDict / dataclass for certificate.json
```

**LB(y) formula:**
```
d  = c - A'y
LB(y) = Σ_r [max(y_r,0)·rl_r + min(y_r,0)·ru_r]
       + Σ_j [max(d_j,0)·l_j + min(d_j,0)·u_j]
convention: 0·inf = 0; clip y_r > 0 when rl_r = -inf
error allowance: (n+m)·eps·Σ|terms|
```

**Module M9 — Verifier float mode (nirbhar_verify/)** — ISOLATED PACKAGE
```
nirbhar_verify/mps_min.py        # minimal MPS reader (no import from nirbhar/)
nirbhar_verify/verify.py         # verify(model_path, cert) → VerifierResult
nirbhar_verify/exact.py          # stub for Phase 5
nirbhar_verify/cuts_check.py     # stub for Phase 5
nirbhar_verify/rays.py           # Farkas/unbounded ray verification
nirbhar_verify/cli.py            # nirbhar verify CERT.json MODEL
```

**Verifier checks (float mode):**
- SHA-256 of original model text vs certificate
- Bound and row violations (absolute and relative)
- Integrality violations
- Recomputed objective
- Recomputed LB(y) and gap
- Farkas/unbounded rays

**Minimal CLI**
```
nirbhar/cli.py                  # nirbhar solve MODEL --engine dual --verify float
nirbhar/api.py                  # nirbhar.load(), nirbhar.solve(), nirbhar.verify()
```

**Tests**
```
tests/test_linalg.py            # residual tests on random + Netlib-derived bases
tests/test_lp_engines.py        # dual simplex on T1 tune-set Netlib LPs
tests/test_safe_bound_property.py  # ∀ random y: LB(y) ≤ true optimum
tests/test_verifier.py          # PASS on all honest T1 solves
tests/test_cli.py               # nirbhar solve afiro.mps → PASS
```

### Acceptance Tests (Phase 1)
- All T1 Netlib LPs → OPTIMAL, verifier PASS, |obj − ref| / max(1, |ref|) ≤ 1e-6.
- `afiro`, `sc50a`, `kb2` also pass in `naive_mode`.
- Warm-started re-solves use measurably fewer iterations than cold starts.
- Safe bound property test: hundreds of random y → LB(y) ≤ true optimum.
- `nirbhar solve data/netlib/afiro.mps --engine dual --verify float` → PASS.

---

## Phase 2 — Scaling, Presolve/Postsolve, IPM, Robustness, Status Models

**Duration estimate: ~5–6 days**

### Goals
- T2 Netlib LPs solved. Stress suite S1/S2 hardened. Status models certified (INFEASIBLE, UNBOUNDED).

### Deliverables

**Module M2 (continued) — Sparse Markowitz LU**
```
nirbhar/linalg/lu_markowitz.py   # replace dense with Markowitz pivot + hypersparse solves
nirbhar/linalg/cholesky.py       # for IPM
nirbhar/linalg/ldlt.py           # for regularized augmented system (QP)
```
*Remove dense-LU-only restriction from KNOWN_LIMITS.md.*

**Module M3 — Scaling + Presolve/Postsolve (nirbhar/presolve/)**
```
nirbhar/presolve/scaling.py      # geometric-mean + Ruiz (simplex/IPM), Ruiz×10 (HPR)
nirbhar/presolve/reductions.py   # each reduction as a class with on/off switch + postsolve record:
                                  #   empty rows/cols, fixed vars, duplicates,
                                  #   singleton rows→bounds, forcing/redundant rows,
                                  #   activity-based bound tightening, dual fixing,
                                  #   doubleton aggregation, integer rounding,
                                  #   big-M coefficient tightening, probing (MILP)
nirbhar/presolve/postsolve.py    # rebuild primal, duals, basis in original space
nirbhar/presolve/stack.py        # ordered reduction stack for correct undo
```

**Module M5 — Mehrotra IPM (nirbhar/ipm/)**
```
nirbhar/ipm/mehrotra.py          # predictor-corrector for LP (Q=0) + convex QP
                                  # normal equations + sparse Cholesky
                                  # LDL^T on regularized augmented system for general Q
                                  # proximal regularization, adaptive step length
                                  # divergence tests → Farkas/improving rays (safe-checked)
```

**Module M12 — Robustness Controller + naive_mode (nirbhar/robust/)**
```
nirbhar/robust/switches.py       # per-engine hardening toggle dataclass
nirbhar/robust/naive_mode.py     # fair textbook config:
                                  #   no scaling, exact costs, Dantzig pricing,
                                  #   largest-infeasibility test, refactor only when forced,
                                  #   no recovery; IPM: no scaling/reg, fixed step;
                                  #   B&C: most-fractional, no presolve/cuts/heuristics
nirbhar/robust/controller.py     # health monitors + escalation table:
                                  #   stall → perturb → Devex → Bland
                                  #   singular basis → refactorize tighter → slack swap → rescale
                                  #   inaccurate → refinement
                                  #   simplex fail → IPM → crossover
                                  #   IPM fail → regularize → simplex/HPR
                                  #   node LP fail → alternate engine → keep open with parent bound
                                  #   final: CERTIFIED_APPROXIMATE or NUMERICAL_ISSUE
                                  # every escalation written to certificate escalations[]
```

**Module M14 (partial) — Infeasibility explanation (nirbhar/explain/iis.py)**
- Farkas ray extraction → deletion filter → IIS (irreducible conflicting set)
- `galenet.mps` must return computed 3-row conflict, not a printed one.

**Tests**
```
tests/test_lp_engines.py         # extend to T2 Netlib
tests/test_presolve_postsolve.py # presolve→solve→postsolve feasible + same obj (T1/T2, T1 MILP)
tests/test_stress.py             # naive vs hardened on §5.4 stress suite
tests/test_status_models.py      # galenet → INFEASIBLE_CERTIFIED; tiny_unbounded → UNBOUNDED_CERTIFIED
```

### Acceptance Tests (Phase 2)
- T2 Netlib LPs → OPTIMAL + verifier PASS.
- Stress suite S1 (Beale cycling): naive_mode fails or loops, hardened → OPTIMAL.
- Stress suite S2 (1e6 rescaled): hardened either matches true optimum OR returns CERTIFIED_APPROXIMATE/NUMERICAL_ISSUE — never a wrong OPTIMAL.
- galenet → INFEASIBLE_CERTIFIED; removing any one of the 3 conflict rows makes it feasible.
- Presolve → solve → postsolve: feasible in original space, same objective (1e-6).

---

## Phase 3 — JAX HPR, Crossover, Dispatcher + Race

**Duration estimate: ~5–6 days**

### Goals
- HPR-family first-order engine operational on CPU (GPU if available). Concurrent root race working.

### Deliverables

**Module M6 — HPR Engines (nirbhar/lp/hpr.py, qp/hpr_qp.py, lp/hpr_batch.py), JAX**

> [!IMPORTANT]
> Read the papers before coding: HPR-LP arXiv:2408.12179, HPR-QP arXiv:2507.02470, GPU relationships arXiv:2509.23903, batched first-order LP arXiv:2601.21990. Write `docs/hpr_notes.md` stating exactly what was implemented and any deviation. Never claim equivalence not verified.

```
nirbhar/lp/hpr.py             # Halpern-anchored PDHG-type for LP
                               # restarts, A + A^T products per iter (own CSR)
                               # bound projections, residual check every K iters
                               # stopping on unscaled KKT residuals
nirbhar/qp/hpr_qp.py          # HPR-QP-family for diagonal Q via same machinery
nirbhar/lp/hpr_batch.py       # batched: state shape (n, B)
                               # per-column restart/step state
                               # converged columns masked out
docs/hpr_notes.md             # what was implemented, deviations from papers
```

**Enable JAX x64 globally:**
```python
import jax
jax.config.update("jax_enable_x64", True)
```

**Module M7 — Crossover (nirbhar/lp/crossover.py)**
```
# from HPR/IPM point:
# classify vars by distance to bounds + complementarity
# build crash basis, finish with dual simplex, remove shifts with primal simplex
# report CERTIFIED_APPROXIMATE vs basic optimal
```

**Module M13 — Dispatcher + Race (nirbhar/dispatch.py, nirbhar/race.py)**
```
nirbhar/dispatch.py           # rules §4.1:
                               #   small LP → dual simplex
                               #   MIP root → concurrent race
                               #   diagonal Q → IPM; non-PSD Q → UNSUPPORTED
                               #   GPU only if present + measured threshold says it wins
                               #   thresholds from bench/crossover_scale.py calibration file
                               #   prints reason for every choice

nirbhar/race.py               # concurrent race: simplex + IPM + HPR in threads
                               # first result passing safe-bound gap check wins
                               # losers cancelled, partial results discarded, never mixed
                               # deterministic mode: fixed thread count + merge order
```

**Crossover-size calibration**
```
bench/crossover_scale.py      # scale ladder: 32x32, 100x100, 316x316, 1000x1000 transport LPs
                               # simplex, IPM, HPR (+ HiGHS if loaded)
                               # timeouts recorded as timeouts, not dropped
                               # writes calibration JSON for dispatcher
```

**GPU measurement (if hardware exists)**
```
bench/gpu_run.py              # runs HPR benchmark on available device
                               # records: device name, FP64 throughput, time
                               # reports FP32 vs FP64 honestly
                               # also runnable on free Colab/Kaggle GPU
```

**Tests**
```
tests/test_lp_engines.py       # HPR on T1/T2: ≤1e-4 unpolished, ≤1e-6 after crossover
tests/test_race_parallel.py    # race result equals sequential result
tests/test_determinism.py      # --deterministic reproduces identical objectives
```

### Acceptance Tests (Phase 3)
- HPR matches Netlib T1 references to 1e-4 unpolished, 1e-6 after crossover.
- Batch of B scenarios equals B independent solves.
- Same JAX code runs on CPU (and GPU if available).
- Race result equals sequential result; losers' partial results never appear.
- Dispatcher prints reason for every choice.

---

## Phase 4 — Certified Branch-and-Cut, MILP T1

**Duration estimate: ~6–7 days**

### Goals
- All T1 MIPLIB MILPs solved to proven optimality with certified tree. Brute-force parity. Cut validity.

### Deliverables

**Module M10 — Certified B&C (nirbhar/mip/, nirbhar/cuts/)**
```
nirbhar/mip/bb.py              # main B&C loop:
                                #   root LP via race → safe bound → root cut loop
                                #   open-node pool with priority queue
                                #   node LPs by warm-started dual simplex from parent basis
                                #   infeasible nodes: Farkas ray → verified; else kept open
                                #   PRUNE only when node safe bound ≥ UB − tol
                                #   integer-feasible nodes: re-verified before accepting
                                #   global bound = min over open nodes' safe bounds
                                #   counters: nodes, open, pruned_by_safe_bound,
                                #     infeasible_with_farkas, kept_open_due_to_weak_bound,
                                #     fixed_by_reduced_cost, incumbent_updates

nirbhar/mip/propagate.py       # activity-based propagation with safe rounding
nirbhar/mip/branching.py       # most-fractional | pseudocost | strong | reliability
nirbhar/mip/nodesel.py         # best-bound | best-estimate+plunging | depth-first
nirbhar/mip/heuristics.py      # rounding, diving (fractional/guided/coeff), feasibility pump, RINS
nirbhar/mip/reduced_cost_fix.py  # certified via term-wise split of LB(y)
nirbhar/mip/parallel_tree.py   # P1: 2-4 workers, shared incumbent, deterministic merge

nirbhar/cuts/gmi.py            # GMI via safe aggregation + MIR with directed rounding
nirbhar/cuts/cmir.py           # c-MIR with δ search and greedy aggregation
nirbhar/cuts/cover.py          # extended cover on knapsack rows
nirbhar/cuts/pool.py           # efficacy, parallelism, density filters + aging
nirbhar/cuts/derivation.py     # derivation record: multipliers, bounds, complementation,
                                #   delta, cover set → goes into certificate
```

**Cut validity rules:**
- Safe aggregation: multipliers derived from valid dual solution
- Directed rounding: round in direction that preserves validity
- Every cut carries a derivation record the verifier can re-derive in exact arithmetic

**Tests**
```
tests/test_milp.py             # T1 MIPLIB → reference optimum + verifier PASS
                                # brute-force parity on 50 seeded random MILPs (≤12 binaries)
tests/test_cuts_valid.py       # no known optimum violated by any generated cut
```

### Acceptance Tests (Phase 4)
- Every T1 MIPLIB instance → reference optimum + verifier PASS.
- Brute-force parity: B&C objective matches exhaustive enumeration on all 50 seeded random MILPs.
- Cut-validity property test: 0 violations across random MILP set.
- No node ever pruned without a recorded safe bound.
- Warm-started node LP uses fewer iterations than cold.

---

## Phase 5 — QP/MIQP, Exact Verifier, Adversarial Suite

**Duration estimate: ~4–5 days**

### Goals
- All 5 QPs and 2 MIQPs solved. Exact verifier with BigInt-equivalent (`fractions.Fraction`). All 7 adversarial corruptions rejected.

### Deliverables

**Module M11 — QP and MIQP (nirbhar/qp/)**
```
nirbhar/qp/ipm_qp.py          # IPM for convex QP (already partial from M5 extension)
nirbhar/qp/bounds.py           # PSD check by Cholesky attempt with tolerance
                                # non-PSD → UNSUPPORTED with reason
                                # QP safe bound: closed-form separable Lagrangian (diagonal Q)
                                # tangent OA bound for general convex Q
nirbhar/qp/kelley.py           # P1: Kelley fallback (epigraph vars + tangent rows)
```

**MIQP:** branch-and-cut on certified QPs; two independent node paths (Kelley/LP vs IPM) must agree.

**Module M9 (complete) — Exact Verifier (nirbhar_verify/)**
```
nirbhar_verify/exact.py        # every float → Fraction, exact dot products
                                # exact objective + bound as fractions + decimals
                                # exact basis proof for small LPs:
                                #   solve B x_B = b, B^T y = c_B in rationals
                                #   confirm primal + dual feasibility → proven optimal
nirbhar_verify/cuts_check.py   # re-derive each cut in exact arithmetic from derivation record
```

**Adversarial suite** (in `tests/test_adversarial.py`)
Seven corruption modes, each must be **rejected or downgraded**:
1. Violate a row constraint
2. Flip an integer variable value
3. Alter the objective value
4. Supply a random `y` → must give weaker valid bound or FAIL, never stronger invalid one
5. Corrupt a cut multiplier in the derivation record
6. Forge an infeasibility ray
7. Tamper with the model hash (SHA-256 mismatch)

Target: 100% adversarial rejection rate.

**Tests**
```
tests/test_qp_miqp.py          # all 5 QPs match reference with bound ≤ primal
                                # both MIQPs match brute-force optimum
                                # non-convex Q → UNSUPPORTED
tests/test_verifier.py         # extend: exact mode agrees with float within stated margin
                                # exact basis proof for small LPs
tests/test_adversarial.py      # 7-corruption adversarial suite, 100% rejection rate
```

### Acceptance Tests (Phase 5)
- All 5 QP references matched with bound ≤ primal.
- Both MIQPs match brute-force optimum; two independent node paths agree.
- Non-convex Q → `UNSUPPORTED`, never solved as if convex.
- Exact verifier agrees with float mode within stated margin.
- 7/7 adversarial corruptions rejected.

---

## Phase 6 — Explainability, Plug-ins, Industrial Generators, Full CLI/API

**Duration estimate: ~5–6 days**

### Goals
- Shadow prices, IIS, ranging working. Refinery LP/MILP/QP/batch running. Plug-in registry with worked extension. Full CLI commands.

### Deliverables

**Module M14 — Full Explainability (nirbhar/explain/)**
```
nirbhar/explain/duals.py       # binding constraints, shadow prices, reduced costs
                                # in plain sentences
                                # state: basis (exact) vs unpolished first-order (approximate)
nirbhar/explain/ranging.py     # cost + RHS ranging from optimal basis
                                # verified by re-solving at range endpoints
nirbhar/explain/iis.py         # (already started Phase 2) full IIS with deletion filter
nirbhar/explain/report.py      # plain-language report builder
```

**Accept for M14:**
- `galenet` → IIS computed (not hardcoded); removing any one member makes it feasible.
- Shadow prices on `afiro`/`sc50a` match finite-difference re-solves.

**Module M15 — Plug-in Registry (nirbhar/extend/)**
```
nirbhar/extend/interfaces.py   # Protocol definitions:
                                #   Engine, Presolver, Propagator, BranchingRule,
                                #   NodeSelector, Heuristic, CutGenerator, ModelClass
nirbhar/extend/registry.py     # central registry; NIRBHAR's own components register here
                                # worked extension: second BranchingRule added without editing bb.py
                                # ModelClass demo: convex NLP via tangent relaxations
                                #   non-convex (bilinear pooling) → LOCAL_ONLY, never OPTIMAL
```

**Module M16 — Industrial Generators (nirbhar/industrial/)**
```
nirbhar/industrial/refinery.py      # 10 crudes, 4 periods, 6 products, CDU, sulfur, inventory
                                     # LP + MILP (campaign/changeover) + QP (price-risk)
                                     # over-constrained infeasible variant (3-row conflict)
                                     # scenario generator (perturbed prices/availability/demand)
nirbhar/industrial/lotsizing.py     # capacitated multi-item lot-sizing MILP
nirbhar/industrial/transport.py     # transportation LP + fixed-charge MILP
nirbhar/industrial/unit_commit.py   # MILP + MIQP + economic-dispatch QP
nirbhar/industrial/facility.py      # facility-location MILP
nirbhar/industrial/known_opt.py     # LP generator (backwards from primal-dual pair)
                                     # QP generator (from chosen KKT point)
```

All generators: seeded, exportable to MPS/QPS, tagged `SYNTHETIC - not MRPL data`.

**Module M17 — Full CLI and API**
```
nirbhar/cli.py                 # complete command set:
#   nirbhar solve MODEL [--engine auto|dual|primal|ipm|hpr|race]
#                       [--presolve on|off] [--naive] [--cuts on|off]
#                       [--verify float|exact] [--tol 1e-6]
#                       [--time-limit S] [--threads N] [--deterministic]
#                       [--out cert.json]
#   nirbhar verify CERT.json MODEL
#   nirbhar explain CERT.json MODEL
#   nirbhar bench netlib|miplib|qp|stress|scale|batch [--baseline highs]
#   nirbhar models
#   nirbhar export-fixtures DIR     # P2: write JSON for UI/demo

nirbhar/api.py                 # nirbhar.load(path), nirbhar.solve(model, **opts)
                                # nirbhar.verify(model, cert, exact=False)
```

**Tests**
```
tests/test_explain.py          # galenet IIS, shadow prices on afiro/sc50a
tests/test_plugins.py          # custom BranchingRule changes decisions
                                # certificate solve_path names the plug-in
tests/test_cli.py              # extend: all commands; export-fixtures produces loadable JSON
```

### Acceptance Tests (Phase 6)
- Known-optimum generators reproduce their optimum to 1e-6.
- Refinery LP/MILP/QP solve with verifier PASS; infeasible variant → INFEASIBLE_CERTIFIED with computed 3-row conflict.
- Registering custom BranchingRule changes branching decisions; certificate names it.
- `nirbhar solve data/netlib/afiro.mps --engine race --verify exact` → PASS.
- `nirbhar explain cert.json model.mps` produces readable output.

---

## Phase 7 — Benchmark Harness, Reports, Documentation

**Duration estimate: ~3–4 days**

### Goals
- Full benchmark suite runnable. All reports regenerable from raw logs. Documentation complete.

### Deliverables

**Module M18 — Benchmark Harness (bench/)**
```
bench/harness.py               # runs solver on manifest entries, writes raw JSON logs
bench/baselines.py             # HiGHS and MPAX baselines (only place they're allowed)
bench/crossover_scale.py       # scale ladder: 32x32→100x100→316x316→1000x1000 transport LPs
                                # timeouts drawn as timeouts, never dropped
bench/stress.py                # stress suite: naive vs hardened, one-mechanism-off ablation
bench/reliability.py           # reliability table: per instance set solved/total,
                                # every failure listed by name
bench/report.py                # python -m bench.report → Markdown + CSV tables:
                                #   Netlib (tune vs report), MIPLIB, QP/MIQP, stress,
                                #   crossover scale, scenario batch
                                #   SGM10 (shift 10s), median/worst ratio to HiGHS
                                #   losses to HiGHS appear explicitly
bench/gpu_run.py               # HPR on available device; FP32 vs FP64 honest
```

**Documentation**
```
docs/ARCHITECTURE.md           # full diagram: Prepare+Route, LP/QP engines,
                                #   MILP certified tree, Certify stages
docs/KNOWN_LIMITS.md           # final honest state: dense paths remaining,
                                #   GPU measured or not, MILP scale reached,
                                #   HPR deviations from papers
docs/hpr_notes.md              # what was implemented; deviations from arXiv papers
docs/instances.md              # instance selection rules for stress suite
README.md                      # how to run, how to benchmark,
                                #   how to run bench/gpu_run.py on a free Colab GPU
```

**Final test run**
- `pytest -m "not slow"` → all green
- `pytest -m "slow" --timeout=300` → T3 stretch instances
- `tools/check_imports.py` → 0 violations
- `python -m bench.report` → regenerates all Markdown + CSV

### Acceptance Tests (Phase 7)
- `python -m bench.report` runs without errors, produces Markdown + CSV for all 6 table types.
- Losses to HiGHS appear in the report.
- Reliability table lists every failure by name.
- `pytest -m "not slow"` all green.
- `tools/check_imports.py` exits 0.
- README documents GPU benchmark path.

---

## Module-to-Phase Summary

| Module | Name | Phase |
|---|---|---|
| M1 | Parser + Model (io/) | 0 |
| M2 | Sparse + Linear algebra (linalg/) | 1 → sparse in 2 |
| M3 | Scaling + Presolve/Postsolve | 2 |
| M4 | Dual + Primal Simplex (lp/) | 1 |
| M5 | Mehrotra IPM (ipm/) | 2 |
| M6 | HPR engines — JAX (lp/hpr, qp/hpr_qp, hpr_batch) | 3 |
| M7 | Crossover (lp/crossover) | 3 |
| M8 | Safe Bounds + Certificate | 1 |
| M9 | Verifier float (nirbhar_verify/) | 1; exact mode in 5 |
| M10 | Certified B&C + Cuts | 4 |
| M11 | QP + MIQP | 5 |
| M12 | Robustness + naive_mode | 2 |
| M13 | Dispatcher + Race | 3 |
| M14 | Explainability | 2 (IIS) + 6 (full) |
| M15 | Plug-in registry | 6 |
| M16 | Industrial generators | 6 |
| M17 | Full CLI + API | 6 |
| M18 | Benchmark harness + reports | 7 |

---

## Test Files Summary

| Test file | Phase | Coverage |
|---|---|---|
| test_parser.py | 0 | manifest counts, all §5.5 traps |
| test_import_rules.py | 0 | check_imports.py exits 0 |
| test_linalg.py | 1 | LU residuals, dense→sparse match |
| test_lp_engines.py | 1→2→3 | dual simplex, IPM, HPR on T1/T2 |
| test_safe_bound_property.py | 1 | LB(y) ≤ true optimum, hundreds of random y |
| test_verifier.py | 1→5 | float mode → exact mode |
| test_cli.py | 1→6 | minimal → full command set |
| test_presolve_postsolve.py | 2 | feasible + same obj in original space |
| test_stress.py | 2 | naive vs hardened, S1/S2 |
| test_status_models.py | 2 | galenet, tiny_infeasible, tiny_unbounded |
| test_race_parallel.py | 3 | race = sequential; deterministic |
| test_determinism.py | 3 | identical objectives with --deterministic |
| test_milp.py | 4 | T1 MIPLIB + brute-force parity |
| test_cuts_valid.py | 4 | 0 cut violations |
| test_qp_miqp.py | 5 | all QPs + MIQPs |
| test_adversarial.py | 5 | 7/7 corruptions rejected |
| test_explain.py | 6 | galenet IIS, shadow prices |
| test_plugins.py | 6 | custom BranchingRule in solve_path |

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Numba JIT compilation slow in CI | Use `NUMBA_DISABLE_JIT=1` for coverage runs; mark JIT tests `@pytest.mark.slow` |
| JAX x64 not enabled by default | Set `jax_enable_x64 = True` in `nirbhar/__init__.py` before any JAX import |
| HPR convergence on ill-conditioned models | Use Ruiz scaling ×10 before HPR; document deviations in hpr_notes.md |
| Dense LU too slow for T2 before Phase 2 | Start Phase 1 with T1 only; sparse LU introduced in Phase 2 |
| HiGHS baseline absent | `requirements-bench.txt` installs `highspy`; skip baseline if import fails, report honestly |
| T3 MILP instances may not solve in time | Report TIME_LIMIT or OPTIMAL_WITHIN_GAP honestly; never drop from tables |
| No GPU on development machine | CPU path is complete; gpu_run.py designed to run on free Colab GPU separately |

---

## What to Do First (Phase 0 Kickoff)

1. `mkdir nirbhar-backend && cd nirbhar-backend`
2. Create `pyproject.toml` with entry point `nirbhar = nirbhar.cli:main`
3. Write `requirements.txt`: `numpy>=1.26`, `numba>=0.60`, `jax[cpu]>=0.4`
4. Write `tools/check_imports.py` (AST scan — mirrors TypeScript `check-imports.mjs`)
5. Implement `nirbhar/io/mps.py` → parse all 26 Netlib + 18 MILP files
6. Write `tests/test_parser.py` driven by `data/manifest.json`
7. Run `pytest tests/test_parser.py` → all green before Phase 1 starts
