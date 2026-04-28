# GMNAP v7 / MathLineage — Current Development Status
*Last Updated: 2026-04-27*

## 🎯 System State (Honest Assessment)

**Pipeline**: 12-stage pipeline (stages 0–8 async, 9–11 sync) — all stages wired and executing
**Regional Coverage**: 37/37 regions fully implemented (100%), 38 processor files
**Region Detection**: Split geo/name-origin architecture with three-tier suffix system, fastText CLI tiebreaker, same-group gate. Expert-validated as production-ready.
**Security**: Injection attack blocking validated
**Performance**: ~3,000 entries/sec at 100K+ scale OFFLINE mode (measured); ~5.4 min/1M actual
**Schema Validation**: v2.0 schema; configurable strict mode (advisory/quarantine/reject)
**Authority Enrichment**: V7 tier orchestrator (`src/authority/manager_tier01.py`) delegates to canonical fetchers in `src/authorities/tierN/` when `OFFLINE=0`. 9 sources have real HTTP code (OpenAlex, Crossref, ORCID_ETD, Crossref_Thesis, zbMATH, Wikidata_P184, GND, HAL, OAI_University); 2 gated behind API keys (Scopus, Dimensions); 1 deferred for institutional access (ProQuest); 1 deferred for ToS (GoogleScholar). MathSciNet stub awaits AMS subscription
**Region Config**: `RegionSpec.load_yaml_config()` is the per-region YAML extension point, cached in `_YAML_CACHE`. The on-disk directory `config/regions/` is currently empty — every region falls back to its hardcoded defaults — so the loader is dormant in practice but tested and ready
**API Server**: FastAPI server with 8 endpoints (/healthz, /readyz, /api/v1/query, /api/v1/lineage, /api/v1/process, /api/v1/suggest, /metrics, /)
**CLI**: `serve` and `version` via `gmnap` entry point; full 7-command CLI in `src/cli/gmnap.py` (query, lineage, process, sources, regions, validate, serve) but NOT wired to the main entry point
**Diaspora Detection**: Implemented — split geo_region vs name_region with conflict flag
**Testing**: 1,792 tests collected (CI runs ~1,740 across 13 test files); 843-entry adjudicated benchmark
**Test Fixtures**: 500 golden dataset + 843 name-origin benchmark + 10,724 Wikidata mathematicians

---

## ✅ What Actually Works

### Pipeline (12 stages)
All stages execute in sequence with real code:
- Stage 0: Config/credential validation
- Stage 1: Unicode normalisation (NFC→NFKD→fold→NFC)
- Stage 1b: LLM thesis extraction (graceful fallback if unavailable)
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
- 37/37 YAML config files in `config/regions/`
- C1 processor loads `config/script_switch.yaml` for Kazakh/Uzbek reform schedules
- Region overlay map (spec §2a) wired for sub-national detection
- Diaspora overlay wired for cross-border mathematician detection

### Quality Gates (8 gates)
All 8 V7 quality gates implemented with mode-specific thresholds.

### GDPR Compliance
- GDPR_DATA field marking, birth year decade-masking
- ShadowNode conversion (`--drop-personal` flag) via `src/core/gdpr.py`
- Source scrubbing (GoogleScholar, ProQuest, CNKI)

### Cache System
- Zstandard compression, 60-day TTL, 50GB max, LRU eviction
- Thread-safe, per-file locks, bad JSON quarantine

---

## 🔴 Known Limitations (Be Honest About These)

### Authority Enrichment: 9 of 14 Sources Have Real HTTP Code

V7's tier orchestrator (`src/authority/manager_tier01.py`) holds the
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
| OpenAlex | 0 | tier0/openalex.OpenAlexFetcher | ✅ WORKING |
| Crossref | 0 | tier0/crossref.CrossrefFetcher | ✅ WORKING |
| ORCID_ETD | 0 | tier0/orcid_etd.ORCIDETDFetcher | ✅ WORKING |
| Crossref_Thesis | 0 | tier0/crossref_thesis.CrossrefThesisFetcher | ✅ WORKING |
| zbMATH_Open | 0 | tier0/zbmath.ZbMATHFetcher | ✅ WORKING |
| Wikidata_P184 | 1 | inline aiohttp+SPARQL in `_fetch_wikidata_p184` | ✅ WORKING |
| GND | 1 | tier1/gnd.GNDFetcher | ✅ WORKING |
| HAL | 1 | tier1/hal.HALFetcher | ✅ WORKING |
| OAI_University | 1 | tier1/oai_university.OAIUniversityFetcher | ✅ WORKING |
| MathSciNet | 2 | (no canonical fetcher) | ⚠️ STUB (needs AMS subscription) |
| Scopus | 2 | (gated stub in manager_tier01) | ⚠️ Requires `SCOPUS_API_KEY` |
| Dimensions | 2 | (gated stub in manager_tier01) | ⚠️ Requires `DIMENSIONS_API_KEY` |
| ProQuest | 3 | (deferred stub) | 🔴 Institutional proxy needed |
| GoogleScholar | 3 | (deferred stub) | 🔴 ToS — opt-in only |

