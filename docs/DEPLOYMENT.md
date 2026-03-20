# GMNAP V7 Deployment Guide

## Prerequisites

- Docker Engine 24+ with Compose V2
- 4 GB RAM minimum (6 GB recommended)
- 2+ CPU cores
- 20 GB disk (includes 131 MB FastText model downloaded during build)

## Quick Start

```bash
# 1. Clone and configure
git clone <repo> && cd gmnap
cp .env.example .env
# Edit .env: set MEMGRAPH_PASSWORD, GMNAP_API_TOKENS

# 2. Build and start
docker compose up -d gmnap redis memgraph nginx

# 3. Load graph seed data (optional — for lineage queries)
docker exec -i gmnap_memgraph mgconsole \
  --host localhost --port 7687 \
  --username gmnap --password "${MEMGRAPH_PASSWORD:-v7_lineage}" \
  < init_memgraph.cypher

# 4. Verify
curl http://localhost/healthz
curl http://localhost:8080/readyz
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `gmnap` | 8080 | API server (FastAPI + Uvicorn) |
| `nginx` | 80 | Reverse proxy, rate limiting |
| `memgraph` | 7687 (bolt) | Graph database for lineage |
| `redis` | 6379 | Rate limit state, session cache |
| `prometheus` | 9090 | Metrics collection (optional) |
| `grafana` | 3001 | Dashboards (optional) |

## Environment Variables

```bash
# Required for production
GMNAP_API_TOKENS=token1,token2     # Comma-separated Bearer tokens (paid tier)
MEMGRAPH_PASSWORD=<strong-password> # Graph database auth

# Network control
OFFLINE=1                           # Block tier-1+ authority sources (default)
OFFLINE=0                           # Enable all authority enrichment
GMNAP_NO_NETWORK=1                  # Block ALL HTTP (airgapped mode)

# Pipeline
PIPELINE_MODE=quick                 # quick (default) / full / extreme
GMNAP_SCHEMA_STRICT=0               # 0=advisory, 1=quarantine, 2=reject

# GDPR
GMNAP_DROP_PERSONAL=1               # Convert to ShadowNodes (strip PII)
```

## API Endpoints

### Public (no auth)
- `GET /healthz` — health check
- `GET /readyz` — readiness check
- `GET /metrics` — Prometheus metrics

### Authenticated (Bearer token or Hashcash PoW)
- `GET /api/v1/query?name=<name>&mode=quick` — single name lookup
- `POST /api/v1/process` — batch processing (up to 10,000 entries)
- `GET /api/v1/lineage/{global_id}?depth=3&format=json` — genealogy query

### Rate Limits
- **Free tier**: 60 req/min (requires `X-Hashcash` header, 18-bit PoW)
- **Paid tier**: 10,000 req/min (requires `Authorization: Bearer <token>`)

## Batch Processing

```bash
# Process entries via API
curl -X POST http://localhost:8080/api/v1/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entries": [
      {"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]},
      {"CanonicalLatin": "Gauss, Carl Friedrich", "CountryCodes": ["DE"]}
    ],
    "mode": "quick"
  }'

# Or via CLI inside the container
docker exec gmnap_api python -m src.cli.gmnap process input.json --mode full
```

## Authority Enrichment Tiers

| Tier | Sources | Default | Control |
|------|---------|---------|---------|
| 0 | OpenAlex, Crossref, ORCID, CrossrefThesis | **ON** | `GMNAP_NO_NETWORK=1` to block |
| 1 | HAL, GND, zbMATH, Wikidata, OAI | OFF | `OFFLINE=0` to enable |
| 2 | Scopus, Dimensions | OFF | Requires API keys |
| 3 | ProQuest, GoogleScholar | OFF | Institutional/ToS gated |

## Monitoring

```bash
# Start with Prometheus + Grafana
docker compose up -d prometheus grafana

# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3001 (admin / gmnap_v7)
```

Key metrics:
- `gmnap_pipeline_runs_total{mode}` — pipeline executions by mode
- `gmnap_entries_processed_total` — total entries processed
- `gmnap_pipeline_duration_seconds` — processing time histogram

## Production Hardening

1. **TLS**: Add TLS termination to nginx or use a load balancer
2. **Secrets**: Use Docker secrets or Vault instead of env vars
3. **Metrics access**: Uncomment IP restrictions in `config/nginx.conf`
4. **Memory**: Set `deploy.resources.limits.memory` per workload
5. **Backups**: Mount named volumes to persistent storage
6. **Logging**: Forward container logs to centralized logging (ELK/Loki)

## Troubleshooting

```bash
# Check service logs
docker compose logs gmnap --tail 50
docker compose logs memgraph --tail 20

# Enter container shell
docker exec -it gmnap_api /bin/bash

# Test Memgraph connectivity
docker exec -i gmnap_memgraph mgconsole \
  --host localhost --port 7687 \
  --username gmnap --password v7_lineage \
  <<< "MATCH (m:Mathematician) RETURN count(m);"

# Reset graph data
docker exec -i gmnap_memgraph mgconsole \
  --host localhost --port 7687 \
  --username gmnap --password v7_lineage \
  <<< "MATCH (n) DETACH DELETE n;"
```
