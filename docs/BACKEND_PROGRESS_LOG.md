# NIRBHAR Backend — Progress Log & System State Audit
**Smart India Hackathon 2026 (SIH26119)**  
**Problem Statement:** Indigenous GPU-Accelerated Optimization Solver (Sovereign Alternative to Xpress / CPLEX)  
**Team:** Vernils | **Client:** Mangalore Refinery and Petrochemicals Limited (MRPL)  
**Date:** March 2026 / October 2026  
**Status:** Phase 0 (Complete), Phase 1 (Core LP Simplex in Progress — 20 Passing, 3 Failing)

---

## 1. Executive Summary

The backend for **NIRBHAR** is an indigenous, from-scratch optimization solver core built strictly in Python 3.11+ / NumPy / Numba / JAX with **zero external solver dependencies** (no SciPy, CVXPY, HiGHS, PuLP, OR-Tools inside the solver engine).

### Milestones Completed:
1. **Phase 0 (Scaffolding & IO Core): COMPLETE**
   - Repository scaffolding under `backend/` with standard package layout.
   - Strict sovereignty enforcement via AST audit in `backend/tools/check_imports.py` (passes 27 files, 0 violations).
   - Core immutable data model in `backend/nirbhar/io/model.py` (`Model`, `CSRMatrix`, `CSCMatrix`, bound conventions, SHA-256 hash tracking).
   - High-performance MPS/QPS parser in `backend/nirbhar/io/mps.py`, `qps.py`, and exporter in `writer.py`. All 12 parser traps and edge cases verified.
   - Independent verifier package in `backend/nirbhar_verify/` with completely isolated MPS parser (`mps_min.py`) and LP solution verifier (`lp_verify.py`).
   - Pytest suite: 20 tests passing out of 24.
2. **Phase 1 (Engine Core — Simplex & Linear Algebra): IN PROGRESS**
   - Dense LU factorization with partial pivoting and iterative refinement (`backend/nirbhar/linalg/lu_markowitz.py`, `refine.py`).
   - LP Basis tracker (`backend/nirbhar/lp/basis.py`).
   - Revised simplex solver (`backend/nirbhar/lp/dual_simplex.py`) scaffolded; currently failing on `afiro` and `adlittle` due to coordinate-shift and Big-M artificial variable interaction bugs.

---

## 2. Test Suite Status & Verification Audit

### Test Summary (`pytest backend/tests`):
- **Total Tests:** 24
- **Passed:** 20 (83.3%)
- **Failed:** 3 (12.5%)
- **Skipped:** 1 (4.2% — `test_all_t1_lp_optimal` conditioned on single-model pass)
- **Time:** ~9.9s

### Detailed Test Results Breakdown:
| Test File | Test Name | Status | Details |
|---|---|---|---|
| `test_import_rules.py` | `test_sovereignty_check_passes` | **PASSED** | 0 forbidden imports; strict isolation verified |
| `test_parser.py` | `test_manifest_loads` | **PASSED** | `data/manifest.json` parsed correctly |
| `test_parser.py` | `test_all_manifest_models_parse` | **PASSED** | All 43 Netlib/MIPLIB/QP/Stress instances parsed |
| `test_parser.py` | `test_manifest_nnz` | **PASSED** | Nonzero count matches manifest references exactly |
| `test_parser.py` | `test_manifest_integer_counts` | **PASSED** | Integer variable counts match manifest |
| `test_parser.py` | `test_roundtrip_afiro` | **PASSED** | Parse -> write -> reparse preserves model integrity |
| `test_parser.py` | `test_trap_dcmulti_importances_ignored` | **PASSED** | Trailing data after `ENDATA` ignored |
| `test_parser.py` | `test_trap_forplan_ranges` | **PASSED** | MPS `RANGES` section parsed correctly |
| `test_parser.py` | `test_trap_misc03_fr_bound` | **PASSED** | Free variable `FR` bound handled |
| `test_parser.py` | `test_trap_bv_bound` | **PASSED** | Binary variable `BV` bound handled |
| `test_parser.py` | `test_trap_fr_bound_inline` | **PASSED** | Inline `FR` bounds handled |
| `test_parser.py` | `test_trap_mi_bound_inline` | **PASSED** | Negative infinity `MI` bounds handled |
| `test_parser.py` | `test_trap_li_ui_bounds` | **PASSED** | Integer bounds `LI` / `UI` handled |
| `test_parser.py` | `test_trap_objsense_max` | **PASSED** | `OBJSENSE MAX` objective negation handled |
| `test_parser.py` | `test_trap_ranges_e_row_positive` | **PASSED** | Equality range sign handled |
| `test_parser.py` | `test_trap_ranges_e_row_negative` | **PASSED** | Equality negative range handled |
| `test_parser.py` | `test_trap_negative_up_zero_lower` | **PASSED** | Negative upper bound with 0 lower bound |
| `test_parser.py` | `test_trap_endata_ignores_trailing` | **PASSED** | Robust trailing whitespace/text tolerance |
| `test_parser.py` | `test_malformed_mps_raises_parse_error` | **PASSED** | Explicit line-numbered exceptions on bad syntax |
| `test_parser.py` | `test_unknown_row_in_columns_raises` | **PASSED** | Missing row reference raises `ParseError` |
| `test_lp_t1.py` | `test_afiro_optimal` | **FAILED** | Returned `obj=0.0` vs ref `-464.753` (rel error 0.998) |
| `test_lp_t1.py` | `test_adlittle_optimal` | **FAILED** | Returned status `NUMERICAL` instead of `OPTIMAL` |
| `test_lp_t1.py` | `test_lp_verifier_passes_on_afiro` | **FAILED** | Independent verifier rejected afiro `obj=0.0` |
| `test_lp_t1.py` | `test_all_t1_lp_optimal` | **SKIPPED** | Skipped pending afiro/adlittle stability |

