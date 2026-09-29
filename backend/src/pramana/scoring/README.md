# scoring

## Purpose
**Pure** two-number compliance score: Verified and Provisional-Inclusive.
Also computes provisional dependence, coverage, Fix-Impact queue (T2).

## Public API (`api.py`)
| Export | Description |
|---|---|
| `CheckStatus` | PASS / FAIL / UNEVALUATED |
| `TrustLevel` | PROVISIONAL < CORROBORATED < DETERMINISTIC |
| `CheckOutcome` | One check result: weight, status, trust, mapping evidence |
| `ScoreComponents` | Numerator + denominator for each score |
| `compute_score(outcomes)` | Pure scoring function |
| `format_score(sc)` | Present as string dict for API / UI |

## Invariants
- **INV-07** Two numbers always together. No blended score.
- **R7** Pure: stdlib + pydantic only. No framework imports.
- Fleet aggregation sums numerators and denominators; never averages percentages.
- Empty denominator → `None` → rendered "n/a".

## Golden test vectors (§7.2)
Vector A: Verified = 25/35 → 71.4%, Provisional-Inclusive = 35/47 → 74.5%

## Track / Tier
Track 3 · Tier 1 (Fix-Impact T2)

## Owner
Track 3
