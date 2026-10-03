# NIRBHAR — Indigenous Certified Hybrid CPU–GPU Optimization Solver Core
### Smart India Hackathon 2026 — SIH26119 | Team Vernils

*NIRBHAR comes from* Atmanirbhar *(self-reliant): a solver built from mathematical first principles, owned and inspectable in India.*

Tags like **[R3]** point to the reference list in §15.

**Contents:** 1 Problem and requirement map · 2 The idea · 3 State of the field and design rules · 4 Architecture · 5 Modules · 6 Algorithms · 7 Certificate · 8 Plug-in interfaces · 9 Benchmark and validation protocol · 10 Demonstration and model families · 11 Innovation and differentiation · 12 Feasibility, methodology, risks · 13 Impact and benefits · 14 Slide-by-slide deck map · 15 References · 16 Judge Q&A

---

## 1. Problem and Requirement Map

| Field | Value |
|---|---|
| PS ID | **SIH26119** |
| PS Title | Indigenous GPU-Accelerated Optimization Solver (Sovereign Alternative to Xpress / CPLEX) |
| Owner | Mangalore Refinery and Petrochemicals Limited (MRPL) |
| Theme / Category | Smart Automation / Software |
| Official link | https://sih2026.vuce.in/ps/SIH26119 |

**What the problem statement says.** Optimization in India's refining, petrochemical, power, logistics, manufacturing and planning sectors depends on a handful of foreign solvers (IBM ILOG CPLEX, Gurobi, FICO Xpress). They are capable, but carry high recurring licence costs, restrictive licensing and no visibility into the algorithms. Open-source solvers (CBC, HiGHS, GLPK, SCIP) have advanced but still lag on several classes of large-scale mixed-integer problems and have not been validated for Indian industrial use cases. The statement is explicit that the hard part is **not the modelling interface**; it is a *numerically robust optimization engine that consistently finds high-quality solutions for large, sparse, highly constrained problems in practical computation times*.

**What is asked.** A sovereign solver **core** for LP, MILP and QP, with an architecture that extends to MIQP, NLP and MINLP; revised simplex, interior point, branch-and-bound, branch-and-cut, cutting planes, presolve, heuristics and advanced node selection; sparse matrix techniques, efficient numerical linear algebra and multi-core parallelism; GPU acceleration where it gives measurable benefit; emphasis on numerical stability, scalability and reliable convergence; **built from scratch, on no existing open-source solver library**. Scope covers refinery scheduling, crude blending, process optimization, production planning, logistics, power dispatch, transportation and supply chains, at thousands to millions of variables and constraints, including highly degenerate models, ill-conditioned matrices and difficult mixed-integer formulations. A basic API or CLI is enough. The solver must solve standard MIPLIB, Netlib or Mittelmann problems, be compared with at least one established solver on quality and speed, and demonstrate robustness on degeneracy, weak relaxations and ill-conditioning.

### 1.1 Requirement → module → evidence

| # | PS requirement | NIRBHAR answer | Evidence we produce |
|---|---|---|---|
| 1 | Sovereign solver **core**, not a modelling environment | Parser + solver core + CLI/API only; no modelling layer | Repo layout; CLI and API demo |
| 2 | Linear programming | Dual and primal simplex on our own sparse LU; interior point; GPU HPR; full presolve | Netlib and Mittelmann tables vs HiGHS |
| 3 | Mixed-integer LP | Certified branch-and-cut (§6.8) | MIPLIB subset table; brute-force match on small MILPs |
| 4 | Quadratic programming (initial focus) | Convex QP: interior point for general sparse Q; HPR-QP on GPU for large models; certified bound | Maros–Mészáros and known-optimum QP tables vs HiGHS |
| 5 | Modular architecture | Eight plug-in interfaces; our own engines and rules register through them (§8) | Extension guide with a worked example |
| 6 | Extension to MIQP | Convex MIQP built in: branch-and-cut over certified QP relaxations (§6.10) | Unit-commitment MIQP family; brute-force match on small MIQPs |
| 7 | Extension to NLP, MINLP | Model-class interface (§6.15): convex NLP via tangent relaxations; non-convex classes return `LOCAL_ONLY`, never `OPTIMAL` | Interface document; worked convex-NLP example |
| 8 | Revised simplex | Bounded revised dual simplex + primal simplex; LU with eta updates; steepest-edge pricing; bound-flipping ratio test | Algorithms document; Netlib tables |
| 9 | Interior-point methods | Mehrotra predictor–corrector for LP and convex QP; own sparse Cholesky and LDLᵀ | IPM column in all LP/QP tables |
| 10 | Branch-and-bound | Certified B&B: prune only on a proven bound (§6.8) | MIPLIB subset; node-count tables |
| 11 | Branch-and-cut, cutting planes | GMI, c-MIR and extended-cover cuts, each carrying a derivation the verifier re-checks (§6.9) | Root-gap-closure table; "no optimum cut off" property test |
| 12 | Presolve | Presolve + postsolve stack incl. dual fixing, aggregation, coefficient tightening, probing (§6.1) | Per-reduction ablation |
| 13 | Heuristics | Rounding, diving family, feasibility pump, RINS | Time-to-first-incumbent table |
| 14 | Advanced node selection | Best-estimate with plunging, periodic best-bound, reliability branching | Node counts vs best-bound |
| 15 | Sparse matrix techniques | CSR/CSC, hypersparse solves, sparse LU (Markowitz), sparse Cholesky (minimum degree) | Residual tests; fill statistics |
| 16 | Efficient numerical linear algebra | Scaling, iterative refinement, condition estimation, GPU sparse products | Residual and conditioning reports |
| 17 | Multi-core parallelization | GIL-free threads, concurrent root race, parallel tree search, batch pools (§6.12) | Core-scaling chart |
| 18 | GPU acceleration where measurable | HPR, batched HPR and HPR-QP in JAX; dispatcher routes to the GPU only where our benchmarks say so | Crossover-size chart |
| 19 | Numerical stability, reliable convergence | Escalation chain, hardening switches, stress suite (§6.11) | Reliability table; naive-vs-hardened table |
| 20 | From scratch; no open-source solver library | Own parser, presolve, LU, Cholesky, simplex, IPM, HPR, B&C, verifier; NumPy/JAX/Numba as array and compiler frameworks only; CI import check | Dependency list; CI report |
| 21 | Refinery scheduling, crude blending, process optimization | Refinery family: blending LP, campaign MILP, price-risk QP | Live demo |
| 22 | Production planning | Capacitated lot-sizing MILP family; multi-period refinery planning | Family table |
| 23 | Logistics, power dispatch, transportation, supply chain | Transportation, unit-commitment and network-design families | Family table |
| 24 | Thousands to millions of variables and constraints | Scale ladder to about 1e6 variables for LP; MILP ceiling reported honestly | Scale chart |
| 25 | Robust on degenerate, ill-conditioned, weak-relaxation models | Stress suite S1–S4; hardened vs naive vs one-mechanism-off | Naive-vs-hardened table; live demo moment |
| 26 | Consistently optimal or near-optimal | Result statuses carry a proven gap | Reliability table |
| 27 | Practical computation times | Numba-compiled kernels; time tables that include our losses | Result tables |
| 28 | Basic API or CLI | `nirbhar solve / verify / bench` and a small Python API | Demo run |
| 29 | Solve MIPLIB, Netlib, Mittelmann problems | Instance sets in §9.1 with a tune/report split | Result tables |
| 30 | Compare with at least one established solver | HiGHS (simplex, IPM, PDLP) and MPAX; a licensed commercial solver as an extra reference if an academic licence is available | Result tables |
| 31 | Transparent, extensible, sovereign foundation | Certificate, independent verifier, open code, explicit open licence | Repo, LICENSE, sample certificates |

---

## 2. The Idea

**One-liner.** NIRBHAR is a from-scratch, India-owned solver core for LP, MILP, QP and convex MIQP. It contains every algorithm family the problem statement names (revised simplex, interior point, branch-and-cut) plus a GPU first-order engine, puts each on the hardware where it measurably wins, and returns answers that are optimal or near-optimal **with a proven gap**, each shipped with a machine-checkable certificate and an independent verification report.

**30-second version (plain language, for non-specialist judges).**
> Refineries plan crude purchases and blending with optimization software they cannot look inside, licensed from abroad. NIRBHAR is a solver built from the mathematics up. It has several different engines and picks the right one for each problem. Big problems go to the GPU, hard ones get a careful CPU treatment, and if one method struggles the solver automatically tries the next and writes down why. Every answer comes with a receipt: a mathematically valid proof of how close to optimal it is, checked by a separate program. If the receipt does not check out, we do not call the answer optimal.

**Two-minute technical version.**
- **Complete engine family, one sparse stack.** Bounded revised dual simplex and primal simplex on our own sparse LU; Mehrotra interior point for LP and convex QP on our own sparse Cholesky/LDLᵀ; GPU Halpern–Peaceman–Rachford (HPR) for very large LPs, convex QP and batches; crossover to a basic solution.
- **Certified branch-and-cut.** A node is pruned only when a *safe* bound, valid for any dual vector, proves it. Cuts (GMI, c-MIR, extended cover), reduced-cost fixing and bound propagation all carry derivations that the verifier re-checks. A weak or approximate bound keeps a node open: slower, never wrong.
- **Convex MIQP** by the same branch-and-cut over certified QP relaxations.
- **Robustness by escalation.** Every failure mode (cycling, stalling, singular basis, growth, IPM stagnation, node LP failure) has a defined next step, and every escalation is written to the certificate. The solver never loops silently and never reports an unverified "optimal".
- **Hybrid parallel execution.** Compiled kernels release the Python GIL, so threads run node LPs concurrently over one shared model; a concurrent root race (simplex vs interior point vs GPU HPR); parallel tree search; batched GPU HPR for scenarios and strong branching; a dispatcher whose thresholds come from our own measurements.
- **Independent verification.** A separate package re-reads the *original* model and re-checks feasibility, integrality, objective, bound, cut derivations and infeasibility proofs, optionally in exact rational arithmetic.
- **Explainable.** Binding constraints, shadow prices, reduced costs, sensitivity ranging and an explanation of *why* a model is infeasible.
- **Broad and validated.** Five industrial model families, an open known-optimum benchmark pack, a stress suite run with and without every hardening mechanism, and honest benchmarks against HiGHS including the cases where we lose.

---
## 3. State of the Field and Design Rules

This section is the evidence behind every design choice that follows.

### 3.1 Where GPUs help and where they do not

| Workload | Best fit today | Evidence |
|---|---|---|
| Giant LPs (hundreds of millions of nonzeros) | GPU/first-order | PDLP solved 8 of 11 giant instances (125M–6.3B nonzeros) to a 1% gap, while Gurobi barrier solved only 3 within a 1 TB RAM limit **[R4b]**. Gurobi reports giant LPs show the most immediate promise **[R17]**. |
| Typical small/medium LPs and MIPs | CPU simplex/barrier | Gurobi states the majority of today's LPs and MIPs perform better with established barrier or simplex methods **[R17]**. |
| Needing a basic solution or high-accuracy duals | Barrier/PDHG **plus crossover** | Crossover is required to obtain a basic solution, which is the starting point for B&B; its cost depends on the quality of the interior/first-order solution and can erase the benefit of faster GPU iterations **[R17]**. |
| MIP with a huge root LP | GPU at the root only | Gurobi's GPU step for MIP is the root LP relaxation **[R17]**; cuOpt runs PDLP, barrier and dual simplex concurrently at the root **[R19]**. |
| B&B tree nodes | CPU dual simplex, warm-started | PDHG has no basis, so sibling LPs are re-solved essentially from scratch; warm-starting batched first-order B&B is called an open problem, and dual-bound certification is slow at high accuracy **[R10]**. |
| Many related LPs (strong branching, bound tightening, scenarios) | GPU, batched | Batched PDHG uses matrix–matrix instead of repeated matrix–vector products, and the paper identifies problem sizes where first-order methods beat simplex **[R9]**; cuOpt exposes batch PDLP for root strong branching **[R19]**. |
| Presolve | CPU today, GPU emerging | cuPSLP reports 11× (Mittelmann LP set) and 42× (GAMS large-scale set) lower shifted-geometric-mean presolve time than CPU PSLP **[R13]**. |
| Small QPs | Second-order (CPU/IPM) | On the Maros–Mészáros set, the authors' own table shows Gurobi at SGM10 0.4 vs HPR-QP 10.5 at 1e-6 tolerance **[R3]**. GPU first-order pays off for large QPs. |

