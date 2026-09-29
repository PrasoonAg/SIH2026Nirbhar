# compliance

## Purpose
Data-driven rule engine. Control tables in `compliance/data/`: check YAMLs, framework
tables (CIS/NIST/STIG/ISO), exploitability multipliers. Predicates are declarative data.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `Framework` | CIS / NIST / STIG / ISO |
| `FrameworkRef` | Control citation with `verified` flag |
| `Check` | check_id, severity, declarative predicate, remediation, blast-radius rules |
| `Finding` | Per-device check result with trust and evidence pointers |
| `ComplianceService` | `evaluate(baseline, device_id, profile_commit)` |

## Invariants
- **INV-08** Every verdict carries trust class and evidence pointers.
- **R9** Predicates are declarative data (`all_of | any_of | not | {setting, op, value}`), never `eval`/`exec`.
- CIS and ISO: store IDs + paraphrase only (licensed text). Unknown IDs → `TODO_VERIFY`.
- Unverified framework mappings tagged in UI and PDF.

## Seed check catalog (§8)
- Critical (20): Telnet enabled · Default SNMP community · Cleartext secrets
- High (10): Missing VTY ACL · No remote syslog · HTTP management active
- Medium (5): Inactivity timeout > 10 min · Plaintext service passwords
- Low (2): Missing logging timestamps · Finger service active

## Track / Tier
Track 3 · Tier 1 (conflict detection T2)

## Owner
Track 3
