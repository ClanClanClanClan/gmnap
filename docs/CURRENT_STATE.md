# GMNAP Current State Documentation
*Last Updated: 2026-03-16*

## Executive Summary

GMNAP v7 is a **production-ready** pipeline for mathematician name authority record processing with full regional coverage, configurable schema validation, an API server, and comprehensive monitoring.

### Key Metrics
- **Regional Coverage**: 100% (37/37 regions)
- **Linguistic Rules**: 34/34 implemented
- **Performance**: 20-25 min/1M entries (OFFLINE mode)
- **Security Compliance**: 100% (injection attacks blocked, trufflehog secret scan)
- **Test Suite**: 441 tests passing (unit + integration)
- **Schema Version**: v2.0 with configurable strict mode
- **Authority Sources**: 9/14 implemented with real HTTP calls; 2 behind subscription; 2 deferred; 1 opt-in only

---

## System Capabilities

### Pipeline (12 stages)
All stages execute in sequence with real code:
- Stage 0: Config/credential validation
- Stage 1: Unicode normalisation (NFC->NFKD->fold->NFC), streaming_chunk_size=8000
- Stage 1b: LLM thesis extraction (graceful fallback)
- Stage 2: Region detection (FastText + script analysis + overlay map + diaspora overlay)
- Stage 3: Region hooks (clean->augment->validate->order_key per region)
- Stage 4: Authority enrichment (9 adapters with real HTTP; extracts NameEvents, AffiliationTimeline, DegreeDate)
- Stage 5: Collision analytics (DuckDB + in-memory fallback)
- Stage 6: Graph consistency (Bayesian coherence, optional Memgraph)
- Stage 7: Short-form tagging (initials clustering, external occurrence counting)
- Stage 8: Schema validation (v2.0, configurable: advisory/quarantine/reject)
- Stage 9: Write & Diff (YAML snapshots, SQL/Cypher changelogs)
- Stage 10-11: Report generation, DOI draft, SFTP push, ATTRIBUTION.txt, idempotency check

### Region Detection Enhancements
- **Overlay map** (spec 2a): 10 sub-national overrides (CH-FR->A2, IN-HN->D1, etc.)
- **Diaspora detection**: Real logic consulting config/diaspora.yaml date ranges
- **Script switch config**: C1 Turkic processor loads config/script_switch.yaml

### Region Processors (37 regions)
All regions have full `clean()`, `augment()`, `validate()`, `order_key()`:
- A1-A5, B1-B3, C1-C9, D1-D5, E1-E7, F1-F4, G1, H1, R0, Z0
- 37/37 YAML config files in `config/regions/`
- All 37 processors auto-load YAML overrides via lazy `ensure_yaml_loaded()` in base class

### API Server
- **FastAPI** server at `src/api/server.py`
- Endpoints: `/healthz`, `/readyz`, `/api/v1/query`, `/api/v1/lineage/{id}`, `/api/v1/process`, `/metrics`
- Rate limiting: free tier 60 req/min (hashcash 18-bit PoW), paid tier 10K/min (Bearer token)
- Prometheus metrics endpoint

### CLI Commands
- `gmnap process` -- run the full pipeline (`--force-extreme` for tier 3)
- `gmnap validate` -- schema-only validation (no pipeline)
- `gmnap serve` -- start the API server via uvicorn
- `gmnap query` -- single name lookup
- `gmnap lineage` -- genealogy query
- `gmnap sources` -- list authority sources
- `gmnap regions` -- list supported regions

### Quality Gates (8 gates)
All 8 V7 quality gates implemented with mode-specific thresholds (Quick/Full/Extreme):
1. duplicate_global_id (must be 0)
2. duplicate_external_id_pct (Quick <=0.10%, Full <=0.05%, Extreme 0%)
3. roundtrip_script_rate_min (>=0.97)
4. genealogy_edge_conflict_pct (Quick <=2%, Full <=1%, Extreme 0%)
5. graph_coherence_score_min (Quick >=0.85, Full >=0.92, Extreme >=0.97)
6. peak_rss_gb_on_2M (<=6GB)
7. warm_cache_runtime_per_1M_min (Quick <=35, Full <=70)
8. idempotent_diff_bytes_max (must be 0)

### GDPR Compliance
- GDPR_DATA field marking on personal data entries
- Birth year decade-masking when cohort < 5
- Source scrubbing (GoogleScholar, ProQuest, CNKI)
- ShadowNode conversion (`--drop-personal` flag) via `src/core/gdpr.py`

### Ops & Monitoring
- **Prometheus metrics**: pipeline_runs_total, pipeline_duration_seconds, entries_processed, schema_errors, authority_hits_by_tier
- **Grafana dashboard**: `config/grafana/dashboard.json` with 8 panels
- **Snapshot retention**: 3650-day (10yr) automatic cleanup of archive snapshots per spec
- **Docker Compose**: gmnap + nginx reverse proxy + memgraph
- **CI**: GitHub Actions with unit, integration, hardcore, property test, secret scan (trufflehog), cost guard
- **Cost guard**: CHF 120/month limit enforced in CI (`make cost-check`)

---

## Authority Enrichment