**Iteration speed is not end-to-end speed.** Gurobi's crossover paper reports a Grace Hopper GPU running PDHG iterations about 25× faster than a CPU system on large models, yet stresses that overall runtime also depends on crossover **[R17b]**.

### 3.2 What production solvers ship

- **Gurobi 13.0:** PDHG for LP, CPU by default with optional GPU, documented as a preview feature; GPU PDHG is Linux-only (linux64, armlinux64) **[R17]**.
- **HiGHS:** simplex, interior point and PDLP for LP (cuPDLP-C and the native HiPDLP, runnable on NVIDIA GPUs on Linux and Windows); active-set and interior-point QP; and a branch-and-cut MIP solver **[R18]**. It is the natural open baseline, and it is not a weak one.
- **NVIDIA cuOpt:** MIP root relaxation in concurrent mode (PDLP, barrier, dual simplex); optional batch PDLP for root strong branching; Papilo presolve; CPU parallel B&B with best-first and diving threads; GPU heuristics; generally available QP **[R19]**.

### 3.3 Research frontier we build on

- **HPR-LP** (Math. Prog. Comp. 2025): reports 2.39×–5.70× speedup over PDLP with presolve (2.03×–4.06× without) at 1e-8 tolerance on an A100 **[R1]**. A follow-up from the same group shows cuPDLPx's base algorithm is a special case of HPR-LP's, and reports HPR-LP as the best overall among current GPU LP solvers **[R2]** (self-reported).
- **HPR-QP:** dual HPR on the restricted Wolfe dual with symmetric Gauss–Seidel, avoiding slack variables that slow convergence **[R3]**.
- **MPAX:** open-source JAX-native first-order LP/QP solver with batched solving and portability across CPU, GPU and TPU **[R8]**. We use it as a numerical reference, never as a dependency.
- **Batched first-order LP in MIP** (Blin et al., 2026) **[R9]** and **B³-PWL** (2026) **[R10]**: the closest prior art for batching the node loop; B³-PWL is restricted to piecewise-linear/SOS2 problems and lists slow dual-bound certification and missing warm-starts as open limitations.
- **Safe bounds from inexact solutions:** arXiv 2603.01306 develops safe lower bounds for pruning, but for sparse generalized linear models, not general MILP **[R11]**. The classical idea of a rigorous bound from an approximate dual is older **[R20]**.
- **Numerical correctness of B&B decisions:** an a-posteriori study in SCIP checking whether integer-feasibility acceptance, LP-infeasibility claims and pruning decisions are justified in exact arithmetic **[R14]**. This motivates our design rule that pruning must rest on a proven bound.
- **PSLP / cuPSLP:** lightweight presolver adopted by cuPDLPx, cuOpt and HPR-LP **[R12]**, and its GPU version **[R13]**.

### 3.4 Design rules that follow

| # | Rule |
|---|---|
| 1 | The GPU is used only where evidence says it helps. Dispatcher thresholds come from our own benchmarks, which mirrors the PS's own condition that GPU acceleration be used where it provides measurable benefit. |
| 2 | Every first-order answer is either polished to a basic solution or reported with its rigorous gap. An approximate answer is never presented as exact. |
| 3 | Tree nodes use a warm-startable LP engine (dual simplex). The GPU serves the root LP and batched operations. |
| 4 | Never prune on an approximate bound. Pruning requires a safe bound; otherwise the node stays open. |
| 5 | Every cut, fixing and infeasibility claim carries a derivation, so validity does not depend on floating-point luck. |
| 6 | Verification is independent of the solver and runs against the *original* model, not the presolved one. |
| 7 | Claim only what is measured. Publish small-instance losses and hardware. |
| 8 | Sovereignty: no third-party solver or factorization code inside the solver. NumPy and JAX are array and GPU frameworks; Numba compiles our own code; SciPy appears only in `bench/` and `tests/`; reference solvers are read-only baselines. A CI import check enforces this (§5). |
| 9 | Robustness is demonstrated, not asserted: every hardening mechanism has a switch, and the stress suite shows what happens with it off. |
| 10 | One certificate for everything: every problem class and model family passes through the same certificate and verifier. |
| 11 | Extensibility by interface: our own engines, rules and heuristics are registered through the same plug-in interfaces a third-party contributor would use. |
| 12 | Practical speed matters as much as correctness (the PS says so): hot loops are compiled, and measured speed against HiGHS is reported, not hidden. |

---

## 4. Architecture

```
 model.mps / .qps ─► parser ─► Model (immutable; the ORIGINAL is kept untouched)
                                  │
                                  ▼
              presolve (scale, reduce) + postsolve stack
                                  │
                                  ▼
        dispatcher  (problem class · size · batch · cores · GPU present?)
   ┌───────────┬────────────┬─────────────┬───────────────┬──────────────────┐
   ▼           ▼            ▼             ▼               ▼                  ▼
 dual /     interior     GPU HPR       HPR-QP        batched HPR       thread pool ·
 primal     point        (JAX)         (JAX)         (scenarios,       process pool
 simplex    LP · QP                                  strong branching) (batches, tree)
 (own LU)   (own chol)
   └───────────┴─────┬──────┴─────────────┴───────────────┴──────────────────┘
                     ▼
        crossover (crash basis + simplex cleanup)  ·  concurrent root race
                     │
        robustness controller: escalation chain, every step logged
                     ▼
   MILP / MIQP layer: certified branch-and-cut
   (propagation · reduced-cost fixing · dual-simplex nodes · reliability branching ·
    best-estimate selection · GMI / c-MIR / cover cuts with derivations ·
    diving, feasibility pump, RINS · safe bound on every prune · Farkas check on infeasible)
                     ▼
                postsolve → original space
                     ▼
   independent verifier (re-reads the original model file; re-derives bounds and cuts)
                     ▼
        certificate.json  +  plain-language explanation
```

### 4.1 Dispatcher rules
1. **Small and medium LP:** CPU dual simplex.
2. **Large LP, and every MILP root:** a **concurrent root race**. Dual simplex, interior point and, if a GPU is present and measured faster at that size, HPR run at the same time. The first to return a result that passes the safe-bound gap check wins; the others are cancelled. Losing engines' partial results are discarded, never mixed in.
3. **Tree nodes:** CPU dual simplex, warm-started from the parent basis, inside worker threads.
4. **QP:** separable or low-rank Q goes to interior point or HPR-QP; general sparse Q goes to interior point (small and medium) or HPR-QP (large, GPU). Q is checked for positive semidefiniteness first; a non-convex Q is refused with status `UNSUPPORTED` and a reason, never solved as if it were convex.
5. **Batches** of same-structure LPs (scenarios, strong-branching candidates): batched HPR on the GPU when a GPU is present and measured faster; otherwise warm-started dual simplex across worker threads; small batches run sequentially.
6. **Any engine failure:** the robustness controller escalates (§6.11); the certificate records it.
7. **No GPU, or any GPU failure:** fall back to the CPU path automatically; JAX runs on CPU.
8. Every size and batch threshold is **set from the crossover measurements in §9**, published together with the core count and GPU used.

---

## 5. Modules

### 5.1 Repository layout

```
nirbhar/
  pyproject.toml   README.md   LICENSE
  tools/         check_imports.py            # CI: fails on forbidden imports outside bench/ and tests/
  nirbhar/
    io/          mps.py  qps.py  model.py    # hand-written parsers; immutable Model
    linalg/      csr.py  lu.py  chol.py  ldl.py  order.py  refine.py  condest.py
    presolve/    scaling.py  reductions.py  probing.py  postsolve.py
    lp/          dual_simplex.py  primal_simplex.py  basis.py  crossover.py
                 hpr.py  hpr_batch.py  kkt.py
    ipm/         mehrotra.py                 # LP and convex QP
    qp/          hpr_qp.py  bounds.py
    mip/         bb.py  propagate.py  branching.py  nodesel.py  heuristics.py
                 bounds.py  parallel_tree.py
                 cuts/  gmi.py  cmir.py  cover.py  pool.py
    robust/      controller.py  switches.py  naive_mode.py
    parallel/    pool.py  shared.py  race.py
    explain/     duals.py  ranging.py  iis.py
    extend/      engine.py  presolver.py  propagator.py  branching.py  nodesel.py
                 heuristic.py  cutgen.py  modelclass.py     # plug-in interfaces
    dispatch.py
    certificate/ builder.py  explain.py  schema.json
    cli.py   api.py
  verify/        # separate package: NO imports from nirbhar.lp / .ipm / .qp / .mip
    verify.py  exact.py  cuts.py  mps_min.py
  bench/         harness.py  fetch.py  hardware.py  configs/  results/
    stress/      degenerate/  illcond/  weakmip/  numerics/  naive_mode.py
    known_opt/   generators for LP and QP with known optimum
  demo/          refinery/  lotsizing/  transport/  dispatch_uc/  supply_chain/
  tests/         unit/  property/  netlib/  adversarial/
  docs/          report.md  algorithms.md  extending.md
```

**Sovereignty rule (enforced).** Inside the solver: our own parser, presolve, sparse LU, Cholesky and LDLᵀ, simplex, interior point, HPR, branch-and-cut and verifier. **NumPy and JAX** are array and GPU frameworks: array containers, sparse matrix–vector kernels and dense primitives such as matmul are fine; sparse factorization and anything that solves an optimization problem is ours. **Numba** compiles our own hot loops and contains no solver code. **SciPy** appears only in `bench/` and `tests/`. `tools/check_imports.py` scans the source tree and fails CI on any forbidden import (`scipy.optimize`, `scipy.sparse.linalg`, HiGHS bindings, `cvxpy`, OR-Tools, PuLP, MPAX and similar) outside `bench/` and `tests/`.

### 5.2 Module specifications

