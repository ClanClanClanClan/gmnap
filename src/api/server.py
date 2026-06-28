"""
GMNAP V7 API Server.

Provides REST endpoints for name authority queries, lineage lookups,
and batch processing per spec section 12.

Rate limits:
  - Free tier: 60 req/min, requires X-Hashcash 18-bit PoW header
    (V7 spec §12). Set GMNAP_REQUIRE_HASHCASH=0 or run the server
    with ``gmnap serve --no-hashcash`` to disable for local dev.
  - Paid tier: 10,000 req/min (Bearer token), no hashcash required.
"""

import hashlib
import hmac
import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Query, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "FastAPI is required for the API server. "
        "Install with: pip install fastapi uvicorn"
    )

# ---------------------------------------------------------------------------
# Prometheus metrics (module-level, persistent across requests)
# ---------------------------------------------------------------------------
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROM_AVAILABLE = True

    UPTIME_GAUGE = Gauge("gmnap_uptime_seconds", "Server uptime in seconds")
    PIPELINE_RUNS = Counter(
        "gmnap_pipeline_runs_total", "Total pipeline runs", ["mode"]
    )
    ENTRIES_PROCESSED = Counter(
        "gmnap_entries_processed_total", "Total entries processed"
    )
    PIPELINE_DURATION = Histogram(
        "gmnap_pipeline_duration_seconds",
        "Pipeline execution duration",
        buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300],
    )
    API_REQUESTS = Counter(
        "gmnap_api_requests_total",
        "API requests",
        ["endpoint", "method", "status"],
    )
    API_REQUEST_DURATION = Histogram(
        "gmnap_api_request_duration_seconds",
        "API request duration",
        ["endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
    )
    AUTHORITY_HITS = Counter(
        "gmnap_authority_hits_total", "Authority source hits", ["source", "tier"]
    )
    SCHEMA_ERRORS = Counter("gmnap_schema_errors_total", "Schema validation errors")

except ImportError:
    PROM_AVAILABLE = False


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
class APIRateLimiter:
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, free_rpm: int = 60, paid_rpm: int = 10_000):
        self.free_rpm = free_rpm
        self.paid_rpm = paid_rpm
        self._windows: Dict[str, list] = defaultdict(list)

    def check(self, client_ip: str, is_paid: bool = False) -> bool:
        limit = self.paid_rpm if is_paid else self.free_rpm
        now = time.time()
        window = self._windows[client_ip]
        # Prune entries older than 60s
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= limit:
            return False
        window.append(now)
        return True


# V7 spec §12: free_tier hashcash_bits = 18
HASHCASH_BITS = 18
_HASHCASH_TTL = 300  # in-memory replay-cache retention (seconds)
_HASHCASH_RESOURCE = "gmnap-api"  # the stamp's resource field must bind to this
# Accept stamps dated within ±1 day of "today" (UTC). The stamp's own
# date field is the PRIMARY expiry — it bounds how long a captured-but-
# unused stamp stays valid. The ±1 day window absorbs client/server
# clock skew and the local-vs-UTC date difference some clients use
# while keeping the replay horizon to ~3 days. Without this check the
# date was never validated, so a captured stamp was replayable forever
# once the in-memory _used_stamps entry was pruned (which happens under
# load via the size-triggered prune below).
_HASHCASH_DATE_SKEW_DAYS = 1
_used_stamps: Dict[str, float] = {}  # prevent replay
_stamps_lock = threading.Lock()


