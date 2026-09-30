# NIRBHAR Showcase

NIRBHAR is a browser-only optimization showcase for a sovereign, certified hybrid CPU–GPU solver core. This project presents a professional engineering prototype for exploring LP, MILP, QP, MIQP, solver verification, robustness, and traceability workflows in a single React + TypeScript + Vite application.

The app is intentionally designed as a credible prototype for a Smart India Hackathon 2026 solution and is built to uphold the key principles of the project brief:

- no backend runtime
- browser-only computation with real JavaScript execution in Web Workers
- solver sovereignty without third-party numeric packages in the solver core
- independent verification and honest status labels
- a polished, professional engineering UI that looks credible for demo and screen recording

---

## Why this project exists

NIRBHAR is designed to demonstrate a solver that does not just spit out a number — it proves its answer. The showcase emphasizes:

- certified lower bounds and dual safety checks
- robust solver diagnostics and escalation paths
- verifier isolation from the main solving engine
- branch-and-cut, presolve, and postsolve transparency
- refinery-planning-style scenarios and model families for demonstration

This prototype is not a commercial solver replacement. It is a traceable, transparent engineering prototype that communicates where the solver is strong, where it is approximate, and where the production target remains beyond browser runtime limits.

---

## Product highlights

- Solve Studio for model intake, engine configuration, live solve lanes, and result review
- Refinery Demo covering LP, MILP, QP, and batch-scenario execution
- Branch-and-Cut Lab with live tree views, cuts, and safe-bound logic
- Robustness Lab comparing naive vs hardened execution
- Independent Verifier with float and exact verification paths
- Benchmarks, model families, CLI/API exploration, and PS compliance views
- Light and dark theme support with persistent user preference
- Strict sovereignty checks to prevent numeric-solver package leakage into the core

---

## Tech stack

- React 19
- TypeScript
- Vite
- Zustand for UI state
- React Router for page navigation
- Recharts for plots and benchmark views
- Framer Motion for lightweight motion and transitions
- Lucide React for consistent iconography
- Web Workers for solver execution isolation
- Vitest for unit and integration tests

---

## Repository structure

```text
SIH2026Nirbhar/
├── public/
│   ├── check-imports.json
│   ├── fonts/
│   └── samples/
├── src/
│   ├── App.css
│   ├── App.tsx
│   ├── index.css
│   ├── main.tsx
│   ├── store.ts
│   ├── data/
│   ├── demo/
│   ├── solver/
│   ├── ui/
│   ├── verify/
│   └── tests/
├── docs/
├── tools/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── README.md
├── KNOWN_LIMITS.md
└── ...
```

---

## Getting started

### Prerequisites

- Node.js 18+
- npm

### Install dependencies

```bash
npm install
```

### Run the app locally

```bash
npm run dev
```

### Production build

```bash
npm run build
```

### Run tests

```bash
npm test
```

### Check solver sovereignty rules

```bash
npm run check-imports
```

---

## Available scripts

```bash
npm run dev          # start the local Vite dev server
npm run build        # verify imports, type-check, and bundle the app
npm run preview      # preview the production build locally
npm test             # run the Vitest suite
npm run typecheck    # run TypeScript without bundling
npm run check-imports # enforce solver/verify import sovereignty rules
```

---

## Engineering principles in this prototype

This project follows the design brief with focus on honesty, traceability, and credibility:

- every solver result is treated as an engineering artifact, not marketing copy
- a solver answer is only shown as `OPTIMAL` when the certified gap and verifier agree
- the solver and verifier are intentionally separate code paths
- all numeric-solver libraries are blocked from the core solver package
- the UI is designed for a serious engineering audience rather than a generic AI landing page

---

## Demo and recording guidance

The project includes a showcase mode and a light-first design, intended for screen capture and product storytelling. Use the built-in UI controls to switch themes and record mode, then run the themed walkthrough in the browser at a standard 1920×1080 layout.

### Recommended video flow

1. Home overview and pitch
2. Refinery LP solve and certificate
3. MILP tree and branch-and-cut
4. QP bound and non-convex refusal
5. Scenario batch + speedup chart
6. Robustness and verifier checks

### Recording tips

- start in Light mode for the primary capture
- use the `Rec Mode` toggle into the top bar to enlarge KPI panels and hide noise
- keep the page centered at 1920×1080 for the core path
- use `R` to run a selected action, `Esc` to cancel, `M` to toggle record mode, and `?` for the shortcut help overlay
- narrate results from the actual outputs instead of using placeholders

### How to add real MPS files

1. place decompressed `.mps` files into `public/samples/`
2. update `public/samples/manifest.json` with the correct metadata: name, path, class, rows, cols, nnz, integer count, and reference objective
3. keep the `split` value set to `tune`, `report`, or `stress` as appropriate
4. rerun `npm run build` and `npm test` to confirm the manifest and parser checks still hold

### What is already included

- a generated-instance inventory in [docs/instances.md](docs/instances.md)
- reference extraction notes in [docs/reference-data.md](docs/reference-data.md)
- reference-diff tracking in [docs/reference-diff.md](docs/reference-diff.md)
- a truthful limitations file in [KNOWN_LIMITS.md](KNOWN_LIMITS.md)

---

## Compliance and quality expectations

The project is structured to align with the prototype brief and a rigorous, evidence-based demo workflow:

- the app is browser-only and offline-friendly after build
- solver results are computed in-browser, not hardcoded
- production claims are restricted to measured values and clearly marked target chips
- the sovereignty panel demonstrates the actual import-scan result
- tests and build checks are part of the development workflow

---

## Known limitations

This prototype is intentionally honest about its limitations. It is a showcase and an engineering prototype, not a full industrial-scale production solver. The project includes a separate `KNOWN_LIMITS.md` file documenting the currently scoped boundaries and areas that remain production targets rather than measured browser results.

---

## Roadmap alignment

The app is structured around an incremental Phase 0 → Phase 7 workflow from the project brief, centered on:

- design and shell readiness
- solver core and independent verification
- presolve and explainability
- branch-and-cut and cuts
- QP and scenario-batch execution
- robustness and adversarial checks
- compliance and showcase polish

---

## Contributing

This repository is built for rapid iteration and demo-grade validation. Changes should prioritize:

- correctness over embellishment
- truthful labels and evidence-backed claims
- solver transparency and verifier checks
- UI readability and professional engineering polish

---

## Verified status

The project is currently validated with the following commands:

```bash
npm test
npm run build
npm run check-imports
```

As of the current workspace state, all of the above completed successfully in this environment.

---

## License

This project is part of the SIH 2026 prototype work and should be treated as a demonstration engineering artifact unless otherwise specified by the owning team or institutional stakeholders.
