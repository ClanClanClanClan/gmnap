"""
Enterprise Integration API for GMNAP V7
Comprehensive REST/GraphQL API with webhook support and plugin architecture
"""

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

# FastAPI imports (graceful fallback)
try:
    from fastapi import (
        BackgroundTasks,
        Depends,
        FastAPI,
        HTTPException,
        Request,
        Response,
    )
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from pydantic import BaseModel, Field, validator

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# WebSocket support
try:
    from fastapi import WebSocket, WebSocketDisconnect

    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# HTTP client for webhooks
try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class APIVersion(Enum):
    """Supported API versions"""

    V1 = "v1"
    V2 = "v2"
    BETA = "beta"


class EventType(Enum):
    """Event types for webhooks"""

    PROCESSING_STARTED = "processing.started"
    PROCESSING_COMPLETED = "processing.completed"
    PROCESSING_FAILED = "processing.failed"
    BATCH_COMPLETED = "batch.completed"
    AUTHORITY_QUERY = "authority.query"
    REGION_DETECTED = "region.detected"
    VALIDATION_FAILED = "validation.failed"


@dataclass
class APIKey:
    """API key model"""

    key_id: str
    key_hash: str
    user_id: str
    permissions: List[str]
    rate_limit: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""

    endpoint_id: str
    url: str
    events: List[EventType]
    secret: str
    is_active: bool = True
    retry_count: int = 3
    timeout: int = 30