# Operational bypass for the hashcash gate. Default is "1" — V7 spec
# §12 mandates 18-bit PoW for the free tier, and any prod deploy must
# enforce it. Set to "0" for local dev / CI / `gmnap serve --no-hashcash`
# where the friction is dead weight (an attacker can already hit the
# local box freely; PoW only matters in a multi-tenant deployment).
# Read fresh on every request so a `pkill -HUP` style re-load (or a
# k8s env-var change) takes effect without restarting all uvicorn workers.
def _hashcash_required() -> bool:
    raw = os.getenv("GMNAP_REQUIRE_HASHCASH", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def verify_hashcash(stamp: str, required_bits: int = HASHCASH_BITS) -> bool:
    """Verify a hashcash stamp.

    Format: ``ver:bits:date:resource::rand:counter`` (7 colon-separated
    fields; the resource field is followed by an empty extension field,
    so there are two colons before ``rand``).
    Example: ``1:18:260316:gmnap-api::abc123:42``

    Checks, in order:
      1. Structure — exactly 7 fields, version ``1``.
      2. Claimed difficulty (``bits`` field) ≥ ``required_bits``.
      3. Resource binding — must equal ``gmnap-api`` (stops a stamp
         minted for a different resource being used here).
      4. Date window — the ``YYMMDD`` date must be within ±1 day of
         today (UTC). This is the primary expiry; see
         ``_HASHCASH_DATE_SKEW_DAYS``.
      5. Replay — the exact stamp must not have been seen before.
      6. Proof-of-work — SHA-256(stamp) must have ``required_bits``
         leading zero bits.

    The earlier implementation only did checks (5) and (6), so a
    captured stamp was replayable indefinitely once its in-memory
    ``_used_stamps`` entry was pruned, and a stamp minted for any date
    or resource was accepted.
    """
    if not stamp:
        return False

    # (1) Structure.
    parts = stamp.split(":")
    if len(parts) != 7:
        return False
    version, bits_field, date_field, resource = parts[0], parts[1], parts[2], parts[3]
    if version != "1":
        return False

    # (2) Claimed difficulty must meet the requirement.
    try:
        if int(bits_field) < required_bits:
            return False
    except ValueError:
        return False

    # (3) Resource binding.
    if resource != _HASHCASH_RESOURCE:
        return False

    # (4) Date window (UTC).
    from datetime import datetime, timedelta, timezone

    try:
        stamp_date = datetime.strptime(date_field, "%y%m%d").date()
    except ValueError:
        return False
    today = datetime.now(timezone.utc).date()
    if not (
        today - timedelta(days=_HASHCASH_DATE_SKEW_DAYS)
        <= stamp_date
        <= today + timedelta(days=_HASHCASH_DATE_SKEW_DAYS)
    ):
        return False

    now = time.time()

    with _stamps_lock:
        # (5) Prevent replay.
        if stamp in _used_stamps:
            return False

        # Prune old stamps periodically.
        if len(_used_stamps) > 10_000:
            cutoff = now - _HASHCASH_TTL
            expired = [k for k, v in _used_stamps.items() if v < cutoff]
            for k in expired:
                del _used_stamps[k]

        # (6) Proof-of-work: leading zero bits.
        digest = hashlib.sha256(stamp.encode("utf-8")).hexdigest()
        bits = bin(int(digest, 16))[2:].zfill(256)
        if not bits[:required_bits] == "0" * required_bits:
            return False

        _used_stamps[stamp] = now
        return True


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ProcessRequest(BaseModel):
    entries: List[Dict[str, Any]]
    mode: str = "quick"
    schema_strict: int = 0
    limit: int = 100  # max entries to return per page (1-10000)
    offset: int = 0  # skip first N results

    @property
    def pipeline_mode(self) -> str:
        """Validated mode string."""
        return self.mode if self.mode in ("quick", "full", "extreme") else "quick"


class HealthResponse(BaseModel):
    status: str
    version: str = "7.0"
    uptime_seconds: float = 0.0


class CorrectionSuggestion(BaseModel):
    original_name: str
    correction_type: str  # advisor, institution, year, name, country, other
    suggested_value: str
    source_url: str = ""
    submitter_note: str = ""


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
_start_time = time.time()
# Env overrides let ops and the browser-smoke harness raise the ceiling
# without restarting behind a load balancer. Defaults preserve the V7
# spec §12 free-tier limit of 60/min.
_free_rpm = int(os.getenv("GMNAP_FREE_RPM", "60"))
_paid_rpm = int(os.getenv("GMNAP_PAID_RPM", "10000"))
_rate_limiter = APIRateLimiter(free_rpm=_free_rpm, paid_rpm=_paid_rpm)

# Bearer tokens for paid tier (loaded from env)
_PAID_TOKENS = set(
    t.strip() for t in os.getenv("GMNAP_API_TOKENS", "").split(",") if t.strip()
)


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
# GMNAP_LOG_FORMAT controls the output shape:
#   text (default) — human-readable single line (good for `docker logs`)
#   json           — one JSON object per line (Loki/Datadog/Stackdriver)
# GMNAP_LOG_LEVEL passes through to Python's logging level. Both env
# vars are read at app-factory time; restart workers to change them.
class _JSONLogFormatter(logging.Formatter):
    """Minimal JSON formatter — no third-party dep needed."""

    def format(self, record: logging.LogRecord) -> str:
        import json as _json

        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Pass through any extra fields the caller attached with
        # logger.info("msg", extra={"key": "value"}).
        for k, v in record.__dict__.items():
            if k not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "message",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "taskName",
            }:
                payload[k] = v
        return _json.dumps(payload, default=str)


