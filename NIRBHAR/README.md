# Smart India Hackathon 2026 — Team Vernils Prototypes

This repository workspace contains two separate, sorted projects for SIH 2026:

---

## 1. [PRAMANA](./PRAMANA) — Network Audit Software
- **Problem Statement:** SIH26155 (NTRO)
- **Role:** Offline, self-teaching, multi-vendor network-configuration compliance auditor.
- **Directory:** [`./PRAMANA`](./PRAMANA)
  - `backend/`: FastAPI + PyTorch/Sentence-Transformers offline compliance engine & Trust Gate.
  - `frontend/`: React 18 + Vite network compliance dashboard & flow visualizer.
  - `deploy/`: Air-gapped Docker Compose and container configurations.
  - `docs/`: Architecture decision records (ADRs), specifications, and invariants.
  - `models/`: Offline model manifest.

---

## 2. [NIRBHAR](./NIRBHAR) — Indigenous Optimization Solver
- **Problem Statement:** SIH26119 (Mangalore Refinery and Petrochemicals Limited / MRPL)
- **Role:** India-owned, sovereign, certified hybrid CPU-GPU solver core for LP, MILP, QP, and MIQP (*"The solver that proves its answers"*).
- **Directory:** [`./NIRBHAR`](./NIRBHAR)
  - `backend/`: Pure Python/NumPy/Numba/JAX solver core (zero external solver packages) + independent verifier + Netlib benchmark test suite.
  - `src/` & `public/`: React 19 + TypeScript + Vite browser showcase (Solve Studio, Refinery Demo, Branch & Cut Lab, Robustness Lab).
  - `data/`: 43 Netlib / MIPLIB / QP benchmark instances with SHA-256 integrity verification.
  - `docs/`: Backend progress logs, gap analysis, and implementation prompts.
