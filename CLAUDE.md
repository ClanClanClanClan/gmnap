# GMNAP v7 / MathLineage — Current Development Status
*Last Updated: 2026-07-06*

## 🎯 System State (Honest Assessment)

**Pipeline**: 12-stage pipeline (stages 0–8 async, 9–11 sync) — all stages wired and executing
**Regional Coverage**: 37/37 regions fully implemented (100%), 38 processor files
**Region Detection**: Split geo/name-origin architecture with three-tier suffix system, fastText CLI tiebreaker, same-group gate. Expert-validated as production-ready.
**Security**: Injection attack blocking validated
**Performance**: **RETRACTED and corrected in R54.** The former headline
("1 M in 362 s / 2 763-per-s, streaming path via `AsyncBatchAggregator`")
was FALSE: that path was a no-op — it fed 16-entry microbatches into a fast
path that skipped region detection and the whole batch-global tail, so the
benchmark measured a dict-copy loop, not the pipeline (proven: forcing the
old streaming path yielded DetectedRegion 0/30; the real path gives 30/30).
The streaming detour and the lossy fast path are removed. Real CPU
parallelism (`_process_batch_parallel`, a process pool) replaces them. Honest
measured numbers (8-core Apple-silicon laptop, OFFLINE, real names, clean
output dir): **serial 4 k = 184/s, 10 k = 233/s; parallel 4 k = 268/s,
10 k = 348/s** (~1.5× from parallelism, Amdahl-capped by the batch-global
tail). Region coverage 100 %; serial and parallel output byte-identical at
10 k. **1 M is now MEASURED (R56): 1 000 000 synthetic+CC entries in
19.6 min (849/s), 100.00 % region coverage verified; CC-less real-name
1 M projects ~75 min from the measured full-real-set anchor (221/s at
39 891).** Full detail in `docs/perf_characterization.md`.
**Schema Validation**: v2.0 schema; configurable strict mode (advisory/quarantine/reject)
**Authority Enrichment**: V7 tier orchestrator (`src/authorities/manager_tier01.py`) delegates to canonical fetchers in `src/authorities/tierN/` when `OFFLINE=0`. **7** sources have real, WORKING HTTP code (OpenAlex, Crossref, ORCID_ETD, zbMATH, Wikidata_P184, HAL, and GND — the last rewritten natively in R66 after being structurally dead). **Crossref_Thesis is DEAD** (returns a bare record, not a FetchResult, so every call resolves to hit:False; and the orchestrator passes it a NAME where it expects a DOI). **OAI_University is NOT IMPLEMENTED** — OAI-PMH is per-repository and no endpoint registry exists. (Until R66 all three were documented '✅ WORKING'; two failed before opening a socket.) 2 gated behind API keys (Scopus, Dimensions); 1 deferred for institutional access (ProQuest); 1 deferred for ToS (GoogleScholar). MathSciNet stub awaits AMS subscription
**Region Config**: `RegionSpec.load_yaml_config()` is the per-region YAML extension point, cached in `_YAML_CACHE`. It is now LIVE: `config/regions/a2.yaml` exists and `A2_WesternEurope.__init__` consumes it (merging extra Germanic/Romance surname particles into its hardcoded defaults) — the first processor to actually apply a YAML override. Other regions still fall back to hardcoded defaults until a `config/regions/<code>.yaml` is added and the processor wired to read it (see A2 as the pattern). Covered by `tests/unit/test_region_yaml_overrides.py`
**API Server**: FastAPI server with 8 endpoints (/healthz, /readyz, /api/v1/query, /api/v1/lineage, /api/v1/process, /api/v1/suggest, /metrics, /)
**CLI**: full 7-command CLI (`query`, `lineage`, `process`, `sources`, `regions`, `validate`, `serve`) in `src/cli/gmnap.py`, wired to the `gmnap` console entry point via `gmnap = "src.cli.gmnap:cli"` in `pyproject.toml`'s `[project.scripts]`. (Earlier docs claimed the 7-command CLI was "NOT wired to the main entry point" and that only `serve`/`version` were exposed — that is stale; `pip install -e .` puts all seven subcommands behind `gmnap`.)
**Diaspora Detection**: Implemented — split geo_region vs name_region with conflict flag
**Testing**: ~2,376 tests collected across `tests/unit/` + 4 newly-triaged dirs (authority, cjk, db, v7) + memgraph e2e + F3 region tests. Coverage gate at `--cov-fail-under=20` with explicit floors at line ≥ 22 % / branch ≥ 18 % (current measured 23.93 % / 19.41 %). 843-entry adjudicated benchmark with deterministic 80/20 train/test split (`src/regions/benchmark_split.py`)
**Test Fixtures**: 500 golden dataset + 843 name-origin benchmark + 10,724 Wikidata mathematicians

---

## ✅ What Actually Works

