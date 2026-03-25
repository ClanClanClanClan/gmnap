"""
Monitoring and observability infrastructure for GMNAP.
Provides logging, metrics, tracing, and health checks.
"""

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Represents a single metric measurement."""

    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    type: str = "gauge"  # gauge, counter, histogram


@dataclass
class HealthCheck:
    """Represents a health check result."""

    name: str
    status: str  # healthy, degraded, unhealthy
    message: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and manages application metrics."""

    def __init__(self, namespace: str = "gmnap"):
        self.namespace = namespace
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._counters: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric (point-in-time value)."""
        metric = Metric(
            name=f"{self.namespace}.{name}",
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            type="gauge",
        )

        with self._lock:
            self._metrics[metric.name].append(metric)

    def counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        full_name = f"{self.namespace}.{name}"

        with self._lock:
            self._counters[full_name] += value

            metric = Metric(
                name=full_name,
                value=self._counters[full_name],
                timestamp=datetime.now(),
                tags=tags or {},
                type="counter",
            )
            self._metrics[full_name].append(metric)

    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric (for distributions)."""
        metric = Metric(
            name=f"{self.namespace}.{name}",
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            type="histogram",
        )

        with self._lock:
            self._metrics[metric.name].append(metric)

    @contextmanager
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager to time operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.histogram(f"{name}.duration", duration, tags)

    def get_metrics(self, name: Optional[str] = None) -> List[Metric]:
        """Get metrics by name or all metrics."""
        with self._lock:
            if name:
                full_name = (
                    f"{self.namespace}.{name}" if not name.startswith(self.namespace) else name
                )
                return list(self._metrics.get(full_name, []))
            else:
                all_metrics = []
                for metrics_list in self._metrics.values():
                    all_metrics.extend(metrics_list)
                return all_metrics

    def get_latest(self, name: str) -> Optional[Metric]:
        """Get the latest value for a metric."""
        metrics = self.get_metrics(name)
        return metrics[-1] if metrics else None

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        with self._lock:
            for metric_name, metrics_list in self._metrics.items():
                if not metrics_list:
                    continue

                latest = metrics_list[-1]

                # Type declaration
                lines.append(f"# TYPE {metric_name} {latest.type}")

                # Metric value
                tags_str = ""
                if latest.tags:
                    tags_list = [f'{k}="{v}"' for k, v in latest.tags.items()]
                    tags_str = "{" + ",".join(tags_list) + "}"

                lines.append(f"{metric_name}{tags_str} {latest.value}")

        return "\n".join(lines)


class HealthMonitor:
    """Monitors application health."""

    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._results: Dict[str, HealthCheck] = {}
        self._lock = threading.Lock()

    def register_check(self, name: str, check_func: Callable[[], HealthCheck]) -> None:
        """Register a health check function."""
        with self._lock:
            self._checks[name] = check_func

    async def run_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks."""
        results = {}

        for name, check_func in self._checks.items():
            try:
                result = await asyncio.get_event_loop().run_in_executor(None, check_func)
                results[name] = result
            except Exception as e:
                results[name] = HealthCheck(
                    name=name,
                    status="unhealthy",
                    message=f"Check failed: {str(e)}",
                    timestamp=datetime.now(),
                )

        with self._lock:
            self._results = results

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        with self._lock:
            results = self._results.copy()

        if not results:
            return {
                "status": "unknown",
                "message": "No health checks have been run",
                "timestamp": datetime.now().isoformat(),
            }

        # Determine overall status
        unhealthy_count = sum(1 for r in results.values() if r.status == "unhealthy")
        degraded_count = sum(1 for r in results.values() if r.status == "degraded")

        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: {
                    "status": check.status,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "metadata": check.metadata,
                }
                for name, check in results.items()
            },
        }


class PerformanceMonitor:
    """Monitors system performance metrics."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self, interval: int = 60) -> None:
        """Start performance monitoring."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(interval,), daemon=True
        )
        self._monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop(self) -> None:
        """Stop performance monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitor_loop(self, interval: int) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                self._collect_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")

    def _collect_metrics(self) -> None:
        """Collect system performance metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics.gauge("system.cpu.percent", cpu_percent)

        # Memory metrics
        memory = psutil.virtual_memory()
        self.metrics.gauge("system.memory.percent", memory.percent)
        self.metrics.gauge("system.memory.used_mb", memory.used / 1024 / 1024)
        self.metrics.gauge("system.memory.available_mb", memory.available / 1024 / 1024)

        # Disk metrics
        disk = psutil.disk_usage("/")
        self.metrics.gauge("system.disk.percent", disk.percent)
        self.metrics.gauge("system.disk.free_gb", disk.free / 1024 / 1024 / 1024)

        # Process metrics
        process = psutil.Process()
        self.metrics.gauge("process.cpu.percent", process.cpu_percent())
        self.metrics.gauge("process.memory.rss_mb", process.memory_info().rss / 1024 / 1024)
        self.metrics.gauge("process.threads", process.num_threads())


class LoggerAdapter(logging.LoggerAdapter):
    """Enhanced logger with structured logging support."""

    def process(self, msg, kwargs):
        """Process log message to add context."""
        extra = kwargs.get("extra", {})

        # Add standard fields
        extra.update(
            {
                "timestamp": datetime.now().isoformat(),
                "logger": self.logger.name,
                "level": kwargs.get("level", "INFO"),
            }
        )

        # Add any additional context
        if hasattr(self, "context"):
            extra.update(self.context)

        kwargs["extra"] = extra
        return msg, kwargs

    def with_context(self, **context) -> "LoggerAdapter":
        """Create a new logger with additional context."""
        new_logger = LoggerAdapter(self.logger, self.extra)
        new_logger.context = {**getattr(self, "context", {}), **context}
        return new_logger


def setup_logging(config: Dict[str, Any]) -> None:
    """Setup application logging."""
    log_level = getattr(logging, config.get("log_level", "INFO"))
    log_format = config.get("log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Configure root logger
    logging.basicConfig(level=log_level, format=log_format)

    # Configure specific loggers
    logging.getLogger("gmnap").setLevel(log_level)
    logging.getLogger("pipeline").setLevel(log_level)

    # Add JSON formatter if requested
    if config.get("json_logs", False):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logging.getLogger().addHandler(handler)


class JSONFormatter(logging.Formatter):
    """JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "pathname",
                "processName",
                "process",
                "threadName",
                "thread",
                "relativeCreated",
                "msecs",
                "getMessage",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