---

## 3. Component Implementation Breakdown

### 3.1 `backend/tools/check_imports.py` (Sovereignty & Isolation Guard)
- Scans `backend/nirbhar` and `backend/nirbhar_verify` via Python AST.
- Blocks: `scipy`, `cvxpy`, `highspy`, `highs`, `ortools`, `pulp`, `pyomo`, `mpax`, `glpk`, `gurobipy`, `cplex`, `xpress`, `cylp`, `pyscipopt`, `clarabel`, `osqp`, etc.
- Enforces strict one-way isolation: `nirbhar_verify/` CANNOT import anything from `nirbhar/`.
- **Status:** **100% Passing** (`[PASS] check_imports PASSED — 27 files scanned, 0 violations`).

### 3.2 `backend/nirbhar/io/` (Parser, Model & Writer)
- `model.py`: Immutable `Model` dataclass.
  - Fields: `name`, `nrows`, `ncols`, `c`, `A_csr`, `A_csc`, `row_lo`, `row_hi`, `col_lo`, `col_hi`, `is_int`, `Q_csr`, `obj_sense`, `obj_const`, `row_names`, `col_names`, `sha256`.
  - Infinity constant `INF = 1e30`.
- `mps.py`: High-performance fixed and free format MPS parser. Handles `NAME`, `OBJSENSE`, `ROWS`, `COLUMNS`, `RHS`, `RANGES`, `BOUNDS`, `QUADOBJ`, `QMATRIX`, `ENDATA`.
- `qps.py`: Parser for quadratic objectives (`QUADOBJ`, `QMATRIX`).
- `writer.py`: Exports `Model` back to standard MPS/QPS format, enabling roundtrip verification.
- **Status:** **100% Complete & Tested.**

### 3.3 `backend/nirbhar/sparse/` (Sparse Matrix Algebra)
- `csr.py`: Custom `CSRMatrix` and `CSCMatrix` dataclasses with `matvec`, `rmatvec`, slicing, and conversions.
- **Status:** **Phase 0 baseline complete.**

### 3.4 `backend/nirbhar/linalg/` (Linear Algebra Core)
- `lu_markowitz.py`: Dense LU factorization with partial pivoting (`LUFactor`).
  - Supports `solve(rhs, transpose=False)`.
  - Condition number estimation via Hager's 1-norm power method.
  - Raises `SingularBasisError` on pivot breakdown (< 1e-14).
  - *Note for Phase 2:* Will be replaced/supplemented by sparse Markowitz LU with threshold partial pivoting and Forrest-Tomlin / product-form updates.
- `refine.py`: Iterative refinement routine (`iterative_refine`) using residual corrections $r = b - A x$, $\Delta x = B^{-1} r$ to eliminate floating-point drift.
- **Status:** **Phase 1 dense LU operational.**

### 3.5 `backend/nirbhar_verify/` (Independent Sovereign Verifier)
- `mps_min.py`: Ultra-lightweight standalone MPS reader (120 lines, zero `nirbhar` imports, pure stdlib + NumPy). Computes independent SHA-256 model hash.
- `lp_verify.py`: Independent LP verification engine (`verify_lp`).
  - Validates:
    1. Primal variable bounds: $col\_lo \le x \le col\_hi$.
    2. Primal constraint bounds: $row\_lo \le A x \le row\_hi$.
    3. Dual feasibility (reduced costs sign relative to active bounds).
    4. Complementary slackness: $(c_j - A_{:,j}^T y) \cdot (x_j - bound) = 0$.
    5. Objective agreement: $|c^T x - b^T y| \le tol$.
    6. Certified duality gap.
  - Generates structured `VerifyResult` (`PASS`/`FAIL` with violation diagnostics).
