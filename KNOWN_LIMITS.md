# KNOWN_LIMITS.md — NIRBHAR Showcase Prototype

This file honestly lists what this prototype does **and what it does not do**, per the SIH26119 specification's requirement for transparent honesty labelling.

## Linear Algebra

- **Dense vs Sparse LU Factorization**: Basis management in `backend/nirbhar/linalg/lu_markowitz.py` uses dense Gaussian elimination with row partial pivoting (`_lu_factor_pure`). It is numerically stable and validated on models up to ~500 rows. Full dynamic sparse Markowitz pivot minimization is designated for the next enterprise milestone.
- **Normal Equations Cholesky for IPM**: Mehrotra Predictor-Corrector IPM (`backend/nirbhar/ipm/mehrotra.py`) solves normal equations $M = A D^2 A^T$ using dense Cholesky decomposition (`np.linalg.cholesky`) with Tikhonov regularization when ill-conditioned.

## GPU / Hardware & JAX

- **JAX Native Execution (Backend)**: JAX 0.11.2 is installed in the Python environment. The Halpern-Peaceman-Rachford (HPR) primal-dual solver (`backend/nirbhar/hpr/hpr_solver.py`) leverages JAX JIT compilation (`@jax.jit`) for hardware-accelerated operator updates and `@jax.vmap` for batched multi-scenario analysis. When executed on CPU, it runs via JAX CPU backend; on systems with CUDA/ROCm, it compiles directly to GPU/TPU kernels.
- **WebGPU (Browser Prototype)**: `src/solver/lp/webgpuHpr.ts` detects WebGPU adapter and device capabilities via `navigator.gpu`. In the browser prototype, matrix operations execute primarily through multi-threaded CPU Web Workers.

## Basis Crossover Engine

- **Crossover Implementation**: `backend/nirbhar/crossover/` and `src/solver/lp/crossover.ts` identify active bound sets ($B, N_L, N_U$) from non-basic continuous iterates (HPR/IPM), form candidate crash bases, and execute simplex polishing to achieve an exact vertex basic solution with zero duality gap.

## Parallel Tree Search & Concurrent Root Race

- **Parallel Branch-and-Cut**: `backend/nirbhar/mip/parallel_bb.py` implements a multi-worker thread pool with a thread-safe shared incumbent and priority queue. On standard CPython, worker threads are concurrent and subject to the Global Interpreter Lock (GIL).
- **Concurrent Root Race**: `backend/nirbhar/robust/controller.py` races Simplex, Mehrotra IPM, and JAX HPR concurrently across three threads; the first engine to prove a certified bound wins.

## Hybrid Architecture Bridge

- **Dual-Mode Operation**: The system operates both as a **standalone client-side Web Worker app** (runs in any browser without installation) and as a **connected industrial system** via `python -m nirbhar.serve 8000`. The web interface allows real-time switching between in-browser execution and native Python/JAX core execution.

## Independent Air-Gapped Verifier

- **Isolation Discipline**: The verifier (`nirbhar_verify/`) operates with 100% architectural independence, importing zero code from `nirbhar/`. It evaluates constraint residuals, dual feasibility, complementary slackness, and duality gap directly against the original MPS model file.
