# federation

## Purpose
T3 — Signed profile-pack export and import.
A pack is **evidence, not authority**; imported mappings enter as Proposed and still pass the local gate.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `FederationError` | Pack signature / hash / schema failure |
| `PackManifest` | Pack metadata with per-file SHA-256 |
| `FederationService` | `export_pack()` / `import_pack()` |

## Invariants
- Import verifies Ed25519 signature against peer trust store (no TOFU).
- Import is idempotent by pack id.
- Imported mappings enter as Proposed → local Trust Gate still runs.
- `SIGNED_PACK` evidence is credited only from a different peer key (INV-06).

## Track / Tier
Track 5 · Tier 3

## Owner
Track 5
