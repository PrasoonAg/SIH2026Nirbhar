# PRAMANA (प्रमाण) — MASTER BUILD PROMPT

SIH26155 · NTRO · Team Vernils · Target agent: Claude Code (also works pasted into a Claude chat)

## 0. How to use

1. Save this file as `docs/MASTER_PROMPT.md`. Create a root `CLAUDE.md` containing one line: `@docs/MASTER_PROMPT.md` (Claude Code loads `CLAUDE.md` each session and resolves `@path` imports). Or paste this file as the first message.
2. Work one phase at a time (§15). Session opener: `Read docs/MASTER_PROMPT.md and docs/progress.md. Execute Phase N. Stop at its exit gate.`
3. Source precedence: `Vernils.pdf` (deck) beats `PRamana.md` (v5 notes). Conflicts and how they were resolved: §16.
4. **Part A (§1–§5) is the constitution. Part B (§6–§17) is the spec.** For a lean `CLAUDE.md`, import only Part A and read Part B sections on demand.

---

# PART A — CONSTITUTION

## 1. Mission

You are lead engineer and architect for **PRAMANA**: an offline, self-teaching, multi-vendor network-configuration compliance auditor for NTRO's 25+-vendor brief.

- Four vendors parse **deterministically**: Cisco IOS, Juniper JunOS, Palo Alto PAN-OS, FortiOS.
- Unfamiliar syntax is matched **offline** against embedding anchors. An admin confirms. The mapping must then clear a **three-check Trust Gate** before it can influence any verdict.
- Trust is earned in stages: `Unmapped → Proposed → AdminReviewed → (Gate) → Provisional → Corroborated`. Failure is `Rejected`, with no override.
- Scores are **two numbers**, Verified and Provisional-Inclusive, side by side. Never one blended figure.
- Everything runs air-gapped. Remediation is suggestion-only.

**Thesis:** AI proposes. Deterministic code decides. Humans approve novel cases. The Trust Gate checks that the approval was right, and the system measures its own checker.

**Tie-breaker for every unclear choice:** pick the option that keeps each claim falsifiable (recomputable by hand or re-runnable from one command) and keeps the probabilistic part of the system as small and as auditable as possible.

**Tiers** (planned scope, from the source docs):
- **T1 — must run live:** ingestion (single file / ZIP) → 4 parsers + embedding fallback → Trust Gate + Provisional/Corroborated → versioned profiles (Git) → compliance engine (CIS/NIST/STIG/ISO) → two-number score → triage + blast-radius flag → per-device PDF.
- **T2 — build if hours remain:** Fix-Impact queue, Simulation Sandbox + Verified Remediation Delta, confidence decay + re-verification, self-audit suite (schedule early, §15), cross-framework conflict detection, Ollama fallback.
- **T3 — seams + roadmap:** Ed25519 signed reports, federated signed profile packs, signed device-onboarding manifest, waiver-expiry escalation.

Tier = planned scope. A feature shows **LIVE** in UI, reports and docs only when its acceptance tests pass (INV-14).

## 2. Invariants (non-negotiable)

Every invariant needs at least one test tagged `@pytest.mark.inv("INV-xx")`. CI runs `scripts/check_inv_coverage.py` and fails if any invariant has no test.

| ID | Rule | Enforced by |
|---|---|---|
| INV-01 | **No override from `Rejected`.** `Rejected` is absorbing. No API, flag, env var, role, CLI command or SQL path moves a mapping out of it. An admin may only create a NEW proposal (new id, `supersedes` link). | Aggregate has no such transition; DB trigger blocks state change out of REJECTED; test enumerates every route and CLI command; property test on the state machine. |
| INV-02 | **The proposer never grades itself.** `proposer` and `trustgate` never import each other or share a model. Verifier model family ≠ proposer model family. Checked at startup and at every gate run; fail closed. | import-linter `independence` contract; `ModelCard.family` registry; unit tests. |
| INV-03 | **Gate = AND of three checks** (regen, lexical, second model). All three always run and are recorded, even after the first failure. Any `FAIL` → `Rejected`. An infrastructure `ERROR` never yields Provisional and never rejects: the mapping stays `AdminReviewed` and the gate may be re-fired (ledgered). | Gate orchestrator tests; fault-injection tests. |
| INV-04 | Known-vendor deterministic lines skip the gate. Only AI-proposed mappings pass it. | Provenance tests in `pipeline`. |
| INV-05 | **Provisional never blocks.** Audits always return verdicts. Provisional-based findings are flagged, included in Provisional-Inclusive, excluded from Verified. | Scoring + pipeline tests. |
| INV-06 | **Corroboration needs new independent evidence.** New evidence class required. Same actor or same checker = weight 0. Repeats add nothing. | Pure `credit()` function; property tests. |
| INV-07 | **Two numbers, always together.** No blended or discounted score exists in types, API, UI or PDF. No invented discount constants. | Response-schema test; grep test for forbidden field names (`blended`, `confidence_multiplier`). |
| INV-08 | Every verdict carries its trust class and evidence pointers. Every score carries provisional-dependence (% of evaluated weight resting on Provisional mappings) and coverage. | Schema tests. |
| INV-09 | **Suggestion-only remediation.** The system never writes to a device. No device credentials. No live-pull path. | Architecture scan: no SSH/telnet/netmiko/paramiko imports. |
| INV-10 | **Measured, not estimated.** Remediation delta = re-audit of a patched scratch copy with the same engine. | Sandbox tests (golden before/after). |
| INV-11 | **Zero network egress at install and runtime.** No DNS, no non-loopback / non-compose-internal sockets, no CDN assets, fonts, telemetry or model downloads. | Pytest socket-block fixture; `scripts/verify_offline.sh`; Compose `core` network with `internal: true`. |
| INV-12 | **Every state transition is ledgered:** timestamp, actor, SHA-256 forward link, same DB transaction as the state change. | Ledger tests; tamper test; UoW test. |
| INV-13 | **Determinism.** Same inputs + same profile commit + same model cards + same thresholds → identical findings, scores and gate verdicts. CPU only, fixed seeds, LLM temperature 0. | Golden + repeat-run tests. |
| INV-14 | **Honest tiering.** LIVE badge only if acceptance tests pass. T2/T3 never presented as built. | Feature registry test: badge computed from test results file. |
| INV-15 | **Residual risk is stated, not hidden.** A correctly regenerated line assigned to the wrong control can pass all three checks. The measured rate appears on the self-audit page and the report appendix. Never claim it solved. | Report snapshot test; UI test. |
| INV-16 | **Secret hygiene.** Credentials, keys and hashes are redacted in logs, reports, packs and UI. Exception: well-known default values that are themselves the finding (e.g. community `public`). | Redactor property tests. |
| INV-17 | **Fail closed.** Missing model integrity, unknown model family, unreadable profile or broken ledger chain → not trusted, loud alert, no silent fallback. | Startup checks + tests. |

