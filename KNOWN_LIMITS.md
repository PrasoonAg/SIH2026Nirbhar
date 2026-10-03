# KNOWN_LIMITS.md — NIRBHAR Showcase Prototype

This file honestly lists what this prototype does **not** do, per the spec's requirement for transparent honesty labelling.

## Linear Algebra

- **Dense LU factorization**: The simplex basis is maintained with dense LU (using eta-file updates). Production NIRBHAR uses sparse Markowitz-ordered LU. Prototype limit: bases > ~300 rows may be slow.
- **Dense Cholesky for IPM**: The interior-point method uses dense Cholesky on the normal equations. Production uses sparse Cholesky with AMD ordering. Prototype limit: ~200–300 variables for IPM.

## GPU / Hardware

- **No GPU computation**: The HPR-family engine is a Halpern-anchored PDHG-type first-order operator running in CPU JavaScript (Web Worker). Production NIRBHAR targets JAX/GPU/TPU via Python+Numba+JAX. No GPU computations occur in this prototype.
- **No CUDA, no WebGPU**: This prototype does not use WebGPU. The GPU chip in the top bar correctly reads "none used (CPU-JS prototype)".

## Scale

- **Small-scale MILP only**: The branch-and-cut engine is correct and certified at small scale (≤ ~100 binaries in reasonable time). Production NIRBHAR targets large-scale MILP. The prototype does not claim million-variable performance.
- **Scenario batch**: The batched HPR engine handles tens to hundreds of scenarios. Thousand-scenario runs may be slow in the browser.

## HPR-Family Engine

- **Approximate HPR-LP operator**: The HPR-family engine implements a Halpern-anchored PDHG-type primal–dual operator. It is not a verified implementation of the published HPR-LP algorithm (which we cannot access offline). It is labelled "HPR-family" throughout, not "HPR-LP". No claim of exact equivalence with the published paper is made.

## Verifier

- **Float64 default**: The default verifier mode uses 64-bit floating-point arithmetic. Exact mode uses BigInt rational arithmetic, which is correct but significantly slower — it is only practical for small instances (< ~200 variables).

## Data

- **Netlib Models**: Canonical uncompressed Netlib `.mps` models (`afiro`, `sc50a`, `sc50b`, `sc105`, `kb2`, `adlittle`, `blend`, `share2b`, `stocfor1`, `recipe`) are bundled in `public/samples/` and active. Additional models can be dropped into `public/samples/` and listed in `manifest.json`.

## Other

- **No HiGHS WASM baseline by default** (P2 feature): The HiGHS WASM baseline column is shown only if the bundled module loads successfully. It is a Phase 7 optional feature.
- **No parallel tree search** (P1 feature): The deterministic parallel B&C (2–4 workers sharing a node pool) is a Phase 7 optional extension. The main B&C runs in a single worker.
- **No crossover engine** (P1 feature): Crossover from first-order solution to a basic solution is a Phase 4 optional extension. The crossover chart remains.
