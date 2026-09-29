# shared_kernel

## Purpose
Lowest layer (L0). Provides IDs, `Clock`, `Severity` weights, `TrustClass`, canonical JSON,
SHA-256 hashing, error hierarchy, `EventBus` protocol and `FeatureTier`.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `new_id()` | Generate UUID v4 |
| `Clock` / `SystemClock` | Time seam |
| `Severity` | CRITICAL/HIGH/MEDIUM/LOW with weights 20/10/5/2 |
| `TrustClass` | PROVISIONAL < CORROBORATED < DETERMINISTIC |
| `FeatureTier` | T1 / T2 / T3 |
| `sha256_bytes` / `sha256_str` | Hashing helpers |
| `canonical_json` | Deterministic JSON (RFC 8785 subset) |
| `PramanaError` hierarchy | Base exceptions |
| `DomainEvent` / `EventBus` | In-process event bus protocol |

## Invariants
- **INV-11** (partial): no network primitives here.
- This module MUST NOT import any other `pramana.*` sub-package.

## Track / Tier
Track 6 · Tier 1

## Owner
All tracks (shared foundation)