## 3. Architecture decision (write as `docs/adr/0001-modular-monolith.md`)

**Decision: modular monolith.** One backend process, one repo, one database. **Hexagonal (ports and adapters)** inside each module. **Functional core** (state machine, scoring, regeneration, independence rules) with an **imperative shell** (DB, models, Git, files). **In-process synchronous domain events.** **Append-only, SHA-256 hash-chained ledger.**

```
Browser ─▶ nginx (React static build + /api reverse proxy)
              └▶ Backend: FastAPI modular monolith (Python 3.11+)
                    ├─ DB: SQLite file (default) | PostgreSQL 15 (fleet mode)
                    ├─ Git object store: profiles.git   (versioned vendor profiles)
                    ├─ File store: configs (content-addressed), reports
                    ├─ Bundled models: MiniLM (proposer) + 2nd-family verifier
                    └─(only below confidence τ)─▶ Ollama llama3.2:3b (T2, internal net)
Backend, DB and Ollama sit on a Compose network with `internal: true` (no route out).
Only nginx also joins an `edge` network, solely to publish the UI port.
```

**Why:**
- Air-gapped single host: no distributed ops, no broker, no service mesh.
- A trust transition must write state and ledger atomically: one DB transaction.
- Six parallel tracks need **enforced** boundaries. Use import-linter contracts, not network hops.
- Gate, state machine and scoring must be pure, so they are hand-recomputable and property-testable.
- Extraction path stays open: modules talk only through ports, so `proposer` or `trustgate` can become sidecars later.

**Rejected:** microservices (ops cost, distributed transactions, zero benefit on one host); layered monolith without boundaries (six tracks would couple); full event sourcing / CQRS (over-scoped; the ledger already gives the audit trail); Celery/Redis (a broker is extra infrastructure to ship air-gapped).

**Background work:** request path stays fast. Bulk ZIP audits, model batches, PDF rendering and the self-audit run as `Job`s (owned by `pipeline`) on an in-process thread pool (`anyio.to_thread`). A `pipeline_job` table holds status and progress; the frontend polls. SQLite: WAL mode, `busy_timeout`, short transactions.

## 4. Module map and dependency rules

Layers (a module may import **only from strictly lower layers, and only their `api.py`**):

```
L0  shared_kernel
L1  identity · ledger · baseline · crypto · scoring
L2  parsing · proposer · trustgate · profiles · compliance
L3  mapping · ingest
L4  pipeline
L5  sandbox · reporting · federation
L6  bootstrap   (composition root; the only place adapters are wired)
```

| Module | Owns | Track | Tier |
|---|---|---|---|
| `shared_kernel` | IDs, `Clock`, `Severity` weights, `TrustClass`, canonical JSON, hashing, error types, `EventBus` protocol, `FeatureTier` | 6 | 1 |
| `identity` | Local users, roles (`operator`, `admin`, `reviewer`, `auditor`), sessions, `Actor` | 5 | 1 |
| `ledger` | Append-only SHA-256 forward-linked ledger, chain verification | 2 | 1 |
| `baseline` | Vendor-neutral setting taxonomy + lexicon, `NormalizedBaseline` schema, **`MappingSpec` engine** (match / render, pure) | 1 | 1 |
| `crypto` | Ed25519 keys, sign/verify, file hashing | 5 | 3 |
| `scoring` | **Pure.** Two-number score, provisional dependence, triage, Fix-Impact | 3 | 1 (Fix-Impact T2) |
| `parsing` | Vendor detection, 4 hand-written grammars, Pydantic AST + `render`, `Redactor`, unrecognized-line extraction | 1 | 1 |
| `proposer` | MiniLM anchor index, top-3 + cosine, Ollama fallback | 1 | 1 (Ollama T2) |
| `trustgate` | 3 checks, gate orchestrator, family guard, self-audit harness | 2 | 1 (self-audit T2) |
| `profiles` | Git-backed versioned vendor profiles, diff, rollback | 2 | 1 |
| `compliance` | Control tables (CIS/NIST/STIG/ISO), check catalog, rule engine, findings, blast-radius, conflicts | 3 | 1 (conflicts T2) |
| `mapping` | `Mapping` aggregate + state machine, spec induction, evidence + corroboration, decay sampler, use-cases | 2 | 1 (decay T2) |
| `ingest` | Uploads, ZIP guards, content-addressed artifacts, sites/devices | 6 | 1 |
| `pipeline` | Audit orchestration (`audit_config`), fleet summary, jobs | 6 | 1 |
| `sandbox` | Scratch copy, apply remediation, re-audit, delta | 3 | 2 |
| `reporting` | Report model, one HTML/CSS template, WeasyPrint PDF, signing hook | 5 | 1 (signing T3) |
| `federation` | Signed profile-pack export/import | 5 | 3 |
| `bootstrap` | Settings, DB/UoW, DI, event wiring, app factory, CLI | 6 | 1 |

**Rules (enforced by `import-linter` + `tests/architecture/`; CI fails on violation; never loosen a contract without an ADR):**

- **R1** No same-layer imports. Cross-module calls go through `api.py` (Protocols, frozen Pydantic DTOs, service facade, errors).
- **R2** `proposer` and `trustgate` never import each other and share no model, index or adapter. Their only shared language is `baseline`.
- **R3** `domain/` folders import no framework: no `sqlalchemy`, `fastapi`, `torch`, `sentence_transformers`, `pygit2`, `weasyprint`, `httpx`.
- **R4** Each module owns tables prefixed `<module>_`. No cross-module FK, join or raw SQL. Reference by opaque ID; read through `api.py`.
- **R5** Adapters (SQLAlchemy repos, model runners, Git, filesystem, HTTP clients) are imported only by `bootstrap`. Modules see `Protocol`s in `ports.py`.
- **R6** Routers are thin: validate DTO → call service → return DTO. A router may import its own module and `identity.api` only.
- **R7** `scoring` and `baseline.mapping_spec` are pure: stdlib + pydantic only.
- **R8** Events are frozen dataclasses on an in-process synchronous bus. Critical handlers (ledger append, profile outbox) run **inside the same transaction**. Notification handlers run after commit. All handlers are idempotent.
- **R9** No `eval`/`exec`/`pickle` on untrusted data anywhere. Check predicates are declarative data, never code.

