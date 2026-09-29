# PRAMANA — Open Questions

Unresolved items that require human input, team decisions, or external sourcing.
When resolved, move to the relevant ADR or spec section and delete the item here.

---

## Architecture / tooling

| # | Question | Owner | Due |
|---|---|---|---|
| OQ-01 | Verify `pygit2` binary wheel availability for the NTRO target host OS/arch before bundling (ADR-0003). If unavailable, evaluate `dulwich`. | Track 2 | Phase 4 |
| OQ-02 | Confirm submission deadline with SPOC and assign the six track owners. | Team lead | Immediately |
| OQ-03 | ONNX export for MiniLM embedding model — evaluate vs raw PyTorch for bundle size and CPU latency. Record as ADR. | Track 1 | Phase 3 |

## Compliance data

| # | Question | Owner | Due |
|---|---|---|---|
| OQ-04 | Source real CIS and STIG control IDs from official documents. Review every `verified: false` entry in `compliance/data/frameworks/`. | Track 3 | Phase 2 |
| OQ-05 | Review Llama 3.2 licence for government/NTRO use before enabling Ollama fallback (T2). | Track 1 | Phase 8 |
| OQ-06 | Review every exploitability multiplier in `compliance/data/exploitability.yaml`. All entries other than Telnet 3.0 and SNMP 2.5 are proposals (`needs_review: true`). | Track 3 | Phase 8 |
| OQ-07 | Licence check for each candidate verifier model (flan-t5-base, deberta-v3-small, Qwen2.5-0.5B) before bundling. | Track 2 | Phase 5 |

## Dataset

| # | Question | Owner | Due |
|---|---|---|---|
| OQ-08 | Open NTRO's attached SIH26155 dataset **before Phase 2**. Place under `data/ntro/` (git-ignored). Adapt fixtures and taxonomy to its contents. | All tracks | Before Phase 2 |
| OQ-09 | Confirm the 60-setting taxonomy covers the NTRO dataset. Add areas if needed. | Track 1 | Phase 3 |

## Self-audit / calibration

| # | Question | Owner | Due |
|---|---|---|---|
| OQ-10 | Threshold calibration (§6.3): `lexical.top_k`, `lexical.min_score`, `second_model.min_score`, `τ_conf`, `held_out.min_lines`. All are placeholders until calibrated on the dev split in Phase 5. | Track 2 | Phase 5 |
| OQ-11 | Verifier model selection (ADR-0004): evaluate flan-t5-base vs deberta-v3-small vs Qwen2.5-0.5B on the self-audit dev split. Pick lowest false-accept at acceptable false-reject. | Track 2 | Phase 5 |

## Security / secrets

| # | Question | Owner | Due |
|---|---|---|---|
| OQ-12 | Confirm acceptable login rate-limit and session timeout values with NTRO security team. | Track 5 | Phase 6 |
| OQ-13 | Clarify whether the NTRO deployment host supports `cap_drop: [ALL]` and read-only rootfs (Compose hardening in Phase 9). | Ops | Phase 9 |
