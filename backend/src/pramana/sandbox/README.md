# sandbox

## Purpose
T2 Simulation Sandbox: apply remediation to an in-memory scratch copy of a config,
then re-audit with the same engine to get a measured before/after delta (INV-10).

## Public API (`api.py`)
| Export | Description |
|---|---|
| `RemediationDelta` | Before/after both scores, resolved findings, regressions |
| `SandboxError` | Simulation failure |
| `SandboxService` | `simulate(device_audit_id, check_id)` |

## Invariants
- **INV-09** Never writes to a device. Operates on in-memory copy only.
- **INV-10** Delta = re-audit of patched scratch copy. Never estimated.
- Original artifact bytes are never modified.
- No template for a vendor/check → `no_remediation_template` (text guidance only).

## Track / Tier
Track 3 · Tier 2

## Owner
Track 3