**Module template:**

```
<module>/
  api.py        # ONLY public surface
  domain/       # pure logic
  service.py    # use-cases; one use-case = one transaction
  ports.py      # Protocols this module needs
  adapters/     # implementations of ports
  router.py     # FastAPI router (thin)
  models.py     # SQLAlchemy tables (prefixed); imported only by adapters/ and alembic env
  README.md     # 10 lines: purpose, public API, invariants, owner track
```

## 5. Working agreements

- Read `docs/progress.md` first. Update it last: phase, done, next, risks.
- Domain rules are test-first. Never weaken, skip or delete a failing test or invariant to get green. If a test is wrong, say why and fix it explicitly.
- Small vertical commits (conventional commits). One concern per commit.
- No new dependency without checking: wheel/package available for the offline bundle, licence acceptable, pinned with hash. Record non-trivial choices as ADRs in `docs/adr/`.
- **Never fabricate:** control IDs, CVE numbers, benchmark figures, model accuracy, false-accept rates. Every number in UI, PDF or docs comes from code or test output. Unknown control ID → `TODO_VERIFY`, never a guess.
- If the spec is ambiguous or two sources conflict: apply the safest default from §16, log it in `docs/open-questions.md`, keep going. Do not stall.
- Type everything. `mypy --strict` on `api.py` and `domain/`. `ruff` clean.
- No network in tests. Model files load from local paths only.
- End every session with: what changed · tests run and results · exit-gate status · open questions.

---

# PART B — SPEC

## 6. Trust lifecycle and Trust Gate

### 6.1 Core objects

- **`MappingSpec`** (`baseline.mapping_spec`, pure): `vendor_id`, `dialect_fingerprint` (SHA-256 of the normalized token skeleton), `pattern` (ordered tokens: literal or typed slot `int|ip|cidr|ident|word|quoted|rest`), `target_setting_id`, `value_bindings` (reversible transforms only), `render_template`. Functions: `match(spec, line_bytes) -> Fragment | None`, `render(spec, fragment) -> bytes`. `Fragment` is a validated Pydantic model generated from the slot types.
- **`induce_spec(line_bytes, target_setting_id, vendor_id)`** (`mapping.domain`): deterministic tokenizer, no AI. The admin may retype slots.
- **`Mapping`** aggregate: id, vendor_id, spec, state, proposer model card, top-3 candidates (anchor id, phrase, cosine), admin actor, support-line refs (artifact SHA-256 + line no.), gate runs, evidence items, `supersedes`, timestamps, profile commit.
- **Support set** for a gate run: the admin-confirmed line plus every other line in the current upload batch that `match` accepts (cap 50).
- **Line provenance:** every normalized observation carries `DETERMINISTIC | CORROBORATED | PROVISIONAL`, a `line_ref` (artifact SHA-256, line no., byte span) and an optional `mapping_id`. Lines no mapping covers are `UNMAPPED`: counted in coverage, never dropped silently.

### 6.2 State machine (pure; implemented in `mapping.domain`; every row writes a ledger entry)

| From | Event | Guard | To | Effects |
|---|---|---|---|---|
| — | `LineUnrecognized` | — | Unmapped | Counted in coverage; grouped by `dialect_fingerprint` |
| Unmapped | `AnchorMatched` | proposer returned ≥ 1 candidate | Proposed | Store top-3 + cosine + proposer model card |
| Proposed | `AdminConfirmed` / `AdminCorrected` | actor role `admin`; target ∈ taxonomy | AdminReviewed | Induce spec; ledger |
| AdminReviewed | `GateFired` | verifier family ≠ proposer family | Gating (transient, same transaction) | Run all three checks |
| Gating | `GatePassed` | regen ∧ lexical ∧ second-model all PASS | **Provisional** | Profile commit |
| Gating | `GateFailed` | any check FAIL (FAIL dominates ERROR) | **Rejected** | Per-check verdicts in ledger |
| Gating | `GateErrored` | ≥ 1 ERROR and no FAIL | AdminReviewed | May re-fire; count re-fires |
| Provisional | `DecaySampled` / `EvidenceRecorded` | — | ReVerification | Re-run gate |
| ReVerification | `Corroborated` | gate re-pass ∧ ≥ 1 credited independent evidence (§6.5) | **Corroborated** | Profile commit |
| ReVerification | `ReGatePassed` | gate re-pass, no credited evidence | Provisional | Update `last_regated_at` |
| ReVerification | `ReGateErrored` | ERROR, no FAIL | Provisional | Retry next cycle |
| ReVerification | `ReGateFailed` | any FAIL | Demoted | **Alert raised**; excluded from both scores at once |
| Demoted | (automatic, same transaction) | — | Rejected | Ledger |
| Rejected | — | — | absorbing | Admin may create a NEW `Mapping` with `supersedes` = old id |

Corroborated mappings are not decay-sampled by default (assumption A3).

### 6.3 The three checks (`trustgate`)

All checks return `PASS | FAIL | ERROR` plus metrics and artifacts. Exceptions, timeouts, missing models and integrity failures are `ERROR`, never `PASS`.

1. **`RegenCheck`** — deterministic, no ML. For every support line `L`: `frag = match(spec, L)`; require `render(spec, frag) == L` byte for byte (line content; terminator compared separately) and `match(spec, render(spec, frag)) == frag`. PASS iff every support line round-trips. Artifact: per-line result, first differing offset, hex diff. Basis: Nakamura et al., arXiv:2511.17948 (round-trip engineering). **Proves well-formed only**; UI copy must say so.
2. **`LexicalCheck`** — BM25 (`rank_bm25.BM25Okapi`). Query: the line's tokens with numbers, IPs and values dropped. Corpus: one lexicon document per baseline setting (name, description, synonyms, control-table text). **The lexicon must never be built from the proposer's anchor phrases.** PASS iff the proposed target ranks ≤ `lexical.top_k` and its normalized score ≥ `lexical.min_score`. Artifact: ranked top-10 table.
3. **`SecondModelCheck`** — `VerifierPort.rank(line, candidates) -> scores`. Candidates: the proposed target plus N lexicon distractors chosen by the gate. PASS iff the proposed target is top-1 and its normalized score ≥ `second_model.min_score`. The verifier is a **different model family** from the proposer. Verifier choice is empirical (ADR-0004): evaluate at least two of `google/flan-t5-base` (T5), `cross-encoder/nli-deberta-v3-small` (DeBERTa), `Qwen/Qwen2.5-0.5B-Instruct` (Qwen) on the self-audit dev split; pick the lowest false-accept at an acceptable false-reject. CPU only, no sampling. Before bundling, verify each model id exists and check its revision and licence.

