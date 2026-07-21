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
**Authority Enrichment**: V7 tier orchestrator (`src/authorities/manager_tier01.py`) delegates to canonical fetchers in `src/authorities/tierN/` when `OFFLINE=0`. 9 sources have real HTTP code (OpenAlex, Crossref, ORCID_ETD, Crossref_Thesis, zbMATH, Wikidata_P184, GND, HAL, OAI_University); 2 gated behind API keys (Scopus, Dimensions); 1 deferred for institutional access (ProQuest); 1 deferred for ToS (GoogleScholar). MathSciNet stub awaits AMS subscription
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
- Stage 4: Authority enrichment via `manager_tier01.enrich_all` → `_call_canonical_fetcher` → `src/authorities/tierN/X.Fetcher.fetch()`. 9 sources with real HTTP. DegreeDate from thesis sources, AffiliationTimeline from last-known institution, NameEvents from alternative name forms. Each `_fetch_*` shim wraps the live call in `retry_with_backoff` (2 retries × 0.5 s exp backoff) and caches the response on disk by SHA-256 of the canonical query payload
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
| Crossref_Thesis | 0 | tier0/crossref_thesis.CrossrefThesisFetcher | ✅ WORKING |
| zbMATH_Open | 0 | tier0/zbmath.ZbMATHFetcher | ✅ WORKING |
| Wikidata_P184 | 1 | inline aiohttp+SPARQL in `_fetch_wikidata_p184` | ✅ WORKING (100 % hit + 96.7 % BirthYear ±1 via P569) |
| GND | 1 | tier1/gnd.GNDFetcher | ✅ WORKING |
| HAL | 1 | tier1/hal.HALFetcher | ✅ WORKING |
| OAI_University | 1 | tier1/oai_university.OAIUniversityFetcher | ✅ WORKING |
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
| Metric | Value | Notes |
|--------|-------|-------|
| Raw ECE (test set) | 0.188 | substantial miscalibration before fix |
| Calibrated ECE (held-out) | **0.039** | PAV fit on 675 train; evaluated on 168 test |
| Brier (raw / calibrated) | 0.151 / 0.133 | re-fit on train-only changed the numbers slightly |
| 5-fold CV ECE on train | 0.002 | within-train variance estimate |

The headline ECE = **0.039** is the honest out-of-sample number.
Earlier reports of "ECE = 0.0009" were measured-on-train and
artefactually small because PAV collapses everything into one
10-bucket bin in-sample. See `docs/calibration.md` for the four
side-by-side reliability diagrams.

### Key Constants
- SIGNATURE_SUFFIXES: 29 (fire leaf at 2.5). R59.3 added the guarded
  Turkic/Balkan seven (maz/mez/oglu/escu/eanu/ovic/evic): -maz/-mez need
  len≥6 + consonant stem (Hispanic -ez/-az class excluded, 'gormaz'
  curated out); bare ASCII -oglu needs Turkic corroboration (ı/ş/ğ/ö/ü/ç
  or a C1 STRONG given) because 'Papasoglu' is adjudicated Greek;
  -escu/-eanu→B2, ASCII -ovic/-evic→B2 (raw ović/ević dedupe-guarded).
  A/B-gated: 843 benchmark + 456 pilot + 450 held-out — deltas are
  abstention→correct only (Moisescu, Iosifescu, Cerrahoğlu, Novaković),
  0 new wrong. Pins: tests/unit/test_signature_suffixes_turkic_balkan.py
