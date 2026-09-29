# identity

## Purpose
Manages local users, roles, sessions and the `Actor` principal used in every ledger entry.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `Role` | `operator` · `admin` · `reviewer` · `auditor` |
| `Actor` | Frozen dataclass: `actor_id`, `username`, `role` |
| `AuthError` | Authentication / authorisation failure |
| `IdentityService` | Session management, password (Argon2id), RBAC |

## Invariants
- Every ledger entry carries `actor_id` (INV-12).
- Routers may import `identity.api` only (R6).

## Track / Tier
Track 5 · Tier 1

## Owner
Track 5
