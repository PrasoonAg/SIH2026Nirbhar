# ledger

## Purpose
Append-only, SHA-256 hash-chained audit ledger. Every domain state transition
writes a ledger entry in the **same DB transaction** as the state change.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `LedgerEntry` | Immutable record with forward hash link |
| `LedgerError` | Chain integrity failure |
| `LedgerPort` | Protocol for the storage adapter |

## Invariants
- **INV-12** Every state transition is ledgered: timestamp, actor, SHA-256 forward link, same transaction.
- **INV-13** Determinism: same inputs → identical entries (apart from timestamps).

## Track / Tier
Track 2 · Tier 1

## Owner
Track 2
