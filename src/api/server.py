"""
GMNAP V7 API Server.

Provides REST endpoints for name authority queries, lineage lookups,
and batch processing per spec section 12.

Rate limits:
  - Free tier: 60 req/min (no auth required)
  - Paid tier: 10,000 req/min (Bearer token)
"""

import hashlib
import hmac
import logging
import os
import threading
import time
from collections import defaultdict
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
class RateLimiter:
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
_HASHCASH_TTL = 300  # stamps valid for 5 minutes
_used_stamps: Dict[str, float] = {}  # prevent replay
_stamps_lock = threading.Lock()


def verify_hashcash(stamp: str, required_bits: int = HASHCASH_BITS) -> bool:
    """Verify a hashcash stamp has sufficient leading zero bits.

    Format: ver:bits:date:resource::rand:counter
    Example: 1:18:260316:gmnap-api::abc123:42
    """
    if not stamp:
        return False

    now = time.time()

    with _stamps_lock:
        # Prevent replay
        if stamp in _used_stamps:
            return False

        # Prune old stamps periodically
        if len(_used_stamps) > 10_000:
            cutoff = now - _HASHCASH_TTL
            expired = [k for k, v in _used_stamps.items() if v < cutoff]
            for k in expired:
                del _used_stamps[k]

        # Verify leading zero bits
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
_rate_limiter = RateLimiter()

# Bearer tokens for paid tier (loaded from env)
_PAID_TOKENS = set(
    t.strip() for t in os.getenv("GMNAP_API_TOKENS", "").split(",") if t.strip()
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="GMNAP V7 API",
        description="Global Mathematician Name Authority Project — REST API",
        version="7.0",
    )

    cors_origins = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:3000"
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization", "X-Hashcash"],
    )

    # ------------------------------------------------------------------
    # Security headers middleware
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
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

        # V7 spec §12: free tier requires hashcash 18-bit PoW for /api/ endpoints
        path = request.url.path
        if not is_paid and path.startswith("/api/"):
            stamp = request.headers.get("X-Hashcash", "")
            if not verify_hashcash(stamp):
                return JSONResponse(
                    status_code=402,
                    content={
                        "detail": "Free tier requires X-Hashcash header (18-bit PoW)",
                        "info": "Format: 1:18:YYMMDD:gmnap-api::rand:counter",
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
        """Readiness probe — checks graph DB if configured."""
        graph_ok = True
        bolt_uri = os.getenv("MEMGRAPH_BOLT", "")
        if bolt_uri:
            try:
                # Attempt a connection check
                import socket

                host, port = bolt_uri.replace("bolt://", "").split(":")
                s = socket.create_connection((host, int(port)), timeout=2)
                s.close()
            except Exception:
                graph_ok = False

        if not graph_ok:
            raise HTTPException(status_code=503, detail="Graph DB not ready")

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
        format: str = Query("json", description="Output format: json/dot/svg"),
    ):
        """Query academic genealogy lineage for a GlobalID."""
        bolt_uri = os.getenv("MEMGRAPH_BOLT", "bolt://localhost:7687")

        # Try neo4j first
        try:
            from src.genealogy.query import lineage_to_dot, query_lineage

            result = query_lineage(global_id, depth=depth, bolt_uri=bolt_uri)
            if result:
                if format == "dot":
                    from starlette.responses import PlainTextResponse

                    return PlainTextResponse(
                        lineage_to_dot(result), media_type="text/vnd.graphviz"
                    )
                return result
        except ImportError:
            pass  # Fall through to local YAML
        except Exception as e:
            logger.debug(f"Neo4j lineage query failed: {e}")

        # Fallback: local YAML files (from pipeline output)
        try:
            from src.cli.gmnap import _query_lineage_graph

            edges = _query_lineage_graph(global_id, depth)
            if edges:
                result = {"root": global_id, "depth": depth, "edges": edges}
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

            edges = GenealogyLookup().traverse_lineage(global_id, depth)
            if edges:
                if format == "dot":
                    from starlette.responses import PlainTextResponse

                    from src.cli.gmnap import _edges_to_dot

                    return PlainTextResponse(
                        _edges_to_dot(global_id, edges),
                        media_type="text/vnd.graphviz",
                    )
                return {"root": global_id, "depth": depth, "edges": edges}
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
    async def metrics():
        """Prometheus-compatible metrics endpoint."""
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

    return app


# Module-level app instance for uvicorn
app = create_app()