### Pipeline (12 stages)
All stages execute in sequence with real code:
- Stage 0: Config/credential validation
- Stage 1: Unicode normalisation (NFC→NFKD→fold→NFC)
- Stage 1b: ETD/thesis extraction — **wired as an OPT-IN** (`V7Pipeline._stage_1b_llm_extract`, called once at the top of `process_batch` before chunking / parallel fan-out so it can add rows without breaking the per-chunk 1:1 contract). Off by default; enable with `GMNAP_ENABLE_LLM_EXTRACT=1` (or `config['pipeline']['enable_llm_extraction']`). It routes through the deterministic regex extractor `src/llm/stage1b_llmextract_etd.extract_from_text` (NOT the old `LLMExtractETDStage` class, which is non-importable — it imports a non-existent `AIIntelligence`/`ExtractionError`), so it stays idempotent with no live LLM. Extracted records carry no GlobalID; stage 1 assigns them canonical SHA-256 ids. Covered by `tests/v7/test_stage1b_etd_extract.py`.
- Stage 2: Region detection (split geo/name-origin, three-tier suffixes, fastText CLI, same-group gate)
- Stage 3: Region hooks (clean→augment→validate→order_key per region)
- Stage 4: Authority enrichment via `manager_tier01.enrich_all` → `_call_canonical_fetcher` → `src/authorities/tierN/X.Fetcher.fetch()`. **7** sources with working HTTP (see the table below; Crossref_Thesis and OAI_University are dead). NOTE: nothing from stage 4 reaches the shipped `data/genealogy_enrichment.json`, which is built solely by `tools/build_genealogy_enrichment.py` from static harvests — and `enrich_by_tiers` merges only `_sources` and advisor NAMES back onto an entry, discarding the birth/death/thesis fields it computed. Claims that stage 4 populates DegreeDate / AffiliationTimeline / NameEvents are NOT backed by code. Each `_fetch_*` shim wraps the live call in `retry_with_backoff` (2 retries × 0.5 s exp backoff) and caches the response on disk by SHA-256 of the canonical query payload
- Stage 5: Collision analytics (DuckDB + in-memory fallback)
- Stage 6: Graph consistency (Bayesian coherence, optional Memgraph)
- Stage 7: Short-form tagging (initials clustering)
- Stage 8: Schema validation (v2.0, configurable: advisory/quarantine/reject)
- Stage 9: Write & Diff (YAML snapshots, SQL/Cypher changelogs)
- Stage 10-11: Report generation (DOI draft, SFTP archive, ATTRIBUTION.txt), idempotency check

### API Server (`src/api/server.py`)
- FastAPI with rate limiting (60/min free, 10K/min paid Bearer)
- `GET /healthz`, `GET /readyz`, `GET /metrics` (Prometheus)
- `GET /api/v1/query?name=...` — name lookup
- `GET /api/v1/lineage/{id}?depth=3` — genealogy
- `POST /api/v1/process` — batch processing
- Start with: `gmnap serve --port 8080`

### Region Processors (37 regions, 240-450 lines each)
All regions have full `clean()`, `augment()`, `validate()`, `order_key()`:
- A1-A5, B1-B3, C1-C9, D1-D5, E1-E7, F1-F4, G1, H1, R0, Z0
- YAML override files: `config/regions/a2.yaml` exists and is
  consumed by `A2_WesternEurope.__init__` (the loader is now LIVE,
  not dormant — A2 merges extra particles from it). The other 36
  regions still run on hardcoded `__init__` defaults until a
  `config/regions/<code>.yaml` is added AND that processor is wired
  to read it (copy A2's pattern: call `self.load_yaml_config()`
  after the defaults and merge). (Earlier docs claimed "37/37 YAML
  files in `config/regions/`"; that was aspirational — see the
  "YAML Config" section below for the real state.)
- C1 processor loads `config/script_switch.yaml` for Kazakh/Uzbek reform schedules
- Region overlay map (spec §2a) wired for sub-national detection (R55 —
  earlier docs claimed this was wired; it was not. `REGION_OVERLAY_MAP`
  in `src/regions/base.py` + `_infer_geo` now resolve sub-national codes
  in CountryCodes: `IN-WB`→D3, `LK-TA`→D2, `RU-NC`→C9, … taking
  precedence over the bare CC. `tests/unit/test_region_overlay_map.py`
  pins the full 10-entry spec contract)
- Diaspora overlay APPLIED (R49): era-scoped CC→region rules from
  `config/diaspora.yaml` drive the geo axis (e.g. TH pre-2015 → E6,
  2016- → A1); detection cache key is era-aware (includes BirthYear)
- Stage 2 copies the split axes onto every record (R47): GeoRegion /
  NameRegion / GroupRegion / ResolutionLevel / RegionCandidates +
  RegionConflict (the diaspora flag — Tao/AU → geo A1, name E1, True)
- GenealogyRelation edges extracted every batch + stage-6 cycle
  rejection (self-loop / mutual advisorship dropped, counted into the
  genealogy_edge_conflict gate) (R48)
- ATTRIBUTION.txt (SPDX per source) written by stage 10 every run (R48)

### Quality Gates (8 gates) — ENFORCED, mode-aware (R47, completed R55)
All 8 V7 quality gates implemented with mode-specific thresholds — and since
R47 they ENFORCE: QUICK is advisory (warn + complete); FULL/EXTREME BLOCK
(`QualityGateBlockedException`) on measured-gate failures against the real
accumulated entries. Unmeasured gates (e.g. graph coherence on a batch with
no advisor relations) are reported as skipped, never spuriously failed.
Results on `pipeline.spec_gate_results`; kill-switch `GMNAP_GATES_ADVISORY=1`.

