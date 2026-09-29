# bootstrap

## Purpose
Composition root — the **only** place adapter implementations are wired.
Owns settings, DB/UoW factory, DI container, event wiring, FastAPI app factory, and CLI.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `BootstrapError` | Startup / configuration failure |
| `create_app()` | FastAPI application factory |

## Invariants
- **R5** Only `bootstrap` imports adapter implementations (SQLAlchemy repos, model runners, Git, filesystem, HTTP clients).
- **INV-17** Verifies model manifest SHA-256s at startup; fails closed on mismatch.
- All other modules see only `Protocol`s in `ports.py`.
- DB via `PRAMANA_DB_URL`: SQLite WAL (default) or PostgreSQL 15 (fleet mode).

## Track / Tier
Track 6 · Tier 1

## Owner
Track 6
