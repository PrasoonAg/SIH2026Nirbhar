<div align="center">

# PRAMANA — प्रमाण

### Offline · Self-Teaching · Multi-Vendor Network-Configuration Compliance Auditor

**SIH Problem Statement 26155 · NTRO · Team Vernils**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Air-Gapped](https://img.shields.io/badge/Network-Zero%20Egress-red)](#deployment)
[![Tests](https://img.shields.io/badge/Tests-228%20pass%2C%200%20fail-brightgreen)](#testing)
[![License](https://img.shields.io/badge/License-Restricted-orange)](#license)

</div>

---

## What is PRAMANA?

**PRAMANA** (Sanskrit: प्रमाण — *means of proof, authoritative evidence*) is a fully offline, self-teaching network-configuration compliance auditor built for NTRO's 25+ vendor estate.

> **Core thesis:** AI *proposes*. Deterministic code *decides*. Humans *approve* novel cases. The Trust Gate *checks* that the approval was right. The system *measures its own checker.*

It is the only auditor that:

- Returns **two scores, always together** — `Verified` (deterministic only) + `Provisional-Inclusive` (includes AI-confirmed mappings that cleared the Trust Gate). Never one blended figure. Never an invented discount constant.
- Runs **fully air-gapped** — zero DNS, zero CDN, zero telemetry at install or runtime.
- **Teaches itself** to understand unfamiliar vendor syntax offline, via a three-check Trust Gate that must be cleared before an AI-proposed mapping can influence any verdict.
- **States its own residual risk** explicitly, never hides it.

---

## Table of Contents

- [Architecture](#architecture)
- [Vendor Support](#vendor-support)
- [Trust Lifecycle](#trust-lifecycle)
- [The Three-Check Trust Gate](#the-three-check-trust-gate)
- [Two-Number Scoring](#two-number-scoring)
- [Compliance Frameworks](#compliance-frameworks)
- [9-Screen UI](#9-screen-ui)
- [Module Map](#module-map)
- [Security Invariants](#security-invariants)
- [Quick Start](#quick-start)
- [Testing](#testing)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Team](#team)

---

## Architecture

```
Browser ──► nginx  (React static build + /api reverse proxy)
               └──► FastAPI Modular Monolith  (Python 3.11+)
                       ├── DB: SQLite file (default) | PostgreSQL 15 (fleet)
                       ├── Git object store: profiles.git  (versioned vendor profiles)
                       ├── File store: configs (content-addressed), reports
                       ├── Bundled models: MiniLM (proposer) + 2nd-family verifier
                       └── (only below confidence τ) ──► Ollama llama3.2:3b (T2, internal)

         ┌────────────────────────────────────────────────────────────────┐
         │                 Docker Compose Network Topology                │
         │  ┌──── core (internal: true) ──────────────────────────────┐  │
         │  │  backend · db · ollama            NO ROUTE OUT (INV-11) │  │
         │  └────────────────────────────────────────────────────────┘  │
         │  ┌──── edge ───────────────────────────────────────────────┐  │
         │  │  nginx only  →  publishes port 8080                     │  │
         │  └────────────────────────────────────────────────────────┘  │
         └────────────────────────────────────────────────────────────────┘
```

**Design decisions:**

| Decision | Rationale |
|---|---|
| Modular monolith | Air-gapped single host — no broker, no service mesh, no distributed transactions |
| Hexagonal (ports & adapters) per module | Gate, state machine and scoring stay pure, hand-recomputable, property-testable |
| Append-only SHA-256 hash-chained ledger | Every state transition is tamper-evident and auditable |
| Functional core / imperative shell | Six parallel tracks enforced by import-linter contracts, not network hops |
| Two separate model families | Proposer ≠ verifier family — grading your own answers is disallowed by architecture |
| SQLite WAL mode default | Zero-ops, deterministic, no extra service to ship air-gapped |

---

## Vendor Support

| Vendor | Parser | Status |
|---|---|---|
| **Cisco IOS** | Hand-written block-stack context parser (no regex, pure deterministic) | ✅ Live |
| **Juniper JunOS** | Hierarchical set-syntax parser with group-expansion | ✅ Live |
| **Palo Alto PAN-OS** | XML tree walker with zone/policy traversal | ✅ Live |
| **FortiOS** | Indented block parser with vdom-aware context | ✅ Live |
| **Unknown / Novel Syntax** | MiniLM embedding → cosine anchor ranking → admin confirmation → Trust Gate | ✅ Live |

All four deterministic parsers produce identical findings on the same input every time (INV-13). Known-vendor lines never enter the AI pathway (INV-04).

---

## Trust Lifecycle

Unfamiliar configuration lines travel through a strictly enforced state machine:

```
Unmapped
   │
   ▼  (MiniLM proposes top-3 anchors + cosine scores)
Proposed
   │
   ▼  (blind admin reviews, selects/corrects slot)
AdminReviewed
   │
   ▼  (Trust Gate — three checks, ALL must pass)
   ├── ANY FAIL ──► Rejected  ██ ABSORBING — no exit, ever (INV-01)
   │
Provisional  (influences Provisional-Inclusive score only)
   │
   ▼  (new independent evidence: same line in another device/session)
Corroborated  (influences both score numbers)
```

**INV-01 is non-negotiable:** No API, flag, environment variable, role, CLI command or SQL path moves a mapping out of `Rejected`. An admin may only create a *new* proposal with a `supersedes` link. Enforced at the aggregate, the database trigger, and exhaustively tested.

---

## The Three-Check Trust Gate

Before an AI-proposed mapping can influence any verdict, it must pass **all three checks**:

| Check | What it verifies | Pass condition |
|---|---|---|
| **RegenCheck** | Can the engine regenerate a spec-conformant config line from the proposed mapping? | Byte-identical round-trip |
| **LexicalCheck** | Does BM25Okapi ranking place this mapping in the top-N of the relevant setting lexicon? | Score ≥ threshold τ |
| **SecondModelCheck** | Does a *different* model family (≠ proposer) independently agree? | Agreement ≥ τ₂ |

All three checks **always run and are recorded**, even after the first failure. An infrastructure `ERROR` never silently yields Provisional — the mapping stays `AdminReviewed` and the gate may be re-fired (ledgered). The gate cannot be gamed by a transient error.

---

## Two-Number Scoring

Every audit produces exactly two numbers, displayed side by side, never blended:

```
┌───────────────────────────────────────────┐
│  Verified Score          82 / 100         │
│  (deterministic checks only)              │
│                                           │
│  Provisional-Inclusive   91 / 100         │
│  (+ gate-cleared AI mappings)             │
│                                           │
│  Coverage: 94%   Severity: LOW            │
│  Blast-Radius: SAFE                       │
└───────────────────────────────────────────┘
```

The gap between the two numbers is itself a signal. A large gap means the AI pathway carries significant weight — surfaced to the operator, never hidden. No discount constants. No confidence multipliers. No blended figures. (INV-07).

---

## Compliance Frameworks

| Framework | Status | Controls |
|---|---|---|
| CIS Benchmarks | ✅ Live (CHK-001 → CHK-010) | AAA, SSH, SNMP, routing, logging, ACL |
| NIST SP 800-53 | ✅ Seed wired | Cross-framework conflict detection |
| DISA STIG | ✅ Seed wired | — |
| ISO 27001 | Roadmap (T2) | — |

Cross-framework conflicts (e.g. CIS mandates OFF, NIST mandates ON) are detected and both citations surfaced — never silently resolved.

---

## 9-Screen UI

A premium dark-mode React 18 dashboard with glassmorphism, micro-animations and zero CDN dependency (all fonts/assets bundled):

| # | Screen | Key Capability |
|---|---|---|
| 1 | **Upload & Ingest** | Single file / ZIP, byte-span validation, ZIP-bomb guards, live progress |
| 2 | **Fleet Compliance Dashboard** | Per-device two-number score cards, severity triage, blast-radius flags |
| 3 | **Offline Training Studio** | Unrecognized queue, MiniLM top-3 anchors + cosine, slot editor, live regen diff, Trust Gate panel |
| 4 | **Mapping Lifecycle** | State machine graph, evidence ledger, admin review — Rejected is hard-locked |
| 5 | **Trust Mechanism Self-Audit** | False-accept/reject rates per stage, Wilson score CIs, model cards, named residual risk |
| 6 | **Fix-Impact Sandbox** | Ranked remediation queue, before/after re-audit delta (INV-10) |
| 7 | **Audit Reports & Evidence** | Two-number scorecards, findings with line refs, Appendix A (Provisional), Appendix B (Self-audit) |
| 8 | **Ledger & Alerts** | Append-only SHA-256 hash-chained audit trail, tamper detection, demotion alerts |
| 9 | **Feature Registry & Invariants** | LIVE vs PLANNED badges, T1/T2/T3 tiers, 17 constitutional invariant → test mapping |

---

## Module Map

```
L0  shared_kernel              (SHA-256, canonical JSON, Severity, TrustClass, event bus)
L1  identity · ledger · baseline · crypto · scoring
L2  parsing · proposer · trustgate · profiles · compliance
L3  mapping · ingest
L4  pipeline                  (job orchestrator — owns all use cases)
L5  sandbox · reporting · federation
L6  bootstrap                 (composition root — ONLY place adapters are wired)
```

**Rule:** A module at layer N may only import from layers < N, and only through their `api.py` surface. 16 import-linter contracts enforce this at every push.

---

## Security Invariants

17 constitutional invariants, all non-negotiable. 12/17 covered by automated tests:

| ID | Invariant |
|---|---|
| INV-01 | `Rejected` state is **absorbing** — no path out, ever |
| INV-02 | Proposer **never grades itself** — separate model families enforced by architecture |
| INV-03 | Gate = AND of **all three checks** — none skipped, even after first failure |
| INV-04 | Known-vendor deterministic lines **skip the gate** entirely |
| INV-05 | Provisional findings **never block** verdicts — always included, always flagged |
| INV-06 | Corroboration requires **new independent evidence** — repeats add zero weight |
| INV-07 | **Two numbers, always together** — no blended score anywhere in types/API/UI/PDF |
| INV-08 | Every verdict carries trust class + evidence pointers |
| INV-09 | **Suggestion-only remediation** — zero device write paths, no live-pull |
| INV-10 | Remediation delta = **measured** (re-audit of patched copy), never estimated |
| INV-11 | **Zero network egress** at install and runtime |
| INV-12 | Every state transition is **ledgered** in the same DB transaction |
| INV-13 | **Determinism** — same inputs → identical outputs, always |
| INV-14 | **Honest tiering** — LIVE badge only when acceptance tests pass |
| INV-15 | **Residual risk stated, not hidden** — appears on self-audit page and report appendix |
| INV-16 | **Secret hygiene** — credentials redacted in logs, reports, UI |
| INV-17 | **Fail closed** — broken chain / unknown family → loud alert, no silent fallback |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- `uv` — `pip install uv`
- Docker + Docker Compose (production)

### Development (no Docker)

```bash
# 1. Clone
git clone <your-remote-url>
cd ainetworkaudit

# 2. Backend
cd backend
uv pip install -e ".[dev]"
python -m pramana.bootstrap.main     # http://localhost:8000

# 3. Frontend (new terminal)
cd ../frontend
npm install
npm run dev                          # http://localhost:5173

# 4. Run tests
cd ..
make test        # 228 pass, 0 fail
make arch        # import-linter + structural checks
make inv         # invariant coverage report
```

### Environment

```bash
cp frontend/.env.example frontend/.env
# VITE_DEMO_MODE=true  <- set false to hit live backend
```

---

## Testing

```
228 passed  ·  1 skipped (Windows/grimp platform skip)  ·  0 failed
12 / 17 invariants covered by automated tests
```

| Suite | Tests | Description |
|---|---|---|
| `tests/unit/` | 33 | Per-vendor golden fixtures, state machine, ledger chaining, scoring golden vector |
| `tests/property/` | 4 | Hypothesis round-trips: parser round-trip + state machine |
| `tests/architecture/` | 77 | Import-linter contracts, forbidden imports, no-live-pull, no egress, schema invariants |
| `tests/e2e/` | 18 | Full API round-trips (ingest → parse → compliance → score) |

```bash
make test          # all suites
make arch          # architecture + import-linter only
make inv           # invariant coverage scanner (warn)
make inv-strict    # fail on missing invariant coverage (CI Phase 8+)
make predemo       # full pre-demo gate: arch + inv-strict + test + selfaudit + verify-offline
```

---

## Deployment

### Zero-Egress Network (INV-11)

```bash
# Default: SQLite, single node
docker compose -f deploy/compose.yaml up --build

# Fleet mode: PostgreSQL
docker compose -f deploy/compose.yaml --profile fleet up --build

# T2: adds Ollama llama3.2:3b (still internal-only)
docker compose -f deploy/compose.yaml --profile fleet --profile t2 up --build
```

UI at `http://localhost:8080` (or `PRAMANA_BIND_ADDR:PRAMANA_PORT`).

### Security Hardening

- `backend`, `db`, `ollama` — Compose network `internal: true` (no external route)
- All containers: `cap_drop: ALL`, `no-new-privileges: true`, `read_only: true`, non-root
- Models bundled at build time: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`
- `scripts/verify_offline.sh` — run inside backend container to confirm zero egress post-deploy
- pytest `block_egress` autouse fixture — every test run blocks all non-loopback sockets

---

## Project Structure

```
ainetworkaudit/
├── backend/
│   ├── src/pramana/          # 18-module hexagonal monolith (L0–L6)
│   │   ├── bootstrap/        # L6: FastAPI app, CLI, settings, DI wiring
│   │   ├── pipeline/         # L4: job orchestrator
│   │   ├── mapping/          # L3: state machine, induce, admin confirm
│   │   ├── ingest/           # L3: content-addressed store, ZIP guards
│   │   ├── compliance/       # L2: predicate engine, CHK-001→010
│   │   ├── parsing/          # L2: Cisco/JunOS/PAN-OS/FortiOS, taxonomy (66 settings)
│   │   ├── proposer/         # L2: MiniLM anchors, cosine ranking
│   │   ├── trustgate/        # L2: regen + lexical + second-model gate
│   │   ├── profiles/         # L2: Git-backed versioned vendor profiles
│   │   ├── scoring/          # L1: two-number model (INV-07)
│   │   ├── ledger/           # L1: SHA-256 hash-chained append-only ledger
│   │   ├── baseline/         # L1: NormalizedBaseline, MappingSpec, Observation
│   │   ├── reporting/        # L5: PDF generation (WeasyPrint), Appendix A/B
│   │   ├── sandbox/          # L5: remediation sandbox, re-audit delta
│   │   └── shared_kernel/    # L0: SHA-256, canonical JSON, Severity, event bus
│   ├── tests/
│   │   ├── unit/             # 33 unit tests
│   │   ├── property/         # Hypothesis property tests
│   │   ├── architecture/     # 77 structural tests
│   │   └── e2e/              # 18 API round-trip tests
│   ├── fixtures/             # Golden config files (all 4 vendors)
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── pages/            # 9 screens
│   │   ├── components/       # Sidebar, ScoreCards, FindingsList, MappingFlow
│   │   ├── api/              # typed client, mock store, useApi hook
│   │   └── pdf/              # client-side PDF generation
│   ├── public/favicon.svg    # State Emblem of India — custom SVG
│   └── vite.config.js
│
├── deploy/
│   ├── compose.yaml          # Production Docker Compose
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
│
├── docs/
│   ├── PRAMANA_MASTER_PROMPT.md  # Full spec (constitution + screen spec)
│   ├── invariants.md             # INV-01 → INV-17 reference
│   ├── adr/                      # Architecture Decision Records (ADR-001–003)
│   └── progress.md               # Phase-by-phase build log
│
├── models/                   # Bundled model weights — not in git, ship via bundle
├── scripts/
│   ├── check_inv_coverage.py
│   └── verify_offline.sh
├── Makefile
└── README.md                 # ← you are here
```

---

## License

Developed as a prototype for **Smart India Hackathon 2026, Problem Statement SIH26155**, submitted to **NTRO (National Technical Research Organisation)**.

All rights reserved. Not for redistribution or production use without explicit authorization.

---

## Team

**Team Vernils** — Smart India Hackathon 2026

> *"Deterministic by default. AI-assisted where it matters. Honest about what it doesn't know."*

---

<div align="center">

**PRAMANA** · SIH26155 · NTRO · Team Vernils · 2026

*AI proposes. Deterministic code decides. Humans approve. The Trust Gate checks.*

</div>
