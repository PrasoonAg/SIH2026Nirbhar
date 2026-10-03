# Reference Data — NIRBHAR Showcase Seed Set

**Status:** This project uses the internally seeded synthetic refinery data and does not rely on any third-party reference site. The original reference prototype references were removed to avoid confusion and duplicated branding.

## Source of the current seed data

The synthetic refinery input set used here is generated from the project's own reference data, stored in `src/data/reference/refinery.json`, and intentionally kept consistent, internally valid, and labelled as synthetic.

## Current seeded refinery reference

The refinery generator in `src/demo/refinery.ts` uses the following default crude data (physically plausible, internally consistent):

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

If additional real refinery data is provided later, update this file and `src/data/reference/` and log the difference in `docs/reference-diff.md`.
