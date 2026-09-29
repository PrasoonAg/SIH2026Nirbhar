# ADR-0001 — Modular Monolith with Hexagonal Architecture

**Status:** Accepted  
**Date:** 2026-09-29  
**Deciders:** Team Vernils  
**Context:** SIH26155 · NTRO · PRAMANA

---

## Context

PRAMANA must run fully air-gapped on a single host with 25+ vendor support,
a multi-stage trust lifecycle, append-only ledger, and six parallel development tracks.

Key constraints:
- Air-gapped: no distributed infrastructure, no broker, no service mesh.
- Trust transitions must write state **and** ledger in **one atomic DB transaction**.
- Six tracks need enforced boundaries so they can be developed in parallel without coupling.
- The gate, state machine and scoring must be **pure** (hand-recomputable, property-testable).
- Extraction path must remain open: `proposer` or `trustgate` must be promotable to sidecars later.

---

## Decision

**Modular monolith.** One backend process, one repo, one database.

Architecture style inside each module: **Hexagonal (ports and adapters)**.  
Functional core (state machine, scoring, `MappingSpec`, `credit()`) with an
**imperative shell** (DB, models, Git, files).  
Domain events are **frozen dataclasses** on an **in-process synchronous bus**.  
Ledger is **append-only, SHA-256 hash-chained**.

```
Browser ──▶ nginx (React static build + /api reverse proxy)
               └▶ Backend: FastAPI modular monolith (Python 3.11+)
                     ├─ DB: SQLite (WAL) default | PostgreSQL 15 fleet mode
                     ├─ Git: data/profiles.git   (versioned vendor profiles)
                     ├─ File store: configs (content-addressed), reports
                     ├─ Bundled models: MiniLM (proposer) + 2nd-family verifier
                     └─ (below τ_conf only) ──▶ Ollama llama3.2:3b (T2, internal net)
```

Layer ordering (a module may import **only from strictly lower layers, via `api.py`**):

```
L0  shared_kernel
L1  identity · ledger · baseline · crypto · scoring
L2  parsing · proposer · trustgate · profiles · compliance
L3  mapping · ingest
L4  pipeline
L5  sandbox · reporting · federation
L6  bootstrap   ← composition root; the ONLY place adapters are wired
```

Boundaries are enforced by **import-linter contracts** (`.importlinter`) and
**architecture tests** (`tests/architecture/`). CI fails on any violation.
Contracts may only be loosened by a new ADR.

---

## Consequences

**Positive:**
- Atomic trust transitions: one DB transaction for state + ledger (INV-12).
- Enforced boundaries without network hops (import-linter replaces a service mesh).
- Pure domain: `scoring`, `baseline.mapping_spec`, `credit()` are hand-recomputable.
- One SQLAlchemy model layer → both SQLite and PostgreSQL.
- No broker to ship air-gapped.

**Negative / trade-offs:**
- Single process is a scaling ceiling; accepted because the use case is one-host air-gap.
- `bootstrap` accumulates wiring complexity; mitigated by DI and UoW patterns.

---

## Rejected alternatives

| Alternative | Reason rejected |
|---|---|
| Microservices | Distributed transactions; zero benefit on one host; ops cost in air-gap |
| Layered monolith without enforced boundaries | Six tracks would couple over time |
| Full event sourcing / CQRS | Over-scoped; the ledger already provides the audit trail |
| Celery / Redis task queue | Extra infrastructure to ship offline; `anyio.to_thread` suffices |