- **Status:** **Complete & operational.** Properly catches invalid solutions (as demonstrated by correctly flagging the erroneous `afiro` solution).

### 3.6 `backend/nirbhar/lp/` (LP Solver Engines)
- `basis.py`: Manages LP basis state:
  - Tracks basic columns from $[A \mid I_{slacks}]$ of dimension $m \times (n+m)$.
  - Variable status flags (`NONBASIC_AT_LOWER = -1`, `NONBASIC_AT_UPPER = -2`, `NONBASIC_FREE = -3`, `BASIC = 0`).
  - Tracks `eta_count` and refactorization triggers.
- `dual_simplex.py`: Current revised simplex implementation.
  - Currently implements a standard-form conversion with Big-M artificial variables and Dantzig pricing.
  - **Issues identified:**
    1. Lower bound shifting logic corrupts RHS $b$.
    2. Negating rows with negative RHS without properly flipping artificial variable signs results in an initial basic point that violates $B x_B = b$.
    3. Big-M constant ($10^7$) overwhelms reduced costs of structural variables, causing premature termination at non-optimal point ($obj=0.0$).
    4. Matrix refactorization during basis updates hits numerical instability on models with wide coefficient spreads like `adlittle`.
- **Status:** **Requires refactoring to Bounded Dual Simplex / Two-Phase Primal Simplex.**

---

## 4. Root Cause Analysis for Current Failures

### 1. `test_afiro_optimal` ($obj=0.0$ vs reference $-464.753$):
- **Mechanism:** In `dual_simplex.py:88-98`:
  ```python
  neg = b_shifted < 0
  b_shifted[neg] = -b_shifted[neg]
  A_t[neg, :] = -A_t[neg, :]
  ```
  `A_t` already contained the identity matrix for artificial variables: `A_t = np.concatenate([A_ext, np.eye(m)], axis=1)`.
  Negating row $i$ made the artificial column $-1$, while `c_t` kept $+M$.
  The initial artificial assignment $x_B = b_{shifted} \ge 0$ therefore gave $A_t[:, basic] x_B = -b_{shifted}$, which violated the equality constraint.
  Because $M = 10^7$, the reduced costs of the artificials dominated the Dantzig pricing, terminating at iteration 29 where nonbasic structural variables with large true negative reduced costs were ignored.

### 2. `test_adlittle_optimal` (`status == NUMERICAL`):
- **Mechanism:** In `dual_simplex.py:185-186`, basis updates only incrementally update $x_B \leftarrow x_B - \text{step} \cdot d$. Over 50 iterations without eta updates or fresh solves, numerical cancellation makes the basis matrix ill-conditioned, and `LUFactor.factor(B)` encounters pivots $< 1e-14$, raising `SingularBasisError` and returning `NUMERICAL`.

### 3. `test_lp_verifier_passes_on_afiro`:
- **Mechanism:** Directly caused by failure (1). The verifier correctly caught:
  `['Primal: 2 constraints below lower bound', 'Dual: 4 negative reduced costs at lower bound', 'Duality gap 1.00e+00 > 1.00e-06']`.
  This proves the independent verifier works as designed.

---

## 5. Next Immediate Steps (Phase 1 Completion)

1. **Refactor `dual_simplex.py` & `basis.py`:**
   - Implement either:
     - **Option A (True Bounded Dual Simplex):** Start dual feasible (slack basis with perturbations if needed), perform dual ratio test (Harris two-pass with bound flipping) moving towards primal feasibility.
     - **Option B (Two-Phase Revised Primal Simplex):**
       - Phase 1: Minimize sum of artificial infeasibilities (objective $\sum a_i$, no Big-M numerical pollution).
       - Phase 2: Once feasible, switch to true objective $c^T x$.
       - Proper upper-bounded simplex: allow nonbasic variables at lower bound $l_j$ OR upper bound $u_j$, so slacks do not double the problem size.
2. **Implement Safe Bound & Certificate Builder (`backend/nirbhar/certificate/`):**
   - Safe dual lower bound formula:
     $$d = c - A^T y$$
     $$LB(y) = \sum_i \left(\max(y_i,0) rl_i + \min(y_i,0) ru_i\right) + \sum_j \left(\max(d_j,0) l_j + \min(d_j,0) u_j\right)$$
   - Conservative float64 error margin: $(n+m) \cdot \epsilon \cdot \sum |terms|$.
   - JSON certificate schema generation (`certificate.json`).
3. **Validate all Netlib T1 LPs:**
   - `afiro`, `adlittle`, `kb2`, `sc50a`, `sc50b`, `blend`, `recipe`, `share1b`, `share2b`, `stocfor1`.
   - Ensure all achieve `OPTIMAL`, relative error $< 10^{-4}$ ($10^{-6}$ target), and `nirbhar_verify` verdict `PASS`.