**Config:** `trustgate/data/gate_config.yaml` holds every threshold. All thresholds in this prompt are **placeholders** until calibrated on the dev split, then frozen. Its SHA-256 is recorded in every `GateReport`. Changing it means a new hash, an ADR and a fresh self-audit.

**`ModelCard`:** `{family, name, revision, weights_sha256, licence}`. `models/manifest.json` lists every bundled weight file. Verify hashes at startup (INV-17). The family guard runs at startup and again on every gate run.

**`GateReport`:** `gate_run_id`, `mapping_id`, `gate_config_hash`, model cards, per-check `{name, verdict, metrics, artifacts, checker_id, duration_ms}`, `outcome`. Persisted; shown in the UI evidence panel and the PDF appendix. Identical inputs give identical reports apart from timestamps and durations.

### 6.4 Corroboration and independence (INV-06)

Evidence item: `{id, mapping_id, class, actor_id | checker_id, input_fingerprint, payload_ref, created_at, weight (0|1), reason}`. `credit(evidence, history) -> (weight, reason)` is a pure function.

- Classes used at first pass (`ADMIN_REVIEW`, `GATE_REGEN`, `GATE_LEXICAL`, `GATE_SECOND_MODEL`) never corroborate.
- **`SECOND_REVIEWER`:** actor ≠ every actor already on this mapping; role `admin` or `reviewer`. The UI hides the first admin's choice until the second submits (blind review). Agreement → weight 1. Disagreement → weight 0, recorded, blocks upgrade until resolved.
- **`HELD_OUT_LINES`:** at least `held_out.min_lines` lines (placeholder 3) whose SHA-256 appears in no prior gate input for this mapping, taken from a config artifact other than the support artifacts. The full gate must re-pass on every one.
- **`SIGNED_PACK`** (T3): valid signature from a trusted peer key ≠ own key; peer not already credited.
- Dedupe key `(mapping_id, class, actor_or_checker_id, input_fingerprint)`. Same actor, same checker, same input, or a class already credited → weight 0. At most one credited item per class.
- Upgrade: credited items ≥ `corroboration.min_independent` (default 1) → Corroborated.

### 6.5 Decay and re-verification (T2)

- **Cycle** = one completed audit batch; also triggerable with `pramana decay-cycle` (assumption A4).
- Sample `max(1, ceil(0.05 × n_provisional))` Provisional mappings when `n_provisional > 0`. Seed = SHA-256 of the cycle id, recorded in the ledger, so the sample is reproducible.
- Re-run the full gate on each sampled mapping. Pass → back to Provisional (or Corroborated if credited evidence exists). Fail → Demoted → Rejected + alert.

### 6.6 Profiles (Git) and rollback (`profiles`)

- Bare repo `data/profiles.git`. Layout: `vendors/<vendor_id>/profile.json`, `vendors/<vendor_id>/mappings/<mapping_id>.json`. Commit per Provisional / Corroborated / Demoted / Rejected transition. Author = actor; message references the ledger sequence number. Library: `pygit2` (fallback GitPython or dulwich) behind `ProfileStorePort`; choose via ADR after checking offline wheel availability.
- Rollback = a new revert commit. Never rewrite history.
- **A mapping is usable in an audit only if it is a member of the profile HEAD tree AND its DB state is Provisional or Corroborated.** Rollback therefore never resurrects a Rejected or Demoted mapping (INV-01 survives rollback). On load, a HEAD member that is Rejected in the DB is excluded and raises an alert.
- DB and Git must never diverge silently: write DB and ledger first, then Git via an idempotent post-commit handler keyed by ledger sequence, plus a startup `profiles.reconcile()` and `pramana profiles verify`.

## 7. Scoring, triage, Fix-Impact, sandbox

### 7.1 Inputs and rules (`scoring`, pure)

`CheckOutcome {check_id, device_id, weight:int, status: PASS|FAIL|UNEVALUATED, trust: DETERMINISTIC|CORROBORATED|PROVISIONAL, mapping_ids}`

- Weights: **Critical 20 · High 10 · Medium 5 · Low 2.**
- A check's trust = the weakest link among the lines and mappings it rests on (`PROVISIONAL < CORROBORATED < DETERMINISTIC`).
- **Negative-evidence pass** (passes only because a line is absent): status is `UNEVALUATED` if any `UNMAPPED` line exists in the config scope where that line could appear. `UNEVALUATED` is excluded from every score and listed with its reason (assumption A7).

### 7.2 Formulas

Use `Fraction` or `Decimal`. Round half-up to one decimal at presentation only. Return numerator and denominator alongside every percentage.

- **Verified** = Σw(PASS ∧ trust ∈ {DET, CORR}) ÷ Σw(evaluated ∧ trust ∈ {DET, CORR}) × 100
- **Provisional-Inclusive** = Σw(PASS) ÷ Σw(evaluated) × 100
- **Provisional dependence** = Σw(evaluated ∧ trust = PROV) ÷ Σw(evaluated) × 100
- **Coverage** = classified lines ÷ non-blank, non-comment lines × 100. A separate figure, never folded into a score.
- Empty denominator → `null`, rendered "n/a". Never 0 or 100.
- Fleet aggregation sums numerators and denominators. Never average per-device percentages.

**Golden vector A** (commit as a test):

| Check | Weight | Result | Trust |
|---|---|---|---|
| C1 | 20 | PASS | DETERMINISTIC |
| C2 | 10 | FAIL | DETERMINISTIC |
| C3 | 5 | PASS | CORROBORATED |
| C4 | 10 | PASS | PROVISIONAL |
| C5 | 2 | FAIL | PROVISIONAL |

Verified = 25/35 → **71.4**. Provisional-Inclusive = 35/47 → **74.5**. Provisional dependence = 12/47 → **25.5**.

**Golden vector B (Fix-Impact):** Telnet 20 × 3.0 × 0.60 = **36.0**. Default SNMP community 20 × 2.5 × 0.20 = **10.0**. Telnet ranks first, 3.6× higher.

### 7.3 Fix-Impact queue (T2)

`Impact = SeverityWeight × ExploitabilityMultiplier × FleetPrevalence`. `FleetPrevalence` = devices failing ÷ devices evaluated for that check, in [0, 1]. Sort: impact desc, then severity desc, prevalence desc, `check_id` asc (deterministic). Each item shows trust badge, affected devices, blast-radius flag and the exact remediation diff per device.