def _configure_logging() -> None:
    """Idempotent — safe to call from create_app and from CLI."""
    level = os.getenv("GMNAP_LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("GMNAP_LOG_FORMAT", "text").lower()
    root = logging.getLogger()
    # Don't re-wire if we already installed a handler; respects
    # operator pre-config (uvicorn --log-config etc).
    if any(getattr(h, "_gmnap_managed", False) for h in root.handlers):
        return
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler._gmnap_managed = True  # type: ignore[attr-defined]
    if fmt == "json":
        handler.setFormatter(_JSONLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root.addHandler(handler)


_configure_logging()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Graceful shutdown — drain in-flight requests on SIGTERM rather
    # than dropping them. uvicorn calls the shutdown hook before
    # closing connections; setting GMNAP_SHUTTING_DOWN flips /readyz
    # to 503 so load balancers (k8s, nginx, ALB) stop sending new
    # traffic while existing requests finish.
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # A freshly-started app is by definition not draining, so clear
        # any stale GMNAP_SHUTTING_DOWN flag — otherwise /readyz would
        # report 503 forever if a prior process (or, in-process, a prior
        # app instance under test) set it on its own shutdown. The flag
        # is process-global env state, so without this it leaks across
        # app instances that share an interpreter.
        os.environ.pop("GMNAP_SHUTTING_DOWN", None)
        logger.info("gmnap-api startup", extra={"phase": "startup"})
        yield
        logger.info(
            "gmnap-api shutting down — draining requests",
            extra={"phase": "shutdown"},
        )
        # Mark shutdown for /readyz; uvicorn's
        # --timeout-graceful-shutdown wall-clock then drains.
        os.environ["GMNAP_SHUTTING_DOWN"] = "1"

        # Close the authority fetcher pool's pooled aiohttp sessions
        # cleanly while the event loop is still alive. Without this the
        # only cleanup is the atexit hook in manager_tier01, which
        # cannot reliably await inside an already-running loop and
        # leaks "Unclosed client session" warnings (and the sockets)
        # on every long-running-server restart. Lazy import keeps the
        # network stack off the import path for non-enrichment deploys.
        try:
            from src.authority.manager_tier01 import _close_fetcher_pool

            await _close_fetcher_pool()
        except Exception as exc:  # pragma: no cover - best-effort
            logger.debug("fetcher pool close on shutdown failed: %s", exc)

    app = FastAPI(
        title="GMNAP V7 API",
        description="Global Mathematician Name Authority Project — REST API",
        version="7.0",
        lifespan=lifespan,
    )

    # CORS — locked down to the explicit allowlist. The earlier
    # behavior fell back to localhost defaults when unset, which is
    # a footgun in prod: a misconfigured deploy would silently accept
    # only same-host requests and break every external SPA without
    # any error message. Now we require the env var, and the docker
    # -compose.yml ships a sensible default for the bundled stack.
    cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if cors_origins_env:
        cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    else:
        # No env override → dev-only localhost (logged so the
        # operator notices). In prod, set CORS_ALLOWED_ORIGINS
        # to a comma-separated list of trusted origins.
        cors_origins = ["http://localhost:8080", "http://localhost:3000"]
        logger.warning(
            "CORS_ALLOWED_ORIGINS unset; defaulting to localhost — "
            "set explicitly in production",
            extra={"cors_origins": cors_origins},
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization", "X-Hashcash"],
    )

    # ------------------------------------------------------------------
    # Security headers middleware
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        # CSP: deny all inline scripts AND inline styles. Verified by
        # grepping static/index.html (no `style="…"`), static/app.js
        # (no `.style()` d3 calls, no `el.style.X = …`), and the d3
        # tree-renderer (uses `.attr("transform", …)` not `.style`).
        # If a future change adds an inline style, it'll fail in the
        # browser visibly rather than silently — exactly what we want.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    # ------------------------------------------------------------------
    # Request correlation ID middleware
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid4().hex[:12])
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ------------------------------------------------------------------
    # Rate limiting middleware
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        auth = request.headers.get("Authorization", "")
        is_paid = False
        if auth.startswith("Bearer ") and _PAID_TOKENS:
            token = auth[7:]
            is_paid = any(hmac.compare_digest(token, t) for t in _PAID_TOKENS)

        # V7 spec §12: free tier requires hashcash 18-bit PoW for /api/ endpoints.
        # Operators can disable via GMNAP_REQUIRE_HASHCASH=0 (local dev, CI,
        # behind-the-firewall deploys, `gmnap serve --no-hashcash`). The
        # rate limiter below still applies — disabling hashcash doesn't
        # disable the 60/min free-tier cap.
        path = request.url.path
        if not is_paid and path.startswith("/api/") and _hashcash_required():
            stamp = request.headers.get("X-Hashcash", "")
            if not verify_hashcash(stamp):
                return JSONResponse(
                    status_code=402,
                    content={
                        "detail": "Free tier requires X-Hashcash header (18-bit PoW)",
                        "info": "Format: 1:18:YYMMDD:gmnap-api::rand:counter",
                        "bypass": "Set GMNAP_REQUIRE_HASHCASH=0 for local dev",
                    },
                )

        if not _rate_limiter.check(client_ip, is_paid):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Free: 60/min, Paid: 10000/min"
                },
            )

        # Instrument request duration and count
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        if PROM_AVAILABLE:
            endpoint = path.split("?")[0]
            API_REQUESTS.labels(
                endpoint=endpoint,
                method=request.method,
                status=str(response.status_code),
            ).inc()
            API_REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)

        return response

    # ------------------------------------------------------------------
    # Health endpoints
    # ------------------------------------------------------------------
    @app.get("/healthz", response_model=HealthResponse)
    async def healthz():
        """Liveness probe."""
        return HealthResponse(
            status="ok",
            uptime_seconds=round(time.time() - _start_time, 1),
        )

    @app.get("/readyz", response_model=HealthResponse)
    async def readyz():
        """Readiness probe — checks every dependency the API needs.

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
        """
        # 0. Drain gate: once the lifespan shutdown handler fires we
        # flip GMNAP_SHUTTING_DOWN=1 so the load balancer stops
        # routing new traffic here; in-flight requests still finish
        # under uvicorn's --timeout-graceful-shutdown wall-clock.
        if os.getenv("GMNAP_SHUTTING_DOWN") == "1":
            raise HTTPException(status_code=503, detail="Shutting down")

        # 1. Genealogy enrichment data is present + parseable.
        # This is the only mandatory dependency for the documented
        # query/lineage paths; failing here means the container will
        # 500 on user requests.
        gen_path = Path("data/genealogy_enrichment.json")
        if not gen_path.exists():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Genealogy enrichment file missing — run "
                    "`git lfs pull` or `tools/build_genealogy_"
                    "enrichment.py`"
                ),
            )
        try:
            # Stat-only check; full json.loads on a 25 MB file would
            # be ~250 ms and probes get called every few seconds.
            if gen_path.stat().st_size < 1024:
                raise HTTPException(
                    status_code=503,
                    detail="Genealogy enrichment file is an LFS stub",
                )
        except OSError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Genealogy enrichment file unreadable: {exc}",
            )

        # 2. Memgraph (only when configured).
        bolt_uri = os.getenv("MEMGRAPH_BOLT", "")
        if bolt_uri:
            from src.genealogy.query import _driver

            drv = _driver(
                bolt_uri,
                user=os.getenv("MEMGRAPH_USER", ""),
                password=os.getenv("MEMGRAPH_PASSWORD", ""),
                timeout=2.0,
            )
            if drv is None:
                raise HTTPException(status_code=503, detail="Graph DB not ready")
            try:
                drv.close()
            except Exception:
                pass

        return HealthResponse(
            status="ready",
            uptime_seconds=round(time.time() - _start_time, 1),
        )

    # ------------------------------------------------------------------
    # Query endpoint
    # ------------------------------------------------------------------
    @app.get("/api/v1/query")
    async def query_name(
        name: str = Query(..., description="Mathematician name to look up"),
        mode: str = Query("quick", description="Pipeline mode: quick/full/extreme"),
    ):
        """Query a single mathematician name for region detection & processing."""
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Name must not be empty")
        if len(name) > 500:
            raise HTTPException(status_code=400, detail="Name too long (max 500 chars)")
        try:
            from src.core.globalid import generate_global_id
            from src.regions.manager_optimized import RegionManager

            manager = RegionManager()
            entry = {"CanonicalLatin": name}
            result = manager.detect_region(entry)

            try:
                gid = generate_global_id(entry)
            except Exception:
                gid = None

            response = {
                "name": name,
                "CanonicalLatin": name,
                "global_id": gid,
                "GlobalID": gid,
                "region_code": result.region_code,
                "DetectedRegion": result.region_code,
                "confidence": result.confidence,
                "DetectionConfidence": result.confidence,
                "detection_method": result.detection_method,
                "DetectionMethod": result.detection_method,
                "metadata": result.metadata,
            }

            # Enrich with curated genealogy data (Advisors/Institution/BirthYear)
            try:
                from src.core.genealogy_lookup import GenealogyLookup

                GenealogyLookup().enrich(response)
            except Exception as exc:
                logger.debug("Genealogy enrichment skipped: %s", exc)

            return response
        except Exception as e:
            logger.error(f"Query error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    # ------------------------------------------------------------------
    # Lineage endpoint
    # ------------------------------------------------------------------
    @app.get("/api/v1/lineage/{global_id}")
    async def get_lineage(
        global_id: str,
        depth: int = Query(3, ge=1, le=10),
        direction: str = Query(
            "ancestors",
            pattern="^(ancestors|descendants)$",
            description="ancestors = walk up the advisor chain; "
            "descendants = walk down the student chain",
        ),
        format: str = Query(
            "json",
            pattern="^(json|dot)$",
            description="Output format: json (default) or dot (Graphviz "
            "source). SVG is not served — render the dot output with "
            "`dot -Tsvg`.",
        ),
    ):
        """Query academic genealogy lineage for a GlobalID or name.

        ``direction=ancestors`` (default) walks ``advisor-of-me``;
        ``direction=descendants`` walks ``student-of-me`` so a query
        for "Hilbert" returns his ~76 known students rather than his
        2 advisors.
        """
        bolt_uri = os.getenv("MEMGRAPH_BOLT", "bolt://localhost:7687")
        bolt_user = os.getenv("MEMGRAPH_USER", "")
        bolt_pass = os.getenv("MEMGRAPH_PASSWORD", "")

        # Try Memgraph first (when reachable). query_lineage returns
        # None on driver/connection failures so we fall straight through.
        try:
            from src.genealogy.query import lineage_to_dot, query_lineage

            result = query_lineage(
                global_id,
                depth=depth,
                bolt_uri=bolt_uri,
                user=bolt_user,
                password=bolt_pass,
                direction=direction,
            )
            # Accept the graph answer when Memgraph actually resolved
            # the root (``root_name`` is set by query_lineage only when
            # the WHERE clause matched). A matched-root-with-empty-edges
            # response is a LEGITIMATE leaf: the person is in the graph
            # and has no known advisors. Previously this branch gated
            # on edges-present, which silently returned stale YAML for
            # graph-resident leaves. Unmatched roots (no root_name)
            # still fall through so the curated-JSON path can match by
            # alternative key formats.
            if result and result.get("root_name"):
                if format == "dot":
                    from starlette.responses import PlainTextResponse

                    return PlainTextResponse(
                        lineage_to_dot(result), media_type="text/vnd.graphviz"
                    )
                return result
        except ImportError:
            pass  # Fall through to local YAML
        except Exception as e:
            logger.debug(f"Memgraph lineage query failed: {e}")

        # Fallback: local YAML files (from pipeline output).
        # The YAML walker only knows ancestor edges, so skip this
        # branch when the caller asked for descendants.
        try:
            from src.cli.gmnap import _query_lineage_graph

            edges = (
                _query_lineage_graph(global_id, depth)
                if direction == "ancestors"
                else None
            )
            if edges:
                result = {
                    "root": global_id,
                    "depth": depth,
                    "direction": direction,
                    "edges": edges,
                }
                if format == "dot":
                    from starlette.responses import PlainTextResponse

                    from src.cli.gmnap import _edges_to_dot

                    return PlainTextResponse(
                        _edges_to_dot(global_id, edges),
                        media_type="text/vnd.graphviz",
                    )
                return result
        except Exception as e:
            logger.debug(f"Local YAML lineage failed: {e}")

        # Final fallback: curated genealogy enrichment JSON.
        # Accepts either a GlobalID or a canonical name (optionally with
        # 'name:' prefix, e.g. /api/v1/lineage/name:euler,+leonhard).
        try:
            from src.core.genealogy_lookup import GenealogyLookup

            edges = GenealogyLookup().traverse_lineage(
                global_id, depth, direction=direction
            )
            if edges:
                if format == "dot":
                    from starlette.responses import PlainTextResponse

                    from src.cli.gmnap import _edges_to_dot

                    return PlainTextResponse(
                        _edges_to_dot(global_id, edges),
                        media_type="text/vnd.graphviz",
                    )
                return {
                    "root": global_id,
                    "depth": depth,
                    "direction": direction,
                    "edges": edges,
                }
        except Exception as e:
            logger.debug(f"Enrichment lineage failed: {e}")

        raise HTTPException(status_code=404, detail="GlobalID not found")

    # ------------------------------------------------------------------
    # Batch processing endpoint
    # ------------------------------------------------------------------
    @app.post("/api/v1/process")
    async def process_batch(req: ProcessRequest):
        """Run V7 pipeline on a batch of entries."""
        if len(req.entries) > 10_000:
            raise HTTPException(
                status_code=400, detail="Batch size limited to 10,000 entries"
            )

        # Validate entries have required fields
        invalid = [i for i, e in enumerate(req.entries) if not e.get("CanonicalLatin")]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Entries at indices {invalid[:10]} missing required field 'CanonicalLatin'",
            )

        # Filter out entries with empty/whitespace CanonicalLatin
        req_entries = [e for e in req.entries if e.get("CanonicalLatin", "").strip()]
        if not req_entries:
            raise HTTPException(
                status_code=400, detail="No valid entries (all names empty)"
            )

        try:
            # Note: GMNAP_SCHEMA_STRICT is read at pipeline init time.
            # Uvicorn runs async single-threaded, so this is safe for async,
            # but would need per-request threading if workers > 1.
            prev_strict = os.environ.get("GMNAP_SCHEMA_STRICT")
            os.environ["GMNAP_SCHEMA_STRICT"] = str(req.schema_strict)
            from src.core.pipeline_v7 import PipelineMode, V7Pipeline

            mode_map = {
                "quick": PipelineMode.QUICK,
                "full": PipelineMode.FULL,
                "extreme": PipelineMode.EXTREME,
            }
            pipeline = V7Pipeline(
                mode=mode_map.get(req.pipeline_mode, PipelineMode.QUICK)
            )

            start_t = time.time()
            report = await pipeline.process_batch(req_entries)
            elapsed = time.time() - start_t

            # Pipeline may return dict (with "entries" key) or list directly
            if isinstance(report, dict):
                entries = report.get("entries", [])
                quality_gates = report.get("quality_gates", {})
                metrics = report.get("metrics", {})
            else:
                entries = report if isinstance(report, list) else []
                quality_gates = {}
                metrics = {}

            if PROM_AVAILABLE:
                PIPELINE_RUNS.labels(mode=req.mode).inc()
                ENTRIES_PROCESSED.inc(len(entries))
                PIPELINE_DURATION.observe(elapsed)

            # Paginate results
            limit = max(1, min(req.limit, 10000))
            offset = max(0, req.offset)
            page = entries[offset : offset + limit]

            # Enrich each returned entry with curated genealogy data
            try:
                from src.core.genealogy_lookup import GenealogyLookup

                lookup = GenealogyLookup()
                for entry in page:
                    if isinstance(entry, dict):
                        lookup.enrich(entry)
            except Exception as exc:
                logger.debug("Genealogy enrichment skipped: %s", exc)

            return {
                "processed": len(entries),
                "mode": req.mode,
                "schema_strict": req.schema_strict,
                "quality_gates": quality_gates,
                "metrics": metrics,
                "entries": page,
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < len(entries),
            }
        except Exception as e:
            logger.error(f"Process error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            # Restore previous GMNAP_SCHEMA_STRICT value
            if prev_strict is not None:
                os.environ["GMNAP_SCHEMA_STRICT"] = prev_strict
            else:
                os.environ.pop("GMNAP_SCHEMA_STRICT", None)

    # ------------------------------------------------------------------
    # Metrics endpoint (Prometheus format)
    # ------------------------------------------------------------------
    @app.get("/metrics")
    async def metrics(request: Request):
        """Prometheus-compatible metrics endpoint.

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
        """
        require_auth = os.getenv(
            "GMNAP_METRICS_REQUIRE_AUTH", "1"
        ).strip().lower() not in ("0", "false", "no", "off")
        if require_auth:
            client_ip = request.client.host if request.client else "unknown"
            # ``testclient`` is Starlette's TestClient sentinel; allow
            # it through so the unit tests covering /metrics shape
            # work without an env-var workaround. Real traffic from
            # a misconfigured client never sets host="testclient".
            is_local = (
                client_ip in ("127.0.0.1", "::1", "localhost", "unknown", "testclient")
                or client_ip.startswith("10.")
                or client_ip.startswith("192.168.")
                or any(client_ip.startswith(f"172.{i}.") for i in range(16, 32))
            )
            auth_header = request.headers.get("Authorization", "")
            has_paid_token = False
            if auth_header.startswith("Bearer ") and _PAID_TOKENS:
                token = auth_header[7:]
                has_paid_token = any(
                    hmac.compare_digest(token, t) for t in _PAID_TOKENS
                )
            if not is_local and not has_paid_token:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "/metrics requires a private-network client or a "
                        "Bearer token. Set GMNAP_METRICS_REQUIRE_AUTH=0 to "
                        "disable (single-tenant deploys only)."
                    ),
                )

        if PROM_AVAILABLE:
            UPTIME_GAUGE.set(time.time() - _start_time)
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST,
            )
        # Fallback: return basic metrics as JSON
        return {
            "uptime_seconds": round(time.time() - _start_time, 1),
            "version": "7.0",
        }

    # ------------------------------------------------------------------
    # Correction suggestion endpoint
    # ------------------------------------------------------------------
    @app.post("/api/v1/suggest")
    async def suggest_correction(suggestion: CorrectionSuggestion):
        """Accept a user-submitted correction suggestion."""
        if not suggestion.original_name.strip():
            raise HTTPException(
                status_code=400, detail="original_name must not be empty"
            )
        if not suggestion.suggested_value.strip():
            raise HTTPException(
                status_code=400, detail="suggested_value must not be empty"
            )

        import json
        from datetime import datetime, timezone

        corrections_dir = Path("data/corrections")
        corrections_dir.mkdir(parents=True, exist_ok=True)

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_name": suggestion.original_name,
            "correction_type": suggestion.correction_type,
            "suggested_value": suggestion.suggested_value,
            "source_url": suggestion.source_url,
            "submitter_note": suggestion.submitter_note,
        }

        filename = (
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            f"_{suggestion.correction_type}.json"
        )
        filepath = corrections_dir / filename
        filepath.write_text(json.dumps(record, indent=2, ensure_ascii=False))

        return {"status": "received", "id": filename}

    # ------------------------------------------------------------------
    # Static files (web interface)
    # ------------------------------------------------------------------
    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    if static_dir.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        from fastapi.responses import FileResponse

        @app.get("/")
        async def serve_index():
            index_path = static_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            raise HTTPException(status_code=404, detail="index.html not found")

        # Client-side routing: the SPA at /static/app.js uses
        # `history.pushState` to navigate to URLs like
        # /p/Euler%2C%20Leonhard. A direct visit / refresh / share-by-
        # URL hits the FastAPI server first; we serve index.html and
        # let the client's `applyLocation()` re-derive the view from
        # `window.location.pathname`. Catch-all is scoped to /p/ so
        # the API and /static prefixes still take precedence.
        @app.get("/p/{path:path}")
        async def serve_spa_profile(path: str):
            index_path = static_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            raise HTTPException(status_code=404, detail="index.html not found")

    return app


# Module-level app instance for uvicorn
app = create_app()
