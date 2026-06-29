# GMNAP V7 / MathLineage — Master Cleanup, Gap-Closure & Capability Plan

*Consolidated 2026-06-28. Sources: the per-clause spec-conformance audit against
`docs/specs_v7_clean.yaml` (R40 workflow `wf_2937ee3f-eb7`, 5/8 areas + synthesis;
3 areas pending re-run) and the beyond-spec capability survey (`wf_5c3f6849-125`).
This is the canonical plan; supersedes scattered in-conversation plans.*

## 0. The two maintainer rules (apply to every item below)

- **Rule A — dormant spec feature ⇒ WIRE, never delete.** A non-running
  implementation of something the spec requires (env-gated, broken import, no
  caller) is a wire-up, not dead code.
- **Rule B — working + tested code BEYOND the spec ⇒ KEEP + DOCUMENT, never
  delete.** The spec is a floor, not a ceiling. Capability breadth is a feature
  (canonical example: ~33 authority fetchers vs the spec's 14). Reconcile docs
  to reflect reality rather than cutting code back to spec.
- **Only** genuine dead code, or a strictly-worse duplicate of a live path, is a
  delete candidate — and only after `grep` proves a live equivalent exists.

Status legend: `compliant` · `partial` · `dormant_impl_exists` (Rule A) ·
`beyond_spec_keep` (Rule B) · `dead_superseded_parallel` (delete candidate) ·
`missing` · `divergent`.

Audit tally (5 conformance areas): **30 compliant · 14 partial · 19 dormant ·
8 divergent · 4 missing · 4 dead**. Headline: *structurally complete but
contractually loose* — a wire-up-and-reconcile job, not a rewrite.

---

## 1. DONE (this round)

- **R40.1 — 6 broken bonus authority fetchers fixed + hardened.**
  `tier1/{acm,ieee,pubmed,springer,viaf,wiley}.py` passed invalid kwargs to
  `FetchResult` (`source=/query=/error=`) — `TypeError` on every call. `pubmed`
  and `viaf` *additionally* passed invalid `AuthorityData` kwargs **and** were
  missing the abstract `parse_response` method (uninstantiable abstract
  classes). All fixed at root; mapping refactored into shared `_to_authority_data`
  helpers. Guarded by three regression layers in
  `tests/unit/test_authority_fetchstatus.py`: (1) AST check that every
  `FetchResult`/`AuthorityData` construction under `src/authorities/` uses only
  real dataclass fields; (2) `FetchStatus`-member validity; (3) abstract-class
  concreteness across the whole roster. **6/6 pass**, black/isort/ruff clean.
  *(This closes conformance §4.8 and the divergent half of §9.)*

---

## 2. BEYOND-SPEC CAPABILITIES TO KEEP (Rule B) — answers "what useful extras do we have?"

Survey `wf_5c3f6849-125` (8 agents) found **41 beyond-spec capabilities**, each
works/tested-verified with file:line citations: **27 keep+document (works +
tested), 11 add-tests-then-keep, 1 fix-then-keep, 2 investigate, 1 delete.**
The same "tested overage is a feature" pattern as the 33-vs-14 authority roster
applies across the whole codebase. Full synthesis cited inline below.

### 2a. KEEP + DOCUMENT — works + tested today (documentation only, no code work)

| Capability | Where | Tested by |
|---|---|---|
| **Python SDK** — sync `Client` + async `AsyncClient` (query/lineage/process/suggest/health/ready), token/hashcash auth, idempotent-only retry (never doubles POSTs) | `src/sdk/client.py:114,320` | `tests/unit/test_sdk.py` (22/22) |
| **Client-side hashcash PoW minting** (auto-attaches `X-Hashcash`, solves the free-tier gate w/o paid token) | `src/sdk/client.py:48,80` | `test_sdk.py:26,45,52,284` |
| **`/api/v1/suggest` corrections endpoint + SDK `.suggest()`** (traversal-hardened disk queue) | `src/api/server.py:986`, `client.py:277` | `test_api_security.py:480,500` |
| **Name-based lineage lookup** (`name:Hilbert, David` instead of GlobalID) | `src/api/server.py:792`, `cli/gmnap.py:655` | `test_api_server.py:136,151` |
| **CLI commands beyond the 2 spec'd** (sources/regions/validate/process; traversal/size/binary guards) | `src/cli/gmnap.py:336,407,421,246` | `test_cli_hardening.py` |
| **Bidirectional lineage + Graphviz DOT** (ancestors\|descendants; svg honestly 422, not silent downgrade) | `server.py:699`, `cli/gmnap.py:185,215,723` | `test_api_server.py:130,146` |
| **Central injection validator `SecurityValidator`** (7 injection families, live per-entry gate) | `src/core/security_validator.py`; wired `streaming_pipeline_v7.py:130`, `manager_optimized.py:3251,3818` | `test_security_validator.py` (32) |
| **Region-level `SecurityFilter`** (script/SQL/LDAP/command scrub, diacritic-preserving) | `src/regions/security.py:29`; wired `base.py:129,149` | yes |
| **Hashcash mint + verify** (full classic-hashcash; backs free-tier gate) | `src/ops/hashcash.py:60`, `sdk/client.py:48` | `tests/security/test_hashcash.py` |
| **GDPR decade-masking + ShadowNode dedupe-hash** (cohort-count, ShadowHash) — *runnable + tested, but not yet wired into live pipeline (see §3.1)* | `src/core/gdpr.py:97,177,207,238` | `test_gdpr.py` |
| **PAV isotonic confidence calibration** (the real held-out ECE=0.039; env-gated, identity no-op when unset) | `src/regions/calibration.py:97`; `manager_optimized.py:3882` | `test_calibration.py`, `test_pav_fitter.py` |
| **Deterministic stratified 80/20 benchmark split** (675 train / 168 test, SEED=42) | `src/regions/benchmark_split.py:53` | `test_benchmark_split.py` |
| **Persistent fastText CLI worker + same-group gate** (~60× vs per-query subprocess) | `manager_optimized.py:2970,4005`; `ft_name_classifier.ftz` | `test_fasttext_cli_worker.py` (gate end-to-end only) |
| **Per-region YAML override system** (live for A2) | `RegionSpec.load_yaml_config`; `config/regions/a2.yaml` | `test_region_yaml_overrides.py` |
| **Bundled 39,892-mathematician enrichment corpus + `GenealogyLookup`** | `src/core/genealogy_lookup.py:155`; `data/genealogy_enrichment.json` | `test_genealogy_lookup.py` |
| **Name resolution** (diacritic/particle/alias/hyphen/short-form: Erdős↔Erdos, von Neumann↔Neumann…von) | `src/core/genealogy_lookup.py:26-272` | `test_genealogy_lookup.py:33` |
| **Bidirectional advisor-chain traversal** (cycle-guarded, depth-bounded, name endpoints) | `src/core/genealogy_lookup.py:306` | `test_genealogy_lookup.py:132` |
| **Memgraph/neo4j live-graph lineage + depth-clamp + DOT** (graceful None-fallback; backs `/readyz`) | `src/genealogy/query.py` | `test_genealogy_query.py` (mocked) |
| **500 golden + 10,724 Wikidata fixtures** | `tests/fixtures/golden_mathematicians.json`, `data/wikidata_mathematicians.json` | golden gate |
| **6 revived tier-1 fetchers** (ACM/IEEE/PubMed/Springer/VIAF/Wiley — R40.1) | `src/authorities/tier1/*` | `test_authority_fetchstatus.py` |
| **Coverage gate w/ line/branch floors** (`--cov-fail-under=20` + line≥22% / branch≥18%) | `.github/workflows/ci.yml`, `pyproject.toml:200` | CI |
| **Per-PR perf-regression gate** (drives real `process_batch`, fails >25% below round-30 floors) | `tools/perf_regression_check.py:70`; ci.yml perf-gate | `test_performance_regression_harness.py` |
| **Three-track adjudicated 843-benchmark eval** (geo ≥99% gate / name-origin / ambiguity) | `test_benchmark_evaluation.py` | self |
| **500-entry golden accuracy gate** (≥99% over 500 names, ≥30 regions) | `test_golden_dataset.py:26` | self |
| **Hypothesis property suite** (>10 Unicode invariants vs spec's 2) | `tests/property/test_unicode_properties.py:137` | CI |
| **Cache thread-safety + per-file locks + bad-JSON quarantine** (corrupt → `bad_json/`, not deleted) | `src/utils/cache.py:77,180,221,508` | `test_cache_system.py:276,381` |

### 2b. KEEP, BUT ADD TESTS FIRST — works, untested (ordered by value/effort)

1. **`AsyncBatchAggregator` streaming path — URGENT.** This *is* the >100k /
   ~2763-per-sec 1M production path, yet has **no valid coverage**: its would-be
   tests import `StreamingPipeline`/`StreamingConfig` from
   `src.core.streaming_pipeline`, which only defines `StreamingPipelineAdapter`
   (stale imports that never touch the live aggregator). `src/core/async_batch_agg.py:24`,
   wired `pipeline_v7.py:34,463`. **Add** `tests/unit/test_async_batch_agg.py`:
   order-preservation over shuffled 1000-entry add_batch, coalescing respects
   min/target/max + max_latency_ms, 100k+1 processes all under a memory ceiling.
2. **Repo-invariant audit battery** (`tools/audit_repo.py`, 18 checks A–J, CI
   `audit-repo`) — no test of the auditor itself. Add `test_audit_repo.py`.
3. **CI perf-regression tool internals** (`tools/perf_regression_check.py`
   `_make_entries`/`_BASELINES` unverified). Add `test_perf_regression_check.py`.
4. **`SQLiteAnalytics` in-memory stage-5 fallback** — the live stage-5 path in
   any no-DuckDB env (incl. this one), zero tests. `src/analytics/sqlite_analytics.py:19`,
   wired `pipeline_v7.py:47,914`. Add `test_sqlite_analytics.py`.
5. **DBLP + arXiv fetchers** — construct/parse cleanly, only the AST guard covers
   them. Add behavioral `parse_response` fixture tests.
6. **K8s manifests + production Helm chart** (`deploy/k8s/*.yaml`,
   `deploy/helm/gmnap/`) — parse clean, no `helm lint`/`kubeconform` ran. Add a
   CI validation step.
7. **docker-compose dev service + healthchecks/graceful-shutdown** — add a YAML-shape assertion.
8. **ResearchGate fetcher** (mock-mode by design) — assert synthetic AuthorityData + document the mock caveat.
9. **Genealogy build pipeline + Wikidata SPARQL fetcher** — pin the `_normalize_key`
   parity contract (`build_...:443` vs runtime) so build/runtime key formats can't drift.

### 2c. FIX, THEN KEEP

- **Tier-2 template-engine stub roster** (cnki/jstor/ethos/j_stage/narcis/scielo/
  tel/cern_cds) — **broken**: `src/authorities/tier2/__init__.py:11` imports a
  non-existent `google_scholar.py` (`ModuleNotFoundError`); the roster guard
  silently skips them (`test_authority_fetchstatus.py` `except: continue`). Fix
  the `__init__` import, make stubs importable, add to the concreteness guard.
  *(If no near-term plan for these 8 sources, maintainer may downgrade to delete;
  the template engine itself is reusable, so fix-the-import is the conservative move.)*

---

## 3. ACTIVATE DORMANT (Rule A) — spec features that exist but don't run (by value/effort)

**2.0 PREREQUISITE — make optional imports import-safe (S/low — do FIRST).**
`src/graph/graph_loader.py:5` top-level `from neo4j import GraphDatabase`
(`ModuleNotFoundError`) cascades through `stage6_graph_consistency`,
`stage8_global_validate`, and the genealogy block → stages 5/6/8 dormant paths
can't be wired. Same pattern: `jinja2` (`stage10_report.py`), `paramiko`
(`archive_sftp.py`). Fix with lazy/optional try-except flags (like Memgraph
elsewhere). **Keystone — unblocks 3.1, 3.3, 3.6.**

- **3.1 GDPR pipeline (§10) — HIGHEST VALUE.** `src/core/gdpr.py` complete +
  tested, **zero live callers**. `gdpr_pipeline` already chains
  mark→scrub→mask→shadow. Wire into `pipeline_v7.py` after enrichment, before
  stage-9 write; add the `--drop-personal` CLI path in `gmnap.py:_run_pipeline`.
  Closes 5 §10 items at once. M/medium (gate behind flag + golden test).
- **3.2 Mode-aware 8-gate checker (§7) — HIGHEST VALUE, "blocking gates" theme.**
  `src/quality/gates.py QualityGateChecker.check_all` is complete + mode-aware +
  tested, **zero callers**; live path runs 3-gate `FastQualityGates` fed `[]`.
  Route the final decision through it on accumulated entries and **raise on
  fail** (reuse `strict_gates.py QualityGateBlockedException`). Ship advisory in
  QUICK / blocking in FULL/EXTREME so CI stays green. L/medium.
- **3.3 Stage 5 edges + stage 6 cycle rejection + stage 8 round-trip/coherence
  (§5).** After 2.0: call `stage5_edge_extract.extract_edges_from_entries`
  unconditionally; wire `memgraph_client.detect_cycles(max_depth=3)` with a
  NetworkX fallback; wire `stage8_global_validate.global_validate` (Dice
  round-trip + coherence). Prefer JSON-Schema `src/validation/schema.py` over the
  70-line hand-rolled validator. M each/medium.
- **3.4 Diaspora split-output reaches the entry (§2/§3).** `RegionDetectionResult`
  computes `geo_region/name_region/group_region/conflict/resolution_level/
  candidates`; stage-2 copies only `region_code/confidence/method`. Copy the six
  fields in all three detect paths. S/low — pure plumbing.
- **3.5 Diaspora overlay application (§3).** `config/diaspora.yaml` loads but is
  never read; `_detect_by_diaspora` is a `return None` stub. Implement ISO-8601
  range matching + override + non-overlap validation. M/medium.
- **3.6 Stage 0 config/licence/DOI checks + Stage 10 DOI/archive/ATTRIBUTION
  (§5/§10).** Wire `stage0_config.py`; wire `datacite_builder.build_draft_doi`,
  `archive_sftp.push_directory_sftp` (OFFLINE-guarded), `attribution.generate_
  attribution_text` → `ATTRIBUTION.txt`. Needs 2.0. S + L/medium.
- **3.7 MathSciNet/Scopus/Dimensions key-gated live calls (§9 tier 2).** All fall
  through to `_offline_skip` even with creds. Route via `_call_canonical_fetcher`
  when key present (Scopus needs a fetcher BUILT). M (Scopus L)/low.
- **3.8 Per-source daily quota enforcement (§9).** `QuotaManager`
  (`base.py:218-440`) fully implemented, **not wired**. Gate
  `_call_canonical_fetcher` through `acquire_quota`. L/low.

---

## 4. FIX DIVERGENT — impl contradicts the spec

1. **Stage 1b is regex, spec wants GPT-4o-mini (§0/§5).** Build a GPT-4o-mini
   PDF extractor (page cap + cost cap) feeding the existing schema-validate +
   SHA-256 cache; keep regex as the OFFLINE fallback (gated); fix/delete the
   broken `AIIntelligence` import in `stage_1b_llm_extract.py`. *(needs LLM
   provider — Phase 6)*
2. **Stage 11 doesn't re-run the pipeline (§5/§7 idempotent_diff_bytes_max 0).**
   Today it serializes the same entries twice. Re-run `process_batch` on the
   original input (re-entrancy guard) and diff snapshots, asserting 0 bytes.
3. **Quality-gate enforcement non-blocking (§7).** `pipeline_v7.py:904-909` warns
   then `pass`. Resolved by 3.2.
4. **Gate config mode-blind (§7).** `FastQualityGates` hardcodes QUICK
   thresholds. Resolved by 3.2.
5. **`iso_territories` contradicts §2 (`regions/base.py:961`).** LT→C9 (spec A3),
   HU→A2 (spec B2), SS in both C3 and F2. Fix code or amend spec via §14.
6. **Google Scholar env-var mismatch (§10).** CLI sets `GMNAP_FORCE_EXTREME`;
   `extreme_adapters.py:11` reads un-prefixed `FORCE_EXTREME`. Fix the name.
7. **ShortFormClusters field-name divergence (§5 stage 7).** Live emits flat
   per-entry `ShortForms`; spec wants cross-entry `ShortFormClusters`. Extend or
   confirm. Low.
8. **~~6 bonus fetchers raise TypeError~~ — DONE in R40.1 (§1 above).**

---

## 5. BUILD MISSING — spec features with no implementation

**Core conformance:**
- **§2a subnational overlay map** (IN-SOUTH→D2, CH-FR→A2, …) — no impl. Build
  `SUBNATIONAL_OVERLAY` consulted in `_detect_geo` before country fallback.
  M/medium.
- **§10 licence_tiers** (public_cc0 / redistributable_cc-by / non-redistributable)
  — zero hits. Build a per-source→tier classifier; `attribution.py` SPDX map is
  the input. M/medium.
- **F1 (French), F4 (Portuguese) particle stubs** — placeholder `pass`. Port A2's
  `french_particles` / G1's Portuguese logic + tests. *Dormant stubs to finish.*
  M/low each.

**Roadmap / future:** GS encrypted cache; F2/H1/E1 partial finishes (reuse A1
`_generate_collapsed_variant`, G1 diacritics); §4 rule-34 reciprocal round-trip
promoted to a collected property test.

---

## 6. DELETE DEAD — conservative, live equivalent proven (run LAST)

| File | Proof of supersession | Action |
|---|---|---|
| `src/authorities/enricher.py` | parallel orchestrator; live = `manager_tier01.enrich_all`; consumers only build artifact + 1 perf test | DELETE after repointing the perf test |
| `src/authorities/tier1/zbmath.py` | duplicate of wired `tier0/zbmath.py` | DELETE after grep confirms no importer |
| `src/authorities/tier0/orcid.py` | older generic ORCID; live = `tier0/orcid_etd`; only consumer is dead `enricher.py` | DELETE with enricher, or INVESTIGATE if generic-ORCID planned |
| `src/pipeline/stage2_detect_region.py` | skeleton; live = `manager_optimized.detect_region` | DELETE after confirming no importer |
| `charts/gmnap/` (duplicate, incomplete Helm chart) | strictly-worse duplicate of `deploy/helm/gmnap/` (6 templates incl. memgraph/ingress/secret vs this one's 2); `deploy/README.md` points only at `deploy/helm/`; zero CI/test refs | **DELETE** (the one clean delete the survey found) |

> The enricher/zbmath/orcid deletes have a **precondition**: migrate their two
> consumers (`tests/performance/test_v7_performance_benchmark.py:36`,
> `tests/authority/test_manager_offline.py`) onto the live `manager_tier01`
> stack first — deleting today breaks those tests. The survey marks them
> *investigate* for exactly this reason; do them in the final cleanup PR.

**Investigate, do NOT delete:**
- **`src/core/encryption.py` (AES-256/RSA) — BROKEN.** `import` raises
  `ModuleNotFoundError: cryptography` (the dep is in no requirements file), no
  live caller, no round-trip test (`tests/paranoid/...:291` labels it "NOT
  TESTED"). §10 mentions only an "encrypted cache" for the GoogleScholar opt-in.
  **Decision needed:** if encryption-at-rest is a real requirement → add the
  `cryptography` dep + a caller + round-trip test (fix_then_keep); else delete.
  Do **not** delete unilaterally — it claims §10/legal-relevant coverage.
- `stage_1b_llm_extract.py` (spec still wants the LLM path);
  `EnhancedQualityGates`/`data_quality.py`/`gates_rolling.py`/`gates_streaming.py`/
  `strict_gates.py` — keep until 3.2 lands, then prune only the genuinely
  redundant. Consolidate-then-prune, never prune-first.

---

## 7. DOCUMENTATION RECONCILIATION (make docs match reality)

**Docs understate what we built (most important — Rule B):**
- **Authority roster.** `DATA_SOURCES.md` + CLAUDE.md list only the spec 14;
  ~33 fetchers exist with **zero** mention of the bonus sources. After R40.1,
  update both to list the FULL roster tagged: **working** (HAL+9 spec),
  **statically-OK** (dblp/arxiv), **fixed+tested** (acm/ieee/pubmed/springer/
  viaf/wiley), **template-stub** (cnki/jstor/ethos/j_stage/narcis/scielo/tel/
  cern_cds).
- **Beyond-spec capabilities (§2 of this plan)** — add a "Capabilities beyond
  the spec" section to CLAUDE.md/README: SDK, calibration, encryption, security
  validator, K8s/Helm, perf gate, enrichment corpus, property/fuzz suites.

**Docs overstate what we built:**
- CLAUDE.md implies GDPR masking/scrubbing, genealogy edges, cycle rejection,
  round-trip validation, DOI/archive/ATTRIBUTION, and "8 blocking mode-aware
  gates" all run in the live pipeline. They are dormant/advisory. Add
  "(dormant — not wired in default run)" qualifiers and DO-NOT-Claim entries
  until 3.1/3.2/3.3/3.6 land.
- Note stage-1b is an OFFLINE regex *fallback*; the §0 GPT-4o-mini path is not
  built.

**Beyond-spec capabilities → add to docs (from §2 survey):**
- **CLAUDE.md** — new "Python SDK" subsection (`src/sdk/`); Security section: dual
  injection layer (`SecurityValidator` + region `SecurityFilter`) + hashcash
  mint/verify + SDK client-side auto-mint; CLI/API: all 7 commands + `/suggest`
  + `--direction` + `dot` are beyond §11's 2 examples (svg honestly 422);
  Performance: name `AsyncBatchAggregator` as the real 1M streaming mechanism
  **and flag it currently untested** until §2b.1 lands; Testing: coverage floors,
  three-track 843 harness, repo-invariant audit battery, browser smoke harness,
  >10-invariant property suite, golden gate, benchmark-split + PAV pair.
- **DATA_SOURCES.md** (create) — authority table with the 6 revived fetchers +
  DBLP/arXiv/ResearchGate(mock) tagged beyond-§9; tier-2 template roster as
  broken-pending-fix; bundled corpora with counts (genealogy 39,892 / wikidata
  10,724 / golden 500 / name-origin benchmark 843) + provenance.
- **README** — SDK quickstart, `/api/v1/suggest`, `name:`-prefix lineage,
  `--direction`/`--format dot`, a Deployment pointer to `deploy/k8s/` +
  `deploy/helm/gmnap/` (drop any `charts/gmnap` reference once deleted).
- Preserve every honesty caveat inline: AsyncBatchAggregator untested, fastText
  gate end-to-end-only, Memgraph live path container-unverified, cache suite
  needs `zstandard`.

**Spec-side (only via §14 change_control):** iso_territories LT/HU/SS — decide
per-territory whether code or spec is authoritative.

---

## 8. SEQUENCED ROADMAP

Each phase is independently shippable + CI-greenable; earlier de-risks later.

- **Phase 1 — Import-safety + cheap wins** *(pure code).* 2.0 keystone import-fix;
  3.4 diaspora split-output; 3.6 stage-0 wire; §4.7 ShortFormClusters; §4.5
  iso_territories LT. **+ consolidate the 3 K8s/Helm copies (§2).**
- **Phase 2 — Make gates real + wire GDPR** *(pure code).* 3.2 blocking gates
  (mode-gated); 3.1 GDPR + `--drop-personal`; §4.2 stage-11 real re-run.
- **Phase 3 — Genealogy graph + validation depth** *(NetworkX fallback; Memgraph
  optional).* 3.3 stage-5/6/8.
- **Phase 4 — Ops/archive + authority hardening + DOC RECONCILIATION** *(some
  infra).* 3.6 DOI/SFTP/ATTRIBUTION; 3.8 QuotaManager; ~~6-fetcher fix~~ DONE;
  add per-fetcher test coverage for dblp/arxiv/template-stubs; **§7 doc
  reconciliation (full roster + beyond-spec section)**; 3.7 tier-2 key-gating.
- **Phase 5 — Subnational + diaspora-overlay + missing builds** *(pure code).*
  §2a overlay; 3.5 diaspora application; §10 licence_tiers; F1/F4 stubs.
- **Phase 6 — LLM extraction + roadmap + DELETE-DEAD pass** *(needs LLM
  provider).* §4.1 GPT-4o-mini stage-1b; GS encrypted cache + env-var fix;
  rule-34 property test; F2/H1/E1; then the §6 delete pass LAST.

**Central files:** `src/core/pipeline_v7.py`, `src/core/gdpr.py`,
`src/quality/gates.py`, `src/graph/graph_loader.py` +
`src/pipeline/stage6_graph_consistency.py` (Phase-1 keystone),
`src/regions/manager_optimized.py`, `src/authority/manager_tier01.py` +
`src/authorities/tier1/*.py`, `DATA_SOURCES.md` + `CLAUDE.md`.

---

## 9. OPEN ITEMS (finalize this plan)

- [x] Fill §2 from beyond-spec survey `wf_5c3f6849-125` — **DONE** (41
      capabilities; 27 keep / 11 add-tests / 1 fix / 2 investigate / 1 delete).
- [ ] Re-run conformance for the 3 rate-limited areas (data-model,
      ops-deploy-tooling, runtime-doi-archive) and fold their requirements in
      (GlobalID 110-vs-128-bit, Variant-Synthesised 7 types, make-target breakage
      `pipeline_v6`, Memgraph 2.12-vs-2.22 drift, streaming_chunk_size 8000,
      cost_cap 120 CHF, runtime SLAs).

## 10. EXECUTION ORDER (merged conformance + beyond-spec sequencing)

The survey's 4-step beyond-spec sequencing interleaves with the §8 conformance
phases:
- **Doc-only PR first** (zero code risk, CI-green, the maintainer's headline
  goal): all of §2a + the §7 reconciliation.
- **Close critical test gaps** next: §2b.1 `AsyncBatchAggregator` (the blind
  headline-perf path — highest priority), then audit battery, perf-tool
  internals, `SQLiteAnalytics`, build-key parity.
- **Roster + infra hardening**: §2b.5–9 (DBLP/arXiv/ResearchGate tests, helm
  lint/kubeconform CI step, compose-shape assertion) + §2c (unbreak tier-2
  template package).
- **Cleanup PR (last)**: §6 — delete `charts/gmnap`; then migrate the 2 tests
  off the dead `src/authorities/` orchestration layer and delete it; make the
  encryption keep-or-cut call. Keep deletion debates out of the earlier PRs so
  they never block the doc + coverage wins.
- These run **alongside** §8 Phases 1–6 (the dormant-wire/divergent-fix
  conformance work), which is the larger track.

---

## 11. WHOLE-PROJECT REFACTORING, DOC & ORG CLEANUP (R41)

Driven by two verified audits (2026-06-28): a **doc + file-org** audit
(`wf_b26fd4d3`) and a **code-architecture** audit (`wf_e96a4711`). Both are
behavior-preserving and test-green; full per-finding output in the run
transcripts. Scope chosen: **Moderate** (organize + consolidate + dead-code +
worst god-file splits; no big-bang rewrite). Two maintainer rules (§0) still
bind: nothing useful is deleted; only grep-proven-dead or strictly-worse
duplicates go.

**Baseline finding (important):** CI gates an explicit ~100-file allowlist
(`ci.yml:157+`, mostly `tests/unit/`). Several non-allowlisted dirs
(`tests/performance`, `hardcore`, `paranoid`) carry **pre-existing** collection
errors — a deleted `src.regions.manager`, a ghost `src.core.pipeline_v6`, a
missing `import pytest`. These are rot to triage in the test-org step, not
refactor regressions. Validate every refactor step against the CI allowlist
(the real green), not the full collection.

### 11.1 — DONE (committed + verified this session, 8 commits `05f3a28`..`05ccb21`)
- **`.gitignore` closed** — `out/` (573 MB), `output/`, `work/`, `snapshots/`,
  `coverage.xml`, `cache_thread_*`, `ultracheck/ultrafix_*.json`, root `archive/`,
  `config/*.bin`, db WAL no longer pollute `git status` (a dozen+ → 0).
- **15 broken `src.regions.manager` test imports repointed** to `manager_optimized`.
- **8 empty placeholder packages deleted** + **dead `src/common/`** (0 importers).
- **Dead `src/authorities/tier1/zbmath.py` removed** (dup of wired `tier0/zbmath`).
- **21 tracked junk files `git rm`'d** (`Makefile.bak`, 9 root debug scripts,
  `realistic_test_results_*.json`, `all_processors.txt`, `has_security.txt`,
  dumps) + generated dirs `cache_thread_0/` + `cache_security_test/`.
- **26 doc-accuracy fixes applied** — the hard `ARCHITECTURE.md` stage-1b ERROR
  fixed, stage-12 row added, README 6→8 endpoints, stale `pipeline_v7.py:328`
  comment, deep-dive reference repointed off the v6 doc.
- **Obsolete docs archived → `docs/archive/2026-06/`** (git mv, history preserved):
  10 root snapshots + 6 `docs/` status files + the `docs/sessions/` tree. **Root
  now holds only the 8 canonical docs.**
- **3 Helm charts → 1 canonical `deploy/helm/gmnap`** (removed 2 dup copies).
- **`e4_korea` de-vendored** — 51 files of `.github/.githooks/locks/audit/
  baselines` removed; processor + `resources/` intact, Korean detection verified.
- Bogus `postgresql:`/`sqlite:` dirs removed (one held a fake-credential filename).
- All of the above: representative CI tests green + the 20-check pre-commit
  invariant battery passes on every commit.

### 11.2 — TIER 1 — ✅ COMPLETE (12 commits, `05f3a28`..`a1fb91e`)
Beyond §11.1: removed tracked scratch dirs (`analysis/`, `test_results/` [stale
dup of `tests/performance/`], `debug_tools/`, `genealogy-phase2/`), dead root
`gmnap/` + `src/gmnap/` stubs; moved 137 dev scripts out of the `src/` package
(`e4_korea/scripts` → `tools/korean_tuning/`, `genealogy_expansion/scripts` →
`tools/genealogy_scripts/`) — **`src/` now ships only package code (0 scripts
under `src/*/scripts/`)**. Kept `Dockerfile.korea` (documented in a README).

### 11.2b — V6 TEST MIGRATION (distinct follow-up, contained)
~19 non-CI test files (`tests/{performance,hardcore,paranoid,security}`) import
the deleted `src.core.pipeline_v6.GMNAPPipeline`. They are **contained** — outside
the CI allowlist and excluded from default `pytest` by `conftest.py`
`collect_ignore_glob` — so they break nothing today. Migrating them to the
`src.core.pipeline_v7.V7Pipeline` API (or retiring the genuinely obsolete ones) is
a separate test-modernization task; some carry valuable logic (injection/fuzzing/
chaos/unicode) worth porting, not deleting. Same root cause as the broken
`make quick/full/extreme` targets (also reference `pipeline_v6`).

### 11.3 — TIER 2 structural consolidation (medium, import-touching; shim→migrate→drop)
- Merge `src/authority` → `src/authorities` (10 importers; re-export shim keeps green).
- Consolidate `src/core/{quality_gates,stage11_gate}.py` into `src/quality/`.
- Dedupe the 6 stage pairs (`stage3/4/5/7/9/11` each have two files) — one pair per PR.
- Migrate the 1 perf-test off `enricher.py`/`orcid.py`, the 5 v7 tests off
  `stage2_detect_region.py`, then delete those (NOT deletable today — live test importers).

### 11.4 — TIER 3 god-file splits (higher risk, incremental, facade-preserving)
Safety net per split: 843-benchmark + 500-golden (0 detection regressions) +
perf gate (±15%) + full allowlist.
- `manager_optimized.py` (6851) → `src/regions/detection/{scorer,fasttext_worker,
  result,region_manager}.py`; **move the `@lru_cache` `_wb`/`_score_priority_rules`
  scorer first and isolated**, perf gate immediately (it's the 2763/s unlock).
- `pipeline_v7.py` (1916, 5 classes) → `src/core/pipeline/{aggregator,metrics,
  gates,orchestrator}.py`.
- `server.py` (1087) and `security_validator.py` (1021) → DEFER (API contract /
  security-sensitive; do last, full suites as gate).

### 11.5 — Needs maintainer confirmation before running
Mass deletes (e4_korea cruft, empty-dir batch — done), the `src/authority`
package rename, the canonical Helm path, and any touch to `security_validator.py`.
Root `archive/` (1,270 untracked entries) is gitignored, not deleted — confirm
disposable.