Exploitability multipliers live in `compliance/data/exploitability.yaml` with a rationale per entry. Telnet 3.0 and default SNMP 2.5 come from the source. **Every other value is a proposal with `needs_review: true`.**

### 7.4 Simulation Sandbox (T2, `sandbox`)

`simulate(device_audit_id, check_id)`: build remediation edits from the compliance templates for that vendor → apply to an in-memory copy of the original bytes → call `pipeline.audit_config` with the same profile commit, model cards and thresholds → report before/after for **both** scores, resolved findings and **regressions** (newly failing checks). The stored artifact is never modified. No template for that vendor/check → `no_remediation_template` (text guidance only). UI label: "Verified Remediation Delta — measured by re-audit".

### 7.5 Blast-radius flag

Set on findings whose remediation touches session (VTY, console, SSH, transport, timeouts), ACL (VTY, management, interface) or AAA. Each check declares `blast_radius` rules as predicates over the baseline plus a note. Example: disabling telnet while SSH is absent → HIGH, "removes remote management access".

## 8. Compliance engine (`compliance`)

- Data-driven. `compliance/data/`: `checks/*.yaml`, `frameworks/{cis,nist,stig,iso}.yaml`, `exploitability.yaml`.
- **Check:** `id`, `title`, `severity`, `predicate` (declarative: `all_of | any_of | not | {setting, op, value}`; ops `eq ne lt gt in present absent`), `evidence_selector`, `remediation` per vendor (edits + rationale), `blast_radius`. Predicates are data, never code (R9).
- **Framework entry:** `check_id`, `control_id`, `title` (your own short paraphrase), `required_state`, `source`, `source_version`, `verified: false` until a human verifies it. UI and PDF tag unverified mappings. CIS and ISO text is licensed: store IDs and paraphrase only, never verbatim text.
- Starter ID hints (verify before marking `verified`): NIST SP 800-53 Rev.5 `AC-17`, `AC-12`, `IA-5`, `SC-8`, `CM-7`, `AU-2`, `AU-8`, `AU-12`. ISO/IEC 27001:2022 Annex A `A.8.5`, `A.8.9`, `A.8.15`, `A.8.20`, `A.8.21`. CIS and STIG IDs: leave `TODO_VERIFY` until sourced.

**Seed check catalog** (source severities; one implementation per vendor):

| Severity | Check |
|---|---|
| Critical (20) | Telnet enabled · Default SNMP community · Cleartext secrets |
| High (10) | Missing VTY ACL · No remote syslog · HTTP management active |
| Medium (5) | Inactivity timeout > 10 min · Plaintext service passwords |
| Low (2) | Missing logging timestamps · Finger service active |

**Cross-framework conflict detection (T2):** when two frameworks give the same check different `required_state`, surface both citations to the admin. Never silently pick one.

## 9. Parsing and proposer

### 9.1 `parsing` (Track 1)

- Hand-written line-state or recursive-descent grammars. No third-party parsing library. Every observation carries an exact line number and byte span.
- **Cisco IOS:** `!`-delimited, indentation-nested blocks; `no` negation prefix. **Juniper JunOS:** both curly-brace hierarchy and flat `set` form. **Palo Alto PAN-OS:** `set` CLI format (T1), XML export (T2). **FortiOS:** `config … edit … set … next … end` nesting.
- Each construct has a Pydantic AST node with `render()`. Property test per vendor: `render(parse(line)) == line`.
- **Vendor detection:** deterministic signature scoring. Ambiguous → return `AMBIGUOUS` and ask the admin. Never guess silently.
- **`Redactor`:** vendor-aware, masks secrets (INV-16). Used by logs, reports, packs and UI.
- Output: `NormalizedBaseline` observations (typed value, scope, provenance, `line_ref`) plus the list of `UnrecognizedLine`s. Blank lines and comments are counted as non-code.

### 9.2 `proposer` (Track 1)

