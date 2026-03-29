"""
GMNAP Analytics and Monitoring System

Comprehensive analytics for tracking system performance, usage patterns,
and data quality metrics across the GMNAP pipeline.
"""

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class RegionAnalytics:
    """Analytics for regional processing."""

    region_code: str
    total_processed: int = 0
    successful_processed: int = 0
    validation_failures: int = 0
    security_blocks: int = 0
    edge_case_successes: int = 0
    edge_case_failures: int = 0
    average_processing_time_ms: float = 0.0
    last_active: Optional[datetime] = None
    error_patterns: Dict[str, int] = field(default_factory=dict)


@dataclass
class PipelineAnalytics:
    """Analytics for pipeline stages."""

    stage_name: str
    executions: int = 0
    total_time_ms: float = 0.0
    average_time_ms: float = 0.0
    failure_count: int = 0
    success_rate: float = 0.0
    throughput_entries_per_sec: float = 0.0
    peak_memory_mb: float = 0.0
    last_execution: Optional[datetime] = None


@dataclass
class SecurityAnalytics:
    """Security-related analytics."""

    total_security_checks: int = 0
    attacks_blocked: int = 0
    attack_types_blocked: Dict[str, int] = field(default_factory=dict)
    vulnerabilities_detected: int = 0
    dos_attempts_blocked: int = 0
    injection_attempts_blocked: int = 0
    last_security_incident: Optional[datetime] = None


@dataclass
class QualityAnalytics:
    """Data quality analytics."""

    total_entries_processed: int = 0
    validation_passes: int = 0
    validation_failures: int = 0
    duplicate_entries_detected: int = 0
    data_completeness_score: float = 0.0
    accuracy_score: float = 0.0
    consistency_score: float = 0.0
    script_validation_success_rate: float = 0.0
    cjk_roundtrip_accuracy: Dict[str, float] = field(default_factory=dict)


@dataclass
class PerformanceAnalytics:
    """Performance analytics."""

    total_processing_time_seconds: float = 0.0
    entries_per_second: float = 0.0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_io_mb: float = 0.0
    network_requests: int = 0
    api_response_time_ms: float = 0.0


