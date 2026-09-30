# Reference Data — Extracted from roviq.xyz (Kavach-Opt)

**Status:** Partial extraction. The browser agent was cancelled due to a network interruption.
Re-run extraction or paste the data manually if needed.

## Pages Visited Before Cancellation

The browser agent loaded https://roviq.xyz/ successfully:
- Landed on the main page (title: "Kavach-Opt — Sovereign Optimization Engine")
- Dismissed a multi-step "Engine Guide" modal (5 steps → Finish)
- Reached the main Overview page
- Was unable to scroll/navigate further tabs due to CDP page ID mismatch error

## Navigation Structure Observed
(Inferred from DOM steps; not fully confirmed)
- Overview / Home
- Engine Guide (modal walkthrough)
- Solve / Solver panel
- Benchmarks
- Refinery Demo (inferred from the NIRBHAR spec references)

## Data NOT Yet Extracted
The following items still need to be extracted (either by re-running the browser agent
or by the user pasting the content):

1. Crude oil names and prices
2. Crude availability caps
3. Crude sulfur %
4. Crude yield vectors (LPG, naphtha, gasoline, ATF, diesel, fuel oil)
5. CDU capacities
6. Product demand ranges
7. Scenario parameters
8. Benchmark instance names and sizes
9. Feature and terminology lists

## Action Required

Either:
A) Re-run the browser agent on https://roviq.xyz/ with a stable connection
B) Visit roviq.xyz and paste the crude data and benchmark lists here manually

## Defaults Used (until extraction completes)

Until the reference data is available, the refinery generator in `src/demo/refinery.ts`
uses the following default crude data (physically plausible, internally consistent):

| Crude | Price ($/bbl) | Avail (kbd) | Sulfur % | LPG | Naphtha | Gasoline | ATF  | Diesel | FuelOil |
|-------|--------------|-------------|----------|-----|---------|---------|------|--------|---------|
| Arab Light    | 82.0 | 120 | 1.8 | 0.04 | 0.12 | 0.18 | 0.08 | 0.32 | 0.26 |
| Arab Heavy    | 76.0 |  80 | 2.9 | 0.02 | 0.09 | 0.15 | 0.07 | 0.30 | 0.37 |
| Basra Light   | 80.0 |  60 | 2.1 | 0.03 | 0.11 | 0.17 | 0.08 | 0.31 | 0.30 |
| Iranian Light | 78.5 |  50 | 1.5 | 0.04 | 0.13 | 0.19 | 0.09 | 0.33 | 0.22 |
| Kuwait        | 79.0 |  70 | 2.6 | 0.03 | 0.10 | 0.16 | 0.07 | 0.31 | 0.33 |
| Murban        | 88.0 |  40 | 0.8 | 0.05 | 0.15 | 0.21 | 0.10 | 0.34 | 0.15 |
| Bonny Light   | 90.0 |  30 | 0.1 | 0.06 | 0.17 | 0.23 | 0.11 | 0.35 | 0.08 |
| Saharan Blend | 89.0 |  25 | 0.1 | 0.06 | 0.16 | 0.22 | 0.10 | 0.34 | 0.12 |
| Oman          | 81.0 |  45 | 1.1 | 0.04 | 0.13 | 0.19 | 0.08 | 0.32 | 0.24 |
| Colombian     | 85.0 |  20 | 0.4 | 0.05 | 0.15 | 0.20 | 0.10 | 0.33 | 0.17 |

All data is SYNTHETIC — not MRPL operational data.
Yield fractions sum to 1.0 for each crude. Verify column sums.

If roviq.xyz data is later found to differ, update this file and src/data/reference/
and log the difference in docs/reference-diff.md.
