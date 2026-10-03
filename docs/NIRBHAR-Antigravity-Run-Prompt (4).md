# NIRBHAR — Frontend Showcase Prototype: Antigravity Run Prompt

> **How to use:** Put Antigravity in Planning mode, paste everything below the line into the agent, and attach `NIRBHAR-Complete-Idea.md` plus your sample files (see §8). Make sure the browser agent is enabled so it can read https://roviq.xyz/ (see §3b). Ask it to stop for your review at the end of each phase in §11.

---

# ROLE

You are a senior full-stack engineer and numerical-optimization engineer. Build **NIRBHAR Showcase**, a browser-only prototype of NIRBHAR, an indigenous certified hybrid CPU–GPU optimization solver core (Smart India Hackathon 2026, PS SIH26119, Team Vernils, for MRPL). The attached `NIRBHAR-Complete-Idea.md` is the source of truth. Read all of it first. Section numbers (§) below refer to it.

The prototype will be screen-recorded for a 2-minute core demo plus optional extras chapters. It must look like a real engineering product, and **every result on screen must be genuinely computed in the browser**.

# 1. HARD CONSTRAINTS

1. **No backend.** Static site only (Vite build). No server, no API calls, no Python. Everything runs in the browser and must work offline after build (bundle all assets and fonts locally; no CDN at runtime).
2. **Real computation, no faked results.** Solvers are real JavaScript/TypeScript implementations running in Web Workers on real model data. Objectives, iteration counts, node counts, gaps, timings, cut counts, and verifier verdicts must come from actual execution. Never hardcode an outcome, timing, or a "naive fails" result. If a demo does not behave as intended, fix the instance or the algorithm, not the display.
3. **Honesty labelling (the idea doc's core rule, §3.4 rule 7 and §14 wording discipline):**
   - A persistent badge: `PROTOTYPE — engines run as CPU JavaScript in your browser. Production NIRBHAR: Python + Numba + JAX (CPU/GPU/TPU).`
   - The "GPU HPR" engine is labelled `HPR-family first-order engine (CPU-JS here; JAX/GPU in production)`. Never claim a GPU ran.
   - All refinery/unit-commitment/etc. models carry a `SYNTHETIC — not MRPL data` tag.
   - Any number not measured in this prototype (for example "≈1e6 variables on GPU") appears only in a clearly styled `PRODUCTION TARGET — not measured here` chip.
   - Never write "GPU-native". Say "certified hybrid CPU–GPU solver core" and "optimal or near-optimal, with a proven gap". Tagline: **"The solver that proves its answers."**
   - `OPTIMAL` is displayed only when the certified gap is within tolerance AND the independent verifier returns PASS. Otherwise show the honest weaker status from §7.
4. **Sovereignty inside the prototype:** `src/solver/**` and `src/verify/**` import NO third-party numeric/solver packages (no mathjs, no glpk.js, no highs, no javascript-lp-solver, no numeric.js). Only TypeScript stdlib and `Float64Array` etc. UI code may use React and chart libraries. Add `npm run check-imports` (a Node script) that scans `src/solver` and `src/verify` and fails on any forbidden import. The UI's Sovereignty panel shows its real output.
5. **Verifier isolation:** `src/verify/**` must not import anything from `src/solver/**`. It has its own minimal MPS reader and its own `LB(y)`, QP-bound and cut-derivation code, and always re-reads the **original MPS text**, never the presolved model. Enforce this in `check-imports` as well.
6. **No SharedArrayBuffer** (needs special headers). Pass data to workers by copy or transfer.
7. Keep every live demo under about 10 seconds on a mid-range laptop; long benchmarks must be cancellable and show progress and honest timeouts.

# 2. TECH STACK

- Vite + React 18 + TypeScript (strict), Tailwind CSS, Zustand (state), Recharts (charts), a hand-rolled SVG/d3-hierarchy tree view for branch-and-bound, Framer Motion (light use), Vitest (solver unit tests).
- Web Workers via Vite's `new Worker(new URL(...), { type: 'module' })`.
- BigInt for exact rational arithmetic (verifier exact mode).
- Optional (P2, see §11): the `highs` WASM package as a live baseline, bundled locally, loaded lazily, and shown only if it loads. It must never be imported by `src/solver` or `src/verify` (only from `src/bench`).

Repo layout (mirror §5.1 where it makes sense):

```
src/
  solver/
    io/        mps.ts  model.ts                 # fixed+free MPS, RANGES, bounds LO/UP/FX/FR/MI/PL/BV/LI/UI, OBJSENSE, MARKER INTORG/INTEND, QUADOBJ/QMATRIX
    linalg/    csr.ts lu.ts chol.ts ldl.ts refine.ts condest.ts
    presolve/  scaling.ts reductions.ts postsolve.ts
    lp/        dualSimplex.ts primalSimplex.ts basis.ts crossover.ts hpr.ts hprBatch.ts
    ipm/       mehrotra.ts
    qp/        hprQp.ts bounds.ts kelley.ts
    mip/       bb.ts propagate.ts branching.ts nodesel.ts heuristics.ts bounds.ts cuts/{gmi,cmir,cover,pool}.ts
    robust/    controller.ts switches.ts naiveMode.ts
    parallel/  pool.ts race.ts
    explain/   duals.ts ranging.ts iis.ts
    extend/    registry.ts                      # the 8 plug-in interfaces (§8)
    dispatch.ts
    certificate/ builder.ts explain.ts schema.ts
    workers/   engine.worker.ts  mip.worker.ts  batch.worker.ts  verify.worker.ts
    cli.ts api.ts
  verify/      verify.ts exact.ts cuts.ts mpsMin.ts        # NO imports from ../solver
  bench/       harness.ts knownOpt.ts stress.ts refs.ts highsBaseline.ts
  demo/        refinery.ts lotsizing.ts transport.ts unitCommit.ts supplyChain.ts
  data/        samples manifest + MPS text (see §8)
  ui/          shell, pages, components
  tests/
tools/check-imports.mjs
```

# 3. DESIGN DIRECTION (professional, sleek, light-first)

**Goal:** it must read as a serious engineering / enterprise tool built by a mature team, in the same family as Linear, Stripe Dashboard, Grafana (light) or a Bloomberg-lite analytics screen. It must **not** look like a typical "AI-generated" landing page. Working, legible and credible beats decorative.

**Themes**
- Ship **two full themes: Light and Dark. Light is the default and the priority**: design and polish it first, and record the video in Light. Dark is a soft charcoal, never near-black.
- Theme toggle (Light / Dark / System) in the top bar. First load is always Light regardless of the OS setting; remember the user's choice afterwards. Implement with CSS variables (design tokens) on `:root` and `[data-theme="dark"]`; no hard-coded colours in components. Charts, the tree view, the sparsity plot, code blocks and the terminal must all read tokens, so switching theme never leaves an unreadable element.

**Palette (tokens; adjust slightly if contrast fails, but keep the character)**

| Token | Light (default) | Dark |
|---|---|---|
| `--bg` (app background) | `#F5F6F8` | `#181B21` |
| `--surface` (cards, panels) | `#FFFFFF` | `#20242C` |
| `--surface-2` (table headers, wells) | `#EEF0F3` | `#282D37` |
| `--border` | `#DDE1E7` | `#333946` |
| `--text` | `#161A21` | `#E7E9ED` |
| `--text-muted` | `#5A6472` | `#9AA3B0` |
| `--primary` (ink navy, buttons, links, active nav) | `#1F3A5F` | `#8DB0DE` |
| `--accent` (saffron, used very sparingly: 2px top hairline, active-tab underline, key KPI marker) | `#D9730D` | `#F0A04B` |
| `--positive` | `#1A7F4B` | `#4CC38A` |
| `--warning` | `#B7791F` | `#E5B454` |
| `--negative` | `#B42318` | `#F47A70` |

- Avoid pure `#000` and pure `#FFF` for large areas. Neutrals are cool greys with a tiny blue tint. Contrast meets WCAG AA in both themes.
- **Status chips** (soft tinted background + solid text + 1px border, same recipe in both themes): `OPTIMAL` green, `OPTIMAL_WITHIN_GAP` teal, `CERTIFIED_APPROXIMATE` amber, `INFEASIBLE_CERTIFIED` / `UNBOUNDED_CERTIFIED` blue, `TIME_LIMIT` grey, `NUMERICAL_ISSUE` red, `UNSUPPORTED` violet, `LOCAL_ONLY` orange. Verifier verdict: a clear `PASS` / `FAIL` badge with an icon, not a giant glowing stamp.
- **Chart series** use a colour-blind-safe palette (Okabe-Ito style) defined as tokens per theme; each engine has a fixed colour everywhere (dual simplex, interior point, HPR-family, baseline). Never rely on colour alone: add line style or direct labels.

**Style rules**
- **Look:** flat, structured, information-dense but calm. 8px spacing grid, 6–8px corner radius, **1px borders instead of shadows** (at most one very subtle shadow for popovers and modals). Tables have thin row dividers, sticky headers and tabular figures. Use a real 12-column layout with consistent gutters.
- **Typography:** Inter (UI) and JetBrains Mono (numbers, logs, JSON, terminal), both bundled locally. Clear scale: page title 24, section 16–18, body 14, table 13, mono 12–13. Numbers right-aligned, fixed decimals, units shown. No decorative fonts.
- **Icons:** one consistent line-icon set (lucide-react). **No emojis anywhere in the UI.**
- **Banned "AI look" patterns:** no purple-to-blue or neon gradients, no gradient text, no glowing or blurred orbs, no glassmorphism or backdrop-blur cards, no glow shadows, no grid/particle/"matrix" backgrounds, no sparkle icons, no floating 3D blobs, no oversized rounded pill everything, no giant hero with stock-marketing copy. The Home page is a clean summary and launch page, not a landing page.
- **Copy tone:** plain, precise, engineering-grade. Short labels, no hype adjectives ("revolutionary", "blazing", "next-gen"). Explanations read like documentation.
- **Charts:** thin 1.5–2px lines, light gridlines, direct labels where possible, solid or hatched fills only (no gradient fills), timeouts drawn as explicit markers, axes always labelled with units. Same components in both themes via tokens.
- **Tree view and diagrams:** crisp SVG, 1px strokes, node colours from status tokens, generous whitespace, readable at 1080p when recorded.
- **Motion:** functional only (150–200 ms ease-out for panel/tab changes; live progress that reflects real solver activity, throttled to about 20–30 updates per second). No bouncing, parallax, or looping decorative animation. **Reduced-motion** toggle honoured.
- **Recording-friendly:** layout designed for 1920×1080, large readable type, no key information hidden in tiny tooltips. **Record Mode** toggle (enlarges KPIs, hides dev-only noise and scrollbars) works in both themes.
- **Persistent top bar:** NIRBHAR wordmark (Devanagari "निर्भर" beside it), prototype badge, Showcase Mode button, Record Mode toggle, theme toggle, hardware chip (`navigator.hardwareConcurrency` cores, "GPU: none used (CPU-JS prototype)"). A 2px saffron-to-green tricolour hairline may sit at the very top edge as the only India cue; no flag imagery or decorative patterns.
- **Design QA gate (Phase 0 and again in Phase 7):** screenshot the Home, Solve Studio, Branch-and-Cut Lab and Benchmarks pages in Light and in Dark at 1920×1080 and 1366×768, and fix contrast, overflow, clipping, and any element that ignores the theme before moving on.

# 3b. REFERENCE PROTOTYPE: USE ITS DATA, NOT ITS DESIGN

An earlier working prototype exists at **https://roviq.xyz/** (page title "Kavach-Opt — Sovereign Optimization Engine"). It is a JavaScript-rendered app, so use the Antigravity **browser agent** to open it, click through every page and tab, and extract its content.

**Take from it (data and content only):**
- Sample model names, sizes and parameters, refinery data (crude names, prices, availabilities, sulfur, yields, CDU capacities, product demands), scenario definitions, benchmark instance lists, feature and terminology lists, and any wording worth reusing.
- Save what you extract to `docs/reference-data.md` (human readable, with the source page for each item) and `src/data/reference/*.json` (machine readable). Where its refinery data is better than the generator defaults in F7, use it as the generator's seed data and keep the structure required by the spec.

**Do NOT take from it:** layout, colours, components, navigation structure, fonts, animations, or visual style. The design for this build is exactly section 3 above.

**Trust rules:**
1. Treat every *number the reference displays as a result* (objective, gap, timing, iteration count, "PASS") as **unverified**. Use its data as **inputs**, and let this app compute the results itself. If your computed result differs from what the reference shows, show your computed value and log the difference in `docs/reference-diff.md` (instance, reference value, our value, likely reason). Never copy a displayed result into the UI.
2. If any reference data looks hard-coded, inconsistent, or physically implausible (negative capacities, yields that do not sum to 1, etc.), flag it in `docs/reference-diff.md` and fix it in our copy with a note.
3. If the browser agent cannot load the site or cannot read a page, **stop and ask me to paste that data**. Do not guess or invent values.
4. All the honesty labels in section 1 still apply to reused data (`SYNTHETIC — not MRPL data`).


# 4. APP SHELL AND NAVIGATION

Left rail with these pages (routes):

1. **Home** — hero, one-liner, 30-second plain-language pitch (§2), the 8 "what is ours" cards (§11.1), a "Start 2-minute demo" button (Showcase Mode) and "Run self-test" button.
2. **Solve Studio** — the general solver front-end (F1–F6).
3. **Refinery Demo** — guided core path: LP → MILP → QP → Scenario batch (F7–F10).
4. **Branch-and-Cut Lab** (F11–F14)
5. **Robustness Lab** (F15–F16)
6. **Verifier** (F17–F18)
7. **Benchmarks** (F19–F22)
8. **Model Families** (F23)
9. **Architecture and Extend** (F24–F26)
10. **CLI and API** (F27)
11. **PS Compliance** (F28) — traceability, comparison, Judge Q&A, impact, references.

# 5. FEATURE SPECIFICATIONS

Priority tags: **P0** = must exist and be flawless for the video; **P1** = strongly wanted; **P2** = only if time remains. Each feature ends with an **Accept** line, used by the self-test page (§12).

## F1 — Model intake (Solve Studio) [P0]
- Model picker with grouped sources: *Netlib LP*, *MIPLIB-style MILP*, *QP / MIQP*, *Known-optimum generated*, *NIRBHAR families*, *Stress suite*, and **Import MPS/QPS** (drag-drop or file picker; parse locally).
- Model card after parse: name, class (LP | MILP | QP | MIQP), rows, cols, nnz, integer count, q_nnz, SHA-256 (Web Crypto) of the original text, bound-type histogram, coefficient dynamic range, a sparsity plot of A (canvas, downsampled), and a "reference optimum" if known.
- Parser errors show line number and reason.
- **Accept:** every bundled sample parses and its rows/cols/nnz equal the values in the manifest; a malformed MPS gives a line-numbered error.

## F2 — Engine configuration [P0]
- Engine selector: `Auto (dispatcher)`, `Dual simplex`, `Primal simplex`, `Interior point`, `HPR (first-order)`, `Concurrent root race`.
- Toggles: presolve on/off with per-reduction switches (§6.1 list); scaling on/off; `naive_mode` master switch; hardening switches (§6.11 table); verifier mode `float | exact`; time limit; tolerance (1e-4, 1e-6, 1e-8).
- **Accept:** `Auto` chooses per the dispatcher rules in §4.1 and shows its reasoning ("small LP → dual simplex", "root → race", "Q diagonal → IPM", "Q non-PSD → UNSUPPORTED").

## F3 — Live solve view [P0]
- **Engine lanes**: one lane per engine (dual simplex, interior point, HPR-family). Each lane runs in its **own Web Worker**, shows live iteration count, objective, primal/dual residual (unscaled), a mini-convergence sparkline, and state (running, WON, cancelled, escalated, failed).
- **Concurrent root race (§4.1 rule 2, §6.12):** all three run at once. The first that returns a result passing the safe-bound gap check wins; the others are terminated and their partial results discarded, never mixed. Show "winner", time-to-win, and the losers' status honestly (a lane can win on one model and lose on another).
- Streaming log with timestamps, presolve summary (rows/cols removed per reduction), engine events, and escalations.
- Pipeline strip mirroring §4: `parse → presolve → dispatch → engine(s) → crossover → (branch-and-cut) → postsolve → verify → certificate`, each stage lighting up with its real elapsed time (feeds `timing_s` in the certificate).
- **Accept:** race on 3 different LPs produces winners that can differ; the terminated engines' results do not appear in the answer; the objective matches the reference to 1e-6 relative.

## F4 — Result, certificate, explanation [P0]
- Result panel: status chip, primal objective, **safe lower bound**, absolute and relative gap, max row/bound/integrality violations, verifier PASS/FAIL, escalations count.
- **Certificate viewer:** collapsible JSON exactly following the §7 schema (all keys; use honest values, e.g. `hardware.gpu = "none (CPU-JS prototype)"`, `bound.arithmetic` `float64+margin` or `exact-rational`, `bound.evaluated_on = "original-model"`, `solve_path` listing the registered components that actually ran, real `escalations[]`). Buttons: **Download certificate.json**, **Download solution**, **Copy JSON**.
- **Plain-language explanation panel** (§6.14, §7): binding constraints, top shadow prices in sentences ("one more unit of CDU capacity is worth …"), reduced costs, how trustworthy the answer is, and a note whether duals come from a basis (exact) or an unpolished first-order solve (approximate).
- **Accept:** downloaded certificate re-validates against the schema in `certificate/schema.ts`; uploading it to the Verifier page (F17) round-trips.

## F5 — Presolve and postsolve visualiser [P1]
- Waterfall of each reduction (empty rows/cols, fixed vars, duplicates, singleton rows→bounds, forcing/redundant rows, activity-based tightening, dual fixing, doubleton aggregation, integer rounding, **big-M coefficient tightening**, probing) with counts, plus a "before/after" size card. Every reduction pushes a postsolve record; the pipeline proves postsolve by reporting `original-space feasibility` and `same objective`.
- **Ablation table** (F13 shares it): turn each reduction off and re-solve, showing effect on iterations/nodes/time.
- **Accept:** presolve → solve → postsolve yields a point feasible for the original model with the same objective within 1e-6 on all Netlib samples.

## F6 — Explainability [P0 for shadow prices and infeasibility, P1 for ranging]
- Shadow prices, reduced costs, cost and RHS **ranging** (from the optimal basis; verified by re-solving at range endpoints, show the check).
- **What-if slider** for two or three key parameters (e.g. Arab Light price, diesel demand) that re-solves via warm-started dual simplex and animates objective change.
- **Infeasibility explanation (§6.14):** for an infeasible model, extract a Farkas ray, then run a **deletion filter** to shrink to an irreducible conflicting set. Show it in plain language ("these 3 constraints cannot all hold: …") and send it to the verifier for re-checking. Status `INFEASIBLE_CERTIFIED`.
- **Accept:** the bundled over-constrained refinery plan returns `INFEASIBLE_CERTIFIED` with an irreducible set of exactly the rows the scenario was designed to conflict (design it so the computed core is 3 named rows: e.g. minimum diesel demand, CDU capacity, and an availability cap on the high-diesel crudes). The core must be **computed**, not printed. Removing any one of the three makes the LP feasible (show that check).

## F7 — Refinery LP [P0] (core path step 1)
Synthetic multi-period crude purchase and blending, seeded generator in `demo/refinery.ts`:
- 10 crude types (use the crude names and figures extracted from the reference prototype, see section 3b, when available and consistent) with price, availability cap per period, sulfur %, and a yield vector over 6 products (LPG, naphtha, gasoline, ATF, diesel, fuel oil).
- 4 periods; CDU capacity per period; per-product demand ranges (min/max sales); product inventory balances across periods with tank limits; linear sulfur limit on the blended feed (state that volume-weighted linear blending is a simplification).
- About 100–150 variables and 60–90 rows. Show the formulation summary in a side drawer (variables, constraint families).
- KPIs on screen (§10): certified gap, verifier PASS/FAIL, **mass-balance residual reported by the verifier**, escalations used, plain-language explanation.
- **Accept:** solves via race, certified, verifier PASS in float and exact modes, mass-balance residual ≤ 1e-9 shown.

## F8 — Refinery MILP: campaigns and changeovers [P0] (core path step 2)
- Add binaries: crude-in-campaign `z[c,t]`, changeover `y[c,t] ≥ z[c,t] − z[c,t−1]` with a changeover cost, big-M linking `p[c,t] ≤ M·z[c,t]`, minimum run length (`p[c,t] ≥ minrun·z[c,t]`), and at most K distinct crudes per period.
- Runs the certified branch-and-cut (F11), showing tree, bound, incumbent, gap, cuts.
- **Accept:** returns `OPTIMAL` (or `OPTIMAL_WITHIN_GAP` honestly if the node limit hits) with verifier PASS; the objective is ≥ the LP relaxation objective; every incumbent is re-verified before display.

## F9 — Refinery QP: price-risk term [P0] (core path step 3)
- Diagonal convex `½ Σ q_c p_c²` price-risk cost on top of the LP.
- Engines: interior point (Mehrotra, normal equations) and HPR-QP-family engine; dispatcher rationale shown (small QP → second-order IPM, as §3.1 says honestly).
- Certified with the **closed-form separable Lagrangian bound** (§6.7) `LBq(y)`; show the formula rendered, the value, and the gap.
- **Non-convex refusal moment:** a button "Make Q indefinite" flips one `q_c` negative; the solver runs its PSD check (Cholesky attempt) and returns `UNSUPPORTED` with the reason "Q is not positive semidefinite (q_c < 0)". It must never solve it as if convex.
- **Kelley fallback (P1):** toggle to solve via epigraph variables + tangent rows with warm-started dual simplex, showing added tangents and the valid LP bound rising.
- **Accept:** IPM and HPR-QP objectives agree within tolerance; bound ≤ primal; non-convex Q returns `UNSUPPORTED`.

## F10 — Scenario batch [P0] (core path step 4)
- Generate N scenarios (slider 50–1000; default 200) of the refinery model with perturbed prices/availability/demand (same structure).
- Three execution modes, run sequentially so timings are comparable, and all **genuinely executed**:
  1. **Sequential warm-started dual simplex** (main thread or one worker).
  2. **Worker pool** of warm-started dual simplex (pool size slider 1…`hardwareConcurrency`).
  3. **Batched HPR-family** (state arrays of shape (n, B); sparse×dense products; per-column restart/step state; converged columns masked out; §6.5 "Batched HPR").
- Outputs: total time per mode, speedup vs sequential, **break-even batch size** (computed from a small sweep of batch sizes, plotted), results equality check (objectives from all modes must agree to 1e-6; mismatches flagged loudly), distribution histogram of scenario objectives, and worst-case scenario drill-down.
- Show sub-linear scaling and small-batch overhead honestly (§6.12); a **core-scaling chart** (time vs workers) is drawn from real measurements.
- **Accept:** all three modes produce matching objectives; a measured speedup chart is drawn; if batching loses at small sizes, the chart shows it.

## F11 — Certified branch-and-cut engine and live tree [P0]
Implement §6.8 exactly:
- Root LP by race → **safe bound**; root cut loop (GMI, c-MIR, extended cover) with warm-started dual simplex re-solves; root heuristics; open-node pool; node selection; activity-based propagation with safe rounding; **reduced-cost fixing certified via the term-wise split of `LB(y)`**; node LP by dual simplex warm-started from the parent basis; infeasible nodes verified by a Farkas ray (else kept open and flagged `unverified infeasibility`); prune **only** when the node's safe bound ≥ UB − tol; integer-feasible nodes update the incumbent (re-verified); reliability branching with strong-branching candidates; periodic diving/RINS; global bound = min over open nodes' safe bounds; gap formula from §6.8.
- **Live tree view:** nodes drawn as they are created. Colours: open, processing, **pruned by safe bound**, **infeasible (Farkas verified)**, **integer-feasible / incumbent**, **kept open due to weak bound**, **fixed by reduced cost** (badge). Click a node to see its bound, depth, branching var, LP iterations, and warm-start iteration savings vs a cold solve (measured on demand).
- Right side: live line chart of incumbent (UB), global lower bound, and gap %; counters mirroring the certificate's `mip` block (nodes, open, pruned_by_safe_bound, infeasible_with_farkas, kept_open_due_to_weak_bound, fixed_by_reduced_cost, incumbent_updates).
- **Accept:** on all bundled small MILPs (≤ 15 binaries) the objective equals brute-force enumeration (button "Brute-force check", F14). No node is ever pruned without a recorded safe bound.

## F12 — Node selection, branching, heuristics selectors [P0 for selectors, P1 for extras]
- Dropdowns: node selection `best-bound | best-estimate + plunging | depth-first`; branching `most-fractional | pseudocost | strong | reliability`; heuristic toggles `rounding | diving (fractional/guided/coefficient) | feasibility pump | RINS`.
- Comparison runner: same instance under different rules; table of nodes, time, **time-to-first-incumbent** (§9.3), and a bar chart "node count vs best-bound".
- **Accept:** on lot-sizing and a MIPLIB-style sample, reliability branching uses fewer nodes than most-fractional; time-to-first-incumbent is reported for each heuristic combination.

## F13 — Cuts: off vs on ("Cut moment", §10) [P0]
- Capacitated multi-item lot-sizing MILP (`demo/lotsizing.ts`, e.g. 3 items × 8 periods, big-M setups: a classic weak relaxation).
- One-click **Cuts OFF vs ON** side by side: root gap closed %, node count collapse, time. Chart: **root-gap-closure per cut family** (GMI, c-MIR, cover) and rejected cuts count.
- **Cut inspector:** list each cut with type, efficacy, its **derivation record** (multipliers λ, chosen bounds, complementation flags, δ; cover set for cover cuts) and a live "Verifier re-derived in exact arithmetic ✓" status. Cuts must be generated with safe aggregation and directed rounding (§6.9), so validity holds regardless of float error.
- **"No optimum cut off" property test button:** runs random small MILPs with brute-force optima and confirms no known optimum violates any generated cut; shows counts.
- **Accept:** cuts ON closes a measurable share of the root gap and reduces nodes; every cut's derivation re-checks in `verify/cuts.ts`; the property test reports 0 violations.

## F14 — Brute-force cross-check for MILP and MIQP [P0]
- Button on every small MILP/MIQP (≤ 15 binaries; for MIQP small unit-commitment): enumerate all binary assignments, solve the remaining LP/QP for each, compare with the B&B result and show a MATCH/MISMATCH chip. For MIQP also compare the **two independent paths** from §6.10 (Kelley outer-approximation nodes vs interior-point nodes).
- **Accept:** MATCH on all bundled small instances.

## F15 — Robustness moment: naive vs hardened [P0] (§6.11, §10 "Robustness moment")
- **Escalation chain viewer:** a timeline of real escalation events (symptom → detection → response → iteration), in the §6.11 table order: stall → perturb → steepest-edge/Devex → Bland; singular basis → refactorize tighter → slack swap → rescale; inaccurate solves → refinement; simplex failing → interior point → crossover; IPM failing → regularization → simplex/HPR; node LP failure → alternate engine → keep node open with the parent's safe bound; final `CERTIFIED_APPROXIMATE` or `NUMERICAL_ISSUE`.
- **Hardening switch panel** (per-engine, §6.11 table) and the **`naive_mode`** master switch (textbook: no scaling, exact costs, textbook ratio test, largest-infeasibility/Dantzig pricing, refactor only when forced, no recovery; IPM: no scaling/regularization/fixed step; B&C: most-fractional, no presolve/cuts/heuristics).
- **Side-by-side runner:** same instance in `naive_mode` vs `hardened`, in two workers simultaneously. Naive lane shows stalls/cycling detection (basis-hash repeat), iteration cap or a **verifier-rejected answer** (a "solve" the verifier rejects counts as failure, §6.11 stress protocol rule 2). Hardened lane shows the escalation log and ends `OPTIMAL` + verifier PASS.
- **Which instances:** (a) a **Beale-style cycling LP** (classic 4-constraint example that cycles under Dantzig pricing with textbook tie-breaking) proving cycling is detected and cured; (b) a degenerate assignment/transportation LP generated at n≈40–60; (c) the refinery LP **rescaled** with row/column factors from 1e-6 to 1e6 (optimum unchanged, so the reference objective is known exactly; tolerances relative to row/col norms). If the naive path does not fail naturally on an instance, pick a harder scaling or size by the written rule below. Never fake a failure.
- **Selection rule (write it in the UI):** "Stress instances were chosen by a stated rule before results were viewed: S1 degenerate = generated + Beale; S2 ill-conditioned = rescaled copies with factors ∈ [1e-6,1e6]; S3 weak relaxation = big-M fixed-charge/lot-sizing; S4 numerically hard = wide coefficient range MILP."
- **Accept:** naive fails or is rejected on at least the Beale case and the rescaled case in a deterministic, repeatable way (seeded); hardened solves and verifier-PASSes; per-mechanism ablation table ("one mechanism off at a time") is produced from real runs, listing **residual hardened failures** too (if none, say "none observed on this suite" — do not fabricate one).

## F16 — Stress suite table [P1]
- Table over S1–S4: instance, mode (hardened / naive / one-mechanism-off), status, iterations, time, unscaled residuals, escalations, verifier result. Run-all button with cancellation; results feed the Reliability table (F21).

## F17 — Independent verifier [P0]
- Separate panel that takes (a) the original MPS text and (b) a solution/certificate JSON and returns PASS/FAIL with a checklist: bound and row violations (absolute and relative), integrality, recomputed objective, recomputed `LB(y)` and gap, Farkas/unboundedness rays, re-derived cuts, reduced-cost fixings. Runs in its own worker using only `src/verify/**`.
- **Exact mode:** BigInt rational arithmetic (every float → exact rational, exact dot products). Show the exact objective and exact bound as fractions plus decimals, and the time cost of exact mode. Also implement the **exact basis proof** for small LPs (solve `B x_B = b` and `Bᵀ y = c_B` in rationals, confirm primal+dual feasibility → proven optimal).
- The verifier UI shows that it received the **original model text**, with its SHA-256 compared to the certificate's.
- **Accept:** PASS on every honest solve; exact mode agrees with float mode within the stated margin.

## F18 — Adversarial suite [P0] ("proof, not just a checker", §6.13, §11.2)
- Buttons that corrupt a correct result and re-run the verifier: **violate a row**, **flip an integer**, **alter the objective**, **supply a random y** (must give a weaker *valid* bound or FAIL, never a stronger invalid one), **corrupt a cut multiplier**, **forge an infeasibility ray**, **tamper with the model hash**.
- Result grid: each corruption → verifier FAIL/weaker-bound, with the exact failing check highlighted. "Run all corruptions" prints an **adversarial rejection rate** (target 100%).
- **Accept:** every corruption is rejected or downgraded; a 7-row results grid renders and is screenshot-friendly.

## F19 — Netlib benchmark [P0]
- Table for the bundled Netlib samples (see §8), split **tune set** vs **report set** (§9.1 split), columns: name, rows×cols×nnz, reference optimum (published), our objective per engine (dual simplex, IPM, HPR-family), relative error, iterations, time, winner of the race, certificate status, verifier result. A run-all button with progress and a per-row "open in Solve Studio". Mismatches in red, by name.
- Optional live baseline column **HiGHS-WASM** (P2): shown only if the bundled module loads; otherwise the column reads "baseline not loaded". Never invent baseline numbers. Also show **published-reference match** as the always-available comparison.
- Show shifted geometric mean of times (SGM10, §9.3) and median/worst ratio to the baseline when available.
- **Accept:** on every bundled Netlib LP all three engines match the published optimum to 1e-6 relative (else the row is red and named).

## F20 — MILP, QP, MIQP tables [P0 for MILP, P1 for QP/MIQP]
- **MIPLIB-style subset** table (§9.1): instance, size, reference optimum, ours, nodes, time, root gap closed by cuts, time to first incumbent, status, verifier, brute-force MATCH where applicable. Loss column: "instances where the reference/baseline would be faster" is reported honestly when a baseline exists.
- **QP table:** known-optimum generated QPs (built backwards from a chosen KKT point) at several sizes, diagonal and general sparse Q; IPM vs HPR-QP-family; the small-QP result honestly shows IPM winning (§3.1).
- **MIQP table:** generated unit-commitment MIQPs and brute-force-checked small ones; Kelley-OA path vs IPM-node path agreement.

## F21 — Charts: crossover, scale ladder, reliability, speed ratio [P0 for crossover and reliability; P1 for others]
- **Crossover-size chart:** solve time vs nonzeros for dual simplex, interior point, HPR-family (and HiGHS-WASM if loaded), points where each wins marked. Real timed runs over a **scale ladder** of generated transportation LPs (§9.1: 32×32 → 100×100 → 316×316 → 1000×1000 lanes; nnz = 2× variables). Each run has a time limit; **timeouts are drawn as timeouts**, not omitted. The dense simplex/IPM will time out early in the browser, and that is fine and must be shown. Run in workers with a Cancel button.
- **Dispatcher calibration:** after a crossover run, compute size thresholds from the measured data, store them (localStorage for convenience only), and let the dispatcher use them; F2's `Auto` reasoning displays "threshold set from your measured crossover at N nnz". This mirrors §4.1 rule 8.
- **Reliability table (§9.3):** per instance set: solved/total, count of each certificate status, escalations used, **every failure listed by name**.
- **Speed-ratio card:** median and worst ratio vs baseline (only if a baseline was run).
- **`PRODUCTION TARGET` chips** for anything not measured (e.g. "≈1e6 vars LP on GPU + IPM").

## F22 — Known-optimum generators [P1]
- LP generator (backwards from a primal–dual pair satisfying complementary slackness) and QP generator (from a chosen KKT point) with size sliders. Solve and show **exact known-optimum vs computed** (relative error), reproducing §9.1's open benchmark pack idea. Button "Download instance as MPS/QPS".

## F23 — Model families [P0 for the summary grid, P1 for each family's detail]
Five families, each synthetic, each with a generator, a "Solve" button and a **one-line result**: status, gap, verifier result (§10):
1. Refinery (F7–F10).
2. **Production planning:** capacitated multi-item lot-sizing MILP (F13).
3. **Transportation/logistics:** transportation LP + fixed-charge MILP (lane-opening binaries); same generator feeds the scale ladder.
4. **Power dispatch:** unit-commitment MILP (on/off binaries, min up/down, ramping, reserve) + **convex MIQP** variant with quadratic generator cost + economic-dispatch QP. 4–6 units × 8–12 periods.
5. **Supply-chain network design:** facility-location MILP (facility binaries, flows).
- **"Solve all five"** button fills the family table (claim C9): status, gap, verifier, time. Each row expandable to the full certificate.

## F24 — Architecture explorer [P1]
- Interactive rendering of the §4 architecture diagram (SVG). After any solve, **highlight the actual path taken** (from `solve_path`) and the engines that raced. Click a node to open its module spec (§5.2 table: function, key design decisions, acceptance test).
- Dispatcher rules 1–8 (§4.1) as a live table with the rule that fired highlighted.

## F25 — Plug-in registry and Extend demo [P0 for the working demo]
- Show the 8 interfaces (§8): `Engine`, `Presolver`, `Propagator`, `BranchingRule`, `NodeSelector`, `Heuristic`, `CutGenerator`, `ModelClass` with their contracts and the components NIRBHAR itself registers through the same registry.
- **Worked extension (the "evidence that it is real" from §8):** an in-app code editor pre-filled with a **second branching rule** (e.g. "lowest-index fractional" or "pseudocost-lite") written against `BranchingRule`. Button "Register" (evaluate with `new Function` in a sandboxed worker) adds it to the F12 dropdown **without touching `bb.ts`**; then solve, and the certificate's `solve_path` lists the plug-in by name.
- **ModelClass demo (P1):** convex NLP example (e.g. minimise `x² + y²` s.t. linear constraints or a convex exp cost) solved by tangent relaxations (Kelley), and a non-convex example (bilinear pooling-style term) that returns **`LOCAL_ONLY`, never `OPTIMAL`**, with the reason.
- **Accept:** registering the custom rule changes the branching decisions (visible in node log) and the certificate names it.

## F26 — Sovereignty panel [P0]
- Renders the real output of `npm run check-imports` (generated at build time into a JSON that the page reads), listing scanned files, allowed imports, forbidden patterns, verifier isolation result, and the dependency list (with what each is used for: React = UI only, etc.). Copy explaining the sovereignty rule of §5.1.

## F27 — CLI and API [P0]
- **In-browser terminal** (xterm-style, custom component is fine) implementing: `nirbhar solve <model> [--engine auto|dual|primal|ipm|hpr|race] [--presolve on|off] [--naive] [--cuts on|off] [--verify float|exact] [--tol 1e-6] [--out cert.json]`, `nirbhar verify <cert.json> <model>`, `nirbhar bench netlib|miplib|qp|stress`, `nirbhar models` (list bundled), `nirbhar explain`, `nirbhar --help`. Output is the real solver's output. Tab-completion for model names; command history.
- Second tab: **Python API view** showing a small realistic snippet (`nirbhar.load("afiro.mps")`, `nirbhar.solve(...)`, `nirbhar.verify(...)`) as read-only code (production API; clearly labelled), next to the equivalent **TypeScript API** which really runs from a "Run" button.
- **Accept:** `nirbhar solve afiro --engine race --verify exact` prints a real result with a certificate and PASS.

## F28 — PS Compliance page [P0]
- **Traceability matrix:** all 31 rows of §1.1 (requirement → NIRBHAR answer → evidence). Each row has a status ("Live in prototype", "Runs in prototype at small scale", "Design only — production target") and a **Run proof** button that deep-links to the page/feature and auto-starts the relevant demo. Rows 17, 18, 24 must not claim GPU or million-variable results; they state what is measured here and label the rest `PRODUCTION TARGET`. Rows 7 (NLP/MINLP) link to F25's ModelClass demo.
- **Capability comparison table** (§11.3) with the footnote "Table entries about other solvers reflect public documentation at time of writing; re-check before presenting."
- **Judge Q&A** accordion (§16), verbatim answers, with "Show me" buttons that jump to the proving demo where possible.
- **Impact and benefits** (§13), **Claims we will not make** (§9.4), **References R1–R43** (§15) filterable by tag.
- **Accept:** each "Run proof" link opens and triggers a working demo; no row claims a capability the prototype does not show without a label.

# 6. SOLVER ENGINE SPECIFICATIONS (WHAT MUST REALLY RUN)

Implement in TypeScript with typed arrays; hot loops written allocation-free. Small-scale correctness first, speed second. Dense linear algebra is acceptable inside the prototype for bases up to a few hundred rows (state that in the UI: "dense LU in prototype; sparse Markowitz LU in production"), but keep A stored as CSR/CSC and use sparse products where cheap.

1. **Model & parser (`io`)**: immutable `Model` (c, A in CSR+CSC, row lo/hi, col lo/hi, integrality, optional Q, names, objective sense, constant). Free and fixed MPS. RANGES rules per the MPS spec (for E rows the sign of R decides), bound types LO/UP/FX/FR/MI/PL/BV/LI/UI, negative UP with zero lower bound handled per convention, integer markers.
2. **Scaling & presolve (`presolve`)**: geometric-mean scaling then Ruiz for simplex/IPM; Ruiz (≈10 iterations) for HPR. Every reduction has an on/off switch and a postsolve record; all stopping tests are evaluated in the **original unscaled space**.
3. **Bounded dual simplex (`lp/dualSimplex`)**: warm-startable `solve(model, basis?, boundOverrides?, addedRows?)` returning status, x, y, z, basis or a Farkas/unbounded ray; LU with product-form eta updates and refactorization triggered by eta length, growth estimate or residual check; dual steepest-edge with Devex fallback; Harris two-pass ratio test with **bound flipping**; cost perturbation with primal-simplex cleanup; basis-hash cycle detection; Bland's rule as last resort; singular-basis recovery by slack swap; Hager 1-norm condition estimate per refactorization.
4. **Primal simplex** for cleanup and as an escalation alternative.
5. **Mehrotra predictor–corrector IPM (`ipm`)** for LP and convex QP (Q = 0 is the LP case): normal equations with dense Cholesky (or LDLᵀ for general Q on the regularized augmented system), primal–dual proximal regularization, adaptive step length, divergence tests producing candidate Farkas/improving rays (accepted only if the safe check confirms).
6. **HPR-family first-order engine (`lp/hpr`, `qp/hprQp`, `lp/hprBatch`)**: Halpern-anchored primal–dual iteration with restarts, per-iteration cost = one product with A and one with Aᵀ (keep an explicit CSR of Aᵀ), projections onto bounds, residual check every fixed number of iterations, stopping on relative KKT residuals in unscaled space. **You cannot read the HPR-LP paper offline; implement a well-known Halpern-anchored PDHG-type operator and label it "HPR-family" in the UI, without claiming exact equivalence with the published HPR-LP.** HPR-QP-family for diagonal Q via the same machinery. Batched variant with state shape (n, B), per-column restart/step state, masking of converged columns.
7. **Safe bounds (`bounds.ts`, and independently again in `verify/`)**: `LB(y)` exactly as in §6.7 for **any** y, with the zero-coefficient-times-infinite-bound convention and float64 evaluation with a conservative error allowance proportional to the sum of absolute term magnitudes; exact rational mode via BigInt; closed-form separable QP Lagrangian bound; tangent bound for general convex Q; Farkas check (`c = 0`, `LB(y) > 0`); bound on the cut-augmented model.
8. **Crossover (`lp/crossover`) [P1]:** classify by distance to bounds/complementarity, complete to a basis, let dual simplex finish, remove shifts with primal simplex. Report `CERTIFIED_APPROXIMATE` vs `basic optimal`, and measure time(engine + polish) vs cold simplex.
9. **Certified B&C (`mip`)** per F11, cuts per F13 (GMI via safe aggregation + MIR with directed rounding; c-MIR with a small δ search and greedy aggregation; extended cover on knapsack rows), cut pool with efficacy/parallelism/density filters and aging.
10. **Robustness controller (`robust`)**: per-engine health monitors, the §6.11 escalation table, every escalation written to the certificate's `escalations[]`, and `naive_mode` as a fair textbook implementation (not sabotaged).
11. **Race and pool (`parallel`)**: one worker per engine with cancellation by `terminate()`; worker pool for batches and strong-branching candidates; deterministic mode (fixed per-worker node budget per round, merge in fixed order) for the parallel tree search, **P1**: 2–4 workers each own a node queue and share incumbent/global bound via message passing at sync points; results must equal the sequential optimal value.
12. **Dispatcher (`dispatch.ts`)**: rules 1–8 of §4.1, with thresholds read from the calibration store when present. Returns the chosen engine(s) plus a human-readable reason.
13. **Certificate builder**: fills every field in the §7 schema from real run data; `OPTIMAL` only if gap ≤ tol AND verifier PASS.

# 7. UNIT TESTS (Vitest, must pass before you say a phase is done)

- MPS parser: counts/bounds/ranges on each bundled sample.
- LU/Cholesky: residual tests on random and Netlib-derived bases.
- Each LP engine reaches the published optimum on afiro, sc50a and kb2 to 1e-6 relative.
- Safe bound property test: for hundreds of random y, `LB(y) ≤` true optimum on LP, separable QP and general QP.
- Brute-force parity on 50 random small MILPs (≤ 12 binaries) and 20 small MIQPs.
- Cut validity: no known optimum violates any generated cut on the random MILP set.
- Adversarial: all seven corruptions FAIL or downgrade.
- Postsolve: presolve → solve → postsolve feasible in original space with equal objective.
- Non-convex Q returns `UNSUPPORTED`.
- Worker race: winner result equals the sequential result.

# 8. DATA: SAMPLE MODELS ("Netlib" and friends)

Put files in `public/samples/` with a `manifest.json` (name, path, class, rows, cols, nnz, integers, reference objective, source, split: tune|report|stress). The app loads whatever the manifest lists, so I can add real files without code changes. **Do NOT type Netlib matrices from memory.** The real, **uncompressed** MPS files are in `nirbhar-sample-pack.zip` (63 models plus `manifest.json` with measured reference optima); the maintainer (me) will copy the relevant ones into `public/samples/`, and the manifest values there **replace** the table below wherever they differ. Netlib originals are compressed (`emps`); I will supply decompressed `.mps`. Until then, build and test with these stand-ins and write the manifest for both:

**A. Real Netlib LPs (reference optima are from the Netlib readme; the app must compute its own answer and compare to this value; I will double-check the values against the files):**

| name | approx. size | published optimum (min) | split |
|---|---|---|---|
| afiro | 27×32 | −464.7531428571 | tune |
| sc50a | 50×48 | −64.57507705856 | tune |
| sc50b | 50×48 | −70.00000000 | tune |
| sc105 | 105×103 | −52.20206121171 | tune |
| kb2 | 43×41 | −1749.900129 | tune |
| adlittle | 56×97 | 225494.9631623 | report |
| blend | 74×83 | −30.81214985 | report |
| share2b | 96×79 | −415.7322407 | report |
| stocfor1 | 117×111 | −41131.97622 | report |
| recipe | 91×180 | −266.616 | report |

**B. MIPLIB-style small MILPs (I will supply real files; reference optima below must be re-checked against the files):** p0033 (3089), stein27 (18), flugpl (1201500), egout (568.1007), bell5 (8966406.49), lseu (1120), gt2 (21166). Until the files arrive, use generated stand-ins (knapsack, set-cover, fixed-charge) with a brute-force optimum.

**C. Built-in generated models (no files needed, all seeded and reproducible):** the refinery LP/MILP/QP/infeasible/scenario generator, lot-sizing, transportation (+fixed charge), unit-commitment (MILP, MIQP, ED-QP), facility location, known-optimum LP/QP generators, the Beale cycling LP, degenerate assignment LP, and the rescaled-refinery ill-conditioned LP (factors 1e-6…1e6). Provide "Export as MPS/QPS" for each so I can test them in other solvers.

**D. Also include** a tiny hand-derived 2-variable LP (§12.2 step 1) with an animated feasible-region plot showing dual simplex, IPM and HPR iterates converging to the known vertex, so the video can start with intuition.

# 9. SHOWCASE MODE (for the video)

A guided runner with an on-screen chapter bar, next/previous by keyboard (→ / ←), and per-scene "Auto-run" that triggers the real demo and pauses when done. Two chapters:

**Core path (about 2 minutes, §10):**
1. 0:00 Hero: "The solver that proves its answers." plus 30-second plain-language pitch.
2. Refinery LP: race lanes → winner → certificate → verifier PASS → plain-language explanation and mass-balance residual.
3. Refinery MILP: live tree, cuts, safe-bound prunes, gap converging, brute-force MATCH.
4. Refinery QP: IPM vs HPR-family, closed-form bound, then "Make Q indefinite" → `UNSUPPORTED`.
5. Scenario batch: sequential vs pool vs batched, speedup chart with honest break-even.

**Extras (each self-contained, so I can cut videos freely):**
6. Robustness moment (about 30 s): naive vs hardened on the rescaled/Beale instance with the escalation log.
7. Cut moment: lot-sizing cuts off vs on, derivations re-checked.
8. Infeasibility moment: over-constrained plan → `INFEASIBLE_CERTIFIED` with the 3 conflicting constraints.
9. Adversarial moment: corrupt → verifier FAIL grid.
10. Netlib table + crossover chart (with timeouts shown).
11. Plug-in extension moment and CLI moment.
12. PS compliance matrix and close.

Persistent KPI strip during core path scenes: **certified gap · verifier PASS/FAIL · mass-balance residual · escalations used · status**.

# 10. UX DETAILS THAT MATTER

- Every long action has a progress state, a Cancel button, and a friendly error state.
- Numbers use tabular figures; large values use engineering notation; gaps show both % and absolute.
- All copy avoids overclaiming: use "certified", "proven gap", "verified", never "GPU-native", never "beats Gurobi/CPLEX/Xpress" (§9.4 "Claims we will not make"). Show that list in F28.
- Keyboard shortcuts: `R` run, `Esc` cancel, `M` toggle record mode, `?` shortcut help.
- Accessibility: contrasts meet AA in both themes, focus rings visible, motion can be reduced, theme choice persists.

# 11. BUILD ORDER AND CHECKPOINTS

Stop after each phase, run `npm run build`, `npm test` and `npm run check-imports`, and summarise what works and what does not. Do not start the next phase until the current one's Accept items pass.

- **Phase 0:** scaffold (Vite/React/TS/Tailwind), design tokens with Light (default) and Dark themes, shell, routing, badges, check-imports script, sample manifest loader, Record Mode, and the reference-data extraction from roviq.xyz (section 3b) into `docs/reference-data.md` and `src/data/reference/`. Run the design QA gate before Phase 1.
- **Phase 1 (P0 engine core):** MPS parser, `Model`, dense LU/Cholesky, bounded dual simplex + primal cleanup, `LB(y)` safe bound, verifier package (float mode), certificate builder. Solve Studio (F1–F4) with the dual-simplex lane only. Netlib afiro/sc50a/kb2 pass.
- **Phase 2:** IPM (LP+QP), HPR-family, workers + concurrent race (F3 full), presolve/postsolve (F5), explainability incl. infeasibility core (F6), Netlib table (F19).
- **Phase 3:** certified B&C + tree UI, cuts, heuristics, branching/selectors, brute-force check (F11–F14), refinery MILP (F8), lot-sizing.
- **Phase 4:** QP/MIQP paths (F9, F20), scenario batch + pool + batched HPR (F10), crossover chart and dispatcher calibration (F21).
- **Phase 5:** robustness lab and stress suite (F15–F16), adversarial suite and exact verifier (F17–F18).
- **Phase 6:** families grid (F23), architecture explorer, plug-in registry demo, sovereignty panel, CLI and API (F24–F27).
- **Phase 7:** PS Compliance page, Showcase Mode, self-test page, polish, README with how to record the video and how to add real MPS files.

If time or complexity forces cuts, drop in this order: HiGHS-WASM baseline, parallel tree search, crossover engine (F21 crossover *chart* stays), Kelley toggle, ranging, ModelClass NLP demo, extended cover. **Never drop:** the verifier, the safe bound, the adversarial grid, the race, the refinery LP/MILP/QP/batch path, cuts on/off, naive vs hardened, the Netlib table, and the PS matrix.

# 12. SELF-TEST PAGE (`/selftest`)

A page that runs the Accept items above (parse counts; Netlib objective match; race winner equals sequential; safe-bound property test; brute-force parity; cut-validity property test; adversarial rejection; non-convex refusal; postsolve feasibility; IIS minimality check; scenario-mode agreement; check-imports result) and prints a green/red checklist with timings. I will run this before recording. Any red item must show the failing instance by name.

# 13. THINGS NOT TO DO

- No fake progress bars, canned logs, canned charts, hardcoded objective values, or hardcoded "naive fails" outcomes.
- No third-party solver/matrix library in `src/solver` or `src/verify`, and no imports from solver into verify.
- No claims of GPU use, of results at 1e6 variables, or of speed parity with commercial solvers.
- No backend, no network calls at runtime, no external CDN assets.
- Don't present an approximate answer as exact; label first-order answers `CERTIFIED_APPROXIMATE` unless polished to a basis.
- Don't silently change instance data to make a demo pass; if a demo needs tuning, record the change and the reason in `docs/instances.md`.

# 14. DELIVERABLES

Working Vite project; `README.md` (run/build/test, how to add real MPS files to `public/samples/`, how to record the video, Showcase Mode keys); `docs/instances.md` (every generated instance, seed, purpose, expected behaviour); passing `npm test`, `npm run check-imports`, and `/selftest`; a short `KNOWN_LIMITS.md` listing honestly what the prototype does not do (dense linear algebra, CPU-only "GPU" engine, small-scale MILP, approximate HPR operator).

Begin with a written plan (architecture, file tree, risks, phase schedule) for my approval, then start Phase 0.