R55 note: until R55 only 7 of the 8 gates were actually recorded —
`warm_cache_runtime_per_1M_min` (the performance gate, ironically the one
that would have flagged the retracted fake 1M claim) had a fully-tested
`check_runtime()` with zero callers. It is now recorded every run: measured
when the batch is ≥500 entries AND took the same execution path a 1M run
would (serial sub-threshold runs can't honestly project pooled-1M runtime);
otherwise reported unmeasured with the projection still visible.
`tests/v7/test_spec_gates_blocking.py::test_all_eight_spec_gates_recorded`
pins the full set.

### GDPR Compliance — LIVE in the pipeline (R47)
`gdpr_pipeline` runs on every batch after enrichment, before the stage-9
write (kill-switch `GMNAP_DISABLE_GDPR=1`):
- GDPR_DATA field marking, birth-year decade-masking (cohort < 5)
- ShadowNode conversion — the CLI `--drop-personal` flag is honored
  end-to-end via `GMNAP_DROP_PERSONAL=1`
- Source scrubbing (GoogleScholar, ProQuest, CNKI) across `_sources`,
  `AuthorityIDs`, and the legacy `AuthoritySources` dict shape

### Cache System
- Zstandard compression, 60-day TTL, 50GB max, LRU eviction
- Thread-safe, per-file locks, bad JSON quarantine

---

## 🔴 Known Limitations (Be Honest About These)

### Authority Enrichment: 9 of 14 Sources Have Real HTTP Code

V7's tier orchestrator (`src/authorities/manager_tier01.py`) holds the
`_fetch_*` shims; the real per-source HTTP code lives in the
canonical fetchers under `src/authorities/tier0/`, `tier1/`, and
`tier2/` (subclasses of `AuthorityFetcher` with an `async def fetch
(query: str) -> FetchResult`). Each shim:

  1. Checks the on-disk cache (`./cache/authority/`, zlib-compressed
     JSON, keyed by SHA-256 of the canonical query payload).
  2. If `OFFLINE=1`, short-circuits to `{hit: False}`.
  3. Otherwise calls `_call_canonical_fetcher(...)`, which lazily
     imports the right Fetcher class, instantiates it with empty
     config, and `await`s `fetch(name)` wrapped in
     `retry_with_backoff(max_retries=2, base_delay=0.5)`.
  4. Translates the returned `FetchResult` (success/not-found/parse-
     error/etc.) into the tier orchestrator's flat dict shape and
     caches the result.

Sources covered:

| Source | Tier | Canonical Fetcher | Status |
|--------|------|-------------------|--------|
| OpenAlex | 0 | tier0/openalex.OpenAlexFetcher | ✅ WORKING (90 % hit, 63 % institution match on curated 30) |
| Crossref | 0 | tier0/crossref.CrossrefFetcher | ✅ WORKING (100 % hit, 30 % institution match) |
| ORCID_ETD | 0 | tier0/orcid_etd.ORCIDETDFetcher | ✅ WORKING via OpenAlex name→ORCID resolve (13 % hit — caps at "registered ORCID exists") |
| Crossref_Thesis | 0 | tier0/crossref_thesis.CrossrefThesisFetcher | 🔴 DEAD — returns a bare record (always hit:False); also passed a name where it wants a DOI |
| zbMATH_Open | 0 | tier0/zbmath.ZbMATHFetcher | ✅ WORKING |
| Wikidata_P184 | 1 | inline aiohttp+SPARQL in `_fetch_wikidata_p184` | ✅ WORKING (100 % hit + 96.7 % BirthYear ±1 via P569) |
| GND | 1 | tier1/gnd.GNDFetcher | ✅ WORKING (R66 native lobid rewrite). Use `fetch_by_gnd_id` (Wikidata P227) — the NAME search is low precision: measured wrong-person on 2 of 3 root nodes |
| HAL | 1 | tier1/hal.HALFetcher | ✅ WORKING |
| OAI_University | 1 | tier1/oai_university.OAIUniversityFetcher | 🔴 NOT IMPLEMENTED — no repository endpoint registry (OAI-PMH is per-repository) |
| MathSciNet | 2 | (no canonical fetcher) | ⚠️ STUB (needs AMS subscription) |
| Scopus | 2 | (gated stub in manager_tier01) | ⚠️ Requires `SCOPUS_API_KEY` |
| Dimensions | 2 | (gated stub in manager_tier01) | ⚠️ Requires `DIMENSIONS_API_KEY` |
| ProQuest | 3 | (deferred stub) | 🔴 Institutional proxy needed |
| GoogleScholar | 3 | (deferred stub) | 🔴 ToS — opt-in only |

**Live measurement (2026-05-01, OFFLINE=0, curated 30)**:
`docs/authority_quality.md` records the most recent end-to-end run.
Headline numbers: any-source hit rate **100 %**, OpenAlex **90 %**
(27/30) with **63 % institution match** (17/27), Crossref **100 %**
(30/30) with 30 % institution match (9/30), ORCID_ETD **13.3 %**
(4/30 — only living mathematicians registered with ORCID),
Wikidata_P184 **100 %** (30/30) with **BirthYear ±1 accuracy 96.7 %**
(29/30). The previous "BirthYear is n/a end-to-end" gap was closed
by extending the Wikidata SPARQL to pull P569 (date of birth)
alongside P184 (advisor). Re-run with `OFFLINE=0 make eval-authority`.

**CRITICAL**: `OFFLINE=1` is the default. Set `OFFLINE=0` for full
enrichment. The tier-0 stubs short-circuit to OFFLINE-skip *before*
the cache check is meaningful, so OFFLINE-mode is a no-op even if
a stale cache exists from an earlier live run.

The 13 dead files that used to live in the old singular `src/authority/`
(`manager.py` and 9 `*_adapter.py` plus 3 helpers) were removed in the
2026-04-27 audit pass. In R42 the two survivors (`manager_tier01.py` and
`common.py`) were merged into the canonical plural package as
`src/authorities/manager_tier01.py` and `src/authorities/common.py`, so the
confusing singular-vs-plural split is gone — all authority code now lives
under `src/authorities/`.

### YAML Config: live for A2, defaults elsewhere
`RegionSpec.load_yaml_config()` reads `config/regions/<lowercase_code>.yaml`
and caches the result in the module-level `_YAML_CACHE`. Tests verify
the loader (`tests/unit/test_region_processors.py::TestYAMLConfigLoader`).

`config/regions/a2.yaml` exists and `A2_WesternEurope.__init__`
consumes it (the first live per-region override — see the Region
Config section above). The other 36 regions fall back to the
hardcoded defaults in their processors' `__init__` until a YAML is
added AND the processor is wired to read it (copy A2's pattern).

The previous "ensure_yaml_loaded() / _apply_yaml_overrides()"
auto-merge machinery was removed in the 2026-04-27 audit because it
had no production caller. Reinstating it would require both the
YAMLs and a hook in each processor's pre-call path.

### Performance (Measured 2026-07-06, R54, 8-core Apple-silicon, OFFLINE)

**The former "1 M in 362 s / 2 763-per-s" claim was FALSE and is
retracted.** It measured a no-op: the pre-R54 ">100 k streaming"
branch (`AsyncBatchAggregator` / `StreamingPipelineAdapter`) fed
16-entry microbatches serially into a fast path that emitted entries
with **no region detection, no enrichment, no GDPR, no writes** — a
dict-copy loop. Proof: forcing that path yielded `DetectedRegion`
**0/30**; the real path gives **30/30**. R54 removed the detour and
the lossy 6-25-entry fast path; every batch size now runs the real
stages.

Numbers below are honest, measured, and reproducible on a clean
`output/` dir (the changelog DB persists across runs — an 800 MB
stale DB inflates stage 9, so wipe `output/` before benchmarking).
Real names sample from `data/genealogy_enrichment.json`.

| Path | N | Throughput | Region coverage |
|---|---|---|---|
| `process_batch` serial (`GMNAP_NO_PARALLEL=1`), real | 4 k | 184 / s | 4000/4000 |
| `process_batch` serial, real | 10 k | 233 / s | 10000/10000 |
| `process_batch` parallel (process pool), real | 4 k | 268 / s | 4000/4000 |
| `process_batch` parallel, real | 10 k | 348 / s | 10000/10000 |
| `process_batch` parallel, real (full set, R56) | 39 891 | 221 / s | 100 % |
| **`process_batch` parallel, synthetic + CC (R56) — MEASURED 1 M** | **1 000 000** | **849 / s (19.6 min)** | **1 000 000/1 000 000** |

Serial and parallel output are **byte-identical** at 10 k (verified;
`tests/v7/test_parallel_path.py`).

**1 M IS NOW MEASURED (R56, 2026-07-07): 1 000 000 entries in 19.6 min
(849/s), RSS peak 10.3 GB on a 24 GB machine, output 1.4 GB, region
coverage verified 100.00 % by querying all 1 M rows in the changelog
DB.** The synthetic workload carries CountryCodes, so the geo branch
resolves via the CC fast path — cheaper per entry than CC-less real
names (221/s at 39.9 k, the full real dataset; a real-name 1 M-scale
run projects to ~75 min from that anchor — that one number is still a
projection, labeled as such). The spec §7 warm-cache gate PASSES at
measured 1 M (19.6 ≤ 35 min QUICK). Memory scales with batch size
(results are held in memory): budget ~10 GB per 1 M rows or chunk the
caller's batches on smaller machines.

Getting to a completable 1 M took a measurement campaign (R56) that
found and fixed four latent scale defects no test had ever exercised:
stage-5's row-wise DuckDB load (6 h at 1 M → ~2 s via CSV+read_csv,
370× measured), stage-6's O(n²) eager `.index()` default (days at 1 M
→ 0.5 s at 200 k), stage-9's monolithic multi-GB string builds
(streamed; HTML diff capped at `GMNAP_HTML_DIFF_MAX_ROWS`), and the
stage-11 re-run clobbering the main run's output artifacts
(`tests/v7/test_stage11_no_clobber.py`).

