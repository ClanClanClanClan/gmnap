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

## Features

- **37 Regions**: Full linguistic processing (clean/augment/validate/order_key) for Anglo, Germanic, Slavic, Arabic, CJK, South Asian, African, and more
- **9 Authority Sources**: OpenAlex, Crossref, ORCID, HAL, GND, Wikidata, zbMATH, OAI, Crossref Thesis
- **12-Stage Pipeline**: Unicode normalization → region detection → authority enrichment → collision analytics → schema validation → output
- **3,000 entries/sec** offline mode (measured on Apple M1, 1M entries in 5.4 min)
- **Web Interface**: Dark-themed SPA at localhost:8080
- **API**: REST endpoints with rate limiting, hashcash PoW, Prometheus metrics
- **GDPR Compliant**: ShadowNode conversion, birth year masking

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

A curated `data/genealogy_enrichment.json` file (51 entries, seeded from
the Math Genealogy Project with transitive advisor chains) provides real
BirthYear / Institution / Advisors for famous mathematicians. API and CLI
responses are enriched automatically when a match is found; unknown names
pass through unchanged.

The lineage endpoint resolves chains from either a GlobalID or a
canonical name:

```bash
curl "localhost:8080/api/v1/lineage/name:Euler,%20Leonhard?depth=3"
# Returns Euler → Johann Bernoulli → Jacob Bernoulli
```

Extend the dataset by editing `tools/build_genealogy_enrichment.py` and
running `PYTHONPATH=. python3 tools/build_genealogy_enrichment.py`.

## License

MIT
