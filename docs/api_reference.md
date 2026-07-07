# GMNAP API (spec v7) reference

Auto-generated from the FastAPI OpenAPI schema by
`tools/gen_api_reference.py`. Version: **0.6.0**.

Endpoints: **9**. Re-generate after any endpoint
change with `make api-docs`. The full machine-readable schema
is at `docs/openapi.json`.

## Endpoints

### `GET /`

**Serve Index**

**Responses:**
  - `200` (application/json) — Successful Response

### `GET /api/v1/lineage/{global_id}`

**Get Lineage**

Query academic genealogy lineage for a GlobalID or name.

``direction=ancestors`` (default) walks ``advisor-of-me``;
``direction=descendants`` walks ``student-of-me`` so a query
for "Hilbert" returns his ~76 known students rather than his
2 advisors.

**Parameters:**
  - `global_id` (`string`, path) **(required)**
  - `depth` (`integer`, query)
  - `direction` (`string`, query) — ancestors = walk up the advisor chain; descendants = walk down the student chain
  - `format` (`string`, query) — Output format: json (default) or dot (Graphviz source). SVG is not served — render the dot output with `dot -Tsvg`.

**Responses:**
  - `200` (application/json) — Successful Response
  - `422` (application/json) — Validation Error

### `POST /api/v1/process`

**Process Batch**

Run V7 pipeline on a batch of entries.

**Request body** (`application/json`): `ProcessRequest`

**Responses:**
  - `200` (application/json) — Successful Response
  - `422` (application/json) — Validation Error

### `GET /api/v1/query`

**Query Name**

Query a single mathematician name for region detection & processing.

**Parameters:**
  - `name` (`string`, query) **(required)** — Mathematician name to look up
  - `mode` (`string`, query) — Pipeline mode: quick/full/extreme

**Responses:**
  - `200` (application/json) — Successful Response
  - `422` (application/json) — Validation Error

### `POST /api/v1/suggest`

**Suggest Correction**

Accept a user-submitted correction suggestion.

**Request body** (`application/json`): `CorrectionSuggestion`

**Responses:**
  - `200` (application/json) — Successful Response
  - `422` (application/json) — Validation Error

### `GET /healthz`

**Healthz**

Liveness probe.

**Responses:**
  - `200` (application/json) — Successful Response

### `GET /metrics`

**Metrics**

Prometheus-compatible metrics endpoint.

Defense-in-depth: nginx restricts /metrics to internal CIDRs
(10.x, 172.16-31.x, 192.168.x, 127.0.0.1) at the edge, but
we ALSO check at the app layer because in a k8s pod or a
misconfigured deploy the client_ip is the load-balancer's
address — nginx's IP allowlist alone isn't enough.

Auth path: either (a) the request is from a localhost /
private-CIDR client (typical scrape from a local Prometheus),
OR (b) it presents a Bearer token from GMNAP_API_TOKENS
(typical scrape from a paid-tier monitoring service). Set
GMNAP_METRICS_REQUIRE_AUTH=0 to disable both checks for
single-tenant deploys behind a trusted reverse proxy.

**Responses:**
  - `200` (application/json) — Successful Response

### `GET /p/{path}`

**Serve Spa Profile**

**Parameters:**
  - `path` (`string`, path) **(required)**

**Responses:**
  - `200` (application/json) — Successful Response
  - `422` (application/json) — Validation Error

### `GET /readyz`

**Readyz**

Readiness probe — checks every dependency the API needs.

Strict by design: a 200 from /readyz means an
operator can route real traffic and expect every documented
endpoint to work. We check, in order:

1. The genealogy enrichment JSON exists and is non-trivially
   sized (stat-only — a full json.loads on the ~25 MB file
   would add ~250 ms to a probe that fires every few seconds,
   so we gate on presence + size > 1 KB to catch a missing or
   unpulled LFS stub, not on parseability). The /query,
   /lineage, and /process endpoints all depend on it; a fresh
   container that lost the LFS file would silently degrade
   without this gate.
2. The Memgraph Bolt handshake succeeds (when MEMGRAPH_BOLT is
   set). Uses verify_connectivity() under a 2 s timeout — same
   path as the lineage endpoint.

Earlier implementations opened a raw TCP socket and accepted
any handshake as "ready" — that returned 200 even when
Memgraph was alive but auth was broken or storage was corrupt.

**Responses:**
  - `200` (application/json) — Successful Response

## Component schemas

Pydantic models referenced by the endpoints above.
Property-level detail lives in the underlying class docstrings
in `src/api/server.py` — this section just lists which models
exist so reviewers can grep for them.

| Schema | Properties |
|---|---|
| `CorrectionSuggestion` | `original_name`, `correction_type`, `suggested_value`, `source_url`, `submitter_note` |
| `HTTPValidationError` | `detail` |
| `HealthResponse` | `status`, `version`, `uptime_seconds` |
| `ProcessRequest` | `entries`, `mode`, `schema_strict`, `limit`, `offset` |
| `ValidationError` | `loc`, `msg`, `type` |

## Cross-cutting middleware (not in the schema)

These behaviours are enforced by FastAPI middleware in
`src/api/server.py` and aren't part of the OpenAPI surface:

- **Rate limiting**: 60 req/min for free tier (configurable
  via `GMNAP_FREE_RPM`); 10 000/min for paid Bearer-token tier
  (configurable via `GMNAP_PAID_RPM`). Tokens listed in
  `GMNAP_API_TOKENS` (comma-separated) skip the free gate.
- **Hashcash proof-of-work**: free tier requires an 18-bit
  SHA-256 stamp in the `X-Hashcash` header (~1 s on a modern CPU).
  See `static/app.js:generateHashcash` for the browser miner.
- **Security headers**: CSP `default-src 'self'; script-src 'self';
  style-src 'self'`, HSTS, X-Frame-Options DENY, etc.
- **Prometheus metrics**: every request records latency + status
  on `gmnap_api_request_duration_seconds` /
  `gmnap_api_requests_total`. Scraped from `/metrics`.

## Reproduce

```bash
make api-docs
# or:  PYTHONPATH=. python3 tools/gen_api_reference.py
```
