#!/usr/bin/env python3
"""
GMNAP CLI - Command-line interface for GMNAP V7
Provides 'serve' command for HTTP server deployment
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure PYTHONPATH includes project root
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import after path is set
try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import PlainTextResponse, JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    logger.warning("FastAPI not available. Install with: pip install fastapi uvicorn")
    FASTAPI_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("prometheus_client not available. Install with: pip install prometheus-client")
    PROMETHEUS_AVAILABLE = False

from src.regions.manager_optimized import RegionManager

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    logger.warning("neo4j package not available. Genealogy endpoints disabled.")
    NEO4J_AVAILABLE = False

from pydantic import BaseModel
from typing import List

# Genealogy API models
class LineagePath(BaseModel):
    length: int
    nodes: List[str]

class LineageResponse(BaseModel):
    start: str
    depth: int
    paths: List[LineagePath]


class GMNAPServer:
    """
    Production HTTP server for GMNAP V7

    Implements deployment pack requirements:
    - /healthz - Kubernetes liveness probe
    - /readyz - Kubernetes readiness probe
    - /metrics - Prometheus metrics endpoint
    - /api/v1/process - Process single entry
    - /api/v1/batch - Process batch of entries

    Modes (via GMNAP_MODE):
    - QUICK: Offline only, no authority calls (default)
    - FULL: Controlled authority calls (tier-0+1)
    - EXTREME: All authority tiers enabled
    """

    def __init__(self):
        self.app = None
        self.manager = None
        self.start_time = time.time()

        # Load configuration from environment
        self.mode = os.getenv("GMNAP_MODE", "QUICK").upper()
        self.live_auth = os.getenv("LIVE_AUTH", "0") == "1"
        self.port = int(os.getenv("PORT", "8080"))
        self.host = os.getenv("HOST", "0.0.0.0")

        # Streaming configuration
        self.streaming_threshold = int(os.getenv("STREAMING_THRESHOLD", "10000"))
        self.streaming_chunk = int(os.getenv("STREAMING_CHUNK_SIZE", "2000"))
        self.streaming_inflight = int(os.getenv("STREAMING_INFLIGHT_LIMIT", "4"))

        # Validate mode
        if self.mode not in ["QUICK", "FULL", "EXTREME"]:
            logger.warning(f"Invalid GMNAP_MODE={self.mode}, using QUICK")
            self.mode = "QUICK"

        # Initialize Prometheus metrics if available
        if PROMETHEUS_AVAILABLE:
            self._init_metrics()

        logger.info(f"GMNAP Server initialized - Mode: {self.mode}, Live Auth: {self.live_auth}")

    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        self.metrics_entries_ok = Counter(
            'gmnap_entries_ok_total',
            'Total number of successfully processed entries'
        )
        self.metrics_entries_failed = Counter(
            'gmnap_entries_failed_total',
            'Total number of failed entries'
        )
        self.metrics_processing_duration = Histogram(
            'gmnap_processing_duration_seconds',
            'Entry processing duration in seconds',
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        self.metrics_batch_size = Histogram(
            'gmnap_batch_size',
            'Batch size distribution',
            buckets=[1, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000]
        )
        self.metrics_authority_calls = Counter(
            'gmnap_authority_calls_total',
            'Total authority API calls',
            ['source', 'status']
        )
        self.metrics_detection_method = Counter(
            'gmnap_detection_method_total',
            'Detection method used',
            ['method']
        )
        self.metrics_active_requests = Gauge(
            'gmnap_active_requests',
            'Number of currently active requests'
        )

        logger.info("Prometheus metrics initialized")

    def _setup_fastapi(self):
        """Setup FastAPI application with all required endpoints"""
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPI not available, cannot create server")
            return None

        app = FastAPI(
            title="GMNAP V7",
            description="Global Mathematician Name Authority Pipeline",
            version="7.0.0",
            docs_url="/docs" if os.getenv("ENABLE_DOCS", "0") == "1" else None
        )

        # Health endpoints for Kubernetes
        @app.get("/healthz")
        async def healthz():
            """
            Liveness probe - basic health check
            Returns 200 if server is running
            """
            return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

        @app.get("/readyz")
        async def readyz():
            """
            Readiness probe - check if server is ready to handle requests
            Checks dependencies: RegionManager, optional Memgraph/Redis
            """
            checks = {
                "manager": False,
                "ml_models": False
            }

            try:
                # Check if manager is initialized
                if self.manager is not None:
                    checks["manager"] = True
                    # Check if ML models are loaded
                    if hasattr(self.manager, '_ml_models_loaded'):
                        checks["ml_models"] = self.manager._ml_models_loaded

                # Overall ready if manager is available
                ready = checks["manager"]

                if ready:
                    return {
                        "status": "ready",
                        "checks": checks,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    return JSONResponse(
                        status_code=503,
                        content={
                            "status": "not ready",
                            "checks": checks,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
            except Exception as e:
                logger.error(f"Readiness check failed: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        @app.get("/metrics")
        async def metrics():
            """
            Prometheus metrics endpoint
            Exports metrics in Prometheus text format
            """
            if not PROMETHEUS_AVAILABLE:
                return PlainTextResponse(
                    "# Prometheus client not available\n",
                    media_type="text/plain"
                )

            try:
                metrics_output = generate_latest()
                return Response(
                    content=metrics_output,
                    media_type=CONTENT_TYPE_LATEST
                )
            except Exception as e:
                logger.error(f"Metrics generation failed: {e}")
                return PlainTextResponse(
                    f"# Error generating metrics: {e}\n",
                    media_type="text/plain"
                )

        @app.get("/")
        async def root():
            """Root endpoint with server information"""
            uptime_seconds = time.time() - self.start_time

            return {
                "service": "GMNAP V7",
                "version": "7.0.0",
                "mode": self.mode,
                "live_auth": self.live_auth,
                "uptime_seconds": uptime_seconds,
                "status": "operational",
                "endpoints": {
                    "health": "/healthz",
                    "readiness": "/readyz",
                    "metrics": "/metrics",
                    "process": "/api/v1/process",
                    "batch": "/api/v1/batch"
                }
            }

        @app.post("/api/v1/process")
        async def process_single(entry: Dict[str, Any]):
            """
            Process a single mathematician entry

            Args:
                entry: Entry dict with CanonicalLatin or CanonicalNative

            Returns:
                Detection result with region, confidence, method
            """
            if PROMETHEUS_AVAILABLE:
                self.metrics_active_requests.inc()

            start_time = time.time()

            try:
                if self.manager is None:
                    raise ValueError("RegionManager not initialized")

                # Process entry
                result = self.manager.detect_region(entry)

                # Update metrics
                if PROMETHEUS_AVAILABLE:
                    duration = time.time() - start_time
                    self.metrics_processing_duration.observe(duration)
                    self.metrics_entries_ok.inc()

                    if hasattr(result, 'detection_method'):
                        self.metrics_detection_method.labels(
                            method=result.detection_method
                        ).inc()

                return {
                    "status": "success",
                    "result": {
                        "region_code": result.region_code,
                        "confidence": result.confidence,
                        "detection_method": result.detection_method,
                        "metadata": result.metadata
                    }
                }

            except Exception as e:
                logger.error(f"Processing failed: {e}")

                if PROMETHEUS_AVAILABLE:
                    self.metrics_entries_failed.inc()

                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )

            finally:
                if PROMETHEUS_AVAILABLE:
                    self.metrics_active_requests.dec()

        @app.post("/api/v1/batch")
        async def process_batch(request: Dict[str, Any]):
            """
            Process a batch of mathematician entries

            Args:
                request: {"entries": [...], "options": {...}}

            Returns:
                Batch processing results
            """
            if PROMETHEUS_AVAILABLE:
                self.metrics_active_requests.inc()

            start_time = time.time()

            try:
                if self.manager is None:
                    raise ValueError("RegionManager not initialized")

                entries = request.get("entries", [])

                if not entries:
                    raise ValueError("No entries provided")

                # Update batch size metric
                if PROMETHEUS_AVAILABLE:
                    self.metrics_batch_size.observe(len(entries))

                # Process each entry
                results = []
                success_count = 0
                error_count = 0

                for entry in entries:
                    try:
                        result = self.manager.detect_region(entry)
                        results.append({
                            "status": "success",
                            "region_code": result.region_code,
                            "confidence": result.confidence,
                            "detection_method": result.detection_method
                        })
                        success_count += 1

                        if PROMETHEUS_AVAILABLE:
                            self.metrics_entries_ok.inc()
                            self.metrics_detection_method.labels(
                                method=result.detection_method
                            ).inc()

                    except Exception as e:
                        results.append({
                            "status": "error",
                            "error": str(e)
                        })
                        error_count += 1

                        if PROMETHEUS_AVAILABLE:
                            self.metrics_entries_failed.inc()

                duration = time.time() - start_time
                throughput = len(entries) / duration if duration > 0 else 0

                return {
                    "status": "success",
                    "batch_size": len(entries),
                    "success_count": success_count,
                    "error_count": error_count,
                    "duration_seconds": duration,
                    "throughput_eps": throughput,
                    "results": results
                }

            except Exception as e:
                logger.error(f"Batch processing failed: {e}")

                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )

            finally:
                if PROMETHEUS_AVAILABLE:
                    self.metrics_active_requests.dec()

        # ====================================================================
        # GENEALOGY API ENDPOINTS
        # ====================================================================

        if NEO4J_AVAILABLE:
            genealogy_bolt_uri = os.getenv("GENEALOGY_BOLT_URI", "bolt://localhost:7688")

            def get_genealogy_driver():
                """Get Neo4j driver for genealogy database"""
                return GraphDatabase.driver(genealogy_bolt_uri, auth=None)

            @app.get("/genealogy/lineage/{global_id}", response_model=LineageResponse)
            async def get_lineage(global_id: str, max_depth: int = 10):
                """
                Get academic lineage (ancestors) for a given mathematician

                Args:
                    global_id: GMNAP GlobalID (e.g., GMN-4BEPQLVCZ2RN6X3OSZDYRA)
                    max_depth: Maximum generations to traverse (default: 10)

                Returns:
                    LineageResponse with all ancestor paths
                """
                try:
                    # Validate and sanitize max_depth (Memgraph doesn't support params in patterns)
                    max_depth = max(1, min(int(max_depth), 50))

                    driver = get_genealogy_driver()
                    with driver.session() as sess:
                        # Query for advisors (ancestors)
                        # Note: Using f-string for depth since Memgraph doesn't support $depth in pattern
                        query = f"""
                            MATCH (s:Person)
                            WHERE s.global_id = $id
                            MATCH path = (s)-[:DOCTORAL_ADVISOR*1..{max_depth}]->(advisor:Person)
                            RETURN
                                length(path) as path_length,
                                [node IN nodes(path) | node.global_id] as node_ids,
                                [node IN nodes(path) | node.canonical_name] as node_names
                            ORDER BY path_length ASC
                        """
                        result = sess.run(query, id=global_id)

                        paths = []
                        for record in result:
                            paths.append(LineagePath(
                                length=record["path_length"],
                                nodes=record["node_ids"]
                            ))

                        driver.close()

                        return LineageResponse(
                            start=global_id,
                            depth=max_depth,
                            paths=paths
                        )

                except Exception as e:
                    logger.error(f"Genealogy lineage query failed: {e}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "error": str(e),
                            "message": "Failed to query genealogy database"
                        }
                    )

            @app.get("/genealogy/descendants/{global_id}", response_model=LineageResponse)
            async def get_descendants(global_id: str, max_depth: int = 10):
                """
                Get academic descendants (students) for a given mathematician

                Args:
                    global_id: GMNAP GlobalID
                    max_depth: Maximum generations to traverse (default: 10)

                Returns:
                    LineageResponse with all descendant paths
                """
                try:
                    # Validate and sanitize max_depth (Memgraph doesn't support params in patterns)
                    max_depth = max(1, min(int(max_depth), 50))

                    driver = get_genealogy_driver()
                    with driver.session() as sess:
                        # Query for students (descendants)
                        # Note: Using f-string for depth since Memgraph doesn't support $depth in pattern
                        query = f"""
                            MATCH (advisor:Person)
                            WHERE advisor.global_id = $id
                            MATCH path = (student:Person)-[:DOCTORAL_ADVISOR*1..{max_depth}]->(advisor)
                            RETURN
                                length(path) as path_length,
                                [node IN nodes(path) | node.global_id] as node_ids,
                                [node IN nodes(path) | node.canonical_name] as node_names
                            ORDER BY path_length ASC
                        """
                        result = sess.run(query, id=global_id)

                        paths = []
                        for record in result:
                            paths.append(LineagePath(
                                length=record["path_length"],
                                nodes=record["node_ids"]
                            ))

                        driver.close()

                        return LineageResponse(
                            start=global_id,
                            depth=max_depth,
                            paths=paths
                        )

                except Exception as e:
                    logger.error(f"Genealogy descendants query failed: {e}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "error": str(e),
                            "message": "Failed to query genealogy database"
                        }
                    )

            @app.get("/genealogy/stats")
            async def get_genealogy_stats():
                """
                Get genealogy database statistics

                Returns:
                    Database stats (person count, edge count, etc.)
                """
                try:
                    driver = get_genealogy_driver()
                    with driver.session() as sess:
                        person_count = sess.run("MATCH (p:Person) RETURN count(p) as cnt").single()["cnt"]
                        edge_count = sess.run("MATCH ()-[r:DOCTORAL_ADVISOR]->() RETURN count(r) as cnt").single()["cnt"]

                        # Get confidence distribution
                        conf_result = sess.run("""
                            MATCH ()-[r:DOCTORAL_ADVISOR]->()
                            WITH r.confidence as conf
                            RETURN
                                count(CASE WHEN conf >= 0.9 THEN 1 END) as high,
                                count(CASE WHEN conf >= 0.7 AND conf < 0.9 THEN 1 END) as medium,
                                count(CASE WHEN conf < 0.7 THEN 1 END) as low
                        """).single()

                        driver.close()

                        return {
                            "status": "ok",
                            "database": genealogy_bolt_uri,
                            "statistics": {
                                "persons": person_count,
                                "relationships": edge_count,
                                "confidence_distribution": {
                                    "high": conf_result["high"],
                                    "medium": conf_result["medium"],
                                    "low": conf_result["low"]
                                }
                            }
                        }

                except Exception as e:
                    logger.error(f"Genealogy stats query failed: {e}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "error": str(e)
                        }
                    )
        else:
            logger.warning("Genealogy endpoints not available (neo4j not installed)")

        return app

    def initialize_manager(self):
        """Initialize RegionManager with ML models"""
        logger.info("Initializing RegionManager...")

        try:
            self.manager = RegionManager()

            # Load ML models if they exist (Phase 2)
            fasttext_path = Path("data/ml_training/fasttext_region_model.bin")
            clf_path = Path("data/ml_training/xgb_region_classifier.pkl")

            if fasttext_path.exists() and clf_path.exists():
                logger.info("Loading ML models...")
                self.manager.load_ml_models(
                    fasttext_path=str(fasttext_path),
                    clf_path=str(clf_path)
                )
                logger.info("ML models loaded successfully")
            else:
                logger.warning("ML models not found, Phase 2 detection unavailable")

            # Configure authority cache (Phase 3)
            # In QUICK mode, OFFLINE is forced to 1
            if self.mode == "QUICK":
                os.environ["OFFLINE"] = "1"
                logger.info("QUICK mode: Authority detection disabled (OFFLINE=1)")
            elif self.mode == "FULL" and self.live_auth:
                os.environ["OFFLINE"] = "0"
                logger.info("FULL mode with LIVE_AUTH=1: Authority detection enabled")
            else:
                os.environ["OFFLINE"] = "1"
                logger.info(f"{self.mode} mode: Authority detection disabled (cache-only)")

            logger.info("RegionManager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize RegionManager: {e}")
            return False

    def serve(self):
        """Start the HTTP server"""
        if not FASTAPI_AVAILABLE:
            logger.error("Cannot start server: FastAPI not installed")
            logger.error("Install with: pip install fastapi uvicorn")
            return 1

        # Initialize manager
        if not self.initialize_manager():
            logger.error("Failed to initialize RegionManager, exiting")
            return 1

        # Setup FastAPI app
        self.app = self._setup_fastapi()
        if self.app is None:
            logger.error("Failed to setup FastAPI application")
            return 1

        # Log configuration
        logger.info("=" * 60)
        logger.info("GMNAP V7 Server Starting")
        logger.info("=" * 60)
        logger.info(f"Mode: {self.mode}")
        logger.info(f"Live Auth: {self.live_auth}")
        logger.info(f"Streaming Threshold: {self.streaming_threshold}")
        logger.info(f"Streaming Chunk Size: {self.streaming_chunk}")
        logger.info(f"Streaming Inflight Limit: {self.streaming_inflight}")
        logger.info(f"Host: {self.host}")
        logger.info(f"Port: {self.port}")
        logger.info("=" * 60)
        logger.info("Endpoints:")
        logger.info(f"  Health:     http://{self.host}:{self.port}/healthz")
        logger.info(f"  Readiness:  http://{self.host}:{self.port}/readyz")
        logger.info(f"  Metrics:    http://{self.host}:{self.port}/metrics")
        logger.info(f"  Process:    http://{self.host}:{self.port}/api/v1/process")
        logger.info(f"  Batch:      http://{self.host}:{self.port}/api/v1/batch")
        logger.info("=" * 60)

        # Start server
        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
            return 0
        except Exception as e:
            logger.error(f"Server failed: {e}")
            return 1


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="GMNAP V7 - Global Mathematician Name Authority Pipeline"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Serve command
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start HTTP server for production deployment"
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8080")),
        help="Port to listen on (default: 8080)"
    )
    serve_parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)"
    )

    # Version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information"
    )

    args = parser.parse_args()

    if args.command == "serve":
        # Override with CLI args if provided
        if hasattr(args, 'port'):
            os.environ["PORT"] = str(args.port)
        if hasattr(args, 'host'):
            os.environ["HOST"] = args.host

        server = GMNAPServer()
        return server.serve()

    elif args.command == "version":
        print("GMNAP V7.0.0")
        print(f"Mode: {os.getenv('GMNAP_MODE', 'QUICK')}")
        print(f"Python: {sys.version}")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