- MEDIUM_SUFFIXES_TO_LEAF: 11 (fire group at 1.2, leaf at +1.0 if corroborated)
- MEDIUM_SUFFIXES_TO_GROUP: 4 (bare -ski/-sky/-ou/-is → group only)
- REGION_GROUPS: 23 groups, 34 leaves
- ft_name_classifier.ftz: 50MB quantized model (23K aligned training
  entries). **Gitignored — NOT bundled.** A fresh clone rebuilds it from
  the committed corpus `data/ml_training/ft_name_training.txt` via
  `make model` (`scripts/ml/build_name_classifier.py`); `make setup` does
  this automatically. Without it, region detection runs rules-only and
  logs a loud warning (R54 — it used to fall back on a silent DEBUG line).
  A rebuild is comparable to, not identical to, the reference artifact
  (fastText training is nondeterministic), so validate before citing the
  exact detection KPIs above.
- Same-group gate: fastText can only refine within an anchored group, never
  cross groups — and NEVER emits without an anchor (R58: the raw
  ft_only_high_conf promotion was removed after adjudicated measurement
  showed 67-81% precision at every threshold; see docs/calibration.md R58
  and tools/ft_threshold_sweep.py)
- R58 accuracy round (real-data pilot -> 40-agent adjudication -> 4 designs
  -> precision+adversarial judges): NumPy-2-dead ML tier revived
  (fasttext predict raises under NumPy>=2; low-level API + loud failure);
  icu-priority weak-evidence gate (sub-2.0 hits route through the
  same-group ft gate as weak_group anchors instead of emitting at 0.76);
  205 curated surname_exact YAML entries across 14 config/regions files
  (every entry backed by a named adjudicated bearer); orthographic group
  anchors (src/regions/detection/orthography.py — Tier-1 signature marks
  veto-immune, Tier-2 contextual marks ft-vetoable, Benaïm group_cap).
  Measured on the 456-name arXiv pilot vs adjudicated truth: abstention
  59% -> 21%, 183 correct conversions, 0 wrong leaves. Guards:
  test_ft_adversarial_pins, test_surname_yaml_supplement,
  test_ortho_group_anchor, test_icu_weak_evidence_gate.

## 📊 Testing

- **~2,376 tests collected** across 50+ files in CI's Core-tests step (unit/, authority/, cjk/, db/, v7/, plus memgraph e2e + property tests)
- **500 golden dataset entries** with verified regions
- **843 adjudicated benchmark entries** from Wikidata (three-track evaluation)
- **10,724 Wikidata mathematicians** + **15,120 OpenAlex entries** as training data
- CI: lint (black 26.3.1 + ruff 0.15.8 + isort), unit tests, property tests, secret scan, cost guard

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
Curated `data/genealogy_enrichment.json` (~39,500 mathematicians: 15
MGP seed + 25 curated stubs + 20,833 Wikidata SPARQL P184 entries +
14,432 OpenAlex author affiliations + transitive advisor stubs)
enriches API / CLI output with BirthYear / Institution / Advisors.
Advisor chains come only from MGP + Wikidata P184 (~20,800 people);
OpenAlex adds Institution + Country coverage for ~18,760 working
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
- ❌ "1,090 tests" — actual count is ~2,376 collected, all run by CI's Core-tests step
- ❌ "Genealogy data for every mathematician" — enrichment covers ~39,500 entries (MGP + Wikidata P184 + OpenAlex affiliations). Only ~20,800 have a full advisor chain; the other ~18,700 have Institution + Country only. Historical / obscure mathematicians without any of these sources pass through with no enrichment.
- ❌ "1 M in 362 s / 2 763-per-s" — **RETRACTED (R54).** That was a no-op path
  that skipped region detection and the batch-global tail. Honest measured
  numbers: real names ~184-233/s serial, ~268-348/s parallel (4 k-10 k, 8-core
  laptop, OFFLINE); synthetic+CC 1 M MEASURED at 849/s / 19.6 min (R56).
  Only the CC-less real-name 1 M figure (~75 min) remains a projection.
- ❌ "streaming path scales to 1 M" — the `AsyncBatchAggregator` /
  `StreamingPipelineAdapter` streaming path is DELETED. Scale now comes from
  `_process_batch_parallel` (a real process pool), not async coalescing (which
  gives zero CPU parallelism for this CPU-bound workload).