| Module | Function | Key design decisions | Acceptance test |
|---|---|---|---|
| `io` | MPS/QPS → immutable `Model` (c, A in CSR/CSC, row lo/hi, col lo/hi, integrality, optional general Q, names) | Hand-written. RANGES, all bound types (UP, LO, FX, FR, MI, PL, BV, LI, UI), OBJSENSE, integer markers, QUADOBJ/QMATRIX | Every chosen Netlib/MIPLIB/QP file parses; row/column/nonzero counts match published statistics |
| `linalg` | Sparse LU, Cholesky, LDLᵀ, orderings, refinement, condition estimate | §6.2 | Factor + solve residual tests on random and Netlib bases; fill and time vs SciPy **inside `tests/` only** |
| `presolve`, `postsolve` | Reductions and reconstruction of x, duals, reduced costs and basis status | §6.1; every reduction pushes a postsolve record | presolve → solve → postsolve gives a point feasible for the original model with the same objective; duals give a valid bound on the original |
| `lp/dual_simplex`, `lp/primal_simplex`, `lp/basis` | Warm-startable simplex engines with rays | §6.3 | Netlib objectives match; warm-started child nodes need fewer iterations than cold solves (measured, reported) |
| `lp/crossover` | IPM/HPR output → basis | §6.6 | Time(engine + polish) vs cold simplex; used only where measured faster or where cold simplex cannot finish |
| `lp/hpr`, `lp/hpr_batch`, `qp/hpr_qp` | JAX first-order engines | §6.5 | Objectives match references to 1e-6 relative; iteration counts comparable to MPAX/HPR-LP on the toy problem and three Netlib instances |
| `ipm/mehrotra` | Predictor–corrector for LP and convex QP | §6.4 | Netlib and Maros–Mészáros objectives match; conditioning tracked |
| `qp/bounds`, `mip/bounds` | Safe bounds from any dual vector | §6.7 | Property test: bound ≤ true optimum for many random y (LP, separable QP, general QP) |
| `mip/bb`, `propagate`, `branching`, `nodesel`, `heuristics` | Certified branch-and-cut core | §6.8 | Random small MILPs (≤ 15 binaries) match brute force; MIPLIB subset |
| `mip/cuts` | GMI, c-MIR, extended cover with derivations | §6.9 | Root-gap closure; brute-force property test that no optimum is ever cut off; every derivation re-checks in the verifier |
| `mip/parallel_tree` | Parallel tree search | §6.12 | Same optimal value as sequential on every test instance; core-scaling chart |
| `robust` | Escalation controller, hardening switches, `naive_mode` | §6.11 | Every stress instance ends with a verifier-checked status or a logged escalation path |
| `parallel` | Thread pool, process pool, shared incumbent, engine race | §6.12 | Results equal sequential solves; measured break-even batch size |
| `explain` | Shadow prices, ranging, infeasibility explanation | §6.14 | Ranging verified by re-solves; infeasible core re-checked by the verifier |
| `verify` | Separate package: original model + solution + certificate → PASS/FAIL | §6.13 | Adversarial suite: every deliberately corrupted solution, bound, cut or ray must FAIL |
| `certificate` | Solve record → JSON + plain-language text | §7 | Schema validation; round-trip |
| `dispatch` | Model + hardware → engine choice | §4.1 | Choice never worse than the slower engine by more than a stated factor on the report set |
| `extend` | Plug-in registry | §8 | `docs/extending.md` example adds a second branching rule without touching `mip/bb.py` |
| `bench` | Harness, baselines, stress suite, reliability table, scale ladder, known-optimum generators | §9 | Reproducible from a single command |
| `demo` | Five synthetic model families and scenario generators | §10 | Core path runs end to end live in under two minutes |

---
## 6. Algorithms in Enough Detail to Implement

### 6.1 Presolve and postsolve
Canonical model: `min ½xᵀQx + cᵀx  s.t.  rlo ≤ Ax ≤ rhi,  l ≤ x ≤ u`, with integrality on a subset of x and Q = 0 for LP/MILP.

**Reductions (each has an on/off switch and a postsolve record):**
- empty rows and columns; fixed variables; duplicate rows and columns;
- singleton rows converted to bounds;
- activity-based redundant and forcing rows, and activity-based bound tightening (with safe rounding);
- dual fixing and dominated columns;
- doubleton-equation aggregation and implied-free column substitution (only where integrality is preserved);
- integer bound rounding;
- **coefficient tightening on big-M rows**, rounded conservatively, which is what makes fixed-charge and lot-sizing relaxations tighter before any cut is generated;
- probing on binaries (implications and fixings), with a work limit.

