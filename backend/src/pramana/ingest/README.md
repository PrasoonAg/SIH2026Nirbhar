# ingest

## Purpose
File and ZIP upload handling: ZIP guards, content-addressed artifact storage,
site/device registration.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `IngestError` / `ZipGuardError` | Upload failure types |
| `Artifact` | Content-addressed config file (SHA-256 key; bytes never modified) |
| `Device` / `Site` | Device and site records |
| `IngestService` | `ingest_file()` / `ingest_zip()` |

## Invariants
- **INV-11** No live-pull path; no device credentials (INV-09).
- **INV-16** Original bytes stored verbatim (redaction is separate and read-only).
- ZIP guards (all configurable): max members, max total uncompressed, max ratio,
  reject absolute paths / `..` / symlinks / nested archives / duplicate names / NUL bytes.

## Track / Tier
Track 6 · Tier 1

## Owner
Track 6
