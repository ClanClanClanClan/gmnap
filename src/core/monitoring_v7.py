"""
V7 Performance Monitoring System - Production Ready
Real-time monitoring, alerting, and reporting for GMNAP V7 architecture
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of performance metrics."""

    THROUGHPUT = "throughput"
    LATENCY = "latency"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    DATABASE_CONNECTIONS = "database_connections"
    QUEUE_DEPTH = "queue_depth"


@dataclass
class PerformanceMetric:
    """Individual performance metric reading."""

    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = "system"
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Performance alert."""

    level: AlertLevel
    metric_type: MetricType
    message: str
    value: float
    threshold: float
    component: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False


@dataclass
class MonitoringConfig:
    """Configuration for V7 monitoring system."""

    # Storage
    metrics_db_path: Path = Path("./cache/monitoring/metrics.db")
    retention_days: int = 30

    # Sampling
    sample_interval_seconds: int = 5
    aggregation_window_minutes: int = 5

    # Alerting thresholds
    throughput_min_threshold: float = 100.0  # entries/sec
    latency_max_threshold: float = 1000.0  # milliseconds
    success_rate_min_threshold: float = 95.0  # percentage
    error_rate_max_threshold: float = 5.0  # percentage
    memory_max_threshold_mb: float = 2048.0  # megabytes

    # Alerting
    enable_alerts: bool = True
    alert_cooldown_minutes: int = 15

    # Reporting
    enable_reports: bool = True
    report_interval_hours: int = 6


class V7MonitoringSystem:
    """
    Production-ready V7 monitoring system.

    Features:
    - Real-time metric collection
    - Historical data storage
    - Automated alerting
    - Performance reporting
    - Health checking
    - Export capabilities
    """

    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.logger = logging.getLogger("v7_monitoring")

        # Initialize storage
        self._init_metrics_database()

        # Active monitoring state
        self._active_alerts: Dict[str, Alert] = {}
        self._last_alert_times: Dict[str, datetime] = {}
        self._alert_handlers: List[Callable[[Alert], None]] = []

        # Performance tracking
        self._current_metrics: Dict[MetricType, PerformanceMetric] = {}
        self._metric_history: List[PerformanceMetric] = []

        self.logger.info("V7 Monitoring System initialized")

    def _init_metrics_database(self) -> None:
        """Initialize SQLite database for metrics storage."""
        self.config.metrics_db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(self.config.metrics_db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    component TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    additional_data TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    component TEXT NOT NULL,
                    message TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    resolved DATETIME,
                    resolved_by TEXT
                )
            """
            )

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")

        self.logger.info(f"Metrics database initialized: {self.config.metrics_db_path}")

    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric."""
        # Store in memory for real-time access
        self._current_metrics[metric.metric_type] = metric
        self._metric_history.append(metric)

        # Persist to database
        with sqlite3.connect(str(self.config.metrics_db_path)) as conn:
            conn.execute(
                """
                INSERT INTO metrics (metric_type, component, value, unit, timestamp, additional_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    metric.metric_type.value,
                    metric.component,
                    metric.value,
                    metric.unit,
                    metric.timestamp.isoformat(),
                    json.dumps(metric.additional_data),
                ),
            )

        # Check for alerts
        if self.config.enable_alerts:
            self._check_thresholds(metric)

        # Limit in-memory history
        if len(self._metric_history) > 1000:
            self._metric_history = self._metric_history[-500:]

    def _check_thresholds(self, metric: PerformanceMetric) -> None:
        """Check metric against alerting thresholds."""
        alert_key = f"{metric.component}:{metric.metric_type.value}"

        # Check cooldown period
        last_alert = self._last_alert_times.get(alert_key)
        if last_alert:
            cooldown_period = timedelta(minutes=self.config.alert_cooldown_minutes)
            if datetime.now() - last_alert < cooldown_period:
                return

        alert = None

        # Throughput checks
        if metric.metric_type == MetricType.THROUGHPUT:
            if metric.value < self.config.throughput_min_threshold:
                alert = Alert(
                    level=AlertLevel.WARNING,
                    metric_type=metric.metric_type,
                    component=metric.component,
                    message=f"Low throughput: {metric.value:.1f} {metric.unit} (threshold: {self.config.throughput_min_threshold})",
                    value=metric.value,
                    threshold=self.config.throughput_min_threshold,
                )

        # Latency checks
        elif metric.metric_type == MetricType.LATENCY:
            if metric.value > self.config.latency_max_threshold:
                alert = Alert(
                    level=(
                        AlertLevel.ERROR
                        if metric.value > self.config.latency_max_threshold * 2
                        else AlertLevel.WARNING
                    ),
                    metric_type=metric.metric_type,
                    component=metric.component,
                    message=f"High latency: {metric.value:.1f} {metric.unit} (threshold: {self.config.latency_max_threshold})",
                    value=metric.value,
                    threshold=self.config.latency_max_threshold,
                )

        # Success rate checks
        elif metric.metric_type == MetricType.SUCCESS_RATE:
            if metric.value < self.config.success_rate_min_threshold:
                alert = Alert(
                    level=AlertLevel.CRITICAL if metric.value < 90.0 else AlertLevel.ERROR,
                    metric_type=metric.metric_type,
                    component=metric.component,
                    message=f"Low success rate: {metric.value:.1f}% (threshold: {self.config.success_rate_min_threshold}%)",
                    value=metric.value,
                    threshold=self.config.success_rate_min_threshold,
                )

        # Error rate checks
        elif metric.metric_type == MetricType.ERROR_RATE:
            if metric.value > self.config.error_rate_max_threshold:
                alert = Alert(
                    level=AlertLevel.CRITICAL if metric.value > 20.0 else AlertLevel.ERROR,
                    metric_type=metric.metric_type,
                    component=metric.component,
                    message=f"High error rate: {metric.value:.1f}% (threshold: {self.config.error_rate_max_threshold}%)",
                    value=metric.value,
                    threshold=self.config.error_rate_max_threshold,
                )

        # Memory checks
        elif metric.metric_type == MetricType.MEMORY_USAGE:
            if metric.value > self.config.memory_max_threshold_mb:
                alert = Alert(
                    level=AlertLevel.WARNING,
                    metric_type=metric.metric_type,
                    component=metric.component,
                    message=f"High memory usage: {metric.value:.1f} MB (threshold: {self.config.memory_max_threshold_mb} MB)",
                    value=metric.value,
                    threshold=self.config.memory_max_threshold_mb,
                )

        if alert:
            self._trigger_alert(alert, alert_key)

    def _trigger_alert(self, alert: Alert, alert_key: str) -> None:
        """Trigger an alert."""
        self._active_alerts[alert_key] = alert
        self._last_alert_times[alert_key] = alert.timestamp

        # Store in database
        with sqlite3.connect(str(self.config.metrics_db_path)) as conn:
            conn.execute(
                """
                INSERT INTO alerts (level, metric_type, component, message, value, threshold, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    alert.level.value,
                    alert.metric_type.value,
                    alert.component,
                    alert.message,
                    alert.value,
                    alert.threshold,
                    alert.timestamp.isoformat(),
                ),
            )

        # Call alert handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")

        self.logger.warning(f"ALERT [{alert.level.value.upper()}] {alert.message}")

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add custom alert handler."""
        self._alert_handlers.append(handler)

    def get_current_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get current performance metrics."""
        result = {}
        for metric_type, metric in self._current_metrics.items():
            result[metric_type.value] = {
                "value": metric.value,
                "unit": metric.unit,
                "timestamp": metric.timestamp.isoformat(),
                "component": metric.component,
            }
        return result

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health assessment."""
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "metrics": self.get_current_metrics(),
            "active_alerts": len(self._active_alerts),
            "recent_alerts": 0,
        }

        # Count recent alerts (last hour)
        hour_ago = datetime.now() - timedelta(hours=1)
        with sqlite3.connect(str(self.config.metrics_db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM alerts 
                WHERE timestamp > ? AND resolved IS NULL
            """,
                (hour_ago.isoformat(),),
            )
            health["recent_alerts"] = cursor.fetchone()[0]

        # Determine overall health status
        if len(self._active_alerts) > 0:
            critical_alerts = [
                a for a in self._active_alerts.values() if a.level == AlertLevel.CRITICAL
            ]
            error_alerts = [a for a in self._active_alerts.values() if a.level == AlertLevel.ERROR]

            if critical_alerts:
                health["status"] = "critical"
            elif error_alerts:
                health["status"] = "degraded"
            elif health["recent_alerts"] > 5:
                health["status"] = "unstable"

        return health

    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        with sqlite3.connect(str(self.config.metrics_db_path)) as conn:
            # Throughput statistics
            cursor = conn.execute(
                """
                SELECT AVG(value), MIN(value), MAX(value), COUNT(*)
                FROM metrics 
                WHERE metric_type = 'throughput' 
                AND timestamp BETWEEN ? AND ?
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )
            throughput_stats = cursor.fetchone()

            # Latency statistics
            cursor = conn.execute(
                """
                SELECT AVG(value), MIN(value), MAX(value), COUNT(*)
                FROM metrics 
                WHERE metric_type = 'latency'
                AND timestamp BETWEEN ? AND ?
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )
            latency_stats = cursor.fetchone()

            # Success rate statistics
            cursor = conn.execute(
                """
                SELECT AVG(value), MIN(value), MAX(value), COUNT(*)
                FROM metrics 
                WHERE metric_type = 'success_rate'
                AND timestamp BETWEEN ? AND ?
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )
            success_stats = cursor.fetchone()

            # Alert count by level
            cursor = conn.execute(
                """
                SELECT level, COUNT(*) 
                FROM alerts 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY level
            """,
                (start_time.isoformat(), end_time.isoformat()),
            )
            alert_counts = dict(cursor.fetchall())

        report = {
            "report_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_hours": hours,
            },
            "performance_summary": {
                "throughput": {
                    "avg_entries_per_sec": throughput_stats[0] or 0,
                    "min_entries_per_sec": throughput_stats[1] or 0,
                    "max_entries_per_sec": throughput_stats[2] or 0,
                    "samples": throughput_stats[3] or 0,
                },
                "latency": {
                    "avg_ms": latency_stats[0] or 0,
                    "min_ms": latency_stats[1] or 0,
                    "max_ms": latency_stats[2] or 0,
                    "samples": latency_stats[3] or 0,
                },
                "success_rate": {
                    "avg_percent": success_stats[0] or 0,
                    "min_percent": success_stats[1] or 0,
                    "max_percent": success_stats[2] or 0,
                    "samples": success_stats[3] or 0,
                },
            },
            "alert_summary": {
                "total_alerts": sum(alert_counts.values()),
                "by_level": alert_counts,
                "active_alerts": len(self._active_alerts),
            },
            "system_health": self.get_system_health(),
            "generated_at": datetime.now().isoformat(),
        }

        return report

    def export_metrics(self, format: str = "json", hours: int = 24) -> str:
        """Export metrics in specified format."""
        if format.lower() == "json":
            report = self.generate_performance_report(hours)
            return json.dumps(report, indent=2)
        elif format.lower() == "csv":
            # Simple CSV export of metrics
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            with sqlite3.connect(str(self.config.metrics_db_path)) as conn:
                cursor = conn.execute(
                    """
                    SELECT metric_type, component, value, unit, timestamp
                    FROM metrics 
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                """,
                    (start_time.isoformat(), end_time.isoformat()),
                )

                rows = ["metric_type,component,value,unit,timestamp"]
                for row in cursor:
                    rows.append(f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]}")

                return "\n".join(rows)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def cleanup_old_data(self) -> None:
        """Clean up old monitoring data based on retention policy."""
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)

        with sqlite3.connect(str(self.config.metrics_db_path)) as conn:
            # Clean up old metrics
            cursor = conn.execute(
                "DELETE FROM metrics WHERE timestamp < ?", (cutoff_date.isoformat(),)
            )
            metrics_deleted = cursor.rowcount

            # Clean up old resolved alerts
            cursor = conn.execute(
                "DELETE FROM alerts WHERE timestamp < ? AND resolved IS NOT NULL",
                (cutoff_date.isoformat(),),
            )
            alerts_deleted = cursor.rowcount

        if metrics_deleted > 0 or alerts_deleted > 0:
            self.logger.info(
                f"Cleaned up {metrics_deleted} old metrics and {alerts_deleted} old alerts"
            )