Where the time goes (real names, per-entry vs tail):
- **Stage 2 region detection** dominates per-entry cost (~6 ms/name)
  — this is the actual product work and is what the process pool
  parallelizes.
- The batch-global tail (stages 5 collision, 9 write, 10 report, 11
  idempotency) is serial in the parent, ~8-9 s at 4 k. R54 fixed the
  stage-9 DuckDB changelog (was 2 single-row `execute()`s per entry —
  ~7.5 ms/entry; now batched `executemany` in one transaction, ~5×).
- `ShortFormClusters` is capped at 64 gids/cluster
  (`GMNAP_SHORTFORM_CLUSTER_CAP`) to bound the O(k²) storage a
  shared short form otherwise creates (pathological synthetic input
  hit 100 KB/entry pre-cap).

Knobs: `GMNAP_NO_PARALLEL=1` (force serial),
`GMNAP_PARALLEL_THRESHOLD` (default 20000 — batches ≥ this use the
pool), `GMNAP_PARALLEL_WORKERS` (default cpu_count-1).

Reproduce:
```bash
rm -rf output/   # stale changelog DB inflates stage 9
PYTHONPATH=. python3 tools/run_benchmark.py --sizes 1000,10000 --real-names
```

Live authority enrichment (OFFLINE=0) is slower because tier-0 APIs
rate-limit. The round-28 `@functools.lru_cache` fix on
`manager_optimized._wb()` (regex-recompile hot loop) remains in
place and is real; it is unrelated to the retracted streaming claim.

---

## 📊 Region Detection (Expert-Validated, Production-Ready)

Architecture: split geo/name-origin branches, hierarchical selective classification.
- **Geo branch**: CC → ROR → DOI (100% accurate when CC provided)
- **Name-origin branch**: surname exact → CJK hybrid → 3-tier scorer → fastText CLI (same-group gated) → R0
- **Output**: `region_code`, `geo_region`, `name_region`, `group_region`, `resolution_level`, `candidates`, `conflict`

### Detection KPIs (843-entry adjudicated benchmark)
*(R58-era adjudication snapshot. R59.3–R59.5 changes were A/B-gated per
corpus: on the 843 the deltas are abstention→correct conversions plus one
wrong→abstention kill (Grušas) — 0 new wrong. Current held-out numbers
live in docs/calibration.md R59.5.)*

