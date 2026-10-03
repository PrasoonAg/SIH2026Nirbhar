# NIRBHAR — Sovereign Certified Optimization Solver Core (Backend)

**Smart India Hackathon 2026 | Problem Statement SIH26119 | Team Vernils | Built for MRPL**

> **"The solver that proves its answers."**

NIRBHAR is an indigenous, sovereign certified mathematical optimization solver core built from first principles with zero external solver dependencies. It solves Linear Programs (LP), Mixed-Integer Linear Programs (MILP), and Convex Quadratic Programs (QP / MIQP), and accompanies every solution with a cryptographically hashed, independently verifiable certificate of optimality or certified infeasibility.

---

## 1. Sovereignty & Architectural Principles

1. **100% Sovereign Math Core**:
   - Zero external solver/optimization packages: strictly **no SciPy, GLPK, HiGHS, cvxpy, or COIN-OR**.
   - Built solely on Python standard library and raw `numpy` for contiguous vector/matrix buffers.
   - Enforced continuously by `python tools/check_imports.py` and `tests/test_import_rules.py`.

2. **Air-Gapped Zero-Trust Verifier (`nirbhar_verify/`)**:
   - The standalone verifier does **not** import any code from `nirbhar/`.
   - Has its own isolated MPS reader, computes safe Lagrangian dual lower bounds $LB(y)$, checks primal & dual feasibility directly on the original model text, and verifies certificates independently.

3. **Mathematical Rigor & Honest Status Disciplines**:
   - `OPTIMAL` is reported only when the certified dual gap $\le \text{tol}$ AND the independent verifier passes.
   - Infeasible models are certified via Farkas rays with contradiction values $b^T y > 0$ and $A^T y \le 0$.
   - Conflicting constraints are isolated via an Irreducible Infeasible Subsystem (IIS) deletion filter.
   - Non-convex quadratic models are checked via Cholesky decomposition and refused honestly with `UNSUPPORTED`.

---

## 2. Solver Engine Architecture

```
NIRBHAR/backend/
├── nirbhar/
│   ├── io/                # Fixed & free MPS reader, bounds, ranges, markers, QMATRIX
│   ├── linalg/            # Markowitz LU, Cholesky, iterative refinement, condition estimator
│   ├── presolve/          # Geometric-mean + Ruiz scaling, singleton/fixed/redundant reductions
│   ├── lp/                # Two-phase bounded revised simplex, safe Lagrangian bound LB(y)
│   ├── ipm/               # High-precision Mehrotra Predictor-Corrector IPM for LP
│   ├── qp/                # PSD verification, Mehrotra QP solver, Kelley Outer-Approximation MIQP
│   ├── cuts/              # Gomory Mixed-Integer (GMI), c-MIR, and Extended Cover cuts
│   ├── mip/               # Certified Branch-and-Cut, branching rules, node selection, heuristics
│   ├── robust/            # Multi-level escalation controller (naive -> Bland -> tight -> presolve -> IPM)
│   ├── explain/           # Farkas ray certificate, IIS deletion filter, plain-English report
│   ├── industrial/        # MRPL multi-period refinery planning generator (LP/MILP/QP)
│   ├── certificate/       # Schema v1.0.0 JSON certificate builder
│   └── cli.py             # Unified CLI (solve, verify, industrial, bench)
├── nirbhar_verify/        # Standalone, isolated verifier package (Zero imports from nirbhar/)
│   ├── checker.py         # Original MPS verification, dual bound checking, Farkas validation
│   ├── mps_minimal.py     # Independent MPS parser
│   └── cli.py             # Standalone `nirbhar-verify` CLI
├── tests/                 # 68 comprehensive unit and integration tests (100% pass)
└── tools/
    └── check_imports.py   # AST-based import sovereignty validator
```

---

## 3. Quick Start & CLI Usage

### Prerequisites
- Python 3.10+
- `numpy`

```bash
cd NIRBHAR/backend
pip install -r requirements.txt
```

### Validate Sovereignty
```bash
python tools/check_imports.py
```
Output:
```
[PASS]  check_imports PASSED - 50 files scanned, 0 violations.
```

### Run Test Suite
```bash
pytest
```
Output:
```
============================== 68 passed ==============================
```

---

## 4. CLI Commands

### 1. Solve an Optimization Model
Solve LP, MILP, or QP models from MPS files with automatic engine dispatch or specific solvers:

```bash
# Auto-dispatch solve with certificate generation
python -m nirbhar.cli solve ../data/netlib/afiro.mps --engine auto --out cert_afiro.json

# Solve with high-precision Interior Point Method (Mehrotra IPM)
python -m nirbhar.cli solve ../data/netlib/blend.mps --engine ipm

# Solve with certified Branch-and-Cut (MILP)
python -m nirbhar.cli solve ../data/milp/p0033.mps --engine bnc --cuts on
```

### 2. Verify a Certificate (Air-Gapped)
Independently verify an optimality certificate against the original MPS formulation:

```bash
python -m nirbhar_verify.cli cert_afiro.json ../data/netlib/afiro.mps
```

### 3. Generate and Solve MRPL Refinery Models
Synthesize multi-period Crude Distillation Unit (CDU), hydrotreater, blending, and inventory models for Mangalore Refinery and Petrochemicals Limited:

```bash
# Multi-period baseline LP
python -m nirbhar.cli industrial --class LP --periods 4 --scenario baseline

# Multi-period MILP with crude campaign switchings and run lengths
python -m nirbhar.cli industrial --class MILP --periods 4 --scenario tight-sulfur

# Multi-period Convex QP with quadratic price-risk terms
python -m nirbhar.cli industrial --class QP --periods 4 --scenario crude-shock
```

### 4. Run Benchmarks
Run Netlib LP, QP, or stress suites:
```bash
python -m nirbhar.cli bench --tier t1 --limit 5
```

---

## 5. Industrial Refinery Formulation (MRPL)

The built-in industrial generator models a realistic refinery flow for MRPL:
- **10 Crude Assays**: Arab Light, Arab Heavy, Bonny Light, Basrah, Brent, Maya, Saharan Blend, Dubai, Urals, Eagle Ford.
- **Processing Units**: Atmospheric CDU, Vacuum Distillation Unit (VDU), Hydrocracker, Fluid Catalytic Cracking (FCC), Reformer.
- **Product Blends**: LPG, High-Speed Diesel (BS-VI compliant, $\le 10$ ppm sulfur), Motor Spirit (Gasoline), Aviation Turbine Fuel (ATF), Fuel Oil.
- **Economic Outputs**: Gross Refining Margin (GRM in $/bbl), shadow prices on CDU capacities, and bottleneck diagnostics.
