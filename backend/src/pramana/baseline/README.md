# baseline

## Purpose
Vendor-neutral setting taxonomy (≥ 60 settings, ≥ 10 areas) and the
**`MappingSpec` engine** (`match` / `render`) — the pure reversible link between
raw config lines and abstract settings.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `Setting` | One taxonomy entry (id, area, name, description, synonyms) |
| `MappingSpec` | Reversible spec: pattern tokens → target setting |
| `match(spec, line_bytes)` | → `Fragment \| None`; pure |
| `render(spec, fragment)` | → `bytes`; pure; round-trip must equal input |
| `NormalizedBaseline` | Output of the parsing stage |
| `Observation` | Typed setting observation with provenance + line_ref |
| `UnrecognizedLine` | Line no parser matched |
| `TaxonomyPort` | Protocol for taxonomy storage |

## Invariants
- **R7** `mapping_spec` is pure: stdlib + pydantic only.
- `render(spec, match(spec, line)) == line` byte-for-byte (tested per-vendor with Hypothesis).

## Track / Tier
Track 1 · Tier 1

## Owner
Track 1
