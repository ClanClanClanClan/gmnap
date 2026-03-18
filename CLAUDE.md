# GMNAP v7 Current Development Status
*Last Updated: 2026-03-16*

## 🎯 System State (Honest Assessment)

**Pipeline**: 12-stage async pipeline — all stages wired and executing
**Regional Coverage**: 37/37 regions fully implemented (100%)
**Linguistic Rules**: 34/34 implemented across region processors
**Security**: Injection attack blocking validated
**Performance**: 20-25 min/1M entries (exceeds targets, OFFLINE mode)
**Schema Validation**: v2.0 schema; configurable strict mode (advisory/quarantine/reject)
**Authority Enrichment**: 9 of 14 sources with real HTTP calls; 2 gated behind API keys; 3 deferred. DegreeDate from thesis sources, AffiliationTimeline from last-known institution, NameEvents from alternative name forms.
**Region Config**: 37/37 YAML config files auto-loaded via lazy `ensure_yaml_loaded()` in base class
**API Server**: FastAPI server with `/healthz`, `/readyz`, `/api/v1/query`, `/api/v1/lineage`, `/api/v1/process`, `/metrics`
**CLI**: `query`, `lineage`, `process`, `sources`, `regions`, `validate`, `serve`
**Diaspora Detection**: Implemented — uses `config/diaspora.yaml` date ranges
**Region Overlay Map**: Spec §2a wired — sub-national overrides (CH-FR, IN-HN, etc.)
**Testing**: 456+ tests (unit + integration + API server + region overlay + SEA roundtrip)
**Test Fixtures**: 1,500 entries across all 37 regions

---

## ✅ What Actually Works

### Pipeline (12 stages)
All stages execute in sequence with real code:
- Stage 0: Config/credential validation
- Stage 1: Unicode normalisation (NFC→NFKD→fold→NFC)
- Stage 1b: LLM thesis extraction (graceful fallback if unavailable)
- Stage 2: Region detection (FastText + script + diaspora overlay + region overlay map)
- Stage 3: Region hooks (clean→augment→validate→order_key per region)
- Stage 4: Authority enrichment (9 adapters with real HTTP; DegreeDate from thesis sources, AffiliationTimeline from last-known institution, NameEvents from alternative name forms)
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

| Source | Tier | Status |
|--------|------|--------|
| OpenAlex | 0 | ✅ WORKING (httpx, /authors endpoint) |
| Crossref | 0 | ✅ WORKING (httpx, /works?query.author=) |
| ORCID_ETD | 0 | ✅ WORKING (httpx, /expanded-search) |
| Crossref_Thesis | 0 | ✅ WORKING (httpx, type=dissertation filter) |
| HAL | 1 | ✅ WORKING (httpx, archives-ouvertes.fr) |
| GND | 1 | ✅ WORKING (httpx, lobid.org, OFFLINE guard) |
| Wikidata_P184 | 1 | ✅ WORKING (httpx, SPARQL P184/P185, OFFLINE guard) |
| OAI_University | 1 | ✅ WORKING (httpx, BASE API, OFFLINE guard) |
| zbMATH_Open | 1 | ✅ WORKING (httpx, api.zbmath.org) |
| MathSciNet | 2 | ⚠️ STUB (needs AMS subscription — see docs/AUTHORITY_ACCESS.md) |
| Scopus | 2 | ⚠️ GATED (needs SCOPUS_API_KEY — free at dev.elsevier.com) |
| Dimensions | 2 | ⚠️ GATED (needs DIMENSIONS_API_KEY — free at app.dimensions.ai) |
| ProQuest | 3 | 🔴 DEFERRED (requires institutional proxy access) |
| GoogleScholar | 3 | 🔴 DEFERRED (ToS — opt-in via --force-extreme + YES_I_ACCEPT_GS_TOS) |

**CRITICAL**: `OFFLINE=1` is the default for tier 1+ sources. Set `OFFLINE=0` for full enrichment.
Tier 0 sources (OpenAlex, Crossref, ORCID, Crossref_Thesis) call APIs directly.

### YAML Config: All 37 Regions Auto-Loaded
37/37 YAML config files exist and are auto-loaded via lazy `ensure_yaml_loaded()` in base class.
`_apply_yaml_overrides()` merges YAML keys onto processor attributes before first hook call.

### Performance Numbers Exclude Real Enrichment
Benchmarks are OFFLINE mode. Live enrichment will be slower due to API rate limits.

---

## 📊 Testing

- **441+ tests passing** (unit + integration + SEA roundtrip + snapshot rollback)
- **1,500 test fixtures** across all 37 regions
- SEA roundtrip: Thai RTGS, Khmer UNGEGN, Lao MOICT 2019
- Snapshot rollback: git revert coherence validated
- 2M synthetic stress test available (`make stress`)
- CI runs: unit, property, integration, hardcore, secret scan, cost guard

---

## 🔧 Production Deployment

### CLI
```bash
gmnap serve --port 8080          # Start API server
gmnap query "Euler, Leonhard"    # Single name lookup
gmnap process input.json --mode full  # Batch processing
gmnap validate input.json        # Schema validation only
gmnap sources                    # List authority sources
gmnap regions                    # List supported regions
```

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