# Global instances
metrics = MetricsCollector()
health = HealthMonitor()
performance = PerformanceMonitor(metrics)


# Standard health checks
def database_health_check() -> HealthCheck:
    """Check database connectivity."""
    try:
        from src.utils.database import DatabaseManager

        db = DatabaseManager()

        # Try a simple query
        db.execute("SELECT 1")
        db.close()

        return HealthCheck(
            name="database",
            status="healthy",
            message="Database is accessible",
            timestamp=datetime.now(),
        )
    except Exception as e:
        return HealthCheck(
            name="database",
            status="unhealthy",
            message=f"Database error: {str(e)}",
            timestamp=datetime.now(),
        )


def disk_space_health_check() -> HealthCheck:
    """Check available disk space."""
    try:
        disk = psutil.disk_usage("/")
        free_gb = disk.free / 1024 / 1024 / 1024

        if free_gb < 1:
            status = "unhealthy"
            message = f"Critical: Only {free_gb:.2f}GB free"
        elif free_gb < 5:
            status = "degraded"
            message = f"Warning: Only {free_gb:.2f}GB free"
        else:
            status = "healthy"
            message = f"{free_gb:.2f}GB free"

        return HealthCheck(
            name="disk_space",
            status=status,
            message=message,
            timestamp=datetime.now(),
            metadata={"free_gb": free_gb, "percent_used": disk.percent},
        )
    except Exception as e:
        return HealthCheck(
            name="disk_space",
            status="unhealthy",
            message=f"Failed to check disk space: {str(e)}",
            timestamp=datetime.now(),
        )


def memory_health_check() -> HealthCheck:
    """Check memory usage."""
    try:
        memory = psutil.virtual_memory()

        if memory.percent > 90:
            status = "unhealthy"
            message = f"Critical: {memory.percent}% memory used"
        elif memory.percent > 80:
            status = "degraded"
            message = f"Warning: {memory.percent}% memory used"
        else:
            status = "healthy"
            message = f"{memory.percent}% memory used"

        return HealthCheck(
            name="memory",
            status=status,
            message=message,
            timestamp=datetime.now(),
            metadata={
                "percent_used": memory.percent,
                "available_mb": memory.available / 1024 / 1024,
            },
        )
    except Exception as e:
        return HealthCheck(
            name="memory",
            status="unhealthy",
            message=f"Failed to check memory: {str(e)}",
            timestamp=datetime.now(),
        )


# Register default health checks
health.register_check("database", database_health_check)
health.register_check("disk_space", disk_space_health_check)
health.register_check("memory", memory_health_check)
