# trustgate

## Purpose
Orchestrates all three trust-gate checks (RegenCheck · LexicalCheck · SecondModelCheck),
enforces the family guard (INV-02), persists GateReports, and hosts the self-audit harness.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `CheckVerdict` | PASS / FAIL / ERROR |
| `CheckResult` | Per-check verdict, metrics, artifacts, duration |
| `GateOutcome` | PASSED / FAILED / ERRORED |
| `GateReport` | Full gate run record (persisted, shown in UI and PDF) |
| `TrustGateService` | `run_gate(mapping_id, support_lines)` |
| `VerifierPort` | Protocol for the second-model adapter |

## Invariants
- **INV-02** `trustgate` NEVER imports `proposer`.
- **INV-03** All three checks always run and are recorded. Any FAIL → Rejected. ERROR (no FAIL) → AdminReviewed, may re-fire.
- **INV-13** Identical inputs → identical GateReport (apart from timestamps and durations).
- Gate config SHA-256 recorded in every GateReport. Config change requires ADR + new hash.

## Track / Tier
Track 2 · Tier 1 (self-audit harness T2)

## Owner
Track 2