**The ≥95 % leaf-precision floor is now ENFORCED IN CI (R72).**
`tests/unit/test_benchmark_evaluation.py:162`. Until R72 it was
local-only: the gitignored fastText model (101 MB) was absent on the
runner, so the assertion `pytest.skip`-ed and no CI run ever evaluated
it. R72 builds the model in CI from the committed corpus
(`data/ml_training/ft_name_training_clean.txt`, 13 427 lines; the build
is byte-deterministic at `thread=1`, R59.5), and the test now
`pytest.fail`s instead of skipping when `CI` is set — a missing model on
a runner is a broken build step, not a reduced-capability environment.
R72 also deleted the fixture's CI down-sample to 100 entries: of those
100, only ~14 emitted a leaf, so a "≥95 %" floor on n=14 admitted
exactly one value (14/14) and duly failed at 13/14 = 92.9 % the first
time a model was present. The gate now measures the full 843.

What the gate actually constrains, measured on a fresh `make model`
build at R72: **144/150 = 96.0 % leaf precision at 34.5 % coverage**
(150 of 435 high-confidence entries emit a non-R0 leaf; group-level
150/152 = 98.7 %). Read it as *precision with abstention*: of the
answers the system is willing to give, 96 % are right. It says nothing
about the 285 high-confidence entries it declines to label. "96 %
precise at a third of coverage" is the honest phrasing; "96 % accurate"
is not. Whole file: ~45 s against its 600 s ceiling.
| Metric | Value | Notes |
|--------|-------|-------|
| MGP ground truth (15 names, no CC) | 15/15 = 100% | All via surname exact or fastText |
| CC-based geo accuracy | 216/216 = 100% | All territory mappings correct |
| Adjudicated leaf precision (523 entries) | 482/482 = 100% | Zero wrong emitted leaves *(in-sample on full 843; held-out test-set numbers in `docs/calibration.md`)* |
| Adjudicated coverage | 482/523 = 92.2% | 41 honest R0 abstentions |
| Adjudicated group-or-better | 523/523 = 100% | |
| Full 843 vs geo labels (informational) | 56% | NOT a name-origin KPI — citizenship ≠ name-origin |
| Classifier errors (genuine) | ~50/843 = 6% | Soviet suffixes, historical boundaries |
| Abstention rate | 235/843 = 28% | Coverage ceiling for name-only classification |

### Calibration KPIs (held-out test set, `src/regions/benchmark_split.py`)
Re-fit in R59.5 on the CURRENT (post-retrain) system:
| Metric | Value | Notes |
|--------|-------|-------|
| Raw ECE (test set) | 0.166 | before calibration |
| Calibrated ECE (held-out) | **0.048** | PAV fit on 675 train; evaluated on 168 test (56 emissions — abstention rose with the R59 precision-first retirements) |
| Brier (raw / calibrated) | 0.204 / 0.182 | |
| 5-fold CV ECE on train | 0.012 | within-train variance estimate |

The headline ECE = **0.048** is the honest out-of-sample number for the
current system ("0.039" belonged to the R58-era system; "ECE = 0.0009"
was measured-on-train and artefactually small). `tools/calibration.py`
now preserves the manual history sections in `docs/calibration.md`
across re-fits (R59.5 — a plain regeneration used to clobber the R58+
audit trail). See `docs/calibration.md` for the reliability diagrams.

### Key Constants
- SIGNATURE_SUFFIXES: 33 (fire leaf at 2.5). R59.4 added dimension B:
  Greek idis/iadis→B3 (exclusion trio davidis/aidis/naidis applied to
  BOTH the STRONG rule and the pre-existing bare '-is' medium rule,
  which was emitting wrong B3@0.75 on Lithuanian 'Aidis'), Persian
  nezhad→C2, Icelandic dottir(+raw dóttir)→A3 (ola- prefix carve-out);
  and fixed the live -sson precision bug — 12 verified non-Nordic -sson
  bearers claimed via surname_exact YAML (a1/a2/b2/g1 — first g1.yaml),
  frasson/masson/wasson abstain via curated scorer exclusion. Pins:
  tests/unit/test_suffix_dimension_b.py. R59.3 added the guarded
  Turkic/Balkan seven (maz/mez/oglu/escu/eanu/ovic/evic): -maz/-mez need
  len≥6 + consonant stem (Hispanic -ez/-az class excluded, 'gormaz'
  curated out); bare ASCII -oglu needs Turkic corroboration (ı/ş/ğ/ö/ü/ç
  or a C1 STRONG given) because 'Papasoglu' is adjudicated Greek;
  -escu/-eanu→B2, ASCII -ovic/-evic→B2 (raw ović/ević dedupe-guarded).
  A/B-gated: 843 benchmark + 456 pilot + 450 held-out — deltas are
  abstention→correct only (Moisescu, Iosifescu, Cerrahoğlu, Novaković),
  0 new wrong. Pins: tests/unit/test_signature_suffixes_turkic_balkan.py
- MEDIUM_SUFFIXES_TO_LEAF: 12 (fire group at 1.2, leaf at +1.0 if
  corroborated; R59.5 added raw-only 'ičius'→C9 — folded 'icius' would
  collide with the Fabricius class)
- MEDIUM_SUFFIXES_TO_GROUP: 4 (bare -ski/-sky/-ou/-is → group only; the
  bare '-is' rule carries the R59.4 davidis/aidis/naidis exclusion trio)