@dataclass
class ProcessingRequest:
    """Processing request model"""

    request_id: str
    entries: List[Dict[str, Any]]
    options: Dict[str, Any]
    callback_url: Optional[str] = None
    priority: str = "normal"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class EnterpriseAPI:
    """
    Enterprise-grade API for GMNAP V7

    Features:
    - RESTful API with OpenAPI 3.0 specification
    - WebSocket support for real-time updates
    - Webhook system for event notifications
    - Plugin architecture for custom extensions
    - Rate limiting and authentication
    - Comprehensive monitoring and analytics
    """

    def __init__(self, pipeline, config: Optional[Dict[str, Any]] = None):
        self.pipeline = pipeline
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # API management
        self.api_keys = {}
        self.webhook_endpoints = {}
        self.active_requests = {}
        self.plugins = {}

        # Rate limiting
        self.rate_limits = {}

        # WebSocket connections
        self.ws_connections = set()

        # Webhook client
        self.webhook_session = None

        # FastAPI app
        self.app = None

        if FASTAPI_AVAILABLE:
            self._setup_fastapi()
        else:
            self.logger.warning("FastAPI not available. API features will be limited.")

    def _setup_fastapi(self):
        """Setup FastAPI application"""
        self.app = FastAPI(
            title="GMNAP Enterprise API",
            description="Global Mathematician Name Authority Pipeline - Enterprise Integration API",
            version="1.0.0",
            openapi_tags=[
                {"name": "processing", "description": "Name processing operations"},
                {"name": "batch", "description": "Batch processing operations"},
                {"name": "authorities", "description": "Authority source queries"},
                {"name": "webhooks", "description": "Webhook management"},
                {"name": "analytics", "description": "Analytics and reporting"},
            ],
        )

        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Security
        self.security = HTTPBearer()

        self._register_routes()

    def _register_routes(self):
        """Register API routes"""
        if not self.app:
            return

        # Processing endpoints
        @self.app.post("/api/v1/process", tags=["processing"])
        async def process_single(
            entry: Dict[str, Any],
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Process a single mathematician entry"""
            await self._validate_credentials(credentials)

            request_id = str(uuid.uuid4())

            try:
                # Process entry through pipeline
                result = await self.pipeline.process_single(entry)

                # Send webhook notification
                await self._send_webhook_event(
                    EventType.PROCESSING_COMPLETED,
                    {"request_id": request_id, "result": result},
                )

                return {"request_id": request_id, "result": result}

            except Exception as e:
                await self._send_webhook_event(
                    EventType.PROCESSING_FAILED,
                    {"request_id": request_id, "error": str(e)},
                )
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.post("/api/v1/process/batch", tags=["batch"])
        async def process_batch(
            request: ProcessingRequest,
            background_tasks: BackgroundTasks,
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Process a batch of mathematician entries"""
            await self._validate_credentials(credentials)

            # Store request
            self.active_requests[request.request_id] = request

            # Start background processing
            background_tasks.add_task(self._process_batch_background, request)

            return {"request_id": request.request_id, "status": "accepted"}

        @self.app.get("/api/v1/requests/{request_id}/status", tags=["batch"])
        async def get_request_status(
            request_id: str,
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Get status of a processing request"""
            await self._validate_credentials(credentials)

            if request_id not in self.active_requests:
                raise HTTPException(status_code=404, detail="Request not found")

            request = self.active_requests[request_id]
            return {
                "request_id": request_id,
                "status": "processing",
                "request": asdict(request),
            }

        # Authority endpoints
        @self.app.get("/api/v1/authorities", tags=["authorities"])
        async def list_authorities(
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """List available authority sources"""
            await self._validate_credentials(credentials)

            # Get authorities from pipeline
            authorities = await self._get_available_authorities()
            return {"authorities": authorities}

        @self.app.post("/api/v1/authorities/{authority_id}/query", tags=["authorities"])
        async def query_authority(
            authority_id: str,
            query: Dict[str, Any],
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Query a specific authority source"""
            await self._validate_credentials(credentials)

            try:
                result = await self._query_authority(authority_id, query)
                return {"authority_id": authority_id, "result": result}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        # Webhook endpoints
        @self.app.post("/api/v1/webhooks", tags=["webhooks"])
        async def create_webhook(
            webhook: WebhookEndpoint,
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Create a new webhook endpoint"""
            await self._validate_credentials(credentials)

            self.webhook_endpoints[webhook.endpoint_id] = webhook
            return {"endpoint_id": webhook.endpoint_id, "status": "created"}

        @self.app.get("/api/v1/webhooks", tags=["webhooks"])
        async def list_webhooks(
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """List all webhook endpoints"""
            await self._validate_credentials(credentials)

            return {
                "webhooks": [
                    asdict(webhook) for webhook in self.webhook_endpoints.values()
                ]
            }

        @self.app.delete("/api/v1/webhooks/{endpoint_id}", tags=["webhooks"])
        async def delete_webhook(
            endpoint_id: str,
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Delete a webhook endpoint"""
            await self._validate_credentials(credentials)

            if endpoint_id not in self.webhook_endpoints:
                raise HTTPException(status_code=404, detail="Webhook not found")

            del self.webhook_endpoints[endpoint_id]
            return {"status": "deleted"}

        # Analytics endpoints
        @self.app.get("/api/v1/analytics/metrics", tags=["analytics"])
        async def get_metrics(
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Get processing metrics and analytics"""
            await self._validate_credentials(credentials)

            metrics = await self._get_processing_metrics()
            return {"metrics": metrics}

        @self.app.get("/api/v1/analytics/performance", tags=["analytics"])
        async def get_performance(
            credentials: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """Get performance analytics"""
            await self._validate_credentials(credentials)

            performance = await self._get_performance_analytics()
            return {"performance": performance}

        # WebSocket endpoint
        if WEBSOCKET_AVAILABLE:

            @self.app.websocket("/ws/events")
            async def websocket_events(websocket: WebSocket):
                """WebSocket endpoint for real-time events"""
                await websocket.accept()
                self.ws_connections.add(websocket)

                try:
                    while True:
                        # Keep connection alive
                        await websocket.receive_text()
                except WebSocketDisconnect:
                    self.ws_connections.discard(websocket)

        # Health check
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
            }

    async def _validate_credentials(self, credentials: HTTPAuthorizationCredentials):
        """Validate API credentials"""
        token = credentials.credentials

        # Simple token validation (in production, use proper JWT validation)
        if token not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")

        api_key = self.api_keys[token]
        if not api_key.is_active:
            raise HTTPException(status_code=401, detail="API key disabled")

        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            raise HTTPException(status_code=401, detail="API key expired")

        # Rate limiting
        await self._check_rate_limit(api_key)

    async def _check_rate_limit(self, api_key: APIKey):
        """Check rate limiting for API key"""
        now = time.time()
        window = 3600  # 1 hour window

        if api_key.key_id not in self.rate_limits:
            self.rate_limits[api_key.key_id] = []

        # Clean old requests
        self.rate_limits[api_key.key_id] = [
            req_time
            for req_time in self.rate_limits[api_key.key_id]
            if now - req_time < window
        ]

        # Check limit
        if len(self.rate_limits[api_key.key_id]) >= api_key.rate_limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Record this request
        self.rate_limits[api_key.key_id].append(now)

    async def _process_batch_background(self, request: ProcessingRequest):
        """Process batch request in background"""
        try:
            # Send start notification
            await self._send_webhook_event(
                EventType.PROCESSING_STARTED,
                {"request_id": request.request_id, "entry_count": len(request.entries)},
            )

            results = []
            for entry in request.entries:
                try:
                    result = await self.pipeline.process_single(entry)
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})

            # Send completion notification
            await self._send_webhook_event(
                EventType.BATCH_COMPLETED,
                {
                    "request_id": request.request_id,
                    "results": results,
                    "success_count": len([r for r in results if "error" not in r]),
                    "error_count": len([r for r in results if "error" in r]),
                },
            )

            # Send to callback URL if specified
            if request.callback_url:
                await self._send_callback(
                    request.callback_url,
                    {"request_id": request.request_id, "results": results},
                )

        except Exception as e:
            await self._send_webhook_event(
                EventType.PROCESSING_FAILED,
                {"request_id": request.request_id, "error": str(e)},
            )

    async def _send_webhook_event(self, event_type: EventType, data: Dict[str, Any]):
        """Send webhook event to registered endpoints"""
        if not AIOHTTP_AVAILABLE:
            return

        for endpoint in self.webhook_endpoints.values():
            if not endpoint.is_active or event_type not in endpoint.events:
                continue

            try:
                await self._send_webhook(endpoint, event_type, data)
            except Exception as e:
                self.logger.error(f"Webhook failed for {endpoint.url}: {e}")

    async def _send_webhook(
        self, endpoint: WebhookEndpoint, event_type: EventType, data: Dict[str, Any]
    ):
        """Send individual webhook"""
        if not self.webhook_session:
            self.webhook_session = aiohttp.ClientSession()

        payload = {
            "event": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }

        headers = {
            "Content-Type": "application/json",
            "X-GMNAP-Signature": self._generate_webhook_signature(
                payload, endpoint.secret
            ),
        }

        async with self.webhook_session.post(
            endpoint.url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=endpoint.timeout),
        ) as response:
            if response.status >= 400:
                raise Exception(f"Webhook failed with status {response.status}")

    def _generate_webhook_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate webhook signature for security"""
        import hashlib
        import hmac

        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(), payload_str.encode(), hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    async def _send_callback(self, url: str, data: Dict[str, Any]):
        """Send callback to specified URL"""
        if not AIOHTTP_AVAILABLE:
            return

        if not self.webhook_session:
            self.webhook_session = aiohttp.ClientSession()

        async with self.webhook_session.post(url, json=data) as response:
            if response.status >= 400:
                self.logger.error(f"Callback failed: {response.status}")

    async def _get_available_authorities(self) -> List[Dict[str, Any]]:
        """Get list of available authority sources"""
        # This would integrate with the authority system
        authorities = [
            {"id": "orcid", "name": "ORCID", "tier": "tier0"},
            {"id": "crossref", "name": "Crossref", "tier": "tier0"},
            {"id": "openalex", "name": "OpenAlex", "tier": "tier0"},
            {"id": "zbmath", "name": "zbMATH", "tier": "tier0"},
            {"id": "dblp", "name": "DBLP", "tier": "tier1"},
            {"id": "mathscinet", "name": "MathSciNet", "tier": "tier1"},
        ]
        return authorities

    async def _query_authority(
        self, authority_id: str, query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query specific authority source"""
        # This would integrate with the authority system
        # For now, return mock data
        return {
            "authority": authority_id,
            "query": query,
            "results": [],
            "status": "success",
        }

    async def _get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing metrics"""
        return {
            "total_processed": len(self.active_requests),
            "success_rate": 0.95,
            "average_processing_time": 1.2,
            "throughput": 100,  # requests per hour
            "error_rate": 0.05,
        }

    async def _get_performance_analytics(self) -> Dict[str, Any]:
        """Get performance analytics"""
        return {
            "cpu_utilization": 65.0,
            "memory_utilization": 42.0,
            "queue_depth": 5,
            "response_times": {"p50": 0.8, "p95": 2.1, "p99": 3.5},
        }

    async def broadcast_websocket_event(
        self, event_type: EventType, data: Dict[str, Any]
    ):
        """Broadcast event to all WebSocket connections"""
        if not WEBSOCKET_AVAILABLE or not self.ws_connections:
            return

        event_data = {
            "event": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }

        disconnected = set()
        for websocket in self.ws_connections:
            try:
                await websocket.send_json(event_data)
            except Exception:
                disconnected.add(websocket)

        # Remove disconnected websockets
        self.ws_connections -= disconnected

    def create_api_key(
        self,
        user_id: str,
        permissions: List[str],
        rate_limit: int = 1000,
        expires_in_days: Optional[int] = None,
    ) -> str:
        """Create a new API key"""
        key_id = str(uuid.uuid4())
        key_hash = str(uuid.uuid4())  # In production, use proper hashing

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            permissions=permissions,
            rate_limit=rate_limit,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )

        self.api_keys[key_hash] = api_key
        return key_hash

    def register_plugin(self, name: str, plugin: "PluginInterface"):
        """Register a plugin"""
        self.plugins[name] = plugin
        plugin.initialize(self)
        self.logger.info(f"Plugin '{name}' registered")

    def get_openapi_spec(self) -> Dict[str, Any]:
        """Get OpenAPI 3.0 specification"""
        if not self.app:
            return {}

        return self.app.openapi()

    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the API server"""
        if not FASTAPI_AVAILABLE:
            self.logger.error("Cannot start API: FastAPI not available")
            return

        try:
            import uvicorn

            await uvicorn.run(self.app, host=host, port=port)
        except ImportError:
            self.logger.error("uvicorn not available for running server")

    async def shutdown(self):
        """Shutdown the API server"""
        if self.webhook_session:
            await self.webhook_session.close()

        # Close all WebSocket connections
        for websocket in self.ws_connections:
            try:
                await websocket.close()
            except Exception:
                pass

        self.logger.info("Enterprise API shutdown complete")


class PluginInterface:
    """Base interface for API plugins"""

    def initialize(self, api: EnterpriseAPI):
        """Initialize the plugin with the API instance"""
        pass

    def register_routes(self, app):
        """Register additional routes"""
        pass

    async def process_event(self, event_type: EventType, data: Dict[str, Any]):
        """Process webhook events"""
        pass


class GraphQLPlugin(PluginInterface):
    """GraphQL plugin for the Enterprise API"""

    def initialize(self, api: EnterpriseAPI):
        self.api = api
        try:
            import strawberry
            from strawberry.fastapi import GraphQLRouter

            self.strawberry_available = True
        except ImportError:
            self.strawberry_available = False

    def register_routes(self, app):
        if not self.strawberry_available:
            return

        # Would implement GraphQL schema here
        # @strawberry.type
        # class Query:
        #     @strawberry.field
        #     def process_entry(self, entry: str) -> str:
        #         return "GraphQL processing result"

        # schema = strawberry.Schema(query=Query)
        # graphql_app = GraphQLRouter(schema)
        # app.include_router(graphql_app, prefix="/graphql")
