# mapping

## Purpose
`Mapping` aggregate root and pure state machine (Unmapped → … → Rejected).
`induce_spec` (deterministic spec induction). Evidence + corroboration.
`credit()` pure function for independence rules.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `MappingState` | All states including absorbing `Rejected` |
| `EvidenceItem` | Corroboration evidence record |
| `credit(evidence, history)` | Pure function: weight + reason for new evidence (INV-06) |
| `Mapping` | Aggregate: id, state, proposal, spec, evidence, `supersedes` |
| `MappingRepository` | Protocol for persistence adapter |

## Invariants
- **INV-01** `Rejected` is absorbing. No transition out. `Mapping.transition()` raises if attempted.
- **INV-06** `credit()` is pure: same actor/checker/input → weight 0; repeats add nothing.
- **INV-12** Every `transition()` call writes a ledger entry in the same transaction.
- Re-proposal from Rejected → new Mapping id with `supersedes` link.

## Track / Tier
Track 2 · Tier 1 (decay T2)

## Owner
Track 2
