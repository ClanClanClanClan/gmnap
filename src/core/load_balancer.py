#!/usr/bin/env python3
"""
Load Balancer and Graceful Degradation for GMNAP v7
Provides intelligent load distribution and service degradation for 99.9% uptime
"""

import asyncio
import json
import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ServiceLevel(Enum):
    """Service level definitions for graceful degradation."""

    FULL = "full"  # All features available
    REDUCED = "reduced"  # Non-essential features disabled
    ESSENTIAL = "essential"  # Only core features available
    MINIMAL = "minimal"  # Bare minimum functionality
    MAINTENANCE = "maintenance"  # Read-only or offline


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    HEALTH_AWARE = "health_aware"
    ADAPTIVE = "adaptive"


@dataclass
class ServiceEndpoint:
    """Service endpoint definition."""

    id: str
    host: str
    port: int
    weight: float = 1.0
    max_connections: int = 1000
    health_check_url: Optional[str] = None

    # Runtime state
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_health_check: float = 0.0
    healthy: bool = True

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100

    @property
    def utilization(self) -> float:
        if self.max_connections == 0:
            return 0.0
        return (self.active_connections / self.max_connections) * 100


@dataclass
class ServiceProfile:
    """Service profile for different degradation levels."""

    level: ServiceLevel
    features_enabled: Set[str]
    max_concurrent_requests: int
    timeout_seconds: float
    cache_enabled: bool
    rate_limit_per_second: int
    description: str


