# PRAMANA — Invariants Reference

Cross-reference: §2 of `docs/PRAMANA_MASTER_PROMPT.md`.

Every invariant must have **at least one test** tagged `@pytest.mark.inv("INV-xx")`.
`scripts/check_inv_coverage.py` fails CI (Phase 8+) if any invariant has no test.

---

| ID | Rule | Enforced by | Test IDs |
|---|---|---|---|
| INV-01 | **No override from `Rejected`.** `Rejected` is absorbing. No API, flag, env var, role, CLI or SQL path moves a mapping out of it. Admin may only create a NEW proposal (new id, `supersedes` link). | Aggregate has no such transition; DB trigger blocks state change out of REJECTED; test enumerates every route and CLI; property test on state machine. | _(Phase 3)_ |
| INV-02 | **The proposer never grades itself.** `proposer` and `trustgate` never import each other or share a model. Verifier model family ≠ proposer model family. Checked at startup and every gate run; fail closed. | import-linter `independence` contract; `ModelCard.family` registry; unit tests. | `tests/architecture/test_architecture.py::test_import_linter_contracts_pass` |
| INV-03 | **Gate = AND of three checks** (regen, lexical, second model). All three always run and are recorded, even after the first failure. Any `FAIL` → `Rejected`. An infrastructure `ERROR` never yields Provisional and never rejects. | Gate orchestrator tests; fault-injection tests. | _(Phase 4)_ |
| INV-04 | Known-vendor deterministic lines skip the gate. Only AI-proposed mappings pass it. | Provenance tests in `pipeline`. | _(Phase 4)_ |
| INV-05 | **Provisional never blocks.** Audits always return verdicts. Provisional-based findings are flagged, included in Provisional-Inclusive, excluded from Verified. | Scoring + pipeline tests. | _(Phase 1)_ |
| INV-06 | **Corroboration needs new independent evidence.** New evidence class required. Same actor or same checker = weight 0. Repeats add nothing. | Pure `credit()` function; property tests. | _(Phase 3)_ |
| INV-07 | **Two numbers, always together.** No blended or discounted score exists in types, API, UI or PDF. No invented discount constants. | Response-schema test; grep test for forbidden field names (`blended`, `confidence_multiplier`). | `tests/architecture/test_architecture.py::test_no_forbidden_score_fields[blended]` |
| INV-08 | Every verdict carries its trust class and evidence pointers. Every score carries provisional-dependence and coverage. | Schema tests. | _(Phase 1)_ |
| INV-09 | **Suggestion-only remediation.** The system never writes to a device. No device credentials. No live-pull path. | Architecture scan: no SSH/telnet/netmiko/paramiko imports. | `tests/architecture/test_architecture.py::test_no_live_pull_imports[paramiko]` (and others) |
| INV-10 | **Measured, not estimated.** Remediation delta = re-audit of a patched scratch copy with the same engine. | Sandbox golden before/after tests. | _(Phase 8)_ |
| INV-11 | **Zero network egress at install and runtime.** No DNS, no non-loopback / non-compose-internal sockets, no CDN assets, fonts, telemetry or model downloads. | Pytest socket-block fixture (autouse); `scripts/verify_offline.sh`; Compose `core` network with `internal: true`. | `tests/architecture/test_no_egress.py::test_external_connect_is_blocked` |
| INV-12 | **Every state transition is ledgered:** timestamp, actor, SHA-256 forward link, same DB transaction as the state change. | Ledger tests; tamper test; UoW test. | _(Phase 3)_ |
| INV-13 | **Determinism.** Same inputs + same profile commit + same model cards + same thresholds → identical findings, scores and gate verdicts. CPU only, fixed seeds, LLM temperature 0. | Golden + repeat-run tests. | _(Phase 1)_ |
| INV-14 | **Honest tiering.** LIVE badge only if acceptance tests pass. T2/T3 never presented as built. | Feature registry test: badge computed from test results file. | _(Phase 6)_ |
| INV-15 | **Residual risk is stated, not hidden.** A correctly regenerated line assigned to the wrong control can pass all three checks. The measured rate appears on the self-audit page and the report appendix. Never claim it solved. | Report snapshot test; UI test. | _(Phase 7)_ |
| INV-16 | **Secret hygiene.** Credentials, keys and hashes are redacted in logs, reports, packs and UI. Exception: well-known default values that are themselves the finding. | Redactor property tests. | _(Phase 2)_ |
| INV-17 | **Fail closed.** Missing model integrity, unknown model family, unreadable profile or broken ledger chain → not trusted, loud alert, no silent fallback. | Startup checks + tests. | _(Phase 3)_ |

---

## Notes

- _(Phase N)_ means: the test will be written in that phase per the phased plan (§15).
- Tests already written in Phase 0 are linked above.
- Run `python scripts/check_inv_coverage.py` at any time to see coverage status.
- Run `python scripts/check_inv_coverage.py --strict` to fail on missing coverage (CI from Phase 8).