class AnalyticsCollector:
    """
    Comprehensive analytics collection system for GMNAP.

    Tracks performance, security, quality, and usage metrics across
    all pipeline stages and regional processors.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize analytics collector.

        Args:
            output_dir: Directory to save analytics data
        """
        self.output_dir = output_dir or Path("./analytics")
        self.output_dir.mkdir(exist_ok=True)

        # Thread safety
        self._lock = threading.RLock()

        # Analytics storage
        self.region_analytics: Dict[str, RegionAnalytics] = {}
        self.pipeline_analytics: Dict[str, PipelineAnalytics] = {}
        self.security_analytics = SecurityAnalytics()
        self.quality_analytics = QualityAnalytics()
        self.performance_analytics = PerformanceAnalytics()

        # Session tracking
        self.session_start = datetime.now()
        self.session_id = f"session_{int(time.time())}"

        # Real-time tracking
        self._active_operations = {}
        self._performance_samples = defaultdict(list)

    def record_region_processing(
        self,
        region_code: str,
        success: bool,
        processing_time_ms: float,
        error_type: Optional[str] = None,
        edge_case_result: Optional[bool] = None,
    ) -> None:
        """Record regional processing metrics."""
        with self._lock:
            if region_code not in self.region_analytics:
                self.region_analytics[region_code] = RegionAnalytics(region_code)

            analytics = self.region_analytics[region_code]
            analytics.total_processed += 1
            analytics.last_active = datetime.now()

            if success:
                analytics.successful_processed += 1
            else:
                analytics.validation_failures += 1
                if error_type:
                    analytics.error_patterns[error_type] = (
                        analytics.error_patterns.get(error_type, 0) + 1
                    )

            # Update average processing time
            total_time = (
                analytics.average_processing_time_ms * (analytics.total_processed - 1)
                + processing_time_ms
            )
            analytics.average_processing_time_ms = total_time / analytics.total_processed

            # Edge case tracking
            if edge_case_result is not None:
                if edge_case_result:
                    analytics.edge_case_successes += 1
                else:
                    analytics.edge_case_failures += 1

    def record_security_event(
        self, attack_type: str, blocked: bool, severity: str = "medium"
    ) -> None:
        """Record security-related events."""
        with self._lock:
            self.security_analytics.total_security_checks += 1

            if blocked:
                self.security_analytics.attacks_blocked += 1
                self.security_analytics.attack_types_blocked[attack_type] = (
                    self.security_analytics.attack_types_blocked.get(attack_type, 0) + 1
                )

                # Categorize attack types
                if "dos" in attack_type.lower() or "length" in attack_type.lower():
                    self.security_analytics.dos_attempts_blocked += 1
                elif any(inj in attack_type.lower() for inj in ["sql", "xss", "command", "script"]):
                    self.security_analytics.injection_attempts_blocked += 1
            else:
                self.security_analytics.vulnerabilities_detected += 1
                self.security_analytics.last_security_incident = datetime.now()

    def record_pipeline_stage(
        self,
        stage_name: str,
        execution_time_ms: float,
        success: bool,
        entries_processed: int = 0,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Record pipeline stage execution metrics."""
        with self._lock:
            if stage_name not in self.pipeline_analytics:
                self.pipeline_analytics[stage_name] = PipelineAnalytics(stage_name)

            analytics = self.pipeline_analytics[stage_name]
            analytics.executions += 1
            analytics.total_time_ms += execution_time_ms
            analytics.average_time_ms = analytics.total_time_ms / analytics.executions
            analytics.last_execution = datetime.now()

            if not success:
                analytics.failure_count += 1

            analytics.success_rate = (
                analytics.executions - analytics.failure_count
            ) / analytics.executions

            if execution_time_ms > 0 and entries_processed > 0:
                analytics.throughput_entries_per_sec = entries_processed / (
                    execution_time_ms / 1000.0
                )

            if memory_usage_mb > analytics.peak_memory_mb:
                analytics.peak_memory_mb = memory_usage_mb

    def record_quality_metrics(
        self,
        total_entries: int,
        validation_passes: int,
        validation_failures: int,
        duplicates: int = 0,
        completeness_score: float = 0.0,
        accuracy_score: float = 0.0,
    ) -> None:
        """Record data quality metrics."""
        with self._lock:
            qa = self.quality_analytics
            qa.total_entries_processed += total_entries
            qa.validation_passes += validation_passes
            qa.validation_failures += validation_failures
            qa.duplicate_entries_detected += duplicates

            # Update running averages
            if qa.total_entries_processed > 0:
                qa.data_completeness_score = (qa.data_completeness_score + completeness_score) / 2
                qa.accuracy_score = (qa.accuracy_score + accuracy_score) / 2

    def record_cjk_roundtrip(self, region_code: str, accuracy: float) -> None:
        """Record CJK round-trip accuracy."""
        with self._lock:
            self.quality_analytics.cjk_roundtrip_accuracy[region_code] = accuracy

    def record_performance_sample(
        self,
        entries_per_second: float,
        memory_mb: float,
        cpu_percent: float,
        cache_hit_rate: float = 0.0,
    ) -> None:
        """Record real-time performance sample."""
        with self._lock:
            pa = self.performance_analytics
            pa.entries_per_second = entries_per_second
            pa.memory_usage_mb = memory_mb
            pa.cpu_usage_percent = cpu_percent
            pa.cache_hit_rate = cache_hit_rate

            # Store samples for trend analysis
            self._performance_samples["eps"].append(entries_per_second)
            self._performance_samples["memory"].append(memory_mb)
            self._performance_samples["cpu"].append(cpu_percent)

            # Keep only last 1000 samples
            for key in self._performance_samples:
                if len(self._performance_samples[key]) > 1000:
                    self._performance_samples[key] = self._performance_samples[key][-1000:]

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics summary."""
        with self._lock:
            session_duration = (datetime.now() - self.session_start).total_seconds()

            # Region performance summary
            region_summary = {}
            for code, analytics in self.region_analytics.items():
                success_rate = (
                    analytics.successful_processed / analytics.total_processed
                    if analytics.total_processed > 0
                    else 0
                )
                region_summary[code] = {
                    "total_processed": analytics.total_processed,
                    "success_rate": success_rate,
                    "avg_processing_time_ms": analytics.average_processing_time_ms,
                    "edge_case_success_rate": (
                        analytics.edge_case_successes
                        / (analytics.edge_case_successes + analytics.edge_case_failures)
                        if (analytics.edge_case_successes + analytics.edge_case_failures) > 0
                        else 0
                    ),
                }

            # Pipeline stage summary
            pipeline_summary = {}
            for stage, analytics in self.pipeline_analytics.items():
                pipeline_summary[stage] = {
                    "executions": analytics.executions,
                    "avg_time_ms": analytics.average_time_ms,
                    "success_rate": analytics.success_rate,
                    "throughput_eps": analytics.throughput_entries_per_sec,
                }

            # Security summary
            security_block_rate = (
                self.security_analytics.attacks_blocked
                / self.security_analytics.total_security_checks
                if self.security_analytics.total_security_checks > 0
                else 0
            )

            return {
                "session_info": {
                    "session_id": self.session_id,
                    "start_time": self.session_start.isoformat(),
                    "duration_seconds": session_duration,
                },
                "regions": region_summary,
                "pipeline_stages": pipeline_summary,
                "security": {
                    "total_checks": self.security_analytics.total_security_checks,
                    "attacks_blocked": self.security_analytics.attacks_blocked,
                    "block_rate": security_block_rate,
                    "attack_types": dict(self.security_analytics.attack_types_blocked),
                    "dos_blocked": self.security_analytics.dos_attempts_blocked,
                    "injection_blocked": self.security_analytics.injection_attempts_blocked,
                },
                "quality": {
                    "total_entries": self.quality_analytics.total_entries_processed,
                    "validation_pass_rate": (
                        self.quality_analytics.validation_passes
                        / (
                            self.quality_analytics.validation_passes
                            + self.quality_analytics.validation_failures
                        )
                        if (
                            self.quality_analytics.validation_passes
                            + self.quality_analytics.validation_failures
                        )
                        > 0
                        else 0
                    ),
                    "duplicate_rate": (
                        self.quality_analytics.duplicate_entries_detected
                        / self.quality_analytics.total_entries_processed
                        if self.quality_analytics.total_entries_processed > 0
                        else 0
                    ),
                    "completeness_score": self.quality_analytics.data_completeness_score,
                    "accuracy_score": self.quality_analytics.accuracy_score,
                    "cjk_roundtrip": dict(self.quality_analytics.cjk_roundtrip_accuracy),
                },
                "performance": asdict(self.performance_analytics),
            }

    def save_analytics(self, filename: Optional[str] = None) -> Path:
        """Save analytics to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analytics_{timestamp}.json"

        filepath = self.output_dir / filename
        report = self.generate_summary_report()

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Analytics saved to {filepath}")
        return filepath

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics."""
        with self._lock:
            return {
                "active_regions": len(
                    [
                        r
                        for r in self.region_analytics.values()
                        if r.last_active and (datetime.now() - r.last_active).seconds < 300
                    ]
                ),
                "total_entries_processed": sum(
                    r.total_processed for r in self.region_analytics.values()
                ),
                "current_performance": asdict(self.performance_analytics),
                "security_status": {
                    "attacks_blocked_last_hour": sum(
                        1
                        for incident in [self.security_analytics.last_security_incident]
                        if incident and (datetime.now() - incident).seconds < 3600
                    ),
                    "total_blocks": self.security_analytics.attacks_blocked,
                },
                "top_performing_regions": sorted(
                    [
                        (
                            code,
                            (
                                analytics.successful_processed / analytics.total_processed
                                if analytics.total_processed > 0
                                else 0
                            ),
                        )
                        for code, analytics in self.region_analytics.items()
                        if analytics.total_processed > 10
                    ],
                    key=lambda x: x[1],
                    reverse=True,
                )[:10],
            }


# Global analytics collector instance
_analytics_collector: Optional[AnalyticsCollector] = None


def get_analytics_collector() -> AnalyticsCollector:
    """Get or create the global analytics collector."""
    global _analytics_collector
    if _analytics_collector is None:
        _analytics_collector = AnalyticsCollector()
    return _analytics_collector


def reset_analytics_collector(output_dir: Optional[Path] = None) -> AnalyticsCollector:
    """Reset the global analytics collector with new configuration."""
    global _analytics_collector
    _analytics_collector = AnalyticsCollector(output_dir)
    return _analytics_collector
