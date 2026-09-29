# ADR-0003 — Git Profile Store with DB Consistency

**Status:** Accepted  
**Date:** 2026-09-29  
**Deciders:** Team Vernils  
**Context:** SIH26155 · NTRO · PRAMANA

---

## Context

PRAMANA maintains versioned vendor profiles: a mapping's `MappingSpec` and metadata
must be preserved at every trust-state transition so that:

1. Audits are reproducible against a specific profile commit (INV-13).
2. Rollback is possible without rewriting history.
3. DB state and Git HEAD never diverge silently.
4. A Rejected or Demoted mapping is excluded even if it appears in Git HEAD (INV-01).

We need a version-control store and must decide: which Git library?

---

## Decision

**Bare Git repository at `data/profiles.git`.**

Layout:
```
vendors/<vendor_id>/profile.json
vendors/<vendor_id>/mappings/<mapping_id>.json
```

One commit per state transition: Provisional / Corroborated / Demoted / Rejected.  
Commit author = actor; message references the ledger sequence number.

### DB ↔ Git consistency protocol

1. **Write DB and ledger first**, inside the same transaction.
2. Git commit fires via an **idempotent post-commit handler** keyed by ledger sequence number.
3. On startup: `profiles.reconcile()` checks HEAD against DB states and raises alerts on divergence.
4. CLI: `pramana profiles verify` re-runs the reconciliation.

### Rollback

Rollback = a new **revert commit**. Git history is never rewritten (no force-push, no amend).

### Audit eligibility rule

A mapping is usable in an audit **iff**:
- Its `mapping_id` appears in the profile HEAD tree, **AND**
- Its DB state is `Provisional` or `Corroborated`.

On load, a HEAD member whose DB state is `Rejected` is excluded and raises an alert (INV-01 survives rollback).

### Git library

**`pygit2`** (libgit2 binding) — preferred for:
- Speed and full libgit2 feature set.
- No subprocess; direct object model.
- Available as a binary wheel for offline installation.

Fallback: `GitPython` or `dulwich` if `pygit2` cannot be bundled (wheel availability
must be verified for the target host before bundling).

Library is imported only by adapters in `bootstrap` (R5). All other modules see
`ProfileStorePort` (a Protocol in `profiles/ports.py`).

> **Human to-do (Phase 4):** Verify `pygit2` binary wheel availability for the NTRO target
> host OS/arch before declaring the library final. If unavailable, update this ADR and
> re-evaluate `dulwich` (pure Python, no binary dependency).

---

## Consequences

**Positive:**
- Full version history with authorship and ledger cross-reference.
- Rollback without history rewrite → clean, auditable git log.
- `ProfileStorePort` protocol means the Git library can be swapped without touching domain code.
- Reconcile on startup catches DB/Git divergence before any audit runs.

**Negative / trade-offs:**
- Two stores (DB + Git) must be kept in sync; mitigated by the idempotent handler + reconcile.
- `pygit2` has a native binary dependency; must be in the offline bundle.
- Git operations (commit, diff) add latency; acceptable because state transitions are infrequent.

---

## Rejected alternatives

| Alternative | Reason rejected |
|---|---|
| DB-only versioning (row snapshots) | No standard diff / rollback UI; no Git tooling |
| Full Git repo with working tree | Unnecessary; bare repo suffices and is cleaner |
| Object storage (S3-like) | No air-gapped equivalent; requires extra infra |
| `gitpython` subprocess mode | Slower, less reliable; subprocess adds attack surface |
