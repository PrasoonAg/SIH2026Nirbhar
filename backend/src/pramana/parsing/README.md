# parsing

## Purpose
Vendor detection, 4 hand-written grammars (Cisco IOS · Juniper JunOS · Palo Alto PAN-OS · FortiOS),
Pydantic AST nodes with `render()`, `Redactor`, and unrecognized-line extraction.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `VendorId` | Detected vendor enum (AMBIGUOUS / UNKNOWN on failure) |
| `ParseResult` | Baseline + line counts + unrecognized list |
| `ParsingService` | `parse(raw_bytes)` / `detect_vendor()` |
| `Redactor` | Masks secrets; used by logs, reports, UI (INV-16) |

## Invariants
- **INV-09** No SSH/telnet/netmiko/paramiko imports.
- **INV-13** Deterministic: same bytes → same AST.
- **R3** `domain/` has no framework imports.
- Ambiguous vendor → `AMBIGUOUS`; never a silent guess.
- Property test per vendor: `render(parse(line)) == line`.

## Track / Tier
Track 1 · Tier 1

## Owner
Track 1