- REGION_GROUPS: 23 groups, 34 leaves
- Raw tokenizer (R59.5): scorer `_WORD` uses the full Unicode letter
  class. The old Latin-1 class split tokens at č/ć/š/ž/ő/ū (U+0100+),
  silently killing every raw-diacritic rule for those marks (the
  'ović'/'ević' raw suffixes, the -ovic dedupe guard, the Łacinka
  '-ovič' abstention — all documented-dead-now-live).
- ft_name_classifier.ftz: ~100MB quantized model, retrained in R59.5 on
  the DE-BIASED committed corpus
  `data/ml_training/ft_name_training_clean.txt` (13,427 lines; derived
  drop-only by `scripts/ml/clean_ft_corpus.py` from the retired
  geo-labeled original — R59 forensics proved the old labels were
  OpenAlex affiliation countries, not etymologies, with the A1 class
  62% contaminated by sampled audit). **Gitignored — NOT bundled.** A
  fresh clone rebuilds it via `make model`
  (`scripts/ml/build_name_classifier.py`); `make setup` does this
  automatically. The build is BYTE-DETERMINISTIC (thread=1, verified
  md5-identical consecutive builds) and hard-fails if known
  contamination reappears (cetin/hazra→A1). Without it, region
  detection runs rules-only with a loud warning (R54).
- Same-group gate: fastText can only refine within an anchored group, never
  cross groups — and NEVER emits without an anchor (R58: the raw
  ft_only_high_conf promotion was removed after adjudicated measurement
  showed 67-81% precision at every threshold; see docs/calibration.md R58
  and tools/ft_threshold_sweep.py). R59.5 closed the one remaining
  cross-group hole: anchorless multi-group orthographic 'permitted' sets
  (š/č/ž → {SLAVIC, BALTIC}) no longer license leaves — the retrained
  model produced the measured counterexample (Grušas, Lithuanian, emitted
  B2@0.93 across the set boundary). Permitted sets still narrow weak
  hints and serve as ft-veto surfaces.
- R58 accuracy round (real-data pilot -> 40-agent adjudication -> 4 designs
  -> precision+adversarial judges): NumPy-2-dead ML tier revived
  (fasttext predict raises under NumPy>=2; low-level API + loud failure);
  icu-priority weak-evidence gate (sub-2.0 hits route through the
  same-group ft gate as weak_group anchors instead of emitting at 0.76);
  205 curated surname_exact YAML entries across 14 config/regions files
  (every entry backed by a named adjudicated bearer; R59.4 grew this to
  ~216 accepted keys across 15 files — g1.yaml added, 'sabbagh' removed
  by the errata provenance rule); orthographic group
  anchors (src/regions/detection/orthography.py — Tier-1 signature marks
  veto-immune, Tier-2 contextual marks ft-vetoable, Benaïm group_cap).
  Measured on the 456-name arXiv pilot vs adjudicated truth: abstention
  59% -> 21%, 183 correct conversions, 0 wrong leaves. Guards:
  test_ft_adversarial_pins, test_surname_yaml_supplement,
  test_ortho_group_anchor, test_icu_weak_evidence_gate.

## 📊 Testing

- **3,295 tests across 145 files named by CI** (unit/, authority/, cjk/, db/, stress/, v7/, integration/, property/). The `test` job's Core-tests step enumerates 140 of them; the rest are the property-test step and the four files only the `coverage` job runs
- **500 golden dataset entries** with verified regions
- **843 adjudicated benchmark entries** from Wikidata (three-track evaluation)
- **10,724 Wikidata mathematicians** + **15,120 OpenAlex entries** as training data
- CI: lint (black 26.3.1 + ruff 0.15.8 + isort), unit tests, property tests, secret scan, repo-invariant audit

### Enforcement status (R72) — what the guards actually measure

R72 was an enforcement-only round: **no product code changed.** (The
*configuration* CI runs under did — see "One consequence" at the end of
this section.) It exists because the repo's recurring defect is *a
claim documented correctly and implemented wrongly, with a guard that
measured the wrong thing*, and the guards themselves had never been
audited.

**The test population CI executes went from 2,821 tests across 103
workflow-named files to 3,295 across 145.** `pytest tests/` collected
124 files; the workflows named 103; nothing checked the difference.
44 files carrying **474 tests had never run in CI**. They are
disproportionately the pin batteries of the most recent
rounds: `test_fetcher_contract.py` (R66.2), `test_vetting_risk.py`,
`test_genealogy_integrity.py` (R64), `test_corrections_ledger.py`
(R68), `test_licence_and_origin_leaks.py` (R67.1),
`test_edge_provenance.py` (R67.5), `test_spec_gates_blocking.py` (R55).

Two of those are cited in the docs *by name* as the evidence for a
claim, and neither was executed by any CI run:
- `tests/v7/test_spec_gates_blocking.py::test_all_eight_spec_gates_recorded`
  — "pins the full set" for the 8-quality-gates claim above
  (CLAUDE.md "Quality Gates" section).
- `tests/unit/test_vetting_risk.py` — "Pinned by …",
  `docs/regime_coverage.md:109`.

The remaining five pin claims this file makes in prose without naming
the file. Either way the shape is the same: the claim was documented,
the test existed and passed locally, and CI never ran it.

**`tools/audit_repo.py` now closes the direction that let that happen.**
G1/G2/G4 walk CI → disk: every path CI names exists (G1), imports (G2),
and *defines* at least one test (G4 — a static AST read, so it answers
the same on every runner; a count would punish a file whose optional
dep is simply absent). **G3 walks disk → CI**: every file `pytest
tests/` collects must appear in some workflow. `_G3_UNWIRED_OK` is the
only permitted exception, it is empty, and G3 fails on a stale entry —
so a new test file cannot be added without running, and a guard cannot
be silently un-wired. Adding a guard used to be a no-op; it is now
checked. Both are gating in the `audit-repo` job; G4 is cheap enough to
run in the `--fast` pre-commit hook too.