class GracefulDegradationManager:
    """Manages service degradation levels based on system health."""

    def __init__(self):
        self.current_level = ServiceLevel.FULL
        self.service_profiles = self._init_service_profiles()
        self.feature_toggles: Dict[str, bool] = {}
        self.degradation_history: deque = deque(maxlen=1000)
        self.logger = logging.getLogger("gmnap.degradation")

    def _init_service_profiles(self) -> Dict[ServiceLevel, ServiceProfile]:
        """Initialize service degradation profiles."""
        return {
            ServiceLevel.FULL: ServiceProfile(
                level=ServiceLevel.FULL,
                features_enabled={
                    "region_detection",
                    "name_processing",
                    "validation",
                    "authority_lookup",
                    "caching",
                    "analytics",
                    "reporting",
                    "batch_processing",
                    "background_jobs",
                    "webhooks",
                },
                max_concurrent_requests=1000,
                timeout_seconds=30.0,
                cache_enabled=True,
                rate_limit_per_second=100,
                description="All features available with full performance",
            ),
            ServiceLevel.REDUCED: ServiceProfile(
                level=ServiceLevel.REDUCED,
                features_enabled={
                    "region_detection",
                    "name_processing",
                    "validation",
                    "authority_lookup",
                    "caching",
                    "batch_processing",
                },
                max_concurrent_requests=500,
                timeout_seconds=20.0,
                cache_enabled=True,
                rate_limit_per_second=50,
                description="Analytics and reporting disabled, reduced capacity",
            ),
            ServiceLevel.ESSENTIAL: ServiceProfile(
                level=ServiceLevel.ESSENTIAL,
                features_enabled={
                    "region_detection",
                    "name_processing",
                    "validation",
                    "caching",
                },
                max_concurrent_requests=200,
                timeout_seconds=15.0,
                cache_enabled=True,
                rate_limit_per_second=20,
                description="Only core name processing features available",
            ),
            ServiceLevel.MINIMAL: ServiceProfile(
                level=ServiceLevel.MINIMAL,
                features_enabled={"region_detection", "name_processing"},
                max_concurrent_requests=50,
                timeout_seconds=10.0,
                cache_enabled=False,
                rate_limit_per_second=5,
                description="Bare minimum functionality, no validation or lookups",
            ),
            ServiceLevel.MAINTENANCE: ServiceProfile(
                level=ServiceLevel.MAINTENANCE,
                features_enabled=set(),
                max_concurrent_requests=0,
                timeout_seconds=5.0,
                cache_enabled=False,
                rate_limit_per_second=0,
                description="System in maintenance mode",
            ),
        }

    def evaluate_required_level(self, health_metrics: Dict[str, Any]) -> ServiceLevel:
        """Evaluate required service level based on health metrics."""
        # Extract key metrics
        cpu_usage = health_metrics.get("cpu_usage", 0)
        memory_usage = health_metrics.get("memory_usage", 0)
        error_rate = health_metrics.get("error_rate", 0)
        response_time = health_metrics.get("avg_response_time", 0)

        # Determine degradation level based on thresholds
        if cpu_usage > 95 or memory_usage > 95 or error_rate > 20:
            return ServiceLevel.MAINTENANCE
        elif cpu_usage > 90 or memory_usage > 90 or error_rate > 10:
            return ServiceLevel.MINIMAL
        elif cpu_usage > 80 or memory_usage > 85 or error_rate > 5 or response_time > 3:
            return ServiceLevel.ESSENTIAL
        elif cpu_usage > 70 or memory_usage > 75 or error_rate > 2 or response_time > 2:
            return ServiceLevel.REDUCED
        else:
            return ServiceLevel.FULL

    def set_service_level(self, level: ServiceLevel, reason: str = ""):
        """Set the current service level."""
        if level == self.current_level:
            return

        previous_level = self.current_level
        self.current_level = level

        # Update feature toggles
        profile = self.service_profiles[level]
        all_features = set().union(
            *[p.features_enabled for p in self.service_profiles.values()]
        )

        for feature in all_features:
            self.feature_toggles[feature] = feature in profile.features_enabled

        # Log the change
        self.degradation_history.append(
            {
                "timestamp": time.time(),
                "previous_level": previous_level.value,
                "new_level": level.value,
                "reason": reason,
            }
        )

        self.logger.warning(
            f"Service level changed: {previous_level.value} -> {level.value} "
            f"({reason})"
        )

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled at current service level."""
        return self.feature_toggles.get(feature, False)

    def get_current_profile(self) -> ServiceProfile:
        """Get current service profile."""
        return self.service_profiles[self.current_level]


class LoadBalancer:
    """
    Intelligent load balancer with health-aware routing and graceful degradation.

    Features:
    - Multiple load balancing strategies
    - Health-aware routing
    - Automatic endpoint recovery
    - Request rate limiting
    - Circuit breaker integration
    - Graceful degradation
    - Real-time metrics and monitoring
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()

        # Service endpoints
        self.endpoints: Dict[str, ServiceEndpoint] = {}
        self.endpoint_order: List[str] = []  # For round-robin
        self.current_endpoint_index = 0

        # Load balancing
        self.strategy = LoadBalancingStrategy(
            self.config.get("strategy", "health_aware")
        )
        self.health_check_interval = self.config.get("health_check_interval", 30.0)

        # Graceful degradation
        self.degradation_manager = GracefulDegradationManager()

        # Request tracking
        self.request_queue: List[Dict[str, Any]] = []
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        self.request_history: deque = deque(maxlen=10000)

        # Rate limiting
        self.rate_limiter = {}
        self.rate_limit_window = 60.0  # 1 minute window

        # Control
        self.running = False
        self.health_check_thread: Optional[threading.Thread] = None
        self.request_processor_thread: Optional[threading.Thread] = None

        # Initialize endpoints from config
        self._init_endpoints()

        self.logger.info("LoadBalancer initialized")

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load load balancer configuration."""
        default_config = {
            "strategy": "health_aware",
            "health_check_interval": 30.0,
            "health_check_timeout": 5.0,
            "max_retries": 3,
            "retry_delay": 1.0,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout": 60.0,
            "endpoints": [],
            "rate_limiting": {"enabled": True, "default_rate": 100, "burst_size": 200},
        }

        if config_path and config_path.exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logging.warning(f"Failed to load load balancer config: {e}")

        return default_config

    def _setup_logging(self) -> logging.Logger:
        """Setup load balancer logging."""
        logger = logging.getLogger("gmnap.loadbalancer")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            formatter = logging.Formatter(
                "%(asctime)s [LOADBALANCER] %(levelname)s: %(message)s"
            )
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    def _init_endpoints(self):
        """Initialize endpoints from configuration."""
        for endpoint_config in self.config.get("endpoints", []):
            endpoint = ServiceEndpoint(
                id=endpoint_config["id"],
                host=endpoint_config["host"],
                port=endpoint_config["port"],
                weight=endpoint_config.get("weight", 1.0),
                max_connections=endpoint_config.get("max_connections", 1000),
                health_check_url=endpoint_config.get("health_check_url"),
            )
            self.add_endpoint(endpoint)

    def start(self):
        """Start the load balancer."""
        if self.running:
            return

        self.running = True

        # Start health checking
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()

        # Start request processor
        self.request_processor_thread = threading.Thread(
            target=self._request_processor_loop
        )
        self.request_processor_thread.daemon = True
        self.request_processor_thread.start()

        self.logger.info("Load balancer started")

    def stop(self):
        """Stop the load balancer."""
        if not self.running:
            return

        self.running = False

        # Wait for threads to finish
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5.0)
        if self.request_processor_thread and self.request_processor_thread.is_alive():
            self.request_processor_thread.join(timeout=5.0)

        self.logger.info("Load balancer stopped")

    def add_endpoint(self, endpoint: ServiceEndpoint):
        """Add a service endpoint."""
        self.endpoints[endpoint.id] = endpoint
        self.endpoint_order.append(endpoint.id)
        self.logger.info(f"Added endpoint: {endpoint.id} ({endpoint.url})")

    def remove_endpoint(self, endpoint_id: str):
        """Remove a service endpoint."""
        if endpoint_id in self.endpoints:
            del self.endpoints[endpoint_id]
            if endpoint_id in self.endpoint_order:
                self.endpoint_order.remove(endpoint_id)
            self.logger.info(f"Removed endpoint: {endpoint_id}")

    def select_endpoint(self) -> Optional[ServiceEndpoint]:
        """Select an endpoint based on the current strategy."""
        available_endpoints = [ep for ep in self.endpoints.values() if ep.healthy]

        if not available_endpoints:
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(available_endpoints)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(available_endpoints)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(available_endpoints)
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_selection(available_endpoints)
        elif self.strategy == LoadBalancingStrategy.HEALTH_AWARE:
            return self._health_aware_selection(available_endpoints)
        elif self.strategy == LoadBalancingStrategy.ADAPTIVE:
            return self._adaptive_selection(available_endpoints)
        else:
            return random.choice(available_endpoints)

    def _round_robin_selection(
        self, endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Round-robin endpoint selection."""
        if not self.endpoint_order:
            return endpoints[0]

        # Find next healthy endpoint in order
        attempts = 0
        while attempts < len(self.endpoint_order):
            endpoint_id = self.endpoint_order[self.current_endpoint_index]
            self.current_endpoint_index = (self.current_endpoint_index + 1) % len(
                self.endpoint_order
            )

            if endpoint_id in self.endpoints and self.endpoints[endpoint_id].healthy:
                return self.endpoints[endpoint_id]

            attempts += 1

        return endpoints[0]  # Fallback

    def _weighted_round_robin_selection(
        self, endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Weighted round-robin selection."""
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return endpoints[0]

        r = random.uniform(0, total_weight)
        cumulative = 0

        for endpoint in endpoints:
            cumulative += endpoint.weight
            if r <= cumulative:
                return endpoint

        return endpoints[-1]

    def _least_connections_selection(
        self, endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Select endpoint with least active connections."""
        return min(endpoints, key=lambda ep: ep.active_connections)

    def _least_response_time_selection(
        self, endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Select endpoint with lowest average response time."""
        return min(endpoints, key=lambda ep: ep.avg_response_time)

    def _health_aware_selection(
        self, endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Health-aware selection considering multiple factors."""

        def health_score(endpoint: ServiceEndpoint) -> float:
            # Lower score is better
            score = 0.0

            # Connection utilization (0-100)
            score += endpoint.utilization * 0.4

            # Error rate (0-100)
            score += endpoint.error_rate * 0.3

            # Response time penalty
            score += min(endpoint.avg_response_time * 10, 100) * 0.2

            # Weight bonus (higher weight = lower score)
            score -= (endpoint.weight - 1.0) * 10 * 0.1

            return score

        return min(endpoints, key=health_score)

    def _adaptive_selection(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Adaptive selection that changes strategy based on conditions."""
        # Use health-aware for now, but could implement more sophisticated logic
        return self._health_aware_selection(endpoints)

    async def route_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route a request through the load balancer."""
        request_id = request_data.get("id", str(time.time()))

        # Check service level and rate limits
        current_profile = self.degradation_manager.get_current_profile()
        if current_profile.level == ServiceLevel.MAINTENANCE:
            return self._maintenance_response(request_id)

        if not self._check_rate_limit(request_data):
            return self._rate_limit_response(request_id)

        # Select endpoint
        endpoint = self.select_endpoint()
        if not endpoint:
            return self._no_endpoint_response(request_id)

        # Execute request
        start_time = time.time()
        try:
            endpoint.active_connections += 1

            # Simulate request execution (in real implementation, make HTTP call)
            response = await self._execute_request(
                endpoint, request_data, current_profile
            )

            # Record success
            endpoint.total_requests += 1
            response_time = time.time() - start_time
            endpoint.avg_response_time = (
                endpoint.avg_response_time * (endpoint.total_requests - 1)
                + response_time
            ) / endpoint.total_requests

            self.request_history.append(
                {
                    "request_id": request_id,
                    "endpoint_id": endpoint.id,
                    "response_time": response_time,
                    "success": True,
                    "timestamp": start_time,
                }
            )

            return response

        except Exception as e:
            # Record failure
            endpoint.failed_requests += 1
            endpoint.total_requests += 1

            self.request_history.append(
                {
                    "request_id": request_id,
                    "endpoint_id": endpoint.id,
                    "response_time": time.time() - start_time,
                    "success": False,
                    "error": str(e),
                    "timestamp": start_time,
                }
            )

            return self._error_response(request_id, str(e))

        finally:
            endpoint.active_connections -= 1

    async def _execute_request(
        self,
        endpoint: ServiceEndpoint,
        request_data: Dict[str, Any],
        profile: ServiceProfile,
    ) -> Dict[str, Any]:
        """Execute request against endpoint with service profile constraints."""
        # Simulate processing time based on service level
        if profile.level == ServiceLevel.FULL:
            await asyncio.sleep(0.1)  # Normal processing time
        elif profile.level == ServiceLevel.REDUCED:
            await asyncio.sleep(0.05)  # Faster due to fewer features
        elif profile.level == ServiceLevel.ESSENTIAL:
            await asyncio.sleep(0.03)  # Even faster
        elif profile.level == ServiceLevel.MINIMAL:
            await asyncio.sleep(0.01)  # Very fast, minimal processing

        # Return response based on enabled features
        response = {
            "request_id": request_data.get("id"),
            "endpoint": endpoint.id,
            "service_level": profile.level.value,
            "timestamp": time.time(),
        }

        # Add features based on service level
        if "region_detection" in profile.features_enabled:
            response["region"] = "A1"  # Placeholder
        if "name_processing" in profile.features_enabled:
            response["processed_name"] = "John Smith"  # Placeholder
        if "validation" in profile.features_enabled:
            response["validation_result"] = "valid"
        if "authority_lookup" in profile.features_enabled:
            response["authority_data"] = {"source": "orcid"}

        return response

    def _check_rate_limit(self, request_data: Dict[str, Any]) -> bool:
        """Check if request is within rate limits."""
        if not self.config.get("rate_limiting", {}).get("enabled", True):
            return True

        client_id = request_data.get("client_id", "default")
        current_time = time.time()

        # Initialize rate limiter for client if needed
        if client_id not in self.rate_limiter:
            self.rate_limiter[client_id] = deque()

        # Remove old requests outside window
        window_start = current_time - self.rate_limit_window
        client_requests = self.rate_limiter[client_id]

        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()

        # Check rate limit
        profile = self.degradation_manager.get_current_profile()
        rate_limit = profile.rate_limit_per_second * (self.rate_limit_window / 60)

        if len(client_requests) >= rate_limit:
            return False

        # Add current request
        client_requests.append(current_time)
        return True

    def _maintenance_response(self, request_id: str) -> Dict[str, Any]:
        """Return maintenance mode response."""
        return {
            "request_id": request_id,
            "error": "service_unavailable",
            "message": "System is in maintenance mode",
            "retry_after": 300,
            "timestamp": time.time(),
        }

    def _rate_limit_response(self, request_id: str) -> Dict[str, Any]:
        """Return rate limit exceeded response."""
        return {
            "request_id": request_id,
            "error": "rate_limit_exceeded",
            "message": "Too many requests, please slow down",
            "retry_after": 60,
            "timestamp": time.time(),
        }

    def _no_endpoint_response(self, request_id: str) -> Dict[str, Any]:
        """Return no available endpoint response."""
        return {
            "request_id": request_id,
            "error": "no_endpoints_available",
            "message": "No healthy endpoints available",
            "timestamp": time.time(),
        }

    def _error_response(self, request_id: str, error: str) -> Dict[str, Any]:
        """Return error response."""
        return {
            "request_id": request_id,
            "error": "processing_error",
            "message": error,
            "timestamp": time.time(),
        }

    def _health_check_loop(self):
        """Health check loop for endpoints."""
        while self.running:
            try:
                for endpoint in self.endpoints.values():
                    self._check_endpoint_health(endpoint)

                time.sleep(self.health_check_interval)

            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                time.sleep(5.0)

    def _check_endpoint_health(self, endpoint: ServiceEndpoint):
        """Check health of individual endpoint."""
        try:
            # Simplified health check - in real implementation would make HTTP request
            # to endpoint.health_check_url or endpoint.url + "/health"

            # For simulation, mark as unhealthy if error rate is too high
            if endpoint.error_rate > 20:
                if endpoint.healthy:
                    endpoint.healthy = False
                    self.logger.warning(
                        f"Endpoint {endpoint.id} marked unhealthy (error rate: {endpoint.error_rate:.1f}%)"
                    )
            else:
                if not endpoint.healthy:
                    endpoint.healthy = True
                    self.logger.info(f"Endpoint {endpoint.id} marked healthy")

            endpoint.last_health_check = time.time()

        except Exception as e:
            if endpoint.healthy:
                endpoint.healthy = False
                self.logger.warning(f"Endpoint {endpoint.id} health check failed: {e}")

    def _request_processor_loop(self):
        """Process queued requests."""
        while self.running:
            try:
                # Process any queued requests
                # In real implementation, this would handle request queuing and processing
                time.sleep(1.0)

            except Exception as e:
                self.logger.error(f"Error in request processor: {e}")
                time.sleep(5.0)

    def update_service_level(self, health_metrics: Dict[str, Any]):
        """Update service level based on health metrics."""
        required_level = self.degradation_manager.evaluate_required_level(
            health_metrics
        )

        if required_level != self.degradation_manager.current_level:
            reason = (
                f"Health metrics: CPU={health_metrics.get('cpu_usage', 0):.1f}%, "
                f"Memory={health_metrics.get('memory_usage', 0):.1f}%, "
                f"Errors={health_metrics.get('error_rate', 0):.1f}%"
            )

            self.degradation_manager.set_service_level(required_level, reason)

    def get_status(self) -> Dict[str, Any]:
        """Get load balancer status."""
        total_requests = sum(ep.total_requests for ep in self.endpoints.values())
        total_errors = sum(ep.failed_requests for ep in self.endpoints.values())

        return {
            "running": self.running,
            "strategy": self.strategy.value,
            "service_level": self.degradation_manager.current_level.value,
            "endpoints": {
                ep.id: {
                    "healthy": ep.healthy,
                    "active_connections": ep.active_connections,
                    "total_requests": ep.total_requests,
                    "error_rate": ep.error_rate,
                    "avg_response_time": ep.avg_response_time,
                    "utilization": ep.utilization,
                }
                for ep in self.endpoints.values()
            },
            "total_requests": total_requests,
            "total_errors": total_errors,
            "overall_error_rate": (total_errors / max(1, total_requests)) * 100,
            "healthy_endpoints": sum(1 for ep in self.endpoints.values() if ep.healthy),
            "total_endpoints": len(self.endpoints),
        }
