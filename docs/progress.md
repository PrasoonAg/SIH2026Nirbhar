# PRAMANA — Progress Log

## Phase 0: Scaffold and Guardrails ✅ COMPLETE

**Exit gate:** `make arch test` green on empty modules.

### Deliverables
| Item | Status |
|---|---|
| All 18 module packages (`api.py` stub + `README.md` + `__init__.py`) | ✅ |
| `.importlinter` — 15 contracts (L0–L6 + INV-02 + R3 × 5 + R7 × 2 + R9) | ✅ |
| `tests/architecture/test_architecture.py` — 77 structural tests | ✅ |
| `tests/conftest.py` — `block_egress` autouse fixture (INV-11) | ✅ |
| `tests/architecture/test_no_egress.py` — socket blocking verification | ✅ |
| `scripts/check_inv_coverage.py` — invariant coverage scanner | ✅ |
| `docs/adr/0001-modular-monolith.md` | ✅ |
| `docs/adr/0002-three-check-gate.md` | ✅ |
| `docs/adr/0003-git-profile-store-db-consistency.md` | ✅ |
| `docs/invariants.md` — INV-01 to INV-17 | ✅ |
| `deploy/compose.yaml` — `core` (`internal: true`) + `edge` networks | ✅ |
| `Makefile` — all §14 targets | ✅ |

### Known platform limitation
`lint-imports` (grimp 3.17) panics on Python 3.12/Windows due to Rust extension incompatibility.
Test `test_import_linter_contracts_pass` is **skipped** on Windows with a clear message.
Run `make arch` on Linux for the authoritative check (contracts are complete and syntactically verified).

---

## Phase 1: Walking Skeleton ✅ COMPLETE

**Exit gate:**
- [x] Golden vector A passes (`tests/unit/test_scoring_golden.py` — 9/9)
- [x] Cisco fixture gives expected findings with line numbers (`tests/unit/test_cisco_ios_parser.py` — 17/17)
- [x] `openapi.json` exported — 4 paths, 10 schemas
- [x] Full E2E API tests (`tests/e2e/test_audit_api.py` — 18/18)
- [x] Frontend builds cleanly (Vite 5, React 18, 1.26s)

### Deliverables
| Item | Status |
|---|---|
| `parsing/domain/cisco_ios.py` — Hand-written Cisco IOS parser (no regex, block-stack context) | ✅ |
| `parsing/service.py` — Vendor detection + parse dispatch | ✅ |
| `compliance/domain/engine.py` — Pure declarative predicate evaluator (no eval/exec — R9) | ✅ |
| `compliance/domain/seed_checks.py` — CHK-001 to CHK-010 (3 wired, 7 stubbed) | ✅ |
| `scoring/api.py` — Two-number model (INV-07): `compute_score`, `format_score` | ✅ |
| `shared_kernel/api.py` — Full: `sha256_bytes`, `canonical_json`, `Severity`, `TrustClass`, error hierarchy, event bus | ✅ |
| `baseline/api.py` — `NormalizedBaseline`, `Observation`, `LineRef`, `Provenance` | ✅ |
| `ingest/api.py` + `ingest/service.py` — Content-addressed store, ZIP guards | ✅ |
| `pipeline/api.py` + `pipeline/service.py` — Orchestration: ingest → parse → compliance → score | ✅ |
| `ingest/router.py` — `POST /api/v1/ingest/file`, `POST /api/v1/ingest/zip` | ✅ |
| `pipeline/router.py` — `POST /api/v1/audits`, `GET /api/v1/audits/{job_id}` | ✅ |
| `bootstrap/main.py` — FastAPI composition root, CORS, health endpoint | ✅ |
| `bootstrap/settings.py` — Pydantic-settings, 12-factor, all thresholds | ✅ |
| `bootstrap/dependencies.py` — DI container (Phase 1 singletons) | ✅ |
| `bootstrap/cli.py` — All §14 CLI commands as stubs, `export-openapi` implemented | ✅ |
| `openapi.json` — exported from live app | ✅ |
| `frontend/` — Vite + React 18, premium dark-mode UI, two-number score cards | ✅ |
| `fixtures/configs/cisco_ios/test_findings.cfg` — negative golden fixture | ✅ |
| `fixtures/configs/cisco_ios/test_clean.cfg` — positive golden fixture | ✅ |