### Tier 0 -- Free, No Auth Required
| Source | Status | What It Returns |
|--------|--------|-----------------|
| OpenAlex | IMPLEMENTED | OpenAlex ID, ORCID, display name, works count, institution, country, h-index |
| Crossref | IMPLEMENTED | DOIs, publication count, co-authors, subjects, venues |
| ORCID_ETD | IMPLEMENTED | ORCID iD, institution names |
| Crossref_Thesis | IMPLEMENTED | Thesis DOI, degree date with precision, institution |

### Tier 1 -- Free, Rate-Limited
| Source | Status | What It Returns |
|--------|--------|-----------------|
| Wikidata_P184 | IMPLEMENTED | Doctoral advisor (P184), students (P185), ORCID (P496), birth/death years |
| OAI_University | IMPLEMENTED | Thesis title, institution, degree date, DOI (via BASE API) |
| HAL | IMPLEMENTED | Institution/lab affiliations |
| GND | IMPLEMENTED | Preferred name, birth/death years |
| zbMATH Open | IMPLEMENTED | zbMATH publication ID |

### Tier 2 -- Subscription Required
| Source | Status | What It Returns |
|--------|--------|-----------------|
| MathSciNet | STUB | Requires AMS subscription. See docs/AUTHORITY_ACCESS.md |
| Scopus | STUB | Requires Elsevier API key. See docs/AUTHORITY_ACCESS.md |
| Dimensions | STUB | Requires Digital Science API key. See docs/AUTHORITY_ACCESS.md |

### Tier 3 -- Restricted
| Source | Status | Notes |
|--------|--------|-------|
| ProQuest | NOT IMPLEMENTED | Requires institutional proxy. See docs/AUTHORITY_ACCESS.md |
| Google Scholar | OPT-IN ONLY | `--force-extreme` + `YES_I_ACCEPT_GS_TOS=yes`; encrypted cache |

**Note**: `OFFLINE=1` is the default. Set `OFFLINE=0` to enable tier 1+ real API calls. Tier 0 adapters always call APIs directly.

### Data Population from Authority Responses
- **NameEvents**: Extracted from ORCID/Wikidata (marriage, legal changes)
- **AffiliationTimeline**: Extracted from OpenAlex/ORCID
- **DegreeDate**: Extracted from thesis data with precision inference (year/month/day)

---

## Testing

| Category | Count | Description |
|----------|-------|-------------|
| Unit | ~300 | Core logic, region processors, utilities, schema |
| Integration | ~50 | Pipeline flow, snapshot rollback |
| SEA Roundtrip | 38 | Thai RTGS, Khmer UNGEGN, Lao MOICT 2019 |
| Quality Gates | ~30 | All 8 V7 gates |
| Stress | available | 2M synthetic (`make stress`) |
| **Verified** | **441** | All passing |

Test fixtures: 1,500 entries across all 37 regions.

---

## Production Deployment

### Recommended Configuration
```bash
export GMNAP_STREAMING=1
export GMNAP_CHUNK=8000           # spec default
export GMNAP_INFLIGHT=16
export PIPELINE_MODE=full
export OFFLINE=0                  # enable live API calls
export GMNAP_SCHEMA_STRICT=0     # 0=advisory, 1=quarantine, 2=reject
export PYTHONPATH=.

python3 -m src.cli.gmnap process input.json --mode full
```

### API Server
```bash
python3 -m src.cli.gmnap serve --port 8080
```

### Docker
```bash
docker compose up -d
# gmnap API on port 8080 (behind nginx on port 80)
# Memgraph on port 7687 (optional)
```

### Make Targets
```bash
make quick              # Quick mode (tier 0, 4 workers)
make full               # Full mode (tier 0+1, 8 workers)
make extreme            # Extreme mode (all tiers, 12 workers)
make test               # Run test suite
make lint               # Black + ruff + isort
make cost-check         # CHF 120/month guard
make update-sources     # Refresh authority configs
```

---

## V7 Spec Compliance Status

### Fully Compliant
- 12-stage pipeline (spec 5)
- 37 region groups + overlay map + diaspora detection (spec 2, 2a, 3)
- 34 linguistic rules (spec 4)
- 8 quality gates with Quick/Full/Extreme thresholds (spec 7)
- Schema v2.0 with DegreeDate, Students, ValidationStatus (spec 0)
- Cost guard CHF 120/month (spec 0)
- Streaming chunk size 8000 (spec 0)
- Snapshot retention 3650 days (spec 0)
- Cache zstd + 50GB + 60-day TTL (spec 0)
- GDPR/ShadowNode/scrubbers (spec 10)
- Hashcash 18-bit PoW for free tier (spec 12)
- Trufflehog secret scan in CI + pre-commit (spec 8)
- All 7 make targets (spec 11)
- CLI commands: query, lineage, process, validate, serve, sources, regions (spec 11)

### Known Gaps
- **VSCode extension** (spec 11): Separate frontend project, not implemented
- **duckdb-batch Docker service** (spec 12): DuckDB is embedded in pipeline process
- **Prometheus alert rules** (spec 12): p95 latency alerting not configured
- **Tier 2-3 authority sources**: Require paid subscriptions (see docs/AUTHORITY_ACCESS.md)
