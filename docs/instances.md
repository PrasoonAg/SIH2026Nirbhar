# Generated Instance Inventory

This file lists the synthetic and generated benchmark instances used by the showcase, together with their seeds, purpose, and expected behavior. All of the refinery-related and planning models are synthetic by design and carry the `SYNTHETIC — not MRPL data` label.

## 1. Core refinery instances

### refinery-lp
- Purpose: baseline LP demo for the guided refinery path
- Seed: deterministic generator based on the synthetic crude table in `src/data/reference/refinery.json`
- Size: about 100–150 variables and 60–90 rows
- Expected behavior: feasible, bounded, certified, verifier PASS in float mode; mass-balance residual near zero
- Notes: used for the LP race, certificate generation, and explanation panel

### refinery-milp
- Purpose: campaign/changeover MILP demonstration for B&C and cuts
- Seed: same crude data as oil refinery LP, with binaries for crude campaigns and changeover variables
- Size: small-to-medium MILP with binary setup and linkage constraints
- Expected behavior: root LP feasible, branch-and-cut closes gap, incumbent verified, and certificate status remains honest
- Notes: must show safe-bound pruning and a live tree with valid incumbent updates

### refinery-qp
- Purpose: convex quadratic refinement with price-risk term
- Seed: same synthetic refinery data; diagonal Q matrix with convex risk penalty
- Size: moderate LP/QP model
- Expected behavior: IPM and HPR-QP converge to the same optimum within tolerance; non-convex Q returns `UNSUPPORTED`
- Notes: closed-form separable Lagrangian lower bound should be displayed when available

### refinery-batch-scenarios
- Purpose: scenario batch comparison across sequential, worker-pool, and batched HPR modes
- Seed: deterministic perturbations on price, availability, and demand values
- Size: 50–1000 scenarios, adjustable via UI slider
- Expected behavior: all modes agree on objective within tolerance; speedup chart reflects real measured timings
- Notes: small-batch overhead should be visible; no fake speedup claims

## 2. Robustness and stress suite

### beale-cycling-lp
- Purpose: demonstrate cycling and recovery under naive simplex behavior
- Seed: deterministic Beale-style LP with textbook degeneracy and cycling tendency
- Expected behavior: naive mode fails or cycles; hardened mode recovers, escalates appropriately, and produces a valid solve
- Notes: deterministic and repeatable for robustness demo

### degenerate-assignment-lp
- Purpose: degenerate assignment/transportation case to stress simplex recovery
- Seed: generated transportation-style LP with repeated bases and near-singular pivots
- Expected behavior: hardened solver should remain stable; naive mode may stall or reject
- Notes: good for escalation and basis-hash diagnosis

### rescaled-refinery-lp
- Purpose: ill-conditioned case to check scaling robustness
- Seed: refinery LP with row/column scaling factors from 1e-6 to 1e6
- Expected behavior: optimum is unchanged; hardened mode remains valid; naive mode may fail or be rejected
- Notes: used in the robustness moment and reliability table

### lot-sizing-mip
- Purpose: weak-relaxation MILP used for cuts-on vs cuts-off demonstration
- Seed: deterministic multi-item production planning model
- Expected behavior: cut generation closes measurable root gap and reduces node count
- Notes: must show derivation records and verifier re-checks for each cut

### transportation-lp
- Purpose: scale-ladder generation for crossover sizing and dispatcher calibration
- Seed: generated transportation network model across 32×32, 100×100, 316×316, and 1000×1000 lanes
- Expected behavior: dense simplex/IPM may time out on larger models; the chart should display timeout markers honestly
- Notes: crossover chart remains a measured performance artifact, not a claim of production scale

### unit-commitment-mip and miqp
- Purpose: power dispatch and MIQP demonstration
- Seed: synthetic 4–6 units × 8–12 periods with min-up/down, ramping, reserve constraints, and quadratic dispatch cost
- Expected behavior: feasible MILP and MIQP solutions, with brute-force checks for small cases
- Notes: convex MIQP is allowed; non-convex variants are rejected as `UNSUPPORTED`

### facility-location-mip
- Purpose: supply-chain network design example
- Seed: synthetic facility-opening and shipment instance
- Expected behavior: MILP solved with honest status and certificate fields
- Notes: used in family-by-family summary table

## 3. Known-optimum generated models

### lp-known-optimum
- Purpose: generated LPs built backward from a primal-dual pair satisfying complementary slackness
- Seed: deterministic random problem generator
- Expected behavior: computed optimum matches the known optimum to tight tolerance
- Notes: used for benchmark and validation flows

### qp-known-optimum
- Purpose: generated convex QP built from a chosen KKT point
- Seed: deterministic generator
- Expected behavior: IPM and HPR-QP agree with the exact optimum within tolerance
- Notes: used for QP benchmarking and bound validation

## 4. External sample placeholders

The app lists Netlib and MIPLIB-style placeholders in `public/samples/manifest.json`. They are intentionally left as placeholders until the real `.mps` files are dropped into `public/samples/`.

Examples:
- afiro
- sc50a
- sc50b
- sc105
- kb2
- adlittle
- blend
- share2b
- stocfor1
- recipe
- p0033
- stein27
- egout
- lseu

Expected behavior when real files are supplied:
- parser counts and bounds match the manifest
- objective comparison is against the published reference value
- verifier returns PASS for valid solutions
- if files are missing, the manifest remains explicitly marked as `placeholder`

## 5. Reporting guidance

When a new synthetic instance is added, record:
- instance name
- seed or generation routine
- purpose in the app
- expected status or certificate outcome
- any known caveats or size limits

This keeps the project honest and makes it easier to track why a case is included in the showcase or robustness suite.
