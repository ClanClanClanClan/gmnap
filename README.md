# MathLineage — Global Mathematician Name Authority

## What It Does

Processes mathematician names across 37 linguistic regions, detecting geographic origin, normalizing naming conventions, and enriching with authority data from 9 sources.

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Query a name
PYTHONPATH=. python -m src.cli.gmnap query "Euler, Leonhard"

# Start the API server
PYTHONPATH=. python -m src.cli.gmnap serve --port 8080

# Open web UI
open http://localhost:8080
```

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

1,090+ tests covering region detection accuracy (1,060), end-to-end workflows (30), API security, CLI, web interface, and nginx config.

## License

MIT