# Helper functions for easy integration
def create_monitoring_config(
    throughput_threshold: float = 100.0,
    latency_threshold: float = 1000.0,
    success_threshold: float = 95.0,
) -> MonitoringConfig:
    """Create monitoring configuration with custom thresholds."""
    return MonitoringConfig(
        throughput_min_threshold=throughput_threshold,
        latency_max_threshold=latency_threshold,
        success_rate_min_threshold=success_threshold,
    )


@contextmanager
def v7_monitoring_session(config: Optional[MonitoringConfig] = None):
    """Context manager for V7 monitoring sessions."""
    if config is None:
        config = MonitoringConfig()

    monitor = V7MonitoringSystem(config)
    try:
        yield monitor
    finally:
        monitor.cleanup_old_data()


# Integration with streaming pipeline
def integrate_streaming_monitoring(pipeline, monitor: V7MonitoringSystem) -> None:
    """Integrate monitoring with V7 streaming pipeline."""

    def record_streaming_metrics():
        """Record streaming pipeline metrics."""
        if hasattr(pipeline, "metrics"):
            metrics = pipeline.metrics

            # Throughput
            monitor.record_metric(
                PerformanceMetric(
                    metric_type=MetricType.THROUGHPUT,
                    value=metrics.average_throughput,
                    unit="entries/sec",
                    component="streaming_pipeline",
                )
            )

            # Success rate
            monitor.record_metric(
                PerformanceMetric(
                    metric_type=MetricType.SUCCESS_RATE,
                    value=metrics.success_rate,
                    unit="percent",
                    component="streaming_pipeline",
                )
            )

            # Latency
            monitor.record_metric(
                PerformanceMetric(
                    metric_type=MetricType.LATENCY,
                    value=metrics.average_latency_ms,
                    unit="milliseconds",
                    component="streaming_pipeline",
                )
            )

    # Add monitoring integration to pipeline
    if hasattr(pipeline, "_monitor_performance"):
        original_monitor = pipeline._monitor_performance

        async def enhanced_monitor():
            await original_monitor()
            record_streaming_metrics()

        pipeline._monitor_performance = enhanced_monitor