**CRITICAL**: `OFFLINE=1` is the default. Set `OFFLINE=0` for full
enrichment. The tier-0 stubs short-circuit to OFFLINE-skip *before*
the cache check is meaningful, so OFFLINE-mode is a no-op even if
a stale cache exists from an earlier live run.

The 13 dead files that used to live in `src/authority/` (`manager.py`
and 9 `*_adapter.py` plus 3 helpers) were removed in the 2026-04-27
audit pass — only `manager_tier01.py` and `common.py` remain in the
singular package.

### YAML Config: extension point only, currently dormant
`RegionSpec.load_yaml_config()` reads `config/regions/<lowercase_code>.yaml`
and caches the result in the module-level `_YAML_CACHE`. Tests verify
the loader (`tests/unit/test_region_processors.py::TestYAMLConfigLoader`).

In practice the directory `config/regions/` does **not** currently
exist in the repo — every region falls back to the hardcoded
defaults set in its processor's `__init__`. The loader is wired and
ready; populate the directory if/when YAML-driven overrides become
the right way to tune a particular region.

The previous "ensure_yaml_loaded() / _apply_yaml_overrides()"
auto-merge machinery was removed in the 2026-04-27 audit because it
had no production caller. Reinstating it would require both the
YAMLs and a hook in each processor's pre-call path.

### Performance (Measured 2026-04-22, Python 3.12, Apple M1, OFFLINE)

Numbers below are from `tools/run_benchmark.py` on synthetic names
(`Surname{i}, Given{i}` with rotated country codes). Real-world names
with signature suffixes hit the fastText tiebreaker far less often, so
the full-pipeline row is a lower bound.

| Path | Throughput | 1 M projection | RSS @10 k |
|---|---|---|---|
| `RegionManager.detect_region` (single stage) | ~3,700 / s | 4.5 min | — |
| `V7Pipeline.process_batch` (rules-only, no fastText) | ~980 / s | 17 min | 166 MB |
| `V7Pipeline.process_batch` (full, fastText CLI tiebreaker) | ~190 / s | 90 min | 348 MB |

Reproduce with:
```bash
PYTHONPATH=. python3 tools/run_benchmark.py --sizes 1000,10000
```

The dramatic gap between detection-only and full pipeline is because
synthetic names never hit a handcrafted rule, so the fastText CLI is
invoked per entry via subprocess. With real names the gap is much
smaller. Live authority enrichment (OFFLINE=0) is slower still because
tier-0 APIs rate-limit.

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
| Adjudicated leaf precision (523 entries) | 482/482 = 100% | Zero wrong emitted leaves |
| Adjudicated coverage | 482/523 = 92.2% | 41 honest R0 abstentions |
| Adjudicated group-or-better | 523/523 = 100% | |
| Full 843 vs geo labels (informational) | 56% | NOT a name-origin KPI — citizenship ≠ name-origin |
| Classifier errors (genuine) | ~50/843 = 6% | Soviet suffixes, historical boundaries |
| Abstention rate | 235/843 = 28% | Coverage ceiling for name-only classification |

### Key Constants
- SIGNATURE_SUFFIXES: 22 (fire leaf at 2.5)
- MEDIUM_SUFFIXES_TO_LEAF: 11 (fire group at 1.2, leaf at +1.0 if corroborated)
- MEDIUM_SUFFIXES_TO_GROUP: 4 (bare -ski/-sky/-ou/-is → group only)
- REGION_GROUPS: 23 groups, 34 leaves
- ft_name_classifier.ftz: 50MB quantized model (23K aligned training entries)
- Same-group gate: fastText can only refine within scorer's group, never cross groups

## 📊 Testing

- **1,792 tests collected** (CI runs ~1,740 across 13 test files)
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
Curated `data/genealogy_enrichment.json` (~20,600 mathematicians: 15
MGP seed + 25 curated stubs + 4,362 Wikidata SPARQL P184 entries +
14,432 OpenAlex author affiliations + transitive advisor stubs)
enriches API / CLI output with BirthYear / Institution / Advisors.
Advisor chains come only from MGP + Wikidata P184 (~4,390 people);
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
- ❌ "1,090 tests" — actual count is 1,792 collected, ~1,740 run by CI
- ❌ "Genealogy data for every mathematician" — enrichment covers ~20,600 entries (MGP + Wikidata P184 + OpenAlex affiliations). Only ~4,390 have a full advisor chain; the other ~16,200 have Institution + Country only. Historical / obscure mathematicians without any of these sources pass through with no enrichment.
- ❌ "3,000 entries/sec on the full pipeline" — that's detection-only. Full `process_batch` with fastText CLI subprocess is ~190/s on synthetic names; ~980/s rules-only. See Performance table for details.
