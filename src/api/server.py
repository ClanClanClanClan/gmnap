"""
GMNAP V7 API Server.

Provides REST endpoints for name authority queries, lineage lookups,
and batch processing per spec section 12.

Rate limits:
  - Free tier: 60 req/min (no auth required)
  - Paid tier: 10,000 req/min (Bearer token)
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

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


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ProcessRequest(BaseModel):
    entries: List[Dict[str, Any]]
    mode: str = "quick"
    schema_strict: int = 0


class HealthResponse(BaseModel):
    status: str
    version: str = "7.0"
    uptime_seconds: float = 0.0


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
_start_time = time.time()
_rate_limiter = RateLimiter()

# Bearer tokens for paid tier (loaded from env)
_PAID_TOKENS = set(
    t.strip()
    for t in os.getenv("GMNAP_API_TOKENS", "").split(",")
    if t.strip()
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="GMNAP V7 API",
        description="Global Mathematician Name Authority Project — REST API",
        version="7.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

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
            is_paid = token in _PAID_TOKENS

        if not _rate_limiter.check(client_ip, is_paid):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Free: 60/min, Paid: 10000/min"},
            )
        response = await call_next(request)
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
        try:
            from src.regions.manager_optimized import OptimizedRegionManager

            manager = OptimizedRegionManager()
            entry = {"CanonicalLatin": name}
            result = manager.detect_region(entry)

            return {
                "name": name,
                "region_code": result.region_code,
                "confidence": result.confidence,
                "detection_method": result.detection_method,
                "metadata": result.metadata,
            }
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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

        try:
            from src.genealogy.query import query_lineage

            result = query_lineage(global_id, depth=depth, bolt_uri=bolt_uri)
            if not result:
                raise HTTPException(status_code=404, detail="GlobalID not found")
            return result
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="Genealogy module not available",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Lineage error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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

        try:
            os.environ["GMNAP_SCHEMA_STRICT"] = str(req.schema_strict)
            from src.core.pipeline_v7 import PipelineV7

            pipeline = PipelineV7(mode=req.mode)
            results = await pipeline.run(req.entries)

            return {
                "processed": len(results),
                "mode": req.mode,
                "schema_strict": req.schema_strict,
                "entries": results[:100],  # Limit response size
                "truncated": len(results) > 100,
            }
        except Exception as e:
            logger.error(f"Process error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ------------------------------------------------------------------
    # Metrics endpoint (Prometheus format)
    # ------------------------------------------------------------------
    @app.get("/metrics")
    async def metrics():
        """Prometheus-compatible metrics endpoint."""
        try:
            from prometheus_client import (
                CollectorRegistry,
                Counter,
                Gauge,
                generate_latest,
            )

            registry = CollectorRegistry()
            uptime = Gauge(
                "gmnap_uptime_seconds",
                "Server uptime in seconds",
                registry=registry,
            )
            uptime.set(time.time() - _start_time)

            return Response(
                content=generate_latest(registry),
                media_type="text/plain; charset=utf-8",
            )
        except ImportError:
            # Fallback: return basic metrics as JSON
            return {
                "uptime_seconds": round(time.time() - _start_time, 1),
                "version": "7.0",
            }

    return app


# Module-level app instance for uvicorn
app = create_app()
