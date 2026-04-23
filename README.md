# MathLineage — Global Mathematician Name Authority

## What It Does

Processes mathematician names across 37 linguistic regions, detecting geographic origin, normalizing naming conventions, and enriching with authority data from 9 sources.

## Quick Start

```bash
# One-time setup (pip install + compile fasttext CLI; ~30 seconds)
make setup

# Query a name (region + genealogy + institution)
gmnap query "Euler, Leonhard"

# Start the API server
gmnap serve --port 8080

# Open the web UI
open http://localhost:8080
```

`make setup` is the recommended path. For a minimal install without the
fasttext tiebreaker (rules-based detection only) run
`pip install -r requirements.txt` instead; the CLI and API still work,
just with lower name-origin accuracy on hard cases.

For a step-by-step reviewer walkthrough (CLI + web UI + API, with
screenshots), see **[DEMO.md](DEMO.md)**. For the architecture
one-pager covering the five design decisions an evaluator asks about,
see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Features

- **37 Regions**: Full linguistic processing (clean/augment/validate/order_key) for Anglo, Germanic, Slavic, Arabic, CJK, South Asian, African, and more
- **9 Authority Sources**: OpenAlex, Crossref, ORCID, HAL, GND, Wikidata, zbMATH, OAI, Crossref Thesis
- **12-Stage Pipeline**: Unicode normalization → region detection → authority enrichment → collision analytics → schema validation → output
- **Genealogy Enrichment**: ~6,200 mathematicians with advisor chains, birth years, and institutions (seeded from MGP + Wikidata SPARQL)
- **Web Interface**: Dark-themed SPA at localhost:8080
- **API**: REST endpoints with rate limiting, hashcash PoW, Prometheus metrics
- **GDPR Compliant**: ShadowNode conversion, birth year masking

### Measured Performance (OFFLINE mode, Apple M1)

| Operation | Throughput | 1 M projection |
|---|---|---|
| `RegionManager.detect_region` (single stage, in-process) | ~3,700 / s | ~4.5 min |
| `V7Pipeline.process_batch` (rules-only, fastText missing) | ~980 / s | ~17 min |
| `V7Pipeline.process_batch` (full, Python fastText module) | ~240 / s | ~70 min |
| `V7Pipeline.process_batch` (full, persistent fastText CLI worker) | ~430 / s | ~39 min |

Synthetic-name benchmarks always trigger the fastText tiebreaker because
nothing matches the rules; real-world names with clear signature suffixes
hit fastText far less often. The **persistent CLI worker** (spawned once
per process and fed queries over stdin) is ~60× faster per tiebreaker
call than the legacy `subprocess.run` pattern, which yields the ~2.3×
end-to-end gain visible in the last row. Reproduce with
`PYTHONPATH=. python3 tools/run_benchmark.py --sizes 1000,10000`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Liveness probe |
| `/readyz` | GET | Readiness probe |
| `/api/v1/query?name=...` | GET | Single name lookup |
| `/api/v1/lineage/{id}` | GET | Academic genealogy |
| `/api/v1/process` | POST | Batch processing |
| `/metrics` | GET | Prometheus metrics |

## CLI Commands

```bash
gmnap query "Name"           # Region detection
gmnap process input.json     # Batch pipeline
gmnap validate input.json    # Schema validation
gmnap serve --port 8080      # Start API server
gmnap sources                # List authority sources
gmnap regions                # List 37 regions
gmnap lineage --id GID       # Academic genealogy
```

## Docker

```bash
cp .env.example .env         # Configure environment
docker compose up -d          # Start all services
curl localhost/healthz        # Verify via nginx
curl localhost:8080/healthz   # Verify direct
```

## Configuration

Copy `.env.example` to `.env` and configure. Key variables:
- `OFFLINE=1` — cache-only mode (default, no network needed)
- `PIPELINE_MODE=quick` — quick/full/extreme
- `GMNAP_API_TOKENS=token1,token2` — paid tier Bearer tokens

## Testing

```bash
PYTHONPATH=. pytest tests/unit/ -q --timeout=120
```

1,792 tests covering region detection accuracy, 500-entry golden dataset, 843-entry adjudicated name-origin benchmark, end-to-end workflows, API security, CLI hardening, web interface, and nginx config.

## Region Detection

Split geo/name-origin architecture validated by external onomastics expert:
- **100% emitted-leaf precision** on 523-entry adjudicated benchmark (zero wrong leaves)
- **100% CC-based accuracy** across 216 territories
- Three-tier suffix system + fastText CLI tiebreaker + same-group gate
- Honest abstention: returns R0 + group hint when uncertain, never forces a wrong leaf

## Genealogy Enrichment

`data/genealogy_enrichment.json` (~6,200 mathematicians) backs the
Advisors / Institution / BirthYear fields in CLI and API responses.
Sources, in order of priority:

1. `data/mgp_validation_data.json` — 15 canonical demo entries from the
   Math Genealogy Project.
2. Hand-curated stubs in `tools/build_genealogy_enrichment.py` for
   transitive advisors like Johann Bernoulli and Pfaff.
3. `data/wikidata_genealogy.json` — 4,385 mathematicians fetched from
   Wikidata SPARQL (`P184` doctoral advisor, `P569` birth date, `P69`
   institution). Fetched with `scripts/data/fetch_wikidata_genealogy.py`.

Name matching is diacritic-insensitive (`Erdős` ↔ `Erdos`) and handles
given-name order, parenthetical aliases, hyphenated compounds, and
Dutch/German particles (`von Neumann` ↔ `Neumann … von`). Unknown names
pass through without fake data.

The lineage endpoint accepts either a GlobalID or a canonical name:

```bash
curl "localhost:8080/api/v1/lineage/name:Euler,%20Leonhard?depth=3"
# Returns Euler → Johann Bernoulli → Jacob Bernoulli
```

Rebuild after editing sources:

```bash
python3 scripts/data/fetch_wikidata_genealogy.py   # optional, hits Wikidata SPARQL
PYTHONPATH=. python3 tools/build_genealogy_enrichment.py
```

## License

MIT
