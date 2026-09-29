# profiles

## Purpose
Git-backed versioned vendor profiles. Commit per state transition
(Provisional / Corroborated / Demoted / Rejected).
A mapping is audit-eligible only if it is in HEAD AND DB state is Provisional or Corroborated.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `ProfileCommit` | Git commit metadata (hash, author, message) |
| `ProfileError` | Git store failure |
| `ProfileStorePort` | Protocol: commit_mapping, head_mapping_ids, reconcile, rollback |

## Invariants
- **INV-01** Rollback never resurrects Rejected / Demoted mappings (DB state wins).
- **INV-12** Write DB + ledger first; Git via idempotent post-commit handler.
- Rollback = new revert commit. Never rewrite history.
- Divergence → `profiles.reconcile()` alert (startup + `pramana profiles verify`).
- Library: pygit2 (preferred) — see ADR-0003.

## Track / Tier
Track 2 · Tier 1

## Owner
Track 2
