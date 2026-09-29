# pipeline

## Purpose
Audit orchestration: resolves config lines through profile HEAD mappings,
dispatches to parsing → compliance → scoring, manages background jobs.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `JobStatus` | PENDING / RUNNING / DONE / FAILED |
| `Job` | Job record with progress (0–100) |
| `PipelineError` | Orchestration failure |
| `PipelineService` | `audit_config()` / `get_job()` |

## Invariants
- **INV-04** Known-vendor deterministic lines skip the gate.
- **INV-05** Provisional never blocks — audits always return verdicts.
- Background jobs run via `anyio.to_thread`; status polled by frontend.
- **INV-13** Same inputs + same profile commit + same model cards → identical findings.

## Track / Tier
Track 6 · Tier 1

## Owner
Track 6
