# NIRBHAR Backend: Master Continuation Prompt (for Claude Sonnet)

> **Context:** Smart India Hackathon 2026 (PS SIH26119) — Team Vernils (for Mangalore Refinery and Petrochemicals Limited / MRPL).  
> **Repository Root:** `d:\Prasoon Work\Codes\Vibe coding\Prototype\`  
> **Backend Directory:** `backend/`  
> **Previous Progress Log:** Read `docs/BACKEND_PROGRESS_LOG.md` before starting.

---

## 1. YOUR ROLE & PROJECT MANDATE

You are a senior numerical-optimization and Python performance engineer. You are building the **NIRBHAR solver core**: an India-owned, sovereign, from-scratch **certified hybrid CPU-GPU solver** for LP, MILP, QP, and convex MIQP.

### The Deck's One-Line Promise:
> **"The solver that proves its answers."**

### Non-Negotiable Hard Rules:
1. **Sovereignty:** `backend/nirbhar/` and `backend/nirbhar_verify/` import **NO external solver library** (NO SciPy, CVXPY, HiGHS, highspy, PuLP, Pyomo, OR-Tools, MPAX, OSQP, Clarabel). Allowed: Python stdlib, NumPy, Numba, JAX. SciPy and highspy are permitted ONLY in `bench/` and `tests/`. Enforced by `backend/tools/check_imports.py` (AST scanner).
2. **Verifier Isolation:** `backend/nirbhar_verify/` imports NOTHING from `backend/nirbhar/`. It maintains its own independent model reader and verification logic.
3. **No Approximate Pruning:** A B&B node is pruned only when its safe lower bound $LB(y) \ge UB - tol$. Infeasible nodes must produce a verified Farkas ray.
4. **Honesty & No Fake Results:** No hardcoded numbers or fake timings. If a test fails, fix the algorithm.
5. **CPU Completeness:** No deliverable may strictly require a GPU; JAX and Numba must execute seamlessly on CPU.

---

## 2. CURRENT STATE OF THE REPOSITORY

### What Is Already Completed & Tested (20 of 24 tests PASSING):
1. **Sovereignty Checker (`backend/tools/check_imports.py`):**
   - 27 files scanned, 0 violations. AST scanner guarantees zero solver library leakage.
2. **Data & Manifest (`data/manifest.json`):**
   - 43 reference models (Netlib LPs, MIPLIB 3 MILPs, QPs, MIQPs, Stress models) with exact HiGHS reference optima.
3. **Model & IO (`backend/nirbhar/io/`):**
   - `model.py`: Immutable `Model` (`c`, `A_csr`, `A_csc`, `row_lo`, `row_hi`, `col_lo`, `col_hi`, `is_int`, `Q_csr`, `obj_const`, SHA-256 hash).
   - `mps.py`: Fixed and free format MPS parser. Passed all 12 trap tests: trailing data after `ENDATA` (`dcmulti`), `RANGES` (`forplan`), `FR` bounds (`misc03`), `BV`, `MI`, `LI/UI`, `OBJSENSE MAX`, negative ranges on E rows, negative UP with zero lower.
   - `qps.py`: Quadratic matrix/objective parser (`QUADOBJ`, `QMATRIX`).
   - `writer.py`: MPS/QPS round-trip export.
4. **Sparse & Linear Algebra (`backend/nirbhar/sparse/`, `backend/nirbhar/linalg/`):**
   - `csr.py`: Custom CSR/CSC sparse data structures.
   - `lu_markowitz.py`: Dense LU factorization (`LUFactor`) with partial pivoting, condition estimation, and `solve(rhs, transpose=False)`.
   - `refine.py`: Iterative refinement (`iterative_refine`) for residual polishing.
5. **Independent Verifier (`backend/nirbhar_verify/`):**
   - `mps_min.py`: Isolated minimal MPS parser.
   - `lp_verify.py`: Independent LP certifier checking row bounds, col bounds, dual feasibility, complementary slackness, and duality gap. Correctly identifies faulty solutions.

### Current Test Suite Output:
Run command: `python -m pytest backend/tests`
- **20 PASSED** (`test_parser.py` all 19 tests, `test_import_rules.py`)
- **3 FAILED:**
  - `backend/tests/test_lp_t1.py::test_afiro_optimal` (obj=0.0 vs ref=-464.753)
  - `backend/tests/test_lp_t1.py::test_adlittle_optimal` (status NUMERICAL instead of OPTIMAL)
  - `backend/tests/test_lp_t1.py::test_lp_verifier_passes_on_afiro` (fails because afiro obj was 0.0)
- **1 SKIPPED:** `backend/tests/test_lp_t1.py::test_all_t1_lp_optimal`

---

## 3. IMMEDIATE PRIORITY: FIX LP SIMPLEX IN PHASE 1

### Detailed Root Cause of Current Failures in `backend/nirbhar/lp/dual_simplex.py`:
1. **Big-M Numerical Destruction & Artificial Variable Row Inversion:**
   - In `_standard_form` and `dual_simplex_solve`, row negations for $b < 0$ negated $A_t$ rows *after* appending identity artificial columns:
     ```python
     A_t = np.concatenate([A_ext, np.eye(m)], axis=1)
     neg = b_shifted < 0
     b_shifted[neg] = -b_shifted[neg]
     A_t[neg, :] = -A_t[neg, :] # Made artificial columns -1!
     ```
     This made the initial artificial basis $B$ have $-1$ on the diagonal, while $x_B = b_{shifted} \ge 0$, violating $B x_B = b$.
   - Combining Big-M ($M = 10^7$) with Dantzig pricing overwhelmed structural reduced costs, causing early termination at iteration 29 with $x=0$, $obj=0.0$.
2. **Numerical Drift on Basis Updates in `adlittle`:**
   - Incremental $x_B$ updates without fresh LU refactorization from original columns caused ill-conditioning, making pivots drop below $10^{-14}$ and returning `NUMERICAL`.

### Your Task to Fix `dual_simplex.py` & `basis.py`:
Implement a clean, numerically sound revised simplex solver. You have two approved approaches:

#### Preferred: Two-Phase Revised Primal Simplex with Bounded Variables:
1. **Standard Form Representation:**
   - Variables with bounds $l_j \le x_j \le u_j$.
   - Shift coordinates: $x'_j = x_j - l_j \in [0, u_j - l_j]$.
   - Constraints: $A x' = b' = b - A l$.
   - Add slack variables for inequalities:
     - For $\le$ constraint $a_i^T x' \le b'_i$: add slack $s_i \ge 0$, $a_i^T x' + s_i = b'_i$.
     - For $\ge$ constraint $a_i^T x' \ge b'_i$: add surplus $s_i \ge 0$, $a_i^T x' - s_i = b'_i$.
     - For equality / ranged rows: handle accordingly.
2. **Phase 1 (Finding Feasibility — NO Big-M):**
   - For rows where the initial slack violates feasibility ($b'_i < 0$), or for equality rows without natural slacks, introduce an artificial variable $a_i \ge 0$.
   - Objective in Phase 1: $\min \sum a_i$.
   - Solve with revised simplex until $\sum a_i = 0$ (primal feasible). If $\min \sum a_i > tol$, return `FarkasRay` (`INFEASIBLE`).
3. **Phase 2 (Optimality):**
   - Drive out any remaining artificial variables from the basis.
   - Restore true objective $c^T x + \text{obj\_const}$.
   - Solve with revised simplex until all nonbasic reduced costs $rc \ge -tol$.
4. **Basis Management & Refactorization:**
   - Every `refactor_freq = 50` iterations, recompute the dense basis matrix $B = A_{all}[:, basic]$ from original data and re-factor with `LUFactor.factor(B)`.
   - Recompute basic values: $x_B = \text{lu.solve}(b_{eq})$.
   - Dual vector: $y = \text{lu.solve}(c_B, \text{transpose=True})$.
   - Reduced costs: $rc_j = c_j - A_{:, j}^T y$.
5. **Primal & Dual Recovery:**
   - Reconstruct $x$ in original unshifted space: $x_j = l_j + x'_j$.
   - Primal objective: $z_p = c^T x + \text{obj\_const}$.
   - Dual objective: $z_d = b^T y + \text{obj\_const}$.
   - Duality gap: $\text{gap} = |z_p - z_d| / (1.0 + |z_d|)$.

### Acceptance Criteria for Phase 1:
- `python -m pytest backend/tests/test_lp_t1.py` passes all tests!
- `afiro`, `adlittle`, and all T1 Netlib instances reach `status == "OPTIMAL"` with relative error $< 10^{-4}$ (target $< 10^{-6}$) against manifest reference optima.
- Independent verifier `verify_lp` returns `PASS` on all solutions.

---

## 4. PHASE 1 FINALIZATION: SAFE BOUND & CERTIFICATE

Once `test_lp_t1.py` is green:
1. Create `backend/nirbhar/certificate/safe_bound.py`:
   - Compute the rigorous dual lower bound valid for ANY $y$:
     $$d = c - A^T y$$
     $$LB(y) = \sum_{i=1}^m \left(\max(y_i,0) rl_i + \min(y_i,0) ru_i\right) + \sum_{j=1}^n \left(\max(d_j,0) l_j + \min(d_j,0) u_j\right)$$
     (with convention $0 \cdot \pm\infty = 0$; clip $y_i$ if multiplying infinite bounds).
   - Conservative float64 error allowance: $(n + m) \cdot \epsilon \cdot \sum |\text{terms}|$.
2. Create `backend/nirbhar/certificate/builder.py`:
   - Generate `certificate.json` adhering to the NIRBHAR schema: `schema_version`, `status`, `model`, `objective`, `bound`, `gap`, `violations`, `hardware`, `solve_path`, `timing_s`, `verifier`.

---

## 5. SUBSEQUENT PHASE ROADMAP

Follow the strict phase order from the project specification:

### Phase 2: Presolve, Interior Point & Robustness
- **M3 Presolve (`backend/nirbhar/presolve/`):**
  - Geometric-mean and Ruiz scaling.
  - Reductions: singleton rows/cols, empty rows/cols, fixed variables, duplicate rows, bound tightening, postsolve reconstruction.
- **M5 Mehrotra IPM (`backend/nirbhar/ipm/mehrotra.py`):**
  - Predictor-corrector for LP and convex QP.
  - Normal equations solve via Cholesky / augmented system LDL^T.
  - Adaptive step-length, centering parameter $\sigma = (\mu_{aff} / \mu)^3$.
- **M12 Robustness Controller (`backend/nirbhar/robust/`):**
  - Escalation table: stall $\to$ perturb $\to$ Devex/Bland; singular $\to$ refactor/slack swap; inaccurate $\to$ iterative refinement.
  - `naive_mode`: fair textbook configuration used to prove where an unhardened solver fails.
- Accept: Netlib T2 models, stress suite S1/S2 (`beale_cycling`, `sc50a_rescaled_1e6`), status models (`galenet`).

### Phase 3: JAX HPR, Crossover & Root Race
- **M6 HPR Engines (`backend/nirbhar/lp/hpr.py`, `qp/hpr_qp.py`, `lp/hpr_batch.py`):**
  - Halpern Peaceman-Rachford first-order engine in JAX (`jax_enable_x64=True`).
  - CPU/GPU unified code path; write `docs/hpr_notes.md`.
- **M7 Crossover (`backend/nirbhar/lp/crossover.py`):**
  - Crash basis from HPR/IPM point $\to$ clean up with simplex to obtain an exact basic optimal solution.
- **M13 Dispatcher & Race (`backend/nirbhar/dispatch.py`, `race.py`):**
  - Concurrent race at root: simplex + IPM + HPR. First to pass safe-bound gap check wins; losers cancelled.

### Phase 4: Certified Branch-and-Cut (MILP)
- **M10 Certified B&C (`backend/nirbhar/mip/`, `backend/nirbhar/cuts/`):**
  - Safe pruning rule: Prune ONLY when $LB(y) \ge UB - tol$.
  - Cuts: GMI, c-MIR, cover cuts with full derivation records.
  - Branching: most-fractional, strong branching, pseudocost.
  - Reduced-cost fixing certified through $LB(y)$ term split.
- Accept: All MIPLIB 3 T1 models solve to optimality with verifier `PASS`.

### Phase 5: Convex QP & MIQP + Exact Verifier Mode
- **M11 QP & MIQP (`backend/nirbhar/qp/`):**
  - Cholesky PSD check; separable Lagrangian bound for diagonal $Q$; tangent outer-approximation bound for general convex $Q$.
- **M9 Exact Mode (`backend/nirbhar_verify/exact.py`):**
  - Exact rational arithmetic with `fractions.Fraction`.
  - Adversarial suite: 7 corruption attacks (row violation, flipped integer, altered obj, bad $y$, forged ray, corrupted cut, hash tampering) — verifier must reject 100%.

### Phase 6: Explainability, Plugins & Industrial Generators
- **M14 Explainability (`backend/nirbhar/explain/`):**
  - Shadow prices, binding constraints, RHS/cost ranging, Irreducible Conflicting Set (IIS) via deletion filter.
- **M15 Plugin Registry (`backend/nirbhar/extend/`):**
  - 8 interfaces (`Engine`, `Presolver`, `Propagator`, `BranchingRule`, `NodeSelector`, `Heuristic`, `CutGenerator`, `ModelClass`).
- **M16 Industrial Generators (`backend/nirbhar/industrial/`):**
  - Synthetic MRPL-like refinery model (blending LP, campaign MILP, price-risk QP, over-constrained infeasible model), lot-sizing, transport, unit commitment.

### Phase 7: Benchmarks & Final Documentation
- **M18 Benchmarks (`backend/bench/`):**
  - Comparative tables vs HiGHS 1.15.1, crossover scaling ladder, GPU benchmarks (`gpu_run.py`).
  - Update `docs/KNOWN_LIMITS.md`, `docs/instances.md`, `README.md`.

---

## 6. COMMAND EXECUTION GUIDELINES

Run these commands in PowerShell from the repository root:
```powershell
# 1. Run full test suite
python -m pytest backend/tests

# 2. Run specifically the T1 LP tests
python -m pytest backend/tests/test_lp_t1.py -v

# 3. Verify sovereignty (zero forbidden imports)
python backend/tools/check_imports.py
```

Always ensure `check_imports.py` and `pytest backend/tests` are executed and reported after your code modifications!