**What the wiring cost to turn on — two latent bugs, no assertion
changed.** Both are the same shape: a test file that passed only
because nothing else ran in the process with it.
- `tests/unit/test_api_privacy_gate.py` (the R57/R67 anonymous-origin
  guard) set `GMNAP_REQUIRE_HASHCASH=0` and `GMNAP_API_TOKENS` at
  **module level**, i.e. at pytest *collection* time, never undone.
  Adding it to the Core-tests step broke **12 previously-green tests**
  in `test_config.py` (the leaked token became
  `config["api"]["tokens"]`; `APIConfig` has no such field) and
  `test_api_server.py` (the leak disabled the hashcash gate those tests
  assert). The leak broke the file in return — `server._PAID_TOKENS`
  and `server._rate_limiter` are import-time globals, so it only ever
  worked when this module imported the server first. Fixed by scoping
  it into a module fixture.
- `tests/unit/test_fetcher_contract.py` used the deprecated
  `asyncio.get_event_loop()`, which raises once any earlier test has
  called `asyncio.run`. All 7 of its tests failed on the harness.
  Fixed to `asyncio.run`.

That is the concrete answer to what the gap cost: these files were not
merely untested, they were landmines that went off the moment anyone
wired them in — and `test_api_privacy_gate.py` was silently corrupting
the environment of every test that would have followed it.

**Three dead gates, handled:**
| Gate | Was | Now |
|------|-----|-----|
| CI "Memory peak check" | Measured `RUSAGE_SELF` of a fresh `python3 -c` process (~0.015 GB) against a 6 GB limit — could not fail | Reads the peak RSS `/usr/bin/time` recorded for the Core-tests run, and **fails if the measurement is missing** rather than passing on an absent number |
| CI `cost-guard` job | Read `cache/api_costs.json` for a CHF 120 budget; `cache/` is gitignored, so the file cannot exist in a CI checkout and the budget was asserted against a constant `0.0` | **Deleted.** The population is structurally empty in CI (runs offline; prod spend lives in a mounted volume no checkout can see). Budget enforcement is operator-side against the deployment's `cache/` volume; the writer stays under test via `tests/unit/test_cost_tracker.py` |
| ≥95 % leaf-precision floor | `pytest.skip`-ed in CI (gitignored model), and its CI sample reduced the denominator to ~14 | Model built in CI from the committed corpus; test `pytest.fail`s rather than skipping when `CI` is set; sample removed, so it measures the full 843 (**96.0 %**, see Detection KPIs) |

Round 34 phase 3's own note on `cost-guard` claimed it had ended that
theatre — it wired the writer and left the reader pointed at a path CI
can never populate. Worth remembering when reading any "now wired"
claim in this file: the question to ask is *which population does the
assertion see on a runner*, not whether the code exists.

**One consequence worth stating plainly.** No product code changed this
round, but the *configuration CI exercises* did. Until R72 the `test`
job had the fastText CLI binary and no model, so `FASTTEXT_AVAILABLE`
was False and every CI run detected in rules-only mode — the ML
tiebreaker documented throughout this file was never exercised by CI.
It now installs the wheel and builds the model, so CI runs the same
rules + ML path a developer gets after `make model`. That is the point
(an accuracy floor cannot be enforced against a classifier that isn't
loaded), but it does mean CI's detection path changed, and the
rules-only configuration that Docker's minimal mode ships is no longer
what CI covers. If the minimal-mode path needs its own gate, that is a
separate round.

---

## 🔧 Production Deployment

### One-time setup
```bash
make setup                       # pip install + compile fasttext (~30s)
```

### CLI (all 7 commands wired via `src.cli.gmnap:cli`)
```bash
gmnap serve --port 8080          # Start API server
gmnap query "Euler, Leonhard"    # Region + advisors + institution + birth year
gmnap process input.json         # Batch pipeline
gmnap lineage --id GID           # Advisor chain
gmnap sources                    # List authority tiers
gmnap regions                    # List 37 regions with names
gmnap validate input.json        # Schema validation
```

### Genealogy enrichment
Curated `data/genealogy_enrichment.json` (~67,500 mathematicians: 15
MGP seed + 25 curated stubs + 28,179 Wikidata SPARQL P184 entries +
16,086 theses.fr French-math students (R63) + 14,432 OpenAlex author
affiliations + transitive advisor stubs) enriches API / CLI output with
BirthYear / Institution / Advisors. Advisor chains come from MGP +
Wikidata P184 + theses.fr (~43,300 people, ~54,800 advisor edges — the
theses.fr edges are IdRef/PPN-disambiguated, ~920 corroborate a Wikidata
edge); OpenAlex adds Institution + Country coverage for ~14,800 working
mathematicians without a formally-recorded doctoral advisor. Same data backs the `/api/v1/lineage/{id}` endpoint as a third
fallback after neo4j and `out/yaml/` lookups. `name:` prefix on the path
parameter lets users query by canonical name instead of GlobalID.
Name matching is diacritic-insensitive (`Erdős`↔`Erdos`), handles
parenthetical aliases, hyphenated given names, and Dutch/German name
particles (`von Neumann`↔`Neumann … von`).
```bash
curl "localhost:8080/api/v1/lineage/name:Hilbert,%20David?depth=3"
```
Rebuild: `python3 scripts/data/fetch_wikidata_genealogy.py` (optional
refetch) then `PYTHONPATH=. python3 tools/build_genealogy_enrichment.py`.