### Frontend Build (All 9 Screens from §11) ✅ COMPLETE
| Screen | File | Key Features & Invariants | Status |
|---|---|---|---|
| 1. Upload & Ingest | `frontend/src/pages/Upload.jsx` | Single/ZIP upload, byte span validation, guard errors, live progress bar, sample loader, offline fallback | ✅ |
| 2. Fleet Dashboard | `frontend/src/pages/Fleet.jsx` | Per-device two score cards (INV-07), coverage %, severity triage, blast-radius flag, site filter | ✅ |
| 3. Training Studio | `frontend/src/pages/Training.jsx` | Unrecognized queue, top-3 MiniLM anchors + cosine scores, slot editor, live regen diff, 3-check Trust Gate panel | ✅ |
| 4. Mapping Lifecycle | `frontend/src/pages/Mapping.jsx` | State machine graph, evidence ledger, blind reviewer action, strictly NO override on Rejected (INV-01) | ✅ |
| 5. Self-Audit | `frontend/src/pages/SelfAudit.jsx` | False-accept/reject rates per stage, Wilson score CIs, model cards, named residual risk statement (INV-15) | ✅ |
| 6. Fix-Impact + Sandbox | `frontend/src/pages/FixImpact.jsx` | Golden vector B (Telnet 36.0 vs SNMP 10.0), remediation diff, before/after score delta, in-memory re-audit (INV-10, T2) | ✅ |
| 7. Reports | `frontend/src/pages/Reports.jsx` | Two-number scorecards, findings table with line references, Appendix A (Provisional evidence), Appendix B (Self-audit) | ✅ |
| 8. Ledger & Alerts | `frontend/src/pages/Ledger.jsx` | Append-only SHA-256 hash-chained ledger, forward links (INV-12), tamper detection, demotion alerts | ✅ |
| 9. Feature Registry | `frontend/src/pages/FeatureRegistry.jsx` | LIVE vs PLANNED badges per feature (INV-14), T1/T2/T3 tiers, 17 constitutional invariant tests mapping | ✅ |
| Navigation Shell | `frontend/src/components/Sidebar.jsx` + `App.jsx` | React Router v6 routing, sticky topbar with audit context, zero-egress offline indicator (INV-11) | ✅ |

---

## Phase 2: Parsers and Catalog (T1) ✅ COMPLETE

**Exit gate:** Per-vendor golden findings; Hypothesis round-trips green; ZIP-bomb tests green.

### Deliverables
| Item | Status |
|---|---|
| JunOS parser (`parsing/domain/junos.py`) | ✅ |
| PAN-OS parser (`parsing/domain/panos.py`) | ✅ |
| FortiOS parser (`parsing/domain/fortios.py`) | ✅ |
| All 10 seed checks (CHK-001 to CHK-010) × 4 vendors (`compliance/domain/seed_checks.py`) | ✅ |
| Framework tables with `verified: false` flags (CIS, NIST, STIG) | ✅ |
| `Redactor` module masks credentials & secrets (INV-16) | ✅ |
| ZIP-bomb & extraction guards tested (`tests/unit/test_ingest_zip.py`) | ✅ |
| Per-vendor golden fixtures + Hypothesis round-trips (`tests/property/test_parser_roundtrip.py`) | ✅ |

---

## Phase 3: Trust Lifecycle Core (T1) ✅ COMPLETE

**Exit gate:** INV-01 and INV-12 tests; state-machine property tests; unseen line returns top-3 + cosine.

### Deliverables
| Item | Status |
|---|---|
| `ledger` + chain verify (`ledger/domain/chain.py` + `ledger/adapters/in_memory.py`) | ✅ |
| INV-12 test suite (`tests/unit/test_inv12_ledger_chaining.py` — 3/3) | ✅ |
| `MappingSpec`, `match()`, `render()` (`baseline/domain/mapping_spec.py` — pure L1) | ✅ |
| `induce_spec()` deterministic tokenizer (`mapping/domain/induce.py`) | ✅ |
| `Mapping` state machine (`mapping/domain/state_machine.py`) with absorbing Rejected state | ✅ |
| INV-01 test suite (`tests/unit/test_inv01_rejected_absorbing.py` — 2/2) | ✅ |
| State machine property tests (`tests/property/test_mapping_state_machine_property.py` — 2/2) | ✅ |
| Canonical taxonomy expanded to 66 settings across 12 functional areas (`parsing/domain/taxonomy.py`) | ✅ |
| `proposer` with MiniLM anchors + cosine ranking (`proposer/domain/anchors.py` + `proposer/service.py`) | ✅ |
| Unseen line returns top-3 candidates + cosine (`tests/unit/test_proposer.py` — 3/3) | ✅ |
| Independent corroboration `credit()` rules (`tests/unit/test_corroboration_credit.py` — 4/4, INV-06) | ✅ |
| Admin confirm/correct/review API orchestrator (`mapping/service.py` — 3/3) | ✅ |
| Proposer and trustgate independence verified (`tests/unit/test_inv02_proposer_independence.py`, INV-02) | ✅ |
| Known-vendor lines skip gate verified (`tests/unit/test_inv04_known_vendor_skip.py`, INV-04) | ✅ |
| All 16 `.importlinter` architecture contracts KEPT with 0 violations | ✅ |

### Current Test Suite Status
```
228 passed, 1 skipped, 0 failed in 5.79s
12/17 canonical invariants covered by automated tests
```

---

## Phase 4: Real Trust Gate (T1) — NEXT

### Next tasks
- [ ] `RegenCheck` adapter (round-trip verification on support sets)
- [ ] `LexicalCheck` adapter (BM25Okapi scoring against setting lexicons)
- [ ] `SecondModelCheck` adapter (Verifier model family ≠ proposer family, INV-02, INV-03)
- [ ] Gate orchestrator + `GateReport` generator
- [ ] Profiles Git store integration (`profiles`)
- [ ] End-to-end integration: unseen line → proposed → confirmed → gate → Provisional → Corroborated

### Open questions
See `docs/open-questions.md`.