**Scaling.** Geometric-mean scaling followed by Ruiz equilibration for the simplex and interior-point engines; Ruiz **[R35]** (about 10 iterations, as in HiGHS's PDLP **[R18]**) for HPR. Each engine stores its own scaling, and all stopping tests are evaluated in the **original unscaled space**.

**Postsolve** reconstructs primal values, duals, reduced costs and basis status in the original space, because the certificate's bound is computed on the original model (§6.7). Rules are read from PSLP **[R12]** and reimplemented independently.

### 6.2 Sparse linear algebra (the engine room)
All inner loops are written over flat arrays and compiled with Numba with the GIL released (`nogil`), so they run at compiled speed and in parallel threads.

- **Matrix storage.** CSR and CSC copies of A (and Aᵀ): row-wise access for propagation and cuts, column-wise access for pricing and basis extraction.
- **LU for simplex bases.** Singleton and triangular parts of the basis are extracted first (slack columns are unit vectors and cost no fill), then the remaining "nucleus" is factorized with a Markowitz ordering and threshold partial pivoting. FTRAN and BTRAN exploit **hypersparsity** with a depth-first reach computation, which is what keeps simplex fast on models whose solves are mostly zeros **[R32]**.
- **Basis updates.** Product-form eta file between refactorizations. A refactorization is triggered by eta-file length, fill growth, a growth-factor estimate, or a residual check, not by a fixed count alone.
- **Cholesky for interior point.** Sparse Cholesky of the normal-equations matrix `A D Aᵀ` with an approximate-minimum-degree ordering **[R31]**, computed once and reused because the sparsity pattern does not change between iterations. Dense columns are split out and handled by a low-rank correction.
- **LDLᵀ for general Q.** The regularized augmented (KKT) system is quasi-definite, so LDLᵀ with a fixed ordering exists and is numerically stable with static regularization **[R30]**.
- **Iterative refinement.** Solves against a factorization are refined against the residual; residuals use compensated (error-free-transformation) dot products.
- **Condition estimation.** A Hager-style 1-norm estimator **[R40]** gives a condition estimate for every basis at refactorization. It is reported in the certificate and feeds the escalation triggers (§6.11).

### 6.3 Dual and primal simplex
**Why dual simplex for tree nodes.** After a branching bound change or a new cut, the parent's basis stays dual feasible, so the child re-optimizes in few pivots. First-order methods have no basis and cannot do this **[R10][R17]**.

- **Bounded dual simplex.** Dual phase 1 by artificial box bounds on free and one-sided variables, removed afterwards **[R22]**.
- **Pricing.** Dual steepest-edge with initial reference weights **[R33]**, falling back to Devex weights when the exact update is too costly.
- **Ratio test.** Harris two-pass with tolerances **[R34]**, extended to the **bound-flipping (long-step) ratio test** **[R22]**, which removes many degenerate pivots by flipping boxed variables instead of pivoting on them.
- **Degeneracy.** Cost perturbation at the start, removed at the end with a primal-simplex cleanup on the true costs. Stall detection (no objective progress over a window) triggers an escalation (§6.11) rather than a silent loop.
- **Anti-cycling.** Basis-hash cycle detection; the last-resort fallback is Bland's rule **[R41]**, which is finite but slow and therefore used only after everything else.
- **Singular basis recovery.** The offending column is replaced by a slack, then the factorization is redone.
- **Primal simplex.** Used for cleanup after cost perturbation and after crossover, and as an alternative engine in the escalation chain.
- **Warm-start API.** `solve(model, basis=None, bound_overrides=None, added_rows=None)`; returns status, x, y, z, basis, or an infeasibility (Farkas) or unboundedness ray.
- **Parallelism.** We parallelize *across* LPs (nodes, strong-branching candidates, scenarios), which scales far better than parallelizing inside one simplex iteration **[R42]**.

### 6.4 Interior-point method (LP and convex QP)
- **Algorithm.** Primal-dual infeasible-start Mehrotra predictor–corrector **[R24][R29]** with adaptive step lengths and a merit-based centering parameter. LP is the case Q = 0, so one code path serves both.
- **Newton systems.** Normal equations with our sparse Cholesky for LP and for QP whose Q is diagonal or low rank; the regularized augmented system with our LDLᵀ for general sparse Q. Primal-dual proximal regularization keeps the systems well posed when the constraint matrix is rank deficient.
- **Why we need it.** Interior point is insensitive to primal degeneracy, so it is the natural second stage when simplex stalls; it is the standard tool for large sparse LP and the reference method for small and medium QP (§3.1: second-order methods beat first-order ones on small QPs **[R3]**).
- **Certified output.** The final multipliers y go through the safe bound of §6.7, so an interior-point answer is reported with its rigorous gap even before crossover.
- **Infeasibility and unboundedness.** Divergence tests produce a candidate Farkas ray or improving ray; it is accepted only if the safe check (§6.7) confirms it.
- **Crossover.** On request, or when B&B needs a basis, the interior solution is converted to a basic solution (§6.6).

### 6.5 GPU first-order engines (JAX)

JAX gives one code path across CPU, GPU and TPU, `jit` compilation, and `vmap`/batched products. The GPU engines are HPR for LP, batched HPR, and HPR-QP for convex QP.

#### HPR for LP

Canonical form, matching the HPR-LP reference: `min ⟨c,x⟩  s.t.  L ≤ Ax ≤ U,  l ≤ x ≤ u` **[R1]**.

- **Iteration.** Halpern iteration anchored at the last restart point: `z_{k+1} = (1/(k+2))·z_0 + ((k+1)/(k+2))·T(z_k)`, where `T` is the semi-proximal Peaceman–Rachford operator applied to the dual formulation. **Take `T`, the restart criteria and the penalty-parameter update from the paper; do not derive them from memory.** Read the reference code (`PolyU-IOR/HPR-LP`), then reimplement independently **[R1]**.
- **Per-iteration cost:** one product with A, one with Aᵀ, and elementwise projections onto bounds. Keep an explicit Aᵀ copy so the transposed product is not a slow scatter.
- **Precision:** JAX defaults to 32-bit floats. Enable 64-bit (`jax_enable_x64`), because 1e-6 to 1e-8 tolerances need it. Consumer GPUs generally have much lower FP64 throughput than data-centre GPUs, so measure before promising speedups.
- **Loop hygiene:** run the loop inside `jax.lax.while_loop`, check residuals every fixed number of iterations (for example 64–200) to avoid host synchronization, and keep shapes static to avoid recompilation.
- **Scaling:** Ruiz scaling in presolve. HiGHS's PDLP defaults to 10 Ruiz iterations, a reasonable starting point **[R18]**. Online preconditioning can further reduce iterations **[R15]**.
- **Stopping:** relative KKT residuals (primal, dual, gap) at the requested tolerance, **evaluated in the original unscaled space**. Scaled residuals can look converged while the original problem is not.
- **Bring-up order:** (1) hand-derive the two-variable LP and run it in NumPy; (2) confirm convergence to the known optimum and watch the KKT residuals fall; (3) port to JAX; (4) cross-check three Netlib instances against MPAX and HiGHS.

#### Batched HPR (scenarios and strong branching)

- Same A, many right-hand sides/costs/bounds: state arrays have shape (n, B), and products use sparse×dense multiplication. This is the matrix–matrix advantage highlighted in **[R9]**.
- Each column keeps its own restart and step state; converged columns are masked out so they stop changing, then periodically compacted.
- Before batching is relied on, a microbenchmark of sparse×dense products and a batched-HPR toy fixes the size regime where it wins. B³-PWL relied on a specialized block-tiled kernel **[R10]**; the dispatcher uses batching only where our own measurements show it faster than warm-started dual simplex across threads.

#### HPR-QP for convex QP
- Dual HPR on the restricted Wolfe dual with symmetric Gauss–Seidel, which avoids slack variables that slow convergence **[R3]**; it reuses the LP machinery. Diagonal and separable Q (blending cost, price risk, economic dispatch) are the natural fit; general sparse Q is handled with the same scheme.
- Q is checked for positive semidefiniteness (every `q_j ≥ 0` for diagonal Q; a sparse factorization attempt or diagonal-dominance test otherwise). A non-convex Q is refused with `UNSUPPORTED`.
- **Expectation, stated honestly:** for small QPs a second-order method is faster (§3.1). The GPU pitch is large-scale QP; small and medium QP go to interior point.
- Every QP result ships a rigorous bound from §6.7.
- **Fallback if HPR-QP stalls:** Kelley cutting planes **[R25]**: replace each `½ q_j x_j²` by an epigraph variable `s_j` and add tangent rows `s_j ≥ ½ q_j x̄² + q_j x̄ (x_j − x̄)` on the fly. Every such LP is a relaxation, so its bound is valid, and the dual simplex re-optimizes cheaply after added rows.

### 6.6 Crossover
From an interior or first-order solution (x, y, z): classify variables by distance to bounds and complementarity, complete to a square non-singular basis by pivoted LU, let the dual simplex finish with cost shifting, remove shifts with a primal-simplex cleanup. Two outcomes are legitimate and the certificate states which: *certified approximate* (engine result plus safe bound, no polish) or *basic optimal* (polished). Crossover can cost more than it saves **[R17]**, so the dispatcher uses it only where measured faster or where the caller needs a basis (B&B, ranging).

### 6.7 Safe bounds from **any** dual vector (the certificate's core)

For an LP `min cᵀx  s.t.  rlo ≤ Ax ≤ rhi,  l ≤ x ≤ u` and **any** multiplier vector `y` (no sign or feasibility requirement), define reduced costs `r = c − Aᵀy` and

```
LB(y) =  Σ_i ( y_i⁺ · rlo_i − y_i⁻ · rhi_i )  +  Σ_j ( r_j⁺ · l_j − r_j⁻ · u_j )
         with  t⁺ = max(t,0),  t⁻ = max(−t,0)
```

Convention: a term with coefficient zero contributes zero even if the bound is infinite. If a non-zero coefficient multiplies an infinite bound, `LB = −∞`.

**Why it is valid.** For any feasible x, the row activity `a = Ax` satisfies `yᵀa ≥ Σ_i (y_i⁺ rlo_i − y_i⁻ rhi_i)`, and `rᵀx ≥ Σ_j (r_j⁺ l_j − r_j⁻ u_j)` by the variable bounds. Since `cᵀx = yᵀAx + rᵀx`, the sum bounds `cᵀx` from below. This is weak duality applied without assuming `y` is dual feasible; approximate `y` simply yields a weaker bound. The idea is classical **[R20]**.

**Consequences.**
- A GPU-approximate `y` from HPR gives a *rigorous* (if imperfect) bound. That is what makes "certified pruning" and "certified approximate LP answers" possible.
- **Floating-point safety:** evaluate in float64 and subtract a conservative error allowance proportional to the sum of absolute term magnitudes (a small multiple of the machine epsilon times the term count). For the final certificate, evaluate `LB(y)` **exactly in rational arithmetic**: every float is an exact rational, so exact evaluation is just an exact dot product, with no simplex in exact arithmetic required. Use exact mode for models up to a size we measure.
- **Infeasibility (Farkas):** set `c = 0`. If `LB(y) > 0` for some `y`, the LP is infeasible, because any feasible x would give `0 ≥ LB(y) > 0`. The dual simplex supplies the ray `y`.
- **Compute on the original model.** Bounds hold for the model they are evaluated on. The final certificate evaluates `LB` on the original (unscaled, un-presolved) model using postsolved duals. If postsolve cannot produce a good `y`, the bound is weak and the certificate says so.
- **Integer improvement (optional):** if every variable in the objective is integer with integer coefficients, the bound may be rounded up conservatively.


**Bounds for convex QP.** For `min ½xᵀQx + cᵀx` with Q positive semidefinite:
- **Separable (diagonal Q): closed-form Lagrangian bound.** Take **any** y, let `r = c − Aᵀy`, and define
```
LBq(y) =  Σ_i ( y_i⁺ · rlo_i − y_i⁻ · rhi_i )  +  Σ_j  min over t ∈ [l_j, u_j] of ( ½ q_j t² + r_j t )
```
  Each inner minimum is closed form: for `q_j > 0` it is attained at `t = clip(−r_j / q_j, l_j, u_j)` (finite even with infinite bounds); for `q_j = 0` it is the linear term of the LP bound with the same infinite-bound convention. It is valid for any y because `f(x) = yᵀAx + Σ_j (½ q_j x_j² + r_j x_j)`; the first part is bounded below as in the LP bound and the second by minimizing each separable term over its bounds. In exact mode every term is rational.
- **General sparse Q: tangent bound.** By convexity `f(x) ≥ f(x̂) + ∇f(x̂)ᵀ(x − x̂)` for any point `x̂`. Minimizing the linearization over the feasible set is an LP, whose bound is the LP bound with cost `∇f(x̂)` plus the constant `f(x̂) − ∇f(x̂)ᵀx̂`. It is valid for any `x̂`, and tight to the accuracy of `x̂`, which is high for an interior-point solution.
- Where both apply the tighter one is reported, and the two are benchmarked against each other.

**Exact basis proof (small and medium LP).** For a basic solution the verifier can solve `B x_B = b` and `Bᵀ y = c_B` in rational arithmetic and confirm primal and dual feasibility exactly, which proves optimality and gives the exact objective value. The dot-product bound above is the always-available default; the exact basis proof is used for models up to a measured size.

**With cuts.** A valid cut is an extra row, so the bound is evaluated on the cut-augmented model; validity of the bound then rests on validity of the cuts (§6.9).

### 6.8 Certified branch-and-cut

```
presolve → root LP by concurrent race → safe bound
root cut loop:
    separate GMI / c-MIR / extended-cover cuts from the LP solution
    keep efficacious, non-parallel, sparse cuts (each with its derivation)
    re-solve by warm-started dual simplex; stop on small bound progress or a round limit
root heuristics: rounding, diving, feasibility pump; RINS once an incumbent exists
open ← { root } ; UB ← incumbent value
while open non-empty and budget left:
    node ← select (best-estimate with plunging; periodic best-bound)
    propagate bounds (activity-based, safe rounding); reduced-cost fixing from the parent's y
    solve node LP by dual simplex, warm-started from the parent basis, with node bounds
    if LP infeasible:
        verify with a Farkas ray via §6.7 (c = 0); if verified, discard
        else keep the node open and flag "unverified infeasibility"
    else:
        LBn ← safe bound (§6.7) from the node's y, using node bounds and valid cuts
        if LBn ≥ UB − tolerance:  prune   (proven)
        elif x integer-feasible:   update incumbent and UB   (re-verified before reporting)
        else:                       branch (reliability branching), push children
    periodically: diving, RINS; cut separation at shallow depths; cut-pool aging
global lower bound ← min over open nodes of their safe bounds (UB if none open)
gap ← (UB − global bound) / max(1, |UB|)
```

- **Reliability branching.** Pseudocost estimates, with strong branching on candidates whose pseudocosts are not yet reliable **[R38]**. Strong-branching candidates are independent LPs, so they run in worker threads or as one batched-HPR call, whichever the dispatcher has measured faster.
- **Node selection.** Best-estimate (using pseudocost estimates) with plunging for fast incumbents, and a periodic switch to best-bound to raise the global bound.
- **Reduced-cost fixing is certified for free.** The safe bound `LB(y)` splits term by term over variables, so changing one variable's bound changes the bound by an amount computable from `r_j`. If the improved bound exceeds UB, the variable is fixed, and the same `y` is the proof.
- **Heuristics.** Simple and ZI rounding; fractional, guided and coefficient diving on warm-started dual simplex; the feasibility pump **[R36]**; RINS as a sub-MIP with a node limit **[R37]**. Every incumbent is re-verified (integrality, feasibility) before it is reported.
- A node whose safe bound is weak **stays open**. The cost is speed, never correctness **[R14]**.

### 6.9 Certified cuts

Cuts close the gap on weak (big-M) formulations, which is exactly where simpler solvers stall. The danger is numerical: a cut computed from a floating-point simplex tableau can cut off a true optimum. NIRBHAR generates cuts by **safe aggregation** **[R27][R26]**, so validity does not depend on floating-point accuracy.

**Safe aggregation.** Write each row as inequalities `aᵢᵀx ≤ βᵢ`. For **any** multiplier vector λ (λ ≥ 0 on inequalities, free on equalities) the aggregated row `(Aᵀλ)ᵀx ≤ λᵀβ` is valid. The multipliers λ may be approximate LP duals, because validity holds for every λ; a poor λ only gives a weak cut.

**Mixed-integer rounding (MIR).** For an aggregated row `Σ_{j∈I} aⱼxⱼ + Σ_{j∈C} cⱼyⱼ ≤ b` with integer `x ≥ 0`, continuous `y ≥ 0` (after shifting and complementing variables at their bounds) and `f = b − ⌊b⌋ > 0`, the inequality
```
Σ_{j∈I} ( ⌊aⱼ⌋ + max(0, fⱼ − f)/(1 − f) ) xⱼ  +  (1/(1 − f)) Σ_{j: cⱼ<0} cⱼ yⱼ  ≤  ⌊b⌋ ,     fⱼ = aⱼ − ⌊aⱼ⌋
```
is valid **[R28]**. c-MIR searches over a small set of scalings δ and over which variables to complement, and uses path aggregation to combine several rows (this is what recovers flow-cover-type strength on fixed-charge and lot-sizing structure).

**Cut families.**
- **GMI.** A Gomory mixed-integer cut is MIR applied to a tableau row, i.e. to the aggregation with λ = the corresponding row of B⁻¹. Generated for basic integer variables with fractional value.
- **c-MIR** on greedily aggregated rows.
- **Extended cover** cuts on knapsack rows (after complementing binaries).

**Directed rounding.** All coefficient arithmetic in generation rounds so that the resulting inequality is valid (slightly weaker), or is done exactly in exact mode.

**Derivation record.** Each cut is stored with its derivation: the multipliers λ, the bound chosen for each continuous variable, complementation flags, and δ (cover cuts store the cover). The verifier **re-derives the cut in exact rational arithmetic and checks that the stored cut is implied by it**; for covers it checks the cover and extension conditions on the original row **[R16]**. A cut without a derivation that checks is not allowed to influence any pruning decision in a result reported as `OPTIMAL`.

**Management.** Efficacy, parallelism and density filters; a limit on the coefficient dynamic range; a cut pool with aging; separation mainly at the root and at shallow depths.

**Reported.** Root gap closed by cuts, per family and per MIPLIB instance, plus the property test that no known optimum is ever cut off.

### 6.10 Convex MIQP

Convex MIQP is branch-and-cut over convex QP relaxations, so the certificate machinery carries over unchanged.
- **Separable convex Q** (unit-commitment generator cost, price risk): each `½ q_j x_j²` gets an epigraph variable and tangent rows (Kelley outer approximation **[R25]**), so every node is an LP solved by warm-started dual simplex. Each LP is a relaxation, so its bound is valid; integrality is enforced by branching, and the tangent rows are refined at integer-feasible nodes until the QP value matches.
- **General convex Q:** node QPs go to interior point, with the tangent bound of §6.7 as the node bound.
- **Cross-check.** HiGHS does not support integer variables together with a quadratic objective according to its README **[R18]**, so MIQP results are validated by brute-force enumeration on small instances and by agreement between our two independent MIQP paths (outer approximation vs interior-point nodes) on the same instances.
- Non-convex Q is refused (`UNSUPPORTED`).

### 6.11 Robustness system

The PS puts numerical robustness first: degenerate models, ill-conditioned matrices and weak relaxations are where weaker implementations "exhibit excessive computation times or fail to converge". NIRBHAR treats robustness as a system with three parts: an escalation chain, switchable hardening mechanisms, and a stress protocol that demonstrates both.

#### Escalation chain
Every engine watches its own health. When a symptom fires, the robustness controller applies the next response and writes it to the certificate (`escalations`). The solver never loops silently and never reports an unverified "optimal".

| Symptom | Detection | Response (in order) |
|---|---|---|
| Stalling or degeneracy | No objective progress over a window; growing count of zero-step pivots | Increase cost perturbation → switch pricing to steepest-edge/Devex → Bland's rule as last resort |
| Cycling | Basis-hash repeat | Perturb and restart from the current basis → Bland's rule |
| Singular or ill-conditioned basis | Pivot below tolerance; condition estimate above threshold; growth factor | Refactorize with a tighter pivot threshold → swap in slack columns → rescale and restart from the current basis |
| Inaccurate solves | Residual above tolerance after iterative refinement | Refine with compensated residuals → refactorize → rescale |
| Simplex still failing | Above responses exhausted | Switch engine to regularized interior point → crossover |
| Interior point failing | Step length collapse, stagnating residuals, indefinite KKT | Increase regularization → change scaling → fall back to simplex or GPU HPR |
| Node LP failure inside B&B | Any of the above at a node | Retry with the alternate engine; if still failing, keep the node open with its parent's safe bound (slower, never wrong) |
| Only an approximate answer available | All exact-basis routes exhausted | Report `CERTIFIED_APPROXIMATE` with the safe bound and gap |
| Nothing certifiable | Chain exhausted | `NUMERICAL_ISSUE`, with the full escalation log |

#### Hardening switches
Every mechanism can be turned off from a config file, so its contribution can be measured.

| Engine | Hardening switches | `naive_mode` (textbook version) |
|---|---|---|
| Dual simplex | scaling · cost perturbation · Harris ratio test · bound flipping · steepest-edge / Devex pricing · periodic refactor with growth check · singular-basis recovery · Bland fallback | all off: no scaling, exact costs, textbook ratio test, largest-infeasibility pricing, refactor only when forced, no recovery |
| Interior point | scaling · regularization · adaptive step length · corrector · dense-column handling | no scaling, no regularization, fixed step fraction |
| HPR / HPR-QP | Ruiz scaling · presolve · restarts · penalty-parameter update (as specified in **[R1]**) | no scaling, no presolve, plain Halpern iteration with a fixed penalty parameter |
| Branch-and-cut | presolve incl. coefficient tightening · probing · cuts · propagation · reduced-cost fixing · reliability branching · heuristics | most-fractional branching, no presolve, no cuts, no heuristics |

#### Stress protocol
1. Run each stress instance in hardened mode, in `naive_mode`, and with one mechanism off at a time. Record certificate status, iterations, time, unscaled residuals, escalations and the verifier result.
2. A "solve" that the verifier rejects counts as a failure, however confident the solver was.
3. Choose instances by a written rule, before looking at any result (§9.1).
4. Naive mode is a fair textbook implementation, not a sabotaged one; the ablations show which single mechanism matters.
5. Ill-conditioned instances are rescaled copies of a well-posed model. Rescaling rows and columns does not change the optimum, so the reference objective is known exactly. Tolerances on these are relative to row and column norms.
6. Report the hardened mode's residual failures too.

### 6.12 Parallel execution (multi-core and GPU)

| Layer | Mechanism | Used for |
|---|---|---|
| Compiled, GIL-free kernels | Numba `nogil` kernels over shared read-only model arrays, one workspace per thread | Node LPs, strong-branching candidates, propagation, cut separation, all in worker threads with no model copying |
| Concurrent root race | Dual simplex, interior point and (if measured faster) GPU HPR run simultaneously; first certified result wins, others are cancelled | Root LP of every large model |
| Parallel tree search | Workers own local node queues; a shared pool holds nodes above a bound/depth threshold; the incumbent and upper bound live in shared memory; the global lower bound is the minimum over all workers' queues at synchronization points | Large MILP and MIQP trees |
| Deterministic mode | Rounds with a fixed per-worker node budget; results merged in a fixed order | Reproducible runs and audits |
| Batch pools | Thread pool of warm-started dual simplex; process pool where Python-level work dominates | Scenario batches, model families |
| GPU batching | Batched HPR with state of shape (n, B) | Scenarios and strong-branching candidates when a GPU is present and measured faster |

Parallel results are always checked against the sequential result: the optimal value must be identical. Scaling is reported honestly: sub-linear, and poor for small batches because of start-up cost. Every parallel run records the core count and GPU in the certificate.

### 6.13 Independent verifier
- A separate package with **no imports from the solver's LP, IPM, QP or MIP code**, its own minimal MPS/QPS reader, and its own implementations of `LB(y)`, the QP bounds and the cut derivations.
- **Float mode checks:** bound and row violations (absolute and relative), integrality, recomputed objective, recomputed bound and gap, Farkas rays and unboundedness rays, re-derived cuts (§6.9), reduced-cost fixings.
- **Exact mode:** the same checks in rational arithmetic for models below a measured size; every float is an exact rational, so exact evaluation is an exact dot product.
- **Adversarial suite:** perturb a correct result (violate a row, flip an integer, alter the objective, supply a random `y`, corrupt a cut multiplier, forge an infeasibility ray) and require the verifier to FAIL, or to return a weaker valid bound.
- The verifier reads the **original model file**, not the presolved model.

### 6.14 Explainability
- **Binding constraints, shadow prices, reduced costs**, in plain language ("one more unit of CDU capacity is worth this much").
- **Sensitivity ranging:** cost and right-hand-side ranging from the optimal basis, and a what-if batch over price/demand scenarios (warm-started dual simplex or batched HPR).
- **Infeasibility explanation.** When a model is infeasible, the Farkas ray identifies a set of rows; a deletion filter shrinks it to an irreducible conflicting set **[R39]**, reported in plain language ("these three constraints cannot all hold") and re-checked by the verifier. This is what a planner actually needs when a plan will not close.
- Shadow prices and reduced costs from an unpolished first-order solve are labelled approximate; the certificate says whether duals come from a basis.

### 6.15 Extension classes: convex NLP, non-convex NLP, MINLP
The architecture is built so a new problem class plugs in without touching the engines. A **model class** (§8) supplies its relaxation, its bound rule and its verifier check.
- **Convex NLP:** linearize a differentiable convex function at a chosen point; this gives a valid LP relaxation and bound (the tangent idea of §6.7). Rigor is limited by how rigorously the function can be evaluated; exact mode applies to polynomial functions.
- **Non-convex NLP and MINLP:** a global bound needs a valid convex relaxation (for example McCormick envelopes with spatial branching). Without one, the solver returns a local answer labelled `LOCAL_ONLY`, never `OPTIMAL`. The certificate's vocabulary already supports this: `OPTIMAL` always means proven.
- **Refinery pooling and property blending** are non-convex; they are handled through this interface with the same honesty rule.

---

## 7. Certificate Specification

Every solve writes `certificate.json` plus solution vectors.

**Status semantics.** `OPTIMAL` is emitted only when the certified gap is within tolerance **and** the independent verifier passes. Otherwise the status is a weaker, honest one. `UNSUPPORTED` always carries a reason (for example, a Q that is not positive semidefinite). `LOCAL_ONLY` is reserved for non-convex classes. The reliability table (§9.3) counts every status per instance set.

```json
{
  "nirbhar_version": "…",
  "model": {"file": "…", "sha256": "…", "rows": 0, "cols": 0, "nnz": 0, "integers": 0,
            "class": "LP | MILP | QP | MIQP", "q_nnz": 0},
  "status": "OPTIMAL | OPTIMAL_WITHIN_GAP | CERTIFIED_APPROXIMATE | INFEASIBLE_CERTIFIED |
             UNBOUNDED_CERTIFIED | TIME_LIMIT | NUMERICAL_ISSUE | UNSUPPORTED | LOCAL_ONLY",
  "objective": {"primal": 0.0, "safe_lower_bound": 0.0, "abs_gap": 0.0, "rel_gap": 0.0},
  "primal_feasibility": {"max_row_violation": 0.0, "max_bound_violation": 0.0,
                          "max_integrality_violation": 0.0, "tolerance": 1e-6},
  "bound": {"method": "weak-duality-any-y | lagrangian-separable-qp | tangent-qp | exact-basis",
            "arithmetic": "float64+margin | exact-rational", "evaluated_on": "original-model"},
  "cuts": {"generated": 0, "applied": 0, "types": {"gmi": 0, "cmir": 0, "cover": 0},
           "derivations_verified": 0, "root_gap_closed": 0.0},
  "solve_path": ["presolve", "root-race(dual-simplex|ipm|hpr-gpu)", "crossover", "branch-and-cut"],
  "escalations": [{"engine": "dual-simplex", "symptom": "stall", "response": "bland-rule", "iteration": 0}],
  "numerics": {"max_condition_estimate": 0.0, "refactorizations": 0, "max_residual_after_refinement": 0.0},
  "hardware": {"cpu": "…", "gpu": "…", "vram": "…", "driver": "…", "cuda": "…", "jax": "…",
               "cpu_cores_used": 0},
  "timing_s": {"parse": 0, "presolve": 0, "jit_compile": 0, "root": 0, "cuts": 0, "tree": 0, "verify": 0},
  "mip": {"nodes": 0, "open_nodes": 0, "pruned_by_safe_bound": 0, "infeasible_with_farkas": 0,
          "kept_open_due_to_weak_bound": 0, "fixed_by_reduced_cost": 0, "incumbent_updates": 0},
  "verifier": {"independent": true, "mode": "float | exact", "result": "PASS | FAIL", "checks": []},
  "explanation": {"binding_constraints": [], "top_shadow_prices": [], "reduced_costs": [],
                  "ranging": [], "infeasible_core": [],
                  "accuracy_note": "duals are approximate unless the solve was polished to a basis"}
}
```

**Plain-language explanation (generated from the certificate):** which constraints are binding, what one extra unit of a scarce resource is worth, how far a non-selected option's cost must drop before it enters the plan, how trustworthy the answer is, and, for infeasible models, which constraints conflict.

---

## 8. Plug-in Interfaces

Thin abstract base classes in `nirbhar/extend/`. Every module is written against them, and our own engines and rules register through the same registry a third-party contributor would use. The sketches fix the contract, not the final signatures.

| Interface | Contract (sketch) | Registered by us |
|---|---|---|
| `Engine` | `solve(model, start=None, bounds=None, rows=None)` → status, x, y, z, basis or ray; declares capabilities (`warm_start`, `batch`, `gpu`, `qp`) | dual simplex, primal simplex, interior point, HPR, batched HPR, HPR-QP |
| `Presolver` | `reduce(model)` → reduced model + postsolve record | every reduction in §6.1 |
| `Propagator` | `propagate(node_bounds, rows)` → tightened bounds with a safe-rounding guarantee | activity-based propagation, reduced-cost fixing |
| `BranchingRule` | `select(node, fractional_set, ctx)` → variable and direction | most-fractional, pseudocost, strong, reliability |
| `NodeSelector` | `next(open_nodes, ctx)` → node | best-bound, best-estimate with plunging |
| `Heuristic` | `run(node_lp, ctx)` → incumbent or none | rounding, diving family, feasibility pump, RINS |
| `CutGenerator` | `separate(node_lp, basis, ctx)` → cuts, each with a derivation and a validity check | GMI, c-MIR, extended cover |
| `ModelClass` | Declares how a class builds its relaxation, which bound rule certifies it, and which verifier check applies | LP, MILP, convex QP, convex MIQP; convex and non-convex NLP/MINLP plug in here |

**Evidence that it is real.** Our own code uses the registry, and the certificate's `solve_path` records which registered components produced the answer. The worked example in `docs/extending.md` adds a second branching rule without touching `mip/bb.py`.

---
## 9. Benchmark and Validation Protocol

### 9.1 Instance sets
- **LP:** Netlib (a small/medium mix, including known degenerate models), plus larger instances from the Mittelmann LP set **[R21]** where the GPU is plausibly favoured. That set has 43 models **[R17b]**.
- **MILP:** a MIPLIB 2017 subset selected by size filters, not by which instances we happen to solve.
- **QP:** generated QPs with a known optimum, built backwards from a chosen KKT point, plus instances from the Maros–Mészáros set (137 in total **[R3]**), general and diagonal Q.
- **MIQP:** generated unit-commitment MIQPs and small instances checked by brute-force enumeration.
- **Known-optimum LP pack:** LPs generated backwards from a chosen primal–dual pair satisfying complementary slackness, so the optimum is known exactly at any size. Published as an open benchmark pack with the generators.
- **Scenario batches:** the refinery model with perturbed prices, availabilities and demands, at several sizes and batch counts.
- **Stress suite,** chosen by written rules **before** looking at any result:
  - **S1 degenerate LPs:** known degenerate Netlib models plus generated highly degenerate assignment and transportation LPs.
  - **S2 ill-conditioned LPs:** Netlib models known for numerical difficulty, plus generated refinery LPs whose rows and columns are rescaled by factors from 1e-6 to 1e6 (the optimum is unchanged, so the reference objective is known).
  - **S3 weak-relaxation MIPs:** generated big-M fixed-charge models (transportation with lane-opening binaries, supply-chain network design), capacitated lot-sizing and refinery campaign-changeover models, plus a MIPLIB 2017 subset chosen by a stated rule (size and root-gap threshold).
  - **S4 numerically hard MIPs:** MIPLIB instances with wide coefficient ranges, chosen by a stated rule.
- **Scale ladder:** a generated transportation LP at about 1e3, 1e4, 1e5 and 1e6 variables (32 × 32, 100 × 100, 316 × 316 and 1000 × 1000 lanes; nonzeros are twice the variable count), plus the refinery LP family at matching nonzero counts. Run on GPU HPR, interior point, dual simplex and HiGHS, each with a time limit; timeouts are shown as timeouts. Go beyond 1e6 only as far as memory and time allow, and report the ceiling reached. MILP ceiling: reported per family, instance-dependent.
- **Model families:** refinery blending and scheduling, capacitated lot-sizing, transportation / logistics, unit-commitment power dispatch, supply-chain network design; each labelled synthetic (§10).
- **Split:** tune on five Netlib instances, report on five unseen ones; enlarge both sets as time allows.

### 9.2 Baselines
- **HiGHS:** simplex, interior point and PDLP, including its GPU-capable PDLP where the hardware allows **[R18]**; its QP and MIP solvers are the references for those classes.
- **MPAX:** a JAX-native peer (LP and QP). If our HPR is far slower than MPAX on the same instance, suspect our implementation, not the method.
- **HPR-LP reference** (Julia/C) if a GPU is available.
- **A licensed commercial solver (CPLEX, Gurobi or Xpress) as an extra reference,** if an academic licence is available.
- Baselines are for comparison and cross-checking only, never imported by the solver.

### 9.3 Metrics and hygiene
- Time to tolerance at 1e-4, 1e-6 and 1e-8, shifted geometric mean (SGM10, as used in **[R1]**), number solved, iterations, unscaled KKT residuals, certified gap.
- MILP: solved count, nodes, time, **root gap closed by cuts**, time to first incumbent, node count vs most-fractional/best-bound.
- Report **JIT compile time and steady-state time separately**; GPU frameworks carry warm-up overhead (cuPDLP.jl reports roughly one second of kernel-launch overhead **[R5]**).
- Our solvers are deterministic, so "multi-seed" only applies to generated instances and tie-breaking. At least five timing repetitions, median and spread, and multiple generated instances per size.
- **Hardware table:** CPU model and threads, GPU model, VRAM, driver, CUDA and JAX versions, FP64 throughput class.
- **Crossover-size chart:** solve time vs nonzeros for dual simplex, interior point, HPR (GPU) and HiGHS, with the point where each wins marked. Also **scenario-batch speedup vs (size, batch count)**. These charts set the dispatcher thresholds.
- **Reliability table:** per instance set: solved / total, the count of each certificate status, escalations used, and **every failure listed by name**.
- **Naive vs hardened:** the same solver with hardening off (`naive_mode`) and with one mechanism off at a time, on the stress suite.
- **Core-scaling chart:** batch and tree-search time vs number of CPU cores (physical and logical cores labelled), next to the GPU batched result.
- **Speed ratio to HiGHS:** median and worst-case time ratio on the Netlib report set, published as measured.
- **Publish losses:** small instances where the GPU path loses, and MILP instances where HiGHS is much faster.

### 9.4 What the benchmarks establish

| # | Claim | Evidence | What we report |
|---|---|---|---|
| C1 | Correctness: objectives match references within 1e-6 relative | Result tables + verifier PASS | Every mismatch, by name |
| C2 | Every solve ships a rigorous bound; "optimal" is never said without one | Certificates + adversarial suite | Adversarial rejection rate |
| C3 | GPU HPR is competitive on large LPs | Crossover-size chart vs HiGHS and MPAX | The size where it wins, and the small instances where it loses |
| C4 | Batched scenario solving beats sequential solves above some batch size | Speedup chart | The break-even batch size |
| C5 | Certified branch-and-cut solves a MIPLIB subset correctly | Results vs HiGHS | Correctness, time and node ratios, including where HiGHS is much faster |
| C6 | Cuts close root gap on weak formulations | Gap-closure table on lot-sizing, fixed-charge and MIPLIB S3 | Gap closed per instance, and cuts rejected |
| C7 | LP scale: GPU HPR and interior point solve generated LPs up to about 1e6 variables | Scale-ladder chart | The ceiling actually reached and what stopped us |
| C8 | Robustness: hardened mode solves stress cases where naive mode fails or stalls | Naive-vs-hardened table and ablations | Residual failures of the hardened mode |
| C9 | Breadth: all five families solve and pass the verifier | Family table | Status, gap and verifier result per family |
| C10 | Multi-core: threads, race and parallel tree search speed up solves | Core-scaling chart | Sub-linear scaling and the small-batch overhead |
| C11 | QP and MIQP: results match references (and brute force) within tolerance and ship valid bounds | QP/MIQP tables | Where interior point beats HPR-QP and vice versa |
| C12 | Practical speed: compiled kernels bring the CPU engines to a measurable ratio of HiGHS | Speed-ratio table | Median and worst-case ratio |

**Claims we will not make:** beating Gurobi, CPLEX or Xpress; general GPU branch-and-bound speedups; any result on hardware we did not test; licence-savings figures without a source; millions of integer variables; calling any result optimal without a verified certificate.

---

## 10. Demonstration and Model Families

All models are **synthetic**, clearly labelled as such (not MRPL data), with realistic structure.

**Refinery planning (core demo; background: crude scheduling MILPs [R43]).**
- **LP:** multi-period crude purchase and blending. About 8–15 crude types with price and availability; CDU capacity; product demand ranges; linear quality limits (for example sulfur); inventory balances across periods.
- **MILP:** campaign and changeover decisions (binaries), minimum run lengths.
- **QP:** a quadratic price-risk cost term, solved and certified with the closed-form bound of §6.7.
- **Scenario batch:** hundreds of price/demand scenarios of the same model, solved sequentially vs batched, with the crossover curve on screen.

**Further families.**
- **Production planning:** capacitated multi-item lot-sizing MILP. A classic weak-relaxation model, so it shows cut gap-closure directly.
- **Transportation / logistics:** transportation LP with a fixed-charge MILP variant (lane-opening binaries); the same generator feeds the scale ladder.
- **Power system dispatch:** unit-commitment MILP (on/off binaries, minimum up/down times, ramping, reserve), with a quadratic generator cost that makes it a natural convex MIQP, and an economic-dispatch QP.
- **Supply-chain network design:** facility-location MILP (facility binaries, flows).

Each is solved through the same certificate and shown as one line: status, gap, verifier result.

**Robustness moment (about 30 seconds).** Run one rescaled, ill-conditioned model in `naive_mode`, where it stalls or returns a solution the verifier rejects; then in hardened mode, where the escalation log shows what the solver did and the result ends `OPTIMAL` with verifier PASS.

**Cut moment.** The lot-sizing model with cuts off vs on: the root gap closes and the node count collapses, while the verifier re-derives every cut.

**Infeasibility moment.** An over-constrained refinery plan: the solver returns `INFEASIBLE_CERTIFIED` and names the three conflicting constraints.

**Core path (under two minutes, live).** Refinery LP → MILP → QP → scenario batch. Everything else sits on an "extras" tab.

**On-screen KPIs:** certified gap, verifier PASS/FAIL, mass-balance residual reported by the verifier, escalations used, and the plain-language explanation.

---

## 11. Innovation and Differentiation

### 11.1 What is and is not novel
**Not novel (say so):** HPR itself (published, peer-reviewed **[R1]**); JAX batched first-order solving (MPAX **[R8]**); bounds from inexact duals **[R11][R20]**; safe MIR/GMI aggregation **[R26][R27]**; verified MIP certificates as a concept **[R16]**; dual simplex inside B&B. The breadth items the PS names (presolve, cuts, node selection, multi-core parallelism, interior point) are standard techniques: we implement them, we do not claim them.

**What is ours:**
1. **Certified answers by default.** Every result carries a bound valid for any dual vector, evaluated exactly in rational arithmetic where the model is small enough, and re-checked by an independent verifier that has been tested against deliberately corrupted results.
2. **Certified branch-and-cut.** Cuts, reduced-cost fixings and infeasibility claims all carry derivations the verifier re-checks; a cut cannot silently cut off the optimum.
3. **Robustness by escalation.** Every failure mode has a defined response, logged in the certificate; a stress suite shows hardened vs naive and each mechanism's contribution, failures included.
4. **A measured hybrid.** Simplex, interior point and GPU first-order engines race at the root; GIL-free threads run the tree; the GPU serves large LPs and batches. Thresholds are published from our own benchmarks, losses included.
5. **One sparse stack from LP to convex MIQP,** with a model-class interface stating certificate semantics for NLP/MINLP extension.
6. **Explainable solves.** Shadow prices, ranging and a minimal explanation of infeasibility, in plain language.
7. **An open Indian-industry benchmark pack.** Five model families and known-optimum LP/QP generators, so any solver can be tested on refinery-shaped, power-dispatch and logistics-shaped problems with ground truth.
8. **Sovereignty with portability.** From-scratch code and one JAX path across CPU, GPU and TPU.

### 11.2 Competitive landscape
- Commercial and open solvers are moving quickly on GPUs (§3.2), so "GPU solver" alone is not a differentiator.
- Other submissions for this problem statement will cover the standard method list, and some will advertise a post-solve check. Breadth is table stakes: covering it removes a deduction, it does not create an edge.
- Our edge is **proof, not just a checker**: a bound valid for any dual vector, exact-arithmetic mode, verified cut derivations, Farkas and unboundedness proofs, and an escalation log, so "optimal" means proven and re-checked by an independent program. It is combined with measured hardware routing and robustness shown in a stress suite.
- Public projects for this problem statement report that a GPU method can run slower than the CPU method on a modest GPU at every measured scale; the lesson, built into this design, is to gate the GPU by measured size and to publish honestly.

### 11.3 Capability comparison (for the comparison slide)

| Capability | NIRBHAR | HiGHS | Gurobi / CPLEX / Xpress |
|---|---|---|---|
| Licence and cost | Sovereign, open, explicit licence | MIT, free | Commercial, recurring licence |
| Internals open and modifiable | Yes | Yes | Closed |
| LP algorithms | Dual/primal simplex, interior point, GPU HPR | Simplex, interior point, PDLP (GPU-capable) **[R18]** | Simplex, barrier; Gurobi documents GPU PDHG as a preview feature **[R17]** |
| Convex QP | Interior point, HPR-QP | Active-set and interior-point QP | Yes |
| Convex MIQP | Yes (§6.10) | Not supported per its README **[R18]** | Yes |
| Certified bound with exact-arithmetic mode and verified cuts | Yes | Not a standard output | Not a standard output in the default workflow |
| Escalation log for numerical trouble | Yes, in the certificate | Solver log only | Solver log only |
| Benchmark scale and maturity | Validated on our protocol (§9), losses published | Extensive | Decades of industrial use |
| Domain benchmark pack for Indian industrial families | Yes (§10) | General-purpose | General-purpose |

*Table entries about other solvers reflect their public documentation at the time of writing; re-check before presenting.*

---
## 12. Feasibility, Methodology, Risks

### 12.1 Why this is buildable
- **Every component has published algorithms and an open reference implementation to cross-check against:** simplex and interior point (Koberstein, Mehrotra, Wright; HiGHS as reference), HPR (paper and code, MPAX as peer), presolve (PSLP), safe cuts and certificates (Cook et al., Eifler–Gleixner, VIPR), branching and heuristics (standard literature).
- **One certificate and one verifier cover everything,** so components can be developed and tested independently and still be checked the same way.
- **JAX and Numba give one code base for CPU, GPU and TPU** and compiled speed on the CPU; the CPU path is complete without a GPU.
- **Correctness is testable at every level:** brute-force enumeration on small MILPs/MIQPs, known-optimum generators, rescaled copies with known optima, adversarial corruption of results.

### 12.2 Methodology and process
1. **Toy checks by hand:** derive a two-variable LP, run HPR, dual simplex and interior point in NumPy, and watch the KKT residuals fall before any scaling up.
2. **Linear algebra first:** sparse LU and Cholesky pass residual tests on random and Netlib bases before any simplex or IPM sits on them.
3. **Correctness before speed:** each engine matches reference objectives on Netlib before it is optimized; then hot loops are compiled and speed against HiGHS is measured.
4. **Certificate and verifier next,** including the adversarial suite, so every later component is checked from the day it exists.
5. **Branch-and-cut on the checked engines:** brute-force match on small MILPs, then cuts with the "no optimum cut off" property test, then MIPLIB subset.
6. **Robustness engineering:** hardening switches, escalation chain, stress suite with naive and ablation runs.
7. **Hardware routing:** crossover measurements set the dispatcher thresholds; parallel results are checked against sequential ones.
8. **Breadth and scale:** model families, known-optimum packs and the scale ladder; tune/report split for all headline numbers.

### 12.3 Challenges and risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | First-order (GPU) answers are low-accuracy; crossover can erase GPU gains **[R17]** | Two honest result classes (certified approximate vs polished); crossover used only where measured to help; interior point and simplex race the GPU at the root |
| 2 | No warm start for first-order node LPs **[R10]** | Tree nodes use dual simplex; the GPU serves the root and batches |
| 3 | JAX sparse batching may be slower than a purpose-built kernel **[R10]** | Microbenchmark first; dispatcher uses batching only where measured faster than threaded dual simplex |
| 4 | FP64 throughput is low on consumer GPUs | Disclose the GPU; measure; route to the GPU only if measured faster |
| 5 | JIT compile time and recompilation | Report separately; static shapes; warm-up run before timing |
| 6 | Numerical divergence in HPR | Toy checks; residual tracking; MPAX cross-check |
| 7 | Floating-point error in the safe bound | Error allowance; exact-rational mode for the final certificate |
| 8 | Postsolve produces poor duals, so the bound is weak on the original model | Test postsolve duals on every instance; certificate states weakness rather than hiding it |
| 9 | Speed of a Python-hosted solver | Numba-compiled, GIL-free kernels over flat arrays; measured ratio to HiGHS published; no claim of parity |
| 10 | Our own sparse LU/Cholesky is slower or less stable than a mature library | Residual and fill tests against SciPy inside `tests/`; condition estimates and refinement; claims tied to measured results |
| 11 | Cuts can cut off optima through floating-point error | Safe aggregation with directed rounding; derivations re-checked in exact arithmetic by the verifier; brute-force property test |
| 12 | Parallel tree search adds nondeterminism and overhead | Deterministic mode; parallel result checked against sequential; scaling reported honestly, including small-instance overhead |
| 13 | Real refinery blending may be non-convex (pooling / property blending) | Confirm MRPL model structure; linear blending LP, scheduling MILP and convex QP are solved directly; non-convex pooling goes through the model-class interface and returns `LOCAL_ONLY` unless a valid relaxation exists |
| 14 | Python or JAX cannot reach million-variable scale on every family | Scale claims rest on GPU HPR and interior point for LP; MILP ceiling stated per family; both measured |
| 15 | GPU access is uncertain | Every capability runs on CPU; JAX falls back automatically |
| 16 | Naive mode looks like a straw man | Textbook defaults, per-mechanism ablations, instances chosen by rule before results, hardened-mode failures published |
| 17 | Ambiguity about which libraries "no solver library" allows | Sovereignty rule (§5.1) enforced by a CI import check and stated openly in the report |

---

## 13. Impact and Benefits

### 13.1 Potential impact on the target audience
- **Direct:** MRPL and other PSU refineries (IOCL, BPCL, HPCL) get an auditable engine for crude blending, scheduling and planning; each answer carries a bound and an explanation, and infeasible plans come with the conflicting constraints named.
- **Sectoral:** the same core generalises to power-grid dispatch, railway and logistics scheduling, production planning and supply-chain design. The synthetic families illustrate the structure; they are not utility or company data.
- **National:** India can inspect and certify the solver logic inside its own critical-infrastructure optimization software.
- **Research ecosystem:** an open, documented Indian implementation of frontier 2025–26 GPU optimization research and of certified branch-and-cut becomes a public asset for academia and PSU R&D; the known-optimum benchmark pack is reusable by others.

### 13.2 Benefits
- **Economic:** avoids recurring per-seat/per-core commercial licence cost. A rupee figure needs MRPL's actual licence data; we do not quote an unsourced number.
- **Strategic and security:** no foreign black box in energy or critical-infrastructure decision-making, aligned with Atmanirbhar Bharat.
- **Technical:** JAX gives hardware independence (CPU, GPU, TPU), so sovereignty does not become vendor lock-in.
- **Auditability:** a machine-checkable certificate, an escalation log and a verifier report turn "trust the solver" into "check the receipt".
- **Educational:** a documented from-scratch solver is a reference implementation for Indian optimization courses.
- **Openness:** an explicit open licence (Apache-2.0 proposed, subject to the hackathon's IP terms), so the code can be inspected, audited and extended.

### 13.3 Target audience
Refineries and process industries (crude planning, blending, scheduling); manufacturing and logistics (production planning, routing, inventory, supply chain); energy and infrastructure teams (generation planning, dispatch, network optimization); industrial R&D and engineering teams maintaining sovereign optimization systems.

---

## 14. Slide-by-Slide Deck Map

The SIH template has six content slides. Suggested content for each, drawn from this document.

| Slide | What goes on it | Source sections |
|---|---|---|
| **1. Title** | Problem Statement ID SIH26119; title; theme Smart Automation; category Software; team name and ID | §1 |
| **2. Proposed solution** | *Detailed explanation:* the eight-point summary (engine family, certified branch-and-cut, escalation, hybrid parallel, verifier, explainable, benchmark pack, extensible). *How it addresses the problem:* sovereignty (from scratch, no solver dependency), inspectable internals, robustness on degenerate/ill-conditioned/weak-relaxation models, measured GPU use. *Innovation and uniqueness:* the eight items of §11.1. *Diagram:* §4 architecture. | §2, §4, §11 |
| **3. Technical approach** | *Technologies:* Python, JAX (CPU/GPU/TPU), Numba, NumPy; own sparse LU/Cholesky. *Methodology:* the eight steps of §12.2. *Flowchart:* model → presolve → dispatcher → engine race → crossover → branch-and-cut → postsolve → verifier → certificate. Links to prototype, repository and demo video. | §5, §6, §12.2 |
| **4. Feasibility and viability** | *Feasibility:* published algorithms, reference implementations, CPU path complete without GPU, testable at every level. *Viability:* benchmark protocol and claims (§9.4), open benchmark pack. *Challenges and risks:* the six most important rows of §12.3 (first-order accuracy, no warm start, FP64 on consumer GPUs, Python speed, cut safety, non-convex refinery models). *Mitigation:* dual-engine race, compiled kernels, verified cuts, measured routing. | §9, §12 |
| **5. Impact and benefits** | *Potential impact:* solver independence, auditable decisions, reusable optimization, refinery-to-grid-to-logistics reach. *Significance and extension:* NLP/MINLP through the model-class interface, open benchmark pack, sovereign infrastructure. *Benefits tree:* Solver Independence · Auditable Decisions · Reusable Core · Execution Flexibility. *Beneficiaries:* §13.3. | §13 |
| **6. Research and references** | *Research foundations (six):* HPR-LP **[R1]**, HPR-QP **[R3]**, MPAX **[R8]**, safe and verified cuts **[R26]**, VIPR **[R16]**, HiGHS/PDLP **[R18]**. *Comparison table:* §11.3. *Benchmarks:* Netlib, MIPLIB, Mittelmann. | §11.3, §15 |

**One-line pitch for the deck:** *"The solver that proves its answers."*

**Visual proof beats paragraphs:** one crossover chart, one naive-vs-hardened table, and one cut gap-closure chart. Label any chart that shows planned numbers as *target*, and replace with measured numbers as soon as they exist.

**Wording discipline:** say "optimal or near-optimal, with a proven gap" and "certified hybrid CPU–GPU solver core". Do not say "GPU-native": the PS asks for GPU acceleration where it provides measurable benefit, and its emphasis is numerical robustness. Put the robustness table beside the crossover chart.

---

## 15. Research and References

| Tag | Reference | Used for |
|---|---|---|
| R1 | Chen, Sun, Yuan, Zhang, Zhao — "HPR-LP: An implementation of an HPR method for solving linear programming", *Math. Prog. Comp.* 17 (2025), arXiv:2408.12179, doi:10.1007/s12532-025-00292-0. Code: `PolyU-IOR/HPR-LP` | 2.39×–5.70× vs PDLP with presolve on A100 |
| R2 | "On the Relationships among GPU-Accelerated First-Order Methods for LP", arXiv:2509.23903 | cuPDLPx base algorithm is a special case of HPR-LP's; best-overall claim is by the same group |
| R3 | Chen, Sun, Yuan, Zhang, Zhao — "HPR-QP", arXiv:2507.02470 (2025) | Restricted Wolfe dual + symmetric Gauss–Seidel; authors' page tables show Gurobi faster on small QPs |
| R4 | Applegate et al. — "Practical Large-Scale Linear Programming using Primal-Dual Hybrid Gradient", NeurIPS 2021 | PDLP; won the 2024 Beale–Orchard-Hays Prize (per **[R2]**) |
| R4b | "PDLP: A Practical First-Order Method for Large-Scale LP", arXiv:2501.07018 | Giant-LP comparison with Gurobi barrier and simplex |
| R5 | Lu, Yang — "cuPDLP.jl", arXiv:2311.12180 | Notes about one second of GPU kernel-launch overhead |
| R6 | Lu, Peng, Yang — "cuPDLPx", arXiv:2507.14051 (2025) | cuPDLPx; related work discussed in **[R2]** |
| R7 | "An Overview of GPU-based First-Order Methods for LP and Extensions", arXiv:2506.02174 | Survey |
| R8 | Lu, Peng, Yang — "MPAX: Mathematical Programming in JAX", arXiv:2412.09734 (Jan 2026 revision). Code: `MIT-Lu-Lab/MPAX` | r2HPDHG for LP, rAPDHG for QP; batched solving. Reference only |
| R9 | Blin, Gualandi, Maes, Lodi, Stellato — "Batched First-Order Methods for Parallel LP Solving in MIP", arXiv:2601.21990 (Jan 2026) | Strong branching and bound tightening; identifies size regimes |
| R10 | Guan et al. — "B³-PWL: GPU-Batched Branch-and-Bound for PWL Optimization with SOS2 Constraints", arXiv:2608.28988 (Aug 2026) | 9.25× vs cuOpt on 43 instances; Gurobi still fastest; limitations listed |
| R11 | Liu, Lodi, Shafiee — arXiv:2603.01306 (Mar 2026) | Safe lower bounds for certifying optimal sparse GLMs (not general MILP) |
| R12 | Cederberg, Boyd — "Presolving for GPU-Accelerated First-Order LP Solvers" (PSLP), arXiv:2604.23951. Code: `dance858/PSLP` | Integrated in cuPDLPx, cuOpt, HPR-LP |
| R13 | Cederberg, Boyd — "GPU-Accelerated Presolving for LP" (cuPSLP), arXiv:2609.16182 (Sept 2026) | 11× / 42× presolve-time reduction reported |
| R14 | Hoen, Gleixner — "Analyzing the numerical correctness of branch-and-bound decisions for MIP", CPAIOR 2025, arXiv:2412.14710 | Motivates pruning only on proven bounds |
| R15 | Lu, Zhang — "Enhanced PDHG for LP with Online Preconditioning", arXiv:2506.17650 | Reports fewer iterations and less time; specific percentage not confirmed |
| R16 | Cheung, Gleixner, Steffy — "Verifying Integer Programming Results", IPCO 2017 (LNCS 10328, pp. 148–160), arXiv:1611.08832. Code: `scipopt/vipr` | Exact-rational verification of branch-and-cut certificates; model for our derivation records |
| R17 | Gurobi: 13.0 release notes and reference manual (PDHG, GPU preview); Help Center "Installing and Running GPU-enabled Gurobi"; blog "Using GPUs to Solve LPs vs. MIPs: What's the Difference?" | Source for the LP-vs-MIP GPU statements |
| R17b | "Concurrent Crossover for PDHG", arXiv:2510.24429 | GPU vs CPU iteration speed and crossover discussion; 43-model Mittelmann set |
| R18 | HiGHS documentation — Solvers page; HiGHS releases | GPU-capable PDLP, QP solvers, branch-and-cut MIP; README: integer variables only when Q is zero (no MIQP) |
| R19 | NVIDIA cuOpt release notes (`github.com/NVIDIA/cuopt`) | Concurrent root solve, batch PDLP strong branching, Papilo presolve |
| R20 | Neumaier, Shcherbina — "Safe bounds in linear and mixed-integer linear programming", *Math. Programming* 99 (2004) | Safe bounds from approximate duals |
| R21 | Benchmarks: MIPLIB 2017 (miplib.zib.de); Netlib LP (netlib.org/lp); Mittelmann (plato.asu.edu/bench.html); Maros–Mészáros QP set | Benchmark sources used in §9 |
| R22 | Classical dual-simplex implementation reference: Koberstein (2005), *The Dual Simplex Method, Techniques for a Fast and Stable Implementation* | Dual-simplex implementation reference, incl. bound-flipping ratio test |
| R23 | Official problem statement SIH26119 — sih2026.vuce.in/ps/SIH26119 | The requirement map (§1) |
| R24 | Mehrotra — "On the implementation of a primal-dual interior point method", *SIAM J. Optimization* 2(4), 1992 | Basis of our interior-point method |
| R25 | Kelley — "The cutting-plane method for solving convex programs", *J. SIAM* 8(4), 1960 | Basis of the QP fallback and MIQP outer approximation (§6.5, §6.10) |
| R26 | Eifler, Gleixner — "Safe and Verified Gomory Mixed Integer Cuts in a Rational MIP Framework", *SIAM J. Optimization* 34(1), 2024, pp. 742–763, arXiv:2303.12365 | Safe aggregation with approximate duals, then MIR; cuts verified per VIPR |
| R27 | Cook, Dash, Fukasawa, Goycoolea — "Numerically safe Gomory mixed-integer cuts", *INFORMS J. Computing* 21 (2009), pp. 641–649 | Origin of safe aggregation for GMI cuts |
| R28 | Marchand, Wolsey — "Aggregation and mixed integer rounding to solve MIPs", *Operations Research* 49(3) (2001) | c-MIR cuts and path aggregation |
| R29 | Wright — *Primal-Dual Interior-Point Methods*, SIAM (1997) | Interior-point implementation reference |
| R30 | Vanderbei — "Symmetric quasidefinite matrices", *SIAM J. Optimization* 5(1) (1995) | LDLᵀ for the regularized KKT system |
| R31 | Amestoy, Davis, Duff — "An approximate minimum degree ordering algorithm", *SIAM J. Matrix Analysis and Applications* 17(4) (1996) | Ordering for sparse Cholesky |
| R32 | Hall, McKinnon — "Hyper-sparsity in the revised simplex method and how to exploit it", *Computational Optimization and Applications* 32 (2005) | Hypersparse FTRAN/BTRAN |
| R33 | Forrest, Goldfarb — "Steepest-edge simplex algorithms for linear programming", *Mathematical Programming* 57 (1992) | Dual steepest-edge pricing |
| R34 | Harris — "Pivot selection methods of the Devex LP code", *Mathematical Programming* 5 (1973) | Ratio test and Devex |
| R35 | Ruiz — "A scaling algorithm to equilibrate both rows and columns norms in matrices", RAL-TR-2001-034 (2001) | Ruiz equilibration |
| R36 | Fischetti, Glover, Lodi — "The feasibility pump", *Mathematical Programming* 104 (2005) | Primal heuristic |
| R37 | Danna, Rothberg, Le Pape — "Exploring relaxation induced neighborhoods to improve MIP solutions", *Mathematical Programming* 102 (2005) | RINS heuristic |
| R38 | Achterberg, Koch, Martin — "Branching rules revisited", *Operations Research Letters* 33 (2005) | Reliability branching |
| R39 | Chinneck, Dravnieks — "Locating minimal infeasible constraint sets in linear programs", *ORSA J. Computing* 3 (1991) | Deletion filter for infeasibility explanations |
| R40 | Hager — "Condition estimates", *SIAM J. Scientific and Statistical Computing* 5 (1984) | 1-norm condition estimator |
| R41 | Bland — "New finite pivoting rules for the simplex method", *Mathematics of Operations Research* 2(2) (1977) | Anti-cycling fallback |
| R42 | Huangfu, Hall — "Parallelizing the dual revised simplex method", *Mathematical Programming Computation* 10(1) (2018), pp. 119–142 | Intra-simplex parallelism (context) and HiGHS reference |
| R43 | Lee, Pinto, Grossmann, Park — "Mixed-integer linear programming model for refinery short-term scheduling of crude oil unloading with inventory management", *Industrial & Engineering Chemistry Research* 35(5) (1996) | Refinery scheduling MILP background |

---

## 16. Judge Q&A Preparation

| Question | Answer |
|---|---|
| "Why not just use HiGHS?" | The PS requires a sovereign core, not a wrapper. HiGHS is our baseline and cross-check, and it is a strong one. It also does not support integer variables with a quadratic objective, which NIRBHAR does. |
| "Another team also has independent verification. What is different?" | Ours is a proof, not just a check: a bound valid for any dual vector evaluated exactly in rational arithmetic, cut derivations the verifier re-derives, Farkas and unboundedness rays, and an escalation log. The verifier is tested against corrupted bounds, cuts and rays. |
| "Why Python, and is it fast enough?" | Python only orchestrates. All hot loops (LU, Cholesky, simplex, propagation, cut separation) are Numba-compiled over flat arrays with the GIL released, and GPU work is JAX. We publish our measured time ratio to HiGHS and make no claim of parity. |
| "Why HPR on the GPU?" | Published, peer-reviewed, and reported by its authors as the strongest GPU LP method; we reproduce before we claim. It races against simplex and interior point at the root, so it is used only where it wins. |
| "Why not run the whole tree on the GPU?" | Even Gurobi limits GPU use in MIP to the root LP and calls broader GPU branch-and-bound active research **[R17]**. First-order iterates cannot warm-start tree nodes **[R10]**. We use the GPU where evidence supports it and run the tree on warm-started dual simplex across CPU threads. |
| "How does it compare with Gurobi?" | We make no such claim. Here are our measured numbers against HiGHS and MPAX, including where we lose. |
| "Why should I trust the answer?" | It ships a rigorous bound, checked by an independent program that has been tested on corrupted solutions, with an exact-arithmetic mode. Cuts are certified too. |
| "How can cuts be trusted? Floating-point cuts can cut off the optimum." | Cuts are generated by safe aggregation with directed rounding, so they are valid whatever the floating-point error; each carries its derivation and the verifier re-derives it exactly. A property test checks that no known optimum is ever cut off. |
| "What happens on degenerate or ill-conditioned models?" | The solver escalates: perturbation, steepest-edge, Bland's rule, refactorization, rescaling, interior point, crossover, GPU HPR with a certified gap. Every step is logged. A named stress suite shows hardened vs naive vs one mechanism off, and lists residual failures. |
| "What if there's no GPU?" | The CPU path is complete and runs everywhere; JAX falls back automatically. |
| "Does it reach millions of variables?" | LP: yes on the GPU and with interior point up to the ceiling we measured on the scale ladder (about 1e6 variables), with hardware disclosed. MILP: reported per family, instance-dependent. We make no claim about millions of integer variables. |
| "Where is the multi-core parallelism?" | GIL-free threads run node LPs and strong-branching candidates; a root race runs three engines at once; parallel tree search has a deterministic mode. Scaling is sub-linear and poor on small batches, and we show that. |
| "QP and MIQP?" | Convex QP with any sparse Q through interior point (small/medium) and HPR-QP (large); convex MIQP through branch-and-cut over certified relaxations. Non-convex Q is refused, never mis-solved. |
| "NLP and MINLP?" | The architecture takes them through the model-class interface; convex NLP reuses the tangent-bound idea, and non-convex classes return `LOCAL_ONLY` unless a valid convex relaxation exists. `OPTIMAL` always means proven. |
| "Do you use SciPy or any library for the hard parts?" | No solver or factorization library is inside the solver: own parser, presolve, sparse LU and Cholesky, simplex, interior point, HPR, branch-and-cut and verifier. NumPy and JAX are array and GPU frameworks, Numba compiles our own code, SciPy appears only in benchmarks and tests, and a CI import check enforces it. |
| "Is B³-PWL proof this works?" | It is a proof of concept on piecewise-linear/SOS2 problems; Gurobi remained fastest there **[R10]**. It shows the direction, not a finished answer. |
| "Are MRPL numbers real?" | The demo models are synthetic and labelled so. The structure matches refinery planning; validation on MRPL's actual model requires their data. |