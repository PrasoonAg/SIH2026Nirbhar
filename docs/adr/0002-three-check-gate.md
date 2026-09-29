# ADR-0002 — Three-Check Trust Gate

**Status:** Accepted  
**Date:** 2026-09-29  
**Deciders:** Team Vernils  
**Context:** SIH26155 · NTRO · PRAMANA  
**Supersedes:** Conflict C1 in §16 (`PRamana.md` proposed 2 checks; deck wins)

---

## Context

PRAMANA must validate AI-proposed config-line → setting mappings before they
can influence compliance verdicts. The validator must:

1. Be auditable and falsifiable (anyone can re-run the checks from one command).
2. Prevent the proposer from grading itself (INV-02).
3. Catch well-formed but semantically wrong mappings (a gap in a 2-check design).
4. Record every check result, even if the first check fails.

The source documents conflict on the number of checks:
- `PRamana.md`: regen check + embedding re-score (2 checks).
- Slide deck: regen + lexical + second model of a **different family** (3 checks).

The deck wins (§16 rule C1). Re-scoring with the proposer's own embedding is
self-grading and would violate INV-02.

---

## Decision

**Gate = AND of three independent checks.** All three always run and are recorded,
even after the first failure. Any `FAIL` → `Rejected`. An infrastructure `ERROR`
(≠ `FAIL`) never rejects and never passes: the mapping stays `AdminReviewed`
and the gate may be re-fired (ledgered).

### Check 1 — RegenCheck (deterministic, no ML)

For every support line `L`:
1. `frag = match(spec, L)` — must succeed.
2. `render(spec, frag) == L` byte for byte (terminator compared separately).
3. `match(spec, render(spec, frag)) == frag` — round-trip.

PASS iff **every** support line round-trips.  
Artifact: per-line result, first differing offset, hex diff.  
**This proves well-formedness only. UI copy must say so** (INV-15 spirit).  
Basis: Nakamura et al., arXiv:2511.17948.

### Check 2 — LexicalCheck (BM25, no ML)

BM25 (`rank_bm25.BM25Okapi`) over the vendor-neutral setting lexicon.  
Query: the line's tokens with numbers, IPs and values dropped.  
Corpus: one document per setting (name + description + synonyms + control-table text).  
**Lexicon must never be built from the proposer's anchor phrases** (INV-02).  
PASS iff the proposed target ranks ≤ `lexical.top_k` **and** its normalised score ≥ `lexical.min_score`.  
Artifact: ranked top-10 table.

### Check 3 — SecondModelCheck (different model family)

`VerifierPort.rank(line, candidates) → scores`.  
Candidates: proposed target + N lexicon distractors chosen by the gate.  
PASS iff proposed target is top-1 **and** normalised score ≥ `second_model.min_score`.  
The verifier must be a **different model family** from the proposer (MiniLM).  
Family guard runs at startup and again on every gate run (INV-02, INV-17).  
Verifier choice deferred to empirical evaluation in ADR-0004.

### Thresholds

All thresholds in `trustgate/data/gate_config.yaml` are **placeholders** until
calibrated on the dev split in Phase 5. The YAML's SHA-256 is recorded in every
`GateReport`. Changing it requires a new config hash, a new ADR and a fresh self-audit.

### Outcome rules

| Verdicts | Outcome | Mapping state |
|---|---|---|
| All three PASS | PASSED | Provisional |
| Any FAIL (dominates ERROR) | FAILED | Rejected (absorbing, INV-01) |
| ≥ 1 ERROR, no FAIL | ERRORED | AdminReviewed (may re-fire) |

---

## Consequences

**Positive:**
- BM25 lexical check catches "well-formed wrong control" cases that regen alone misses.
- Second-model from a different family prevents the proposer from grading itself (INV-02).
- All three checks recorded even after first failure → full audit trail (INV-12).
- ERROR is not FAIL: infrastructure transience never silently rejects a correct mapping (INV-03 / assumption A10).

**Negative / trade-offs:**
- Three checks increase gate latency; mitigated by CPU-only models and background jobs.
- Threshold calibration is required before the gate is meaningful (Phase 5).

---

## Rejected alternatives

| Alternative | Reason rejected |
|---|---|
| 2 checks (regen + embedding re-score) | Proposer grades itself; violates INV-02 |
| 1 check (regen only) | Does not detect semantically wrong mappings |
| LLM as sole check | Not deterministic; fails INV-13; not independently auditable |
| Fail on first check | Incomplete audit trail; violates INV-03 |