### Edge trust — every advisor edge is stratified, never blanket-flagged
~99% of referenced Wikidata P184 statements cite MGP, so a Wikidata edge is
**not** independent corroboration of an MGP claim. Rather than flag all of
them, `tools/vetting_risk.py` stratifies by (degree country x era x recorded
credential) into four tiers: **TRUST** (flag removed), **REVIEW** (cannot
affirm — absence of evidence), **SUSPECT** (a positive marker it is wrong),
**RETYPE** (people right, relation label wrong — a habilitation sponsor, a
laurea relatore; confidence deliberately NOT demoted).

Two mechanisms feed it, and both are gated by tests because both had already
failed silently once:

- **`TRUST_ANCHOR`** — a TRUST row is the only thing that REMOVES a flag, so
  every country with one must name the event that opens it, and the anchor
  year must EQUAL the window start. Six countries were TRUSTed wrongly
  (Greece ran the yfigesia to 1983, Belgium the agregation to 2010,
  Norway/Denmark's higher doctorates are unsupervised by design) and each was
  caught only by a human fact-check that happened to be run. REVIEW needs no
  anchor: "we cannot affirm this" asserts nothing. Each anchor records a
  `basis`: **document** (a datable event — should carry a source, and the
  count still missing one is pinned) or **judgement** (no such event exists;
  nothing happened to the German Promotion in 1945, so chasing a citation
  there is chasing nothing). A `source` is only accepted WITH the quote read
  on the page and the retrieval date — a URL nobody opened looks like
  evidence, which is worse than a blank.
- **The sibling-credential test** — the rule whose absence caused every
  failure this model has had. A second doctoral credential disqualifies a
  country only if it is UNGATED (obtainable without already holding the
  supervised doctorate) AND a material route. Gated ones — German
  Habilitation, French HDR, the British higher doctorate — are post-doctoral
  by construction and only annotate. This is what makes Portugal a
  disqualification (art. 33 allows a thesis defended "sem a orientacao") and
  what stops "a habilitation exists" from taking out most of Europe.
- **Sudoc registry evidence** — France is REVIEW for 1810-1985 because several
  doctorates ran in parallel and a mathematician routinely held two under
  DIFFERENT advisors (Brezis: 3e cycle 1966 under Choquet, doctorat d'Etat
  1971 under Lions). `scripts/data/fetch_sudoc_thesis_types.py` joins by exact
  P269/IdRef — never by name, because 9.9% of French advisor surnames map to
  more than one real person — and exactly ONE pre-1985 doctorate resolves that
  specific doubt, lifting the edge to TRUST.

What the model cannot affirm is a measurement, not a paragraph:

```bash
make regime-coverage        # parked population, by country, with the ceiling
```

`era_unknown` is the single largest reason across the whole classified graph —
larger than every country rule combined. **Date coverage, not country
research, is the binding constraint.** See `docs/regime_coverage.md`.

R71 verified the anchors themselves (25-agent adversarial pass: one agent
re-deriving each year BLIND to the current value, another told it and tasked
only with breaking it). It found that 202 East German doctorates were being
TRUSTed by the WEST German rule — Wikidata P69→P17 returns modern Germany for
Leipzig/Humboldt/Jena, so the DD row written for Promotion A vs B covered 13
edges — and that Portugal keeps a statutory unsupervised route to the
doctorate. 315 edges left TRUST, every movement toward more flagging.

Corrections are append-only and applied on EVERY build, so a retraction
survives the next harvest re-asserting the error (`docs/CORRECTIONS.md`).

### Docker Compose
```bash
docker compose up -d             # Memgraph + nginx + GMNAP API
curl localhost/healthz            # Via nginx
curl localhost:8080/healthz       # Direct
```

### Environment Variables
```bash
GMNAP_SCHEMA_STRICT=0   # 0=advisory, 1=quarantine, 2=reject
OFFLINE=1                # Cache-only (default)
PIPELINE_MODE=quick      # quick/full/extreme
GMNAP_API_TOKENS=...    # Comma-separated Bearer tokens for paid tier
```

---

## ❌ DO NOT Claim

- ❌ "14 authority sources fully working" — 9 have real HTTP code; 2 need API keys; 3 deferred
- ❌ "Real-time authority enrichment" — OFFLINE=1 for tier 1+ by default; tier 0 calls APIs directly
- ❌ "100% name-origin accuracy" — 100% emitted-leaf precision on adjudicated set, but 28% abstention rate; 56% on raw citizenship labels (wrong metric for name-origin)
- ❌ "1,090 tests" / "~2,376 tests" — actual count is **3,295 run by CI's Core-tests step** (R72). And the old "all run by CI's Core-tests step" rider was itself false: at c68b734 the step named 103 files while `pytest tests/` collected 124, so 474 tests in 44 files never ran in CI. G3 in `tools/audit_repo.py` now makes that gap fail the build.
- ❌ "Genealogy data for every mathematician" — enrichment covers ~67,500 entries (MGP + Wikidata P184 + theses.fr + OpenAlex affiliations). Only ~43,300 have a full advisor chain; the rest have Institution + Country only. Historical / obscure mathematicians without any of these sources pass through with no enrichment.
- ❌ "1 M in 362 s / 2 763-per-s" — **RETRACTED (R54).** That was a no-op path
  that skipped region detection and the batch-global tail. Honest measured
  numbers: real names ~184-233/s serial, ~268-348/s parallel (4 k-10 k, 8-core
  laptop, OFFLINE); synthetic+CC 1 M MEASURED at 849/s / 19.6 min (R56).
  Only the CC-less real-name 1 M figure (~75 min) remains a projection.
- ❌ "streaming path scales to 1 M" — the `AsyncBatchAggregator` /
  `StreamingPipelineAdapter` streaming path is DELETED. Scale now comes from
  `_process_batch_parallel` (a real process pool), not async coalescing (which
  gives zero CPU parallelism for this CPU-bound workload).
