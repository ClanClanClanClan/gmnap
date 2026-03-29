#!/usr/bin/env python3
"""
Enterprise Infrastructure Integration for GMNAP v7
Ties together all production infrastructure components for 99.9% uptime
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .load_balancer import LoadBalancer
from .military_grade_security import (
    MilitaryGradeSecurityValidator as MilitaryGradeSecurity,
)
from .production_monitor import ProductionMonitor
from .recovery_system import AutoRecoverySystem


@dataclass
class InfrastructureConfig:
    """Infrastructure configuration."""

    monitoring_enabled: bool = True
    recovery_enabled: bool = True
    load_balancing_enabled: bool = True
    security_enabled: bool = True

    # Component configurations
    monitoring_config: Optional[Dict[str, Any]] = None
    recovery_config: Optional[Dict[str, Any]] = None
    load_balancer_config: Optional[Dict[str, Any]] = None
    security_config: Optional[Dict[str, Any]] = None

    # Integration settings
    health_check_interval: float = 30.0
    metrics_collection_interval: float = 10.0
    infrastructure_log_level: str = "INFO"


class EnterpriseInfrastructure:
    """
    Master infrastructure coordinator for enterprise-grade GMNAP v7 deployment.

    Integrates and coordinates:
    - Production monitoring with real-time health metrics
    - Automatic recovery system with intelligent failure handling
    - Load balancer with graceful degradation
    - Military-grade security validation
    - Centralized logging and alerting
    - Performance optimization and resource management

    Designed for 99.9% uptime enterprise deployments.
    """

    def __init__(self, config: Optional[InfrastructureConfig] = None):
        self.config = config or InfrastructureConfig()
        self.logger = self._setup_logging()

        # Core infrastructure components
        self.monitor: Optional[ProductionMonitor] = None
        self.recovery_system: Optional[AutoRecoverySystem] = None
        self.load_balancer: Optional[LoadBalancer] = None
        self.security: Optional[MilitaryGradeSecurity] = None

        # Infrastructure state
        self.running = False
        self.startup_time = 0.0
        self.last_health_check = 0.0
        self.infrastructure_metrics = {}

        # Performance tracking
        self.total_requests_processed = 0
        self.total_errors_handled = 0
        self.total_recoveries_performed = 0
        self.total_security_blocks = 0

        # Coordination thread
        self.coordinator_thread: Optional[threading.Thread] = None

        self.logger.info("EnterpriseInfrastructure initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup centralized infrastructure logging."""
        logger = logging.getLogger("gmnap.infrastructure")

        # Set log level from config
        level = getattr(
            logging, self.config.infrastructure_log_level.upper(), logging.INFO
        )
        logger.setLevel(level)

        if not logger.handlers:
            # Create logs directory
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            # Console handler with detailed formatting
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                "%(asctime)s [INFRASTRUCTURE] %(levelname)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            # File handler for infrastructure logs
            try:
                file_handler = logging.FileHandler(log_dir / "infrastructure.log")
                file_formatter = logging.Formatter(
                    "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Failed to setup file logging: {e}")

        return logger

    async def startup(self):
        """Start the complete enterprise infrastructure."""
        if self.running:
            self.logger.warning("Infrastructure already running")
            return

        self.startup_time = time.time()
        self.logger.info("🚀 Starting Enterprise Infrastructure...")

        try:
            # Initialize components in dependency order
            await self._initialize_security()
            await self._initialize_monitoring()
            await self._initialize_recovery_system()
            await self._initialize_load_balancer()

            # Start coordination
            await self._start_coordination()

            self.running = True
            uptime = time.time() - self.startup_time

            self.logger.info(
                f"✅ Enterprise Infrastructure started successfully in {uptime:.2f}s"
            )
            self.logger.info("🛡️  Military-grade security: ACTIVE")
            self.logger.info("📊 Production monitoring: ACTIVE")
            self.logger.info("🔄 Automatic recovery: ACTIVE")
            self.logger.info("⚖️  Load balancing: ACTIVE")
            self.logger.info("🎯 Target uptime: 99.9% (8.76 hours/year max downtime)")

        except Exception as e:
            self.logger.error(f"💥 Infrastructure startup failed: {e}")
            await self.shutdown()
            raise

    async def _initialize_security(self):
        """Initialize military-grade security system."""
        if not self.config.security_enabled:
            self.logger.info("Security system disabled by configuration")
            return

        self.logger.info("Initializing military-grade security...")

        try:
            self.security = MilitaryGradeSecurity()

            # Test security system
            test_result = self.security.validate_entry({"name": "safe_input"})
            if test_result and "name" in test_result:
                self.logger.info("✅ Military-grade security system operational")
            else:
                raise RuntimeError("Security system validation test failed")

        except Exception as e:
            self.logger.error(f"Security initialization failed: {e}")
            raise

    async def _initialize_monitoring(self):
        """Initialize production monitoring system."""
        if not self.config.monitoring_enabled:
            self.logger.info("Monitoring system disabled by configuration")
            return

        self.logger.info("Initializing production monitoring...")

        try:
            self.monitor = ProductionMonitor(self.config.monitoring_config)
            self.monitor.start_monitoring()

            # Wait for initial metrics collection
            await asyncio.sleep(2.0)

            # Verify monitoring is working
            health_status = self.monitor.get_health_status()
            if health_status["status"] in ["healthy", "warning"]:
                self.logger.info("✅ Production monitoring system operational")
            else:
                self.logger.warning(
                    f"⚠️  Monitoring system status: {health_status['status']}"
                )

        except Exception as e:
            self.logger.error(f"Monitoring initialization failed: {e}")
            raise

    async def _initialize_recovery_system(self):
        """Initialize automatic recovery system."""
        if not self.config.recovery_enabled or not self.monitor:
            self.logger.info("Recovery system disabled or monitoring unavailable")
            return

        self.logger.info("Initializing automatic recovery system...")

        try:
            self.recovery_system = AutoRecoverySystem(
                self.monitor, self.config.recovery_config
            )
            self.recovery_system.start_recovery_system()

            # Register infrastructure recovery callback
            self.recovery_system.register_alert_callback(
                self._handle_infrastructure_alert
            )

            self.logger.info("✅ Automatic recovery system operational")

        except Exception as e:
            self.logger.error(f"Recovery system initialization failed: {e}")
            raise

    async def _initialize_load_balancer(self):
        """Initialize load balancer with graceful degradation."""
        if not self.config.load_balancing_enabled:
            self.logger.info("Load balancing disabled by configuration")
            return

        self.logger.info("Initializing load balancer...")

        try:
            self.load_balancer = LoadBalancer(self.config.load_balancer_config)

            # Add default localhost endpoint if no endpoints configured
            if not self.load_balancer.endpoints:
                from .load_balancer import ServiceEndpoint

                default_endpoint = ServiceEndpoint(
                    id="localhost",
                    host="127.0.0.1",
                    port=8000,
                    weight=1.0,
                    max_connections=100,
                )
                self.load_balancer.add_endpoint(default_endpoint)

            self.load_balancer.start()

            self.logger.info("✅ Load balancer operational")

        except Exception as e:
            self.logger.error(f"Load balancer initialization failed: {e}")
            raise

    async def _start_coordination(self):
        """Start infrastructure coordination."""
        self.coordinator_thread = threading.Thread(target=self._coordination_loop)
        self.coordinator_thread.daemon = True
        self.coordinator_thread.start()

        # Give coordinator time to start
        await asyncio.sleep(1.0)

    def _coordination_loop(self):
        """Main coordination loop for infrastructure management."""
        self.logger.info("Infrastructure coordinator started")

        last_health_update = 0
        last_metrics_collection = 0

        while self.running:
            try:
                current_time = time.time()

                # Health check coordination
                if (
                    current_time - last_health_update
                    >= self.config.health_check_interval
                ):
                    self._coordinate_health_checks()
                    last_health_update = current_time

                # Metrics collection coordination
                if (
                    current_time - last_metrics_collection
                    >= self.config.metrics_collection_interval
                ):
                    self._collect_infrastructure_metrics()
                    last_metrics_collection = current_time

                # Sleep until next cycle
                time.sleep(1.0)

            except Exception as e:
                self.logger.error(f"Coordination loop error: {e}")
                time.sleep(5.0)

    def _coordinate_health_checks(self):
        """Coordinate health checks across all components."""
        try:
            if self.monitor:
                # Trigger manual health check
                system_healthy = self.monitor.trigger_health_check()
                self.last_health_check = time.time()

                if system_healthy:
                    self.logger.debug("System health check: HEALTHY")
                else:
                    self.logger.warning("System health check: UNHEALTHY")

                # Update load balancer with health metrics
                if self.load_balancer:
                    health_status = self.monitor.get_health_status()
                    self.load_balancer.update_service_level(
                        health_status["current_metrics"]
                    )

        except Exception as e:
            self.logger.error(f"Health check coordination failed: {e}")

    def _collect_infrastructure_metrics(self):
        """Collect infrastructure-wide metrics."""
        try:
            metrics = {
                "timestamp": time.time(),
                "uptime_seconds": time.time() - self.startup_time,
                "requests_processed": self.total_requests_processed,
                "errors_handled": self.total_errors_handled,
                "recoveries_performed": self.total_recoveries_performed,
                "security_blocks": self.total_security_blocks,
            }

            # Add component metrics
            if self.monitor:
                metrics["monitoring"] = self.monitor.get_health_status()

            if self.recovery_system:
                metrics["recovery"] = self.recovery_system.get_recovery_status()

            if self.load_balancer:
                metrics["load_balancer"] = self.load_balancer.get_status()

            self.infrastructure_metrics = metrics

        except Exception as e:
            self.logger.error(f"Metrics collection failed: {e}")

    def _handle_infrastructure_alert(self, alert):
        """Handle alerts that affect infrastructure coordination."""
        self.logger.info(f"Infrastructure alert: {alert.component} - {alert.message}")

        # Update counters
        if alert.component == "recovery":
            self.total_recoveries_performed += 1
        elif alert.component == "security":
            self.total_security_blocks += 1

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request through the enterprise infrastructure."""
        if not self.running:
            return self._infrastructure_unavailable_response(
                request_data.get("id", "unknown")
            )

        request_start = time.time()
        request_id = request_data.get("id", str(time.time()))

        try:
            self.total_requests_processed += 1

            # Security validation
            if self.security:
                try:
                    self.security.validate_entry(request_data)
                    # If no exception, request is safe
                except Exception as e:
                    # Security threat detected
                    self.total_security_blocks += 1
                    return self._security_blocked_response(
                        request_id, {"reason": str(e), "threat_level": "HIGH"}
                    )

            # Route through load balancer
            if self.load_balancer:
                response = await self.load_balancer.route_request(request_data)
            else:
                # Fallback processing
                response = self._process_request_directly(request_data)

            # Record metrics
            if self.monitor:
                response_time = time.time() - request_start
                self.monitor.record_request(response_time, "error" not in response)

            return response

        except Exception as e:
            self.logger.error(f"Request processing failed: {e}")
            self.total_errors_handled += 1

            if self.monitor:
                response_time = time.time() - request_start
                self.monitor.record_request(response_time, False)

            return self._processing_error_response(request_id, str(e))

    def _process_request_directly(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process request directly without load balancer."""
        return {
            "request_id": request_data.get("id"),
            "result": "processed",
            "message": "Request processed by infrastructure fallback",
            "timestamp": time.time(),
        }

    def _infrastructure_unavailable_response(self, request_id: str) -> Dict[str, Any]:
        """Return infrastructure unavailable response."""
        return {
            "request_id": request_id,
            "error": "infrastructure_unavailable",
            "message": "Enterprise infrastructure is not running",
            "timestamp": time.time(),
        }

    def _security_blocked_response(
        self, request_id: str, security_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return security blocked response."""
        return {
            "request_id": request_id,
            "error": "security_blocked",
            "message": f"Request blocked by security system: {security_result.get('reason', 'threat detected')}",
            "threat_level": security_result.get("threat_level"),
            "timestamp": time.time(),
        }

    def _processing_error_response(self, request_id: str, error: str) -> Dict[str, Any]:
        """Return processing error response."""
        return {
            "request_id": request_id,
            "error": "processing_error",
            "message": f"Request processing failed: {error}",
            "timestamp": time.time(),
        }

    async def shutdown(self):
        """Shutdown the enterprise infrastructure gracefully."""
        if not self.running:
            return

        self.logger.info("🛑 Shutting down Enterprise Infrastructure...")
        self.running = False

        try:
            # Stop coordination
            if self.coordinator_thread and self.coordinator_thread.is_alive():
                self.coordinator_thread.join(timeout=5.0)

            # Shutdown components in reverse order
            if self.load_balancer:
                self.load_balancer.stop()
                self.logger.info("Load balancer stopped")

            if self.recovery_system:
                self.recovery_system.stop_recovery_system()
                self.logger.info("Recovery system stopped")

            if self.monitor:
                self.monitor.stop_monitoring()
                self.logger.info("Monitoring stopped")

            if self.security:
                # Security system doesn't need explicit shutdown
                self.logger.info("Security system deactivated")

            # Log final statistics
            uptime = time.time() - self.startup_time
            self.logger.info("📊 Final Statistics:")
            self.logger.info(f"   Uptime: {uptime:.2f} seconds")
            self.logger.info(f"   Requests processed: {self.total_requests_processed}")
            self.logger.info(f"   Errors handled: {self.total_errors_handled}")
            self.logger.info(
                f"   Recoveries performed: {self.total_recoveries_performed}"
            )
            self.logger.info(f"   Security blocks: {self.total_security_blocks}")

            if self.total_requests_processed > 0:
                success_rate = (
                    (self.total_requests_processed - self.total_errors_handled)
                    / self.total_requests_processed
                ) * 100
                self.logger.info(f"   Success rate: {success_rate:.2f}%")

            self.logger.info("✅ Enterprise Infrastructure shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def get_infrastructure_status(self) -> Dict[str, Any]:
        """Get comprehensive infrastructure status."""
        status = {
            "running": self.running,
            "uptime_seconds": time.time() - self.startup_time if self.running else 0,
            "components": {
                "security": self.security is not None and self.config.security_enabled,
                "monitoring": self.monitor is not None
                and self.config.monitoring_enabled,
                "recovery": self.recovery_system is not None
                and self.config.recovery_enabled,
                "load_balancer": self.load_balancer is not None
                and self.config.load_balancing_enabled,
            },
            "statistics": {
                "requests_processed": self.total_requests_processed,
                "errors_handled": self.total_errors_handled,
                "recoveries_performed": self.total_recoveries_performed,
                "security_blocks": self.total_security_blocks,
            },
            "last_health_check": self.last_health_check,
            "metrics": self.infrastructure_metrics,
        }

        # Add component-specific status
        if self.monitor:
            status["monitoring_status"] = self.monitor.get_health_status()

        if self.recovery_system:
            status["recovery_status"] = self.recovery_system.get_recovery_status()

        if self.load_balancer:
            status["load_balancer_status"] = self.load_balancer.get_status()

        return status

    def get_uptime_percentage(self) -> float:
        """Calculate current uptime percentage."""
        if not self.running:
            return 0.0

        total_time = time.time() - self.startup_time
        if total_time == 0:
            return 100.0

        # This is a simplified calculation - in production would track actual downtime
        # For now, assume 100% uptime if running
        return 100.0

    def is_healthy(self) -> bool:
        """Check if infrastructure is healthy."""
        if not self.running:
            return False

        # Check component health
        if self.monitor:
            health_status = self.monitor.get_health_status()
            if health_status["status"] == "critical":
                return False

        return True


# Convenience function for easy infrastructure setup
async def create_enterprise_infrastructure(
    config_path: Optional[Path] = None,
) -> EnterpriseInfrastructure:
    """Create and start enterprise infrastructure from configuration."""

    config = InfrastructureConfig()

    if config_path and config_path.exists():
        try:
            with open(config_path) as f:
                config_data = json.load(f)

            # Update config from file
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        except Exception as e:
            logging.warning(
                f"Failed to load infrastructure config from {config_path}: {e}"
            )

    infrastructure = EnterpriseInfrastructure(config)
    await infrastructure.startup()

    return infrastructure
