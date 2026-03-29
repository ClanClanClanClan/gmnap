#!/usr/bin/env python3
"""
Production Monitor for GMNAP v7
Enterprise-grade monitoring and health management for 99.9% uptime
"""

import json
import logging
import queue
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil


class HealthStatus(Enum):
    """System health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILURE = "failure"


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class HealthMetric:
    """Individual health metric."""

    name: str
    value: float
    threshold_warning: float
    threshold_critical: float
    unit: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    @property
    def status(self) -> HealthStatus:
        """Determine status based on thresholds."""
        if self.value >= self.threshold_critical:
            return HealthStatus.CRITICAL
        elif self.value >= self.threshold_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


@dataclass
class SystemAlert:
    """System alert/notification."""

    level: AlertLevel
    component: str
    message: str
    timestamp: float
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "component": self.component,
            "message": self.message,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "iso_timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


class CircuitBreaker:
    """Circuit breaker for component protection."""

    def __init__(
        self, name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record successful operation."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
        self.failure_count = 0

    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "can_execute": self.can_execute(),
        }


class ProductionMonitor:
    """
    Enterprise production monitoring system for 99.9% uptime.

    Features:
    - Real-time health monitoring
    - Circuit breakers for component protection
    - Automatic alerting and recovery
    - Performance metrics tracking
    - Load balancing support
    - Graceful degradation
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()

        # Health metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.current_metrics: Dict[str, HealthMetric] = {}

        # Alerting system
        self.alerts: deque = deque(maxlen=10000)
        self.alert_callbacks: List[Callable] = []
        self.alert_queue = queue.Queue()

        # Circuit breakers
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # System state
        self.system_status = HealthStatus.HEALTHY
        self.uptime_start = time.time()
        self.total_requests = 0
        self.failed_requests = 0

        # Performance tracking
        self.response_times: deque = deque(maxlen=1000)
        self.throughput_history: deque = deque(maxlen=100)

        # Monitoring control
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.alert_thread: Optional[threading.Thread] = None

        # Initialize default circuit breakers
        self._init_circuit_breakers()

        self.logger.info("ProductionMonitor initialized")

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load monitoring configuration."""
        default_config = {
            "monitoring_interval": 1.0,  # seconds
            "metrics_retention_hours": 24,
            "alert_cooldown_seconds": 300,
            "circuit_breaker_defaults": {
                "failure_threshold": 5,
                "recovery_timeout": 60.0,
            },
            "thresholds": {
                "cpu_usage": {"warning": 80.0, "critical": 95.0},
                "memory_usage": {"warning": 85.0, "critical": 95.0},
                "disk_usage": {"warning": 85.0, "critical": 95.0},
                "response_time": {"warning": 1.0, "critical": 3.0},
                "error_rate": {"warning": 1.0, "critical": 5.0},
            },
        }

        if config_path and config_path.exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logging.warning(f"Failed to load config from {config_path}: {e}")

        return default_config

    def _setup_logging(self) -> logging.Logger:
        """Setup production monitoring logging."""
        logger = logging.getLogger("gmnap.monitor")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                "%(asctime)s [MONITOR] %(levelname)s: %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            # File handler for production logs
            try:
                log_path = Path("logs")
                log_path.mkdir(exist_ok=True)
                file_handler = logging.FileHandler(log_path / "production.log")
                file_formatter = logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Failed to setup file logging: {e}")

        return logger

    def _init_circuit_breakers(self):
        """Initialize default circuit breakers."""
        defaults = self.config["circuit_breaker_defaults"]

        components = [
            "region_detection",
            "name_processing",
            "database_operations",
            "authority_lookup",
            "cache_operations",
            "validation",
        ]

        for component in components:
            self.circuit_breakers[component] = CircuitBreaker(
                name=component,
                failure_threshold=defaults["failure_threshold"],
                recovery_timeout=defaults["recovery_timeout"],
            )

    def start_monitoring(self):
        """Start the monitoring system."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.uptime_start = time.time()

        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        # Start alert processing thread
        self.alert_thread = threading.Thread(target=self._alert_processing_loop)
        self.alert_thread.daemon = True
        self.alert_thread.start()

        self.logger.info("Production monitoring started")
        self._emit_alert(AlertLevel.INFO, "system", "Production monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring system."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False

        # Wait for threads to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        if self.alert_thread and self.alert_thread.is_alive():
            self.alert_thread.join(timeout=5.0)

        self.logger.info("Production monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        self.logger.info("Monitoring loop started")

        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()

                # Collect application metrics
                self._collect_application_metrics()

                # Evaluate health status
                self._evaluate_system_health()

                # Sleep until next collection
                time.sleep(self.config["monitoring_interval"])

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5.0)  # Error recovery delay

    def _alert_processing_loop(self):
        """Process alerts in background thread."""
        while self.monitoring_active:
            try:
                # Process queued alerts
                alert = self.alert_queue.get(timeout=1.0)
                self._process_alert(alert)

            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing alert: {e}")

    def _collect_system_metrics(self):
        """Collect system-level metrics."""
        thresholds = self.config["thresholds"]

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_metric = HealthMetric(
            name="cpu_usage",
            value=cpu_percent,
            threshold_warning=thresholds["cpu_usage"]["warning"],
            threshold_critical=thresholds["cpu_usage"]["critical"],
            unit="%",
        )
        self._record_metric(cpu_metric)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_metric = HealthMetric(
            name="memory_usage",
            value=memory.percent,
            threshold_warning=thresholds["memory_usage"]["warning"],
            threshold_critical=thresholds["memory_usage"]["critical"],
            unit="%",
        )
        self._record_metric(memory_metric)

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        disk_metric = HealthMetric(
            name="disk_usage",
            value=disk_percent,
            threshold_warning=thresholds["disk_usage"]["warning"],
            threshold_critical=thresholds["disk_usage"]["critical"],
            unit="%",
        )
        self._record_metric(disk_metric)

        # Load average (Unix systems)
        try:
            load_avg = psutil.getloadavg()[0]  # 1-minute load average
            load_metric = HealthMetric(
                name="load_average",
                value=load_avg,
                threshold_warning=psutil.cpu_count() * 0.8,
                threshold_critical=psutil.cpu_count() * 1.2,
                unit="",
            )
            self._record_metric(load_metric)
        except AttributeError:
            # Not available on Windows
            pass

    def _collect_application_metrics(self):
        """Collect application-specific metrics."""
        thresholds = self.config["thresholds"]

        # Calculate error rate
        if self.total_requests > 0:
            error_rate = (self.failed_requests / self.total_requests) * 100
            error_metric = HealthMetric(
                name="error_rate",
                value=error_rate,
                threshold_warning=thresholds["error_rate"]["warning"],
                threshold_critical=thresholds["error_rate"]["critical"],
                unit="%",
            )
            self._record_metric(error_metric)

        # Calculate average response time
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            response_metric = HealthMetric(
                name="avg_response_time",
                value=avg_response_time,
                threshold_warning=thresholds["response_time"]["warning"],
                threshold_critical=thresholds["response_time"]["critical"],
                unit="s",
            )
            self._record_metric(response_metric)

        # Calculate throughput
        current_time = time.time()
        current_time - 60
        recent_requests = sum(1 for t in self.response_times if current_time - t <= 60)

        throughput_metric = HealthMetric(
            name="throughput",
            value=recent_requests,
            threshold_warning=0,  # No warning threshold for throughput
            threshold_critical=0,  # No critical threshold for throughput
            unit="req/min",
        )
        self._record_metric(throughput_metric)

        # Record uptime
        uptime_seconds = current_time - self.uptime_start
        uptime_metric = HealthMetric(
            name="uptime",
            value=uptime_seconds,
            threshold_warning=0,
            threshold_critical=0,
            unit="s",
        )
        self._record_metric(uptime_metric)

    def _record_metric(self, metric: HealthMetric):
        """Record a health metric."""
        self.metrics[metric.name].append(metric)
        self.current_metrics[metric.name] = metric

        # Check for threshold breaches
        if metric.status == HealthStatus.CRITICAL:
            self._emit_alert(
                AlertLevel.CRITICAL,
                "metrics",
                f"{metric.name} is CRITICAL: {metric.value}{metric.unit} "
                f"(threshold: {metric.threshold_critical}{metric.unit})",
            )
        elif metric.status == HealthStatus.WARNING:
            self._emit_alert(
                AlertLevel.WARNING,
                "metrics",
                f"{metric.name} is WARNING: {metric.value}{metric.unit} "
                f"(threshold: {metric.threshold_warning}{metric.unit})",
            )

    def _evaluate_system_health(self):
        """Evaluate overall system health."""
        if not self.current_metrics:
            return

        critical_count = sum(
            1
            for m in self.current_metrics.values()
            if m.status == HealthStatus.CRITICAL
        )
        warning_count = sum(
            1 for m in self.current_metrics.values() if m.status == HealthStatus.WARNING
        )

        previous_status = self.system_status

        if critical_count > 0:
            self.system_status = HealthStatus.CRITICAL
        elif warning_count > 0:
            self.system_status = HealthStatus.WARNING
        else:
            self.system_status = HealthStatus.HEALTHY

        # Alert on status changes
        if self.system_status != previous_status:
            if self.system_status == HealthStatus.CRITICAL:
                self._emit_alert(
                    AlertLevel.EMERGENCY,
                    "system",
                    f"System status changed to CRITICAL ({critical_count} critical metrics)",
                )
            elif self.system_status == HealthStatus.WARNING:
                self._emit_alert(
                    AlertLevel.WARNING,
                    "system",
                    f"System status changed to WARNING ({warning_count} warning metrics)",
                )
            else:
                self._emit_alert(
                    AlertLevel.INFO, "system", "System status returned to HEALTHY"
                )

    def _emit_alert(self, level: AlertLevel, component: str, message: str):
        """Emit a system alert."""
        alert = SystemAlert(level, component, message, time.time())
        self.alerts.append(alert)

        # Queue for background processing
        try:
            self.alert_queue.put_nowait(alert)
        except queue.Full:
            self.logger.warning("Alert queue is full, dropping alert")

        # Log the alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.CRITICAL: logging.ERROR,
            AlertLevel.EMERGENCY: logging.CRITICAL,
        }.get(level, logging.INFO)

        self.logger.log(log_level, f"[{component}] {message}")

    def _process_alert(self, alert: SystemAlert):
        """Process an individual alert."""
        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")

    def record_request(self, response_time: float, success: bool = True):
        """Record a request for metrics."""
        self.total_requests += 1
        if not success:
            self.failed_requests += 1

        self.response_times.append(response_time)

        # Record in circuit breaker
        component = "request_processing"  # Could be more specific
        if component in self.circuit_breakers:
            if success:
                self.circuit_breakers[component].record_success()
            else:
                self.circuit_breakers[component].record_failure()

    def execute_with_circuit_breaker(
        self, component: str, func: Callable, *args, **kwargs
    ):
        """Execute function with circuit breaker protection."""
        if component not in self.circuit_breakers:
            # Create circuit breaker on demand
            defaults = self.config["circuit_breaker_defaults"]
            self.circuit_breakers[component] = CircuitBreaker(
                name=component,
                failure_threshold=defaults["failure_threshold"],
                recovery_timeout=defaults["recovery_timeout"],
            )

        breaker = self.circuit_breakers[component]

        if not breaker.can_execute():
            raise RuntimeError(
                f"Circuit breaker {component} is OPEN - operation blocked"
            )

        try:
            result = func(*args, **kwargs)
            breaker.record_success()
            return result
        except Exception as e:
            breaker.record_failure()
            self._emit_alert(
                AlertLevel.WARNING, component, f"Circuit breaker failure: {e}"
            )
            raise

    def register_alert_callback(self, callback: Callable[[SystemAlert], None]):
        """Register callback for alert notifications."""
        self.alert_callbacks.append(callback)

    def get_health_status(self) -> Dict[str, Any]:
        """Get current system health status."""
        return {
            "status": self.system_status.value,
            "uptime_seconds": time.time() - self.uptime_start,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "error_rate": (self.failed_requests / max(1, self.total_requests)) * 100,
            "current_metrics": {
                name: {
                    "value": metric.value,
                    "unit": metric.unit,
                    "status": metric.status.value,
                    "timestamp": metric.timestamp,
                }
                for name, metric in self.current_metrics.items()
            },
            "circuit_breakers": {
                name: breaker.get_status()
                for name, breaker in self.circuit_breakers.items()
            },
            "recent_alerts": [alert.to_dict() for alert in list(self.alerts)[-10:]],
        }

    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for specified time period."""
        cutoff_time = time.time() - (hours * 3600)

        summary = {}
        for name, metric_history in self.metrics.items():
            recent_metrics = [m for m in metric_history if m.timestamp >= cutoff_time]

            if recent_metrics:
                values = [m.value for m in recent_metrics]
                summary[name] = {
                    "count": len(recent_metrics),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "current": recent_metrics[-1].value,
                    "unit": recent_metrics[-1].unit,
                }

        return summary

    def trigger_health_check(self) -> bool:
        """Manually trigger a health check."""
        try:
            self._collect_system_metrics()
            self._collect_application_metrics()
            self._evaluate_system_health()
            return self.system_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