- **Anchors:** `proposer/data/anchors/*.yaml`. Each anchor = a baseline setting id plus 3–10 phrases (vendor-neutral descriptions and example lines from different vendors). Embeddings are precomputed at build time into `anchors.npz` with a manifest carrying the model-card hash. Runtime loads local paths only (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`).
- **Model:** `sentence-transformers/all-MiniLM-L6-v2` class, CPU. Cosine top-3 → `Proposal {candidates[{setting_id, anchor_phrase, cosine}], model_card}`. Deterministic.
- **Fallback (T2):** if top-1 cosine < `τ_conf`, call Ollama `llama3.2:3b` with the redacted line plus the top-10 candidate settings. Temperature 0, fixed seed, JSON-schema output validated by Pydantic. The returned `setting_id` must exist in the taxonomy (reject hallucinated ids). Timeout 20 s. Any failure → return the embedding top-3 only. Check the Llama licence for government use.
- Seed the taxonomy with **≥ 60 settings across ≥ 10 areas** (management, AAA, SNMP, logging, NTP, banner, secrets, ACL, interface services, routing auth, …) so top-k ranks and top-3 anchors are meaningful.
- Proposals are generated eagerly for up to 200 unrecognized signatures per audit, grouped by `dialect_fingerprint`.

## 10. Reporting, signing, federation

### 10.1 Reporting (T1, Track 5)

- One Jinja2 template (autoescape ON) and one CSS file render both the on-screen preview (`GET /reports/{id}/preview`) and the PDF (WeasyPrint). One report definition, never two.
- Install WeasyPrint's native dependencies (Pango, Cairo, GDK-PixBuf) into the backend image at build time on the connected host.
- **Per device:**
  - Header: device, vendor, site, audit timestamp, tool version, profile commit, gate config hash.
  - Verified and Provisional-Inclusive **side by side**, plus provisional dependence and coverage. Trust legend.
  - Findings table: check, severity, trust badge, framework refs (unverified tag where applicable), exact config line (line number + redacted text), remediation diff, blast-radius note.
  - `UNEVALUATED` list with reasons.
  - **Appendix A:** evidence for every Provisional mapping the report relied on (top-3 anchors, cosines, regen diff, per-check verdicts).
  - **Appendix B:** trust-mechanism self-audit (rates with intervals, corpus hash, seed) and the named residual-risk statement (INV-15).
  - T2 adds Fix-Impact rank and measured remediation delta.
- `ReportData` is a canonical JSON object. Its SHA-256 prints in the footer.

### 10.2 Signing (T3; small, so do it first among T3 items)

- `crypto`: Ed25519 via `cryptography`. Keys generated offline with `pramana keys generate`. Private key mode `0600` under `data/keys/`, optional passphrase. `key_id` = SHA-256 fingerprint of the public key.
- Sign the **exact PDF bytes**. Ship `report.pdf` + `report.pdf.sig.json` `{alg, key_id, sha256, signature_b64, signed_at, tool_version}`. Footer prints the key fingerprint and the `ReportData` hash.
- Verify with `pramana verify-report <pdf> <sig> --pubkey <pem>` and an offline UI verify page. Flip one byte → FAIL.

### 10.3 Federated packs (T3; roadmap; seams only unless T1 and T2 are done)

- Pack = zip: `manifest.json` (schema version, site id, `exported_at`, per-file SHA-256) + `mappings/*.json`. Contents: dialect fingerprint, control mapping, approval metadata, sanitized exemplar lines. **Never raw configuration text.**
- Signature: Ed25519 over the RFC 8785 (JCS) canonical manifest. Import verifies the signature against a peer trust store (no trust-on-first-use; fingerprints compared out-of-band at the USB handoff), verifies every file hash, rejects schema mismatches, and is idempotent by pack id.
- **A pack is evidence, not authority.** Imported mappings enter as `Proposed` with `SIGNED_PACK` evidence attached and still pass the local gate. A valid pack for an existing local mapping is credited as evidence (§6.4).
- Other T3 seams: reserve `ledger` entry kinds for device-onboarding manifests and waiver expiry. Do not implement them.

## 11. Frontend (Tracks 4 and 5)

- React 18 + TypeScript + Vite + Tailwind. React Router, TanStack Query, React Flow for the lifecycle graph.
- **Generated client:** `pramana export-openapi` → `openapi.json` → `openapi-typescript` (+ `openapi-fetch`) → `frontend/src/api/schema.d.ts`. CI fails if the generated file is stale. Never hand-write API types.
- **Offline UI:** fonts self-hosted, no CDN, no analytics, no external images. nginx sends `Content-Security-Policy: default-src 'self'`.
- **Trust badges**, identical everywhere: DETERMINISTIC (navy), CORROBORATED (green), PROVISIONAL (amber), REJECTED / DEMOTED (red). Always a text label, never colour alone.

**Screens**

1. **Upload:** single file or ZIP, job progress, guard errors shown verbatim.
2. **Fleet dashboard / triage:** per-device two score cards side by side, provisional dependence, coverage, severity-sorted findings with blast-radius flag, site prevalence.
3. **Training Studio:** queue of unrecognized signatures. Confirm/correct screen: redacted raw line, top-3 anchors with phrases and cosine scores, target dropdown (taxonomy), slot editor, live regen diff. Submit shows the gate panel with three check verdicts and their artifacts.
4. **Mapping page:** React Flow state machine with current state highlighted, evidence ledger, per-check reports, blind second-reviewer action. **No override control on Rejected**, only "Re-propose from scratch".
5. **Self-audit:** false-accept and false-reject per stage and overall with intervals, corpus hash, seed, model cards, residual-risk statement.
6. **Fix-Impact + Sandbox (T2):** ranked queue, remediation diff, before/after of both scores, regressions.
7. **Reports:** preview, PDF download, (T3) verify.
8. **Ledger and alerts:** chain status, demotion alerts.
9. **Feature registry:** LIVE / PLANNED badge per feature, computed from the test-results file (INV-14).

Tests: Vitest + React Testing Library for components; Playwright for the demo path, running offline.

## 12. Security, offline operation, deployment

- **Uploads.** ZIP guards, all configurable (defaults are placeholders): max members, max total uncompressed bytes, max member bytes, max compression ratio. Stream extraction with counters. Reject absolute paths, `..`, symlinks, nested archives, duplicate names. Accept text only (reject NUL bytes). Cap line length and line count. Store original bytes content-addressed by SHA-256; never normalize stored bytes.
- **Parsing.** Per-file time budget. No catastrophic-backtracking regexes: use hand-written scanners; any regex must be linear-time and reviewed.
- **AuthN/Z.** Local accounts, Argon2id, HttpOnly + SameSite=Strict session cookies, CSRF token, login rate-limit. RBAC: `operator` (upload, audit), `admin` (confirm, correct), `reviewer` (second review), `auditor` (read-only). Every ledger entry carries `actor_id`.
- **Model integrity.** Verify `models/manifest.json` SHA-256s at startup (INV-17).
- **Supply chain.** Pin Python with hashes (`uv pip compile --generate-hashes` or pip-tools), npm lockfile with integrity, Docker images by digest. SBOM at bundle time (T2).
- **Compose.** Two networks: `core` (`internal: true`; backend, DB, Ollama, and nginx) and `edge` (nginx only). nginx is the only container that publishes a port, bound to the host address the operator chooses. Backend, DB and Ollama have no route out. `cap_drop: [ALL]`, `no-new-privileges`, non-root users, read-only root filesystem where possible, healthchecks. DB via `PRAMANA_DB_URL`: SQLite `data/pramana.db` (WAL) by default, PostgreSQL 15 in fleet mode. One SQLAlchemy 2.0 model layer + Alembic for both; run integration tests against both.
- **Offline bundle.** On the connected build host, `deploy/bundle/build_bundle.sh` builds images, runs `docker save` to tarballs, builds a wheelhouse (`pip download`), an npm cache and the model weights, and writes `MANIFEST.sha256`. On the air-gapped host, `deploy/bundle/install_offline.sh` verifies the manifest, runs `docker load`, `compose up`, a healthcheck, then `scripts/verify_offline.sh`. Ship pip and npm caches so the host can rebuild, but prefer prebuilt images. Use CPU-only PyTorch wheels; consider ONNX for the embedding model (ADR).
- **`verify_offline.sh`.** From inside the backend container: DNS lookups and TCP connects to public addresses must fail, app health must pass, a result file is written.
- **Secrets in configs (INV-16).** Redact before logging, before sending to Ollama, before rendering, before packing.

## 13. Testing and self-audit

Layout under `backend/tests/`: `unit/` (pure domain) · `property/` (Hypothesis) · `contract/` (OpenAPI snapshot, generated-client sync) · `architecture/` (import-linter, table ownership, forbidden calls) · `integration/` (DB, Git, models; SQLite and PostgreSQL) · `e2e/` (API-level demo path) · `selfaudit/`.

- **Hypothesis:** fixed seeds (`derandomize=True` or `@seed`), `database=None`. Properties:
  - parser round-trip per vendor;
  - scoring bounds and monotonicity (0–100; adding a passing PROVISIONAL check never changes Verified; with no PROVISIONAL checks Verified equals Provisional-Inclusive);
  - state machine: random event sequences never reach an illegal state; `Rejected` is absorbing;
  - ledger: flip any byte and verification fails;
  - `credit()` independence rules;
  - `Redactor` never leaks a secret.
- **Golden:** vectors A and B (§7); per-vendor fixture configs → expected findings with line numbers; PDF text-extraction snapshot.
- **No-egress fixture:** autouse, blocks `socket.connect` to non-loopback addresses and `getaddrinfo` (INV-11).
- **Benchmarks:** `pytest-benchmark` for parse, embed, gate and audit latency. Quote only measured numbers.

### Self-audit: `pramana selfaudit --seed N --per-anchor M`

1. **Ground truth:** `(line, setting)` pairs from the known-vendor fixtures, already proven by the deterministic parsers.
2. **Correct set:** M mutations per pair (renamed directives, reordered blocks, inserted cosmetic noise lines) with the true target kept. Run the full gate. Gate rejects → **false-reject**.
3. **Wrong-control set:** same lines, wrong target swapped in. Report two sub-sets **separately**: *random* wrong targets and *hard negatives* (nearest neighbours by BM25 and by cosine, sibling settings). Gate accepts → **false-accept**.
4. **Dev / test split.** Dev calibrates thresholds. Test is frozen and reported. Never tune on test.
5. **Report:** per-stage and overall false-accept and false-reject with counts, rates and 95 % Wilson intervals; corpus SHA-256; seed; gate config hash; model cards; and the rate at which a wrong control fooled **all three** checks (the named residual risk).
6. Output `selfaudit_report.json` + Markdown. The UI page and PDF appendix B read it.
7. `make predemo` re-runs it and fails if any false-accept point estimate is worse than the committed `selfaudit/baseline.json`.

## 14. Repo layout and tooling

```
pramana/
  CLAUDE.md                       # one line: @docs/MASTER_PROMPT.md
  Makefile
  docs/        MASTER_PROMPT.md · progress.md · open-questions.md · invariants.md · demo-script.md · adr/
  backend/
    pyproject.toml · alembic/ · import-linter config
    src/pramana/                  # module packages exactly as in §4
    tests/                        # unit property contract architecture integration e2e selfaudit
    fixtures/                     # configs/{cisco_ios,junos,panos,fortios}/ · unseen_lines/ · demo/wrong_control.json
  frontend/    src/{api,features,components}/ · vitest · playwright
  deploy/      compose.yaml · Dockerfile.backend · Dockerfile.frontend · nginx.conf · bundle/
  models/      manifest.json · weights (git-ignored or git-lfs)
  scripts/     check_inv_coverage.py · verify_offline.sh
  data/        (runtime; git-ignored)  ntro/ (NTRO dataset, if provided)
```

- **Tooling:** Python 3.11+, `uv` or pip-tools (hashes), ruff, mypy, pytest, hypothesis, pytest-benchmark, import-linter. Node LTS, Vite, Vitest, Playwright.
- **CLI `pramana`** (argparse or typer): `db upgrade`, `selfaudit`, `ledger verify`, `profiles verify`, `decay-cycle`, `export-openapi`, `keys generate`, `verify-report`, `pack export|import` (T3), `seed-demo`.
- **Makefile:** `setup`, `test`, `arch`, `inv`, `selfaudit`, `openapi`, `web`, `bundle`, `verify-offline`, `predemo` (= arch + inv + test + selfaudit + verify-offline).

## 15. Phased plan and exit gates

From Phase 2 the six tracks run in parallel. Publish `api.py` Protocols and fakes in Phases 0–1 so no track blocks another. Do not start a phase until the previous exit gate is green.

| Phase | Goal | Deliverables | Exit gate |
|---|---|---|---|
| **0 Scaffold and guardrails** | Boundaries exist before code does | Repo layout (§14); every module package with `api.py` stub + README; import-linter contracts; architecture tests; no-egress fixture; `check_inv_coverage.py` (warn-only until Phase 8); ADR-0001 modular monolith, ADR-0002 three-check gate, ADR-0003 Git profile store + DB consistency; `docs/invariants.md` (INV → test ids); Compose skeleton with `core` (`internal: true`) and `edge` networks | `make arch test` green on empty modules; dev stack healthy |
| **1 Walking skeleton (T1)** | One vertical slice, end to end | Cisco IOS upload → parse → 3 seed checks → two-number score (all DETERMINISTIC) → JSON API → minimal page; ports + fakes for gate and proposer | Golden vector A passes; Cisco fixture gives expected findings with line numbers; `openapi.json` exported and generated client compiles |
| **2 Parsers and catalog (T1)** | Four vendors, full seed catalog | JunOS, PAN-OS, FortiOS grammars; all 10 seed checks × 4 vendors; framework tables (unverified flags); `Redactor`; ZIP guards; fixtures | Per-vendor golden findings; Hypothesis round-trips green (fixed seed); ZIP-bomb tests green |
| **3 Trust lifecycle core (T1)** | The state machine and ledger, before real models | `ledger` + chain verify; `Mapping` state machine (pure) + repos + DB triggers; `induce_spec`; taxonomy ≥ 60 settings; `proposer` with MiniLM anchors; admin confirm/correct API; verifier + gate as **test doubles only** (in `tests/`, never wired in `bootstrap`) | INV-01 and INV-12 tests; state-machine property tests; unseen line returns top-3 + cosine |
| **4 Real Trust Gate (T1)** | The spine | `RegenCheck`, `LexicalCheck`, `SecondModelCheck` adapters; family guard; model-manifest verification; `GateReport`; `profiles` Git store + reconcile; pipeline resolves lines through profile mappings; `SECOND_REVIEWER` corroboration path | Demo beats via API: (a) Cisco → instant verdict; (b) unseen line → Provisional, two scores diverge, provisional dependence > 0; (c) well-formed wrong-control mapping → regen PASS, lexical and/or second-model FAIL → Rejected; (d) second reviewer → Corroborated, same-actor attempt gets weight 0. INV-02 to INV-06 tests |
| **5 Self-audit and calibration (T2, scheduled early)** | Measure the gate, then freeze it | Corpus generator; harness; dev/test split; threshold calibration; verifier ADR-0004; `selfaudit_report.json`; committed baseline | Same seed → identical report; `make selfaudit` green; thresholds frozen under a new config hash; under the frozen thresholds the demo wrong-control fixture is still Rejected and the demo correct mapping is still Provisional |
| **6 Admin UI (T1)** | Screens 1–5, 8, 9 (§11) | React Flow lifecycle; Training Studio; two-number cards; evidence panel; feature registry | Playwright demo path green against the offline backend |
| **7 Reporting (T1)** | Per-device PDF | Template + WeasyPrint; blast-radius notes; appendices A and B; residual-risk statement | PDF text snapshot; preview text equals PDF text |
| **8 Tier 2** | In order of demo value | Fix-Impact queue → Sandbox + Verified Remediation Delta → decay sampler + `HELD_OUT_LINES` evidence → Ollama fallback → cross-framework conflicts | Golden vector B; sandbox before/after golden; decay reproducible from seed; independence property tests |
| **9 Offline hardening and bundle** | Ship it | Compose hardening; bundle scripts; `verify_offline.sh`; demo seed; `docs/demo-script.md`; `make predemo`; INV coverage enforced | On a host with networking disabled: install from bundle, run the full demo path |
| **10 Tier 3 seams** | Only after Phase 9 | Ed25519 signed reports first; then federated packs; device manifest and waivers stay documented roadmap | Each item per §10, or it stays `PLANNED` and hidden from demo claims |

**Demo acceptance script** (`docs/demo-script.md`, rehearsed with the network cable unplugged):
1. Known Cisco config → instant verdict, both scores shown.
2. Unseen line → top-3 anchors + cosine → admin confirms → regen passes → Provisional; both scores diverge. Show elapsed time from unseen line to Provisional, computed from ledger timestamps (source claim: new-vendor onboarding in one guided session).
3. Deliberately wrong-control mapping → regen PASS, lexical / second-model reject → Rejected, no override control visible.
4. Self-audit page: measured false-accept and false-reject with intervals; residual risk read aloud.
5. (T2) Top Fix-Impact item → measured before/after delta.
6. (T3, only if built) Flip one byte of the PDF → verification fails.

## 16. Source conflicts, assumptions, open decisions

### Source conflicts (deck wins over `PRamana.md`)

| # | `PRamana.md` says | Deck says | Resolution |
|---|---|---|---|
| C1 | Gate = regen + embedding re-score (2 checks) | Gate = regen + lexical + second model of a different family (3 checks) | Use 3 checks. Re-scoring with the proposer's own embedding is self-grading and would violate INV-02. |
| C2 | Corroborated = second independent pass triggered by the decay sampler | Corroborated = new evidence class: 2nd reviewer, held-out lines, signed pack; same admin or checker = 0 | Use the deck. A decay re-gate counts only as `HELD_OUT_LINES` evidence when its input is disjoint. |
| C3 | Signed reports and federation are T3 roadmap, "does not run in the hackathon build" | Both appear in the pipeline and impact slides | Build seams, schedule last (Phase 10), label per INV-14. |
| C4 | Self-audit suite is T2 | Named as the mitigation for "trust mechanism unmeasured", re-run before every demo | Keep the T2 label, build early (Phase 5) because thresholds cannot be calibrated without it. |
| C5 | Explainable match evidence is T2 | Top-3 anchors + cosine + regen diff are core to the admin-confirm step | Put in T1. The API returns it anyway. |
| C6 | Track 6 lists an "optional live-pull path" | No live device credentials; network unplugged on stage | Excluded (INV-09). |

### Assumptions (safest defaults; confirm with the team)

- **A1** `Demoted` → `Rejected` is automatic in the same transaction; `Demoted` stays as a ledger state and raises an alert.
- **A2** A `Rejected` record is terminal. Re-proposal creates a new mapping id linked by `supersedes`.
- **A3** Only Provisional mappings are decay-sampled. The sources are silent on Corroborated.
- **A4** "Cycle" = one completed audit batch, plus manual trigger.
- **A5** `HELD_OUT_LINES` = at least 3 lines (placeholder), disjoint by SHA-256 from every prior gate input, from a different config artifact, all passing the full gate.
- **A6** Waivers are not implemented before T3, so no scoring rule for them exists yet.
- **A7** Negative-evidence passes become `UNEVALUATED` when unmapped lines exist in scope.
- **A8** Verifier default is chosen empirically (ADR-0004) among non-MiniLM, non-Llama families.
- **A9** All thresholds (`top_k`, `min_score`, `τ_conf`, `held_out.min_lines`, ZIP limits) are placeholders until calibrated or agreed.
- **A10** Gate `ERROR` (infrastructure) ≠ `FAIL` (substantive). `ERROR` never rejects and never passes.
- **A11** Exploitability multipliers other than Telnet 3.0 and default SNMP 2.5 are proposals flagged `needs_review`.
- **A12** Coverage and provisional dependence are reported next to the two scores, never blended into them.
- **A13** Fleet scores sum numerators and denominators; they do not average percentages.

### Human to-dos (an agent cannot do these)

- Open NTRO's attached dataset (the SIH26155 "Dataset" tag) **before Phase 2**. Put it under `data/ntro/` (git-ignored). Adapt fixtures and taxonomy to what it contains.
- Source real CIS and STIG control IDs from the official documents; review every `verified: false` entry; review every exploitability multiplier.
- Check licences: Llama 3.2 (Ollama fallback), each candidate verifier, CIS Benchmarks, ISO text.
- Confirm the submission deadline with your SPOC. Assign the six track owners.

## 17. Kickoff prompts (copy one per session)

- **Phase 0:** `Read docs/MASTER_PROMPT.md. Execute Phase 0. Scaffold every module in §4 with api.py stubs and READMEs, import-linter contracts, architecture tests, the no-egress fixture, ADR-0001 to 0003 and a Compose skeleton. Stop at the exit gate and report.`
- **Phase N (generic):** `Read docs/MASTER_PROMPT.md and docs/progress.md. Execute Phase N from §15, tests first. Respect §2 and §4. Stop at the exit gate. Report changes, test results, gate status and open questions.`
- **Track prompt:** `You own Track T (modules M) for Phase N. Work only inside your modules and their tests, through other modules' api.py. Use fakes for modules that are not ready. Stop when your part of the Phase N exit gate passes.`
- **Audit prompt (run any time):** `Audit the repo against §2 and §4 of docs/MASTER_PROMPT.md. List every invariant without a test, every architecture-rule violation, and every place a T2/T3 feature is presented as LIVE. Fix nothing; report only.`
