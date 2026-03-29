#!/usr/bin/env python3
"""
Automated Performance Regression Detection for GMNAP V7 Pipeline

Monitors pipeline stage performance metrics and detects performance regressions
to prevent degradation in production systems.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PerformanceBaseline:
    """Performance baseline for a pipeline stage or operation"""

    stage_name: str
    operation_type: str  # 'latency', 'throughput', 'memory', 'cpu'
    baseline_value: float
    acceptable_variance: float  # Percentage (e.g., 0.1 = 10%)
    measurement_unit: str  # 'ms', 'ops/sec', 'MB', 'percent'
    confidence_interval: Tuple[float, float]
    sample_size: int
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMeasurement:
    """Individual performance measurement"""

    stage_name: str
    operation_type: str
    value: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionAlert:
    """Performance regression alert"""

    stage_name: str
    operation_type: str
    severity: str  # 'WARNING', 'CRITICAL', 'SEVERE'
    current_value: float
    baseline_value: float
    variance_percentage: float
    threshold_exceeded: float
    timestamp: datetime
    measurements_analyzed: int
    confidence_score: float
    remediation_suggestions: List[str] = field(default_factory=list)


class PerformanceRegressionDetector:
    """
    Automated performance regression detection system

    Monitors pipeline performance metrics and detects statistically significant
    regressions using baseline comparison and trend analysis.
    """

    def __init__(self, config_dir: Path, alert_thresholds: Optional[Dict[str, float]] = None):
        self.config_dir = Path(config_dir)
        self.metrics_dir = self.config_dir / "performance" / "metrics"
        self.baselines_dir = self.config_dir / "performance" / "baselines"
        self.alerts_dir = self.config_dir / "performance" / "alerts"

        # Create directories if they don't exist
        for dir_path in [self.metrics_dir, self.baselines_dir, self.alerts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Default alert thresholds (variance percentages)
        self.alert_thresholds = alert_thresholds or {
            "WARNING": 0.15,  # 15% regression
            "CRITICAL": 0.25,  # 25% regression
            "SEVERE": 0.40,  # 40% regression
        }

        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.measurements: List[PerformanceMeasurement] = []
        self.active_alerts: List[RegressionAlert] = []

        # Statistical parameters
        self.min_sample_size = 10
        self.confidence_level = 0.95
        self.lookback_window_hours = 24

        self._load_baselines()
        logger.info(
            f"Performance regression detector initialized with {len(self.baselines)} baselines"
        )

    def _load_baselines(self) -> None:
        """Load existing performance baselines"""
        baseline_files = list(self.baselines_dir.glob("*.json"))

        for baseline_file in baseline_files:
            try:
                with open(baseline_file, "r") as f:
                    data = json.load(f)
                    baseline = PerformanceBaseline(
                        stage_name=data["stage_name"],
                        operation_type=data["operation_type"],
                        baseline_value=data["baseline_value"],
                        acceptable_variance=data["acceptable_variance"],
                        measurement_unit=data["measurement_unit"],
                        confidence_interval=tuple(data["confidence_interval"]),
                        sample_size=data["sample_size"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        metadata=data.get("metadata", {}),
                    )

                    key = f"{baseline.stage_name}_{baseline.operation_type}"
                    self.baselines[key] = baseline

            except Exception as e:
                logger.error(f"Failed to load baseline {baseline_file}: {e}")

    def _save_baseline(self, baseline: PerformanceBaseline) -> None:
        """Save performance baseline to disk"""
        key = f"{baseline.stage_name}_{baseline.operation_type}"
        baseline_file = self.baselines_dir / f"{key}.json"

        baseline_data = {
            "stage_name": baseline.stage_name,
            "operation_type": baseline.operation_type,
            "baseline_value": baseline.baseline_value,
            "acceptable_variance": baseline.acceptable_variance,
            "measurement_unit": baseline.measurement_unit,
            "confidence_interval": list(baseline.confidence_interval),
            "sample_size": baseline.sample_size,
            "timestamp": baseline.timestamp.isoformat(),
            "metadata": baseline.metadata,
        }

        try:
            with open(baseline_file, "w") as f:
                json.dump(baseline_data, f, indent=2)
            logger.info(f"Saved baseline for {key}")
        except Exception as e:
            logger.error(f"Failed to save baseline {key}: {e}")

    def _calculate_confidence_interval(
        self, measurements: List[float], confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for measurements"""
        if len(measurements) < 2:
            mean_val = measurements[0] if measurements else 0.0
            return (mean_val, mean_val)

        mean = np.mean(measurements)
        std_err = np.std(measurements, ddof=1) / np.sqrt(len(measurements))

        # Use t-distribution for small samples, normal for large samples
        if len(measurements) < 30:
            from scipy import stats

            t_val = stats.t.ppf((1 + confidence) / 2, len(measurements) - 1)
            margin = t_val * std_err
        else:
            # Normal approximation for large samples
            z_val = 1.96 if confidence == 0.95 else 2.576  # 99% confidence
            margin = z_val * std_err

        return (mean - margin, mean + margin)

    async def establish_baseline(
        self,
        stage_name: str,
        operation_type: str,
        measurements: List[float],
        measurement_unit: str,
        acceptable_variance: float = 0.15,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PerformanceBaseline:
        """
        Establish performance baseline from historical measurements

        Args:
            stage_name: Name of pipeline stage
            operation_type: Type of operation (latency, throughput, etc.)
            measurements: Historical performance measurements
            measurement_unit: Unit of measurement
            acceptable_variance: Acceptable performance variance (percentage)
            metadata: Additional baseline metadata

        Returns:
            Created performance baseline
        """
        if len(measurements) < self.min_sample_size:
            raise ValueError(
                f"Need at least {self.min_sample_size} measurements, got {len(measurements)}"
            )

        # Calculate statistics
        baseline_value = float(np.median(measurements))  # Use median for robustness
        confidence_interval = self._calculate_confidence_interval(
            measurements, self.confidence_level
        )

        baseline = PerformanceBaseline(
            stage_name=stage_name,
            operation_type=operation_type,
            baseline_value=baseline_value,
            acceptable_variance=acceptable_variance,
            measurement_unit=measurement_unit,
            confidence_interval=confidence_interval,
            sample_size=len(measurements),
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        # Store baseline
        key = f"{stage_name}_{operation_type}"
        self.baselines[key] = baseline
        self._save_baseline(baseline)

        logger.info(f"Established baseline for {key}: {baseline_value:.2f} {measurement_unit}")
        return baseline

    def record_measurement(
        self,
        stage_name: str,
        operation_type: str,
        value: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a performance measurement

        Args:
            stage_name: Name of pipeline stage
            operation_type: Type of operation
            value: Measured performance value
            context: Additional measurement context
        """
        measurement = PerformanceMeasurement(
            stage_name=stage_name,
            operation_type=operation_type,
            value=value,
            timestamp=datetime.now(),
            context=context or {},
        )

        self.measurements.append(measurement)

        # Persist measurement to disk
        measurement_file = (
            self.metrics_dir / f"measurements_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )
        measurement_data = {
            "stage_name": measurement.stage_name,
            "operation_type": measurement.operation_type,
            "value": measurement.value,
            "timestamp": measurement.timestamp.isoformat(),
            "context": measurement.context,
        }

        try:
            with open(measurement_file, "a") as f:
                json.dump(measurement_data, f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to persist measurement: {e}")

    def _get_recent_measurements(
        self, stage_name: str, operation_type: str, hours_back: int = 24
    ) -> List[PerformanceMeasurement]:
        """Get recent measurements for a stage and operation type"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        return [
            m
            for m in self.measurements
            if (
                m.stage_name == stage_name
                and m.operation_type == operation_type
                and m.timestamp >= cutoff_time
            )
        ]

    def _calculate_regression_severity(self, variance_percentage: float) -> str:
        """Calculate regression severity based on variance percentage"""
        abs_variance = abs(variance_percentage)

        if abs_variance >= self.alert_thresholds["SEVERE"]:
            return "SEVERE"
        elif abs_variance >= self.alert_thresholds["CRITICAL"]:
            return "CRITICAL"
        elif abs_variance >= self.alert_thresholds["WARNING"]:
            return "WARNING"
        else:
            return "INFO"

    def _generate_remediation_suggestions(
        self, stage_name: str, operation_type: str, variance_percentage: float
    ) -> List[str]:
        """Generate remediation suggestions based on regression type"""
        suggestions = []

        if operation_type == "latency" and variance_percentage > 0:
            suggestions.extend(
                [
                    f"Check {stage_name} stage for performance bottlenecks",
                    "Review recent code changes that may have affected latency",
                    "Monitor system resources (CPU, memory, I/O)",
                    "Consider increasing parallelization or caching",
                ]
            )

        elif operation_type == "throughput" and variance_percentage < 0:
            suggestions.extend(
                [
                    f"Investigate throughput degradation in {stage_name}",
                    "Check for resource contention or blocking operations",
                    "Review batch size and processing parameters",
                    "Monitor queue depths and processing backlogs",
                ]
            )

        elif operation_type == "memory" and variance_percentage > 0:
            suggestions.extend(
                [
                    f"Investigate memory usage increase in {stage_name}",
                    "Check for memory leaks or retention issues",
                    "Review data structure sizes and caching policies",
                    "Consider memory profiling and optimization",
                ]
            )

        return suggestions

    async def detect_regressions(
        self, stage_name: Optional[str] = None, operation_type: Optional[str] = None
    ) -> List[RegressionAlert]:
        """
        Detect performance regressions against established baselines

        Args:
            stage_name: Specific stage to check (None for all)
            operation_type: Specific operation type to check (None for all)

        Returns:
            List of regression alerts
        """
        alerts = []

        # Filter baselines to check
        baselines_to_check = {}
        for key, baseline in self.baselines.items():
            if stage_name and baseline.stage_name != stage_name:
                continue
            if operation_type and baseline.operation_type != operation_type:
                continue
            baselines_to_check[key] = baseline

        for key, baseline in baselines_to_check.items():
            # Get recent measurements
            recent_measurements = self._get_recent_measurements(
                baseline.stage_name, baseline.operation_type, self.lookback_window_hours
            )

            if len(recent_measurements) < 3:  # Need minimum measurements for analysis
                continue

            # Calculate current performance
            current_values = [m.value for m in recent_measurements]
            current_performance = float(np.median(current_values))

            # Calculate variance from baseline
            variance = (current_performance - baseline.baseline_value) / baseline.baseline_value
            variance_percentage = variance * 100

            # Check if variance exceeds acceptable threshold
            if abs(variance) > baseline.acceptable_variance:
                severity = self._calculate_regression_severity(variance_percentage)
                confidence_score = min(len(current_values) / self.min_sample_size, 1.0)

                alert = RegressionAlert(
                    stage_name=baseline.stage_name,
                    operation_type=baseline.operation_type,
                    severity=severity,
                    current_value=current_performance,
                    baseline_value=baseline.baseline_value,
                    variance_percentage=variance_percentage,
                    threshold_exceeded=abs(variance) - baseline.acceptable_variance,
                    timestamp=datetime.now(),
                    measurements_analyzed=len(current_values),
                    confidence_score=confidence_score,
                    remediation_suggestions=self._generate_remediation_suggestions(
                        baseline.stage_name, baseline.operation_type, variance_percentage
                    ),
                )

                alerts.append(alert)
                logger.warning(
                    f"Performance regression detected: {baseline.stage_name}/{baseline.operation_type} "
                    f"- {variance_percentage:+.1f}% change ({severity})"
                )

        # Update active alerts
        self.active_alerts.extend(alerts)

        # Save alerts to disk
        if alerts:
            await self._save_alerts(alerts)

        return alerts

    async def _save_alerts(self, alerts: List[RegressionAlert]) -> None:
        """Save regression alerts to disk"""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        alerts_file = self.alerts_dir / f"alerts_{timestamp_str}.json"

        alerts_data = []
        for alert in alerts:
            alert_data = {
                "stage_name": alert.stage_name,
                "operation_type": alert.operation_type,
                "severity": alert.severity,
                "current_value": alert.current_value,
                "baseline_value": alert.baseline_value,
                "variance_percentage": alert.variance_percentage,
                "threshold_exceeded": alert.threshold_exceeded,
                "timestamp": alert.timestamp.isoformat(),
                "measurements_analyzed": alert.measurements_analyzed,
                "confidence_score": alert.confidence_score,
                "remediation_suggestions": alert.remediation_suggestions,
            }
            alerts_data.append(alert_data)

        try:
            with open(alerts_file, "w") as f:
                json.dump(alerts_data, f, indent=2)
            logger.info(f"Saved {len(alerts)} alerts to {alerts_file}")
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")

    async def generate_performance_report(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Generate comprehensive performance report

        Args:
            hours_back: Hours of history to include in report

        Returns:
            Performance report dictionary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        recent_measurements = [m for m in self.measurements if m.timestamp >= cutoff_time]

        # Group measurements by stage and operation
        performance_data = {}
        for measurement in recent_measurements:
            key = f"{measurement.stage_name}_{measurement.operation_type}"
            if key not in performance_data:
                performance_data[key] = []
            performance_data[key].append(measurement.value)

        # Calculate performance statistics
        stage_stats = {}
        for key, values in performance_data.items():
            if len(values) >= 3:  # Minimum for meaningful stats
                stage_stats[key] = {
                    "count": len(values),
                    "mean": float(np.mean(values)),
                    "median": float(np.median(values)),
                    "std_dev": float(np.std(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "percentile_95": float(np.percentile(values, 95)),
                    "percentile_99": float(np.percentile(values, 99)),
                }

        # Recent alerts
        recent_alerts = [alert for alert in self.active_alerts if alert.timestamp >= cutoff_time]

        alert_summary = {
            "total_alerts": len(recent_alerts),
            "by_severity": {
                "SEVERE": len([a for a in recent_alerts if a.severity == "SEVERE"]),
                "CRITICAL": len([a for a in recent_alerts if a.severity == "CRITICAL"]),
                "WARNING": len([a for a in recent_alerts if a.severity == "WARNING"]),
            },
        }

        report = {
            "timestamp": datetime.now().isoformat(),
            "reporting_period_hours": hours_back,
            "measurements_analyzed": len(recent_measurements),
            "baselines_count": len(self.baselines),
            "performance_statistics": stage_stats,
            "alert_summary": alert_summary,
            "recent_alerts": [
                {
                    "stage_name": alert.stage_name,
                    "operation_type": alert.operation_type,
                    "severity": alert.severity,
                    "variance_percentage": alert.variance_percentage,
                    "timestamp": alert.timestamp.isoformat(),
                }
                for alert in recent_alerts[-10:]  # Last 10 alerts
            ],
        }

        return report

    def clear_old_measurements(self, days_to_keep: int = 7) -> int:
        """
        Clear old performance measurements to manage memory usage

        Args:
            days_to_keep: Number of days of measurements to retain

        Returns:
            Number of measurements cleared
        """
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)

        measurements_before = len(self.measurements)
        self.measurements = [m for m in self.measurements if m.timestamp >= cutoff_time]

        cleared_count = measurements_before - len(self.measurements)

        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} old measurements (keeping {days_to_keep} days)")

        return cleared_count


# Convenience functions for common use cases


async def detect_latency_regressions(
    detector: PerformanceRegressionDetector, stage_name: str, recent_latencies: List[float]
) -> List[RegressionAlert]:
    """
    Convenience function to detect latency regressions for a specific stage

    Args:
        detector: Performance regression detector instance
        stage_name: Name of pipeline stage
        recent_latencies: Recent latency measurements in milliseconds

    Returns:
        List of regression alerts
    """
    # Record recent measurements
    for latency in recent_latencies:
        detector.record_measurement(stage_name, "latency", latency)

    # Detect regressions
    return await detector.detect_regressions(stage_name=stage_name, operation_type="latency")


async def establish_v7_pipeline_baselines(
    detector: PerformanceRegressionDetector, historical_data: Dict[str, Dict[str, List[float]]]
) -> Dict[str, PerformanceBaseline]:
    """
    Establish performance baselines for all V7 pipeline stages

    Args:
        detector: Performance regression detector instance
        historical_data: Historical performance data by stage and operation type

    Returns:
        Dictionary of established baselines
    """
    baselines = {}

    for stage_name, stage_data in historical_data.items():
        for operation_type, measurements in stage_data.items():
            if len(measurements) >= detector.min_sample_size:
                try:
                    baseline = await detector.establish_baseline(
                        stage_name=stage_name,
                        operation_type=operation_type,
                        measurements=measurements,
                        measurement_unit="ms" if operation_type == "latency" else "ops/sec",
                        acceptable_variance=0.15,  # 15% variance threshold
                        metadata={
                            "pipeline_version": "v7",
                            "established_at": datetime.now().isoformat(),
                        },
                    )

                    key = f"{stage_name}_{operation_type}"
                    baselines[key] = baseline

                except Exception as e:
                    logger.error(
                        f"Failed to establish baseline for {stage_name}/{operation_type}: {e}"
                    )

    return baselines


if __name__ == "__main__":
    import asyncio

    async def demo():
        """Demo of performance regression detection"""
        config_dir = Path("./config")
        detector = PerformanceRegressionDetector(config_dir)

        # Mock historical data for establishing baselines
        historical_data = {
            "stage_1_region_detection": {
                "latency": [45.2, 47.1, 44.8, 46.3, 45.9, 46.7, 45.1, 44.9, 46.2, 45.5],
                "throughput": [
                    220.5,
                    218.9,
                    221.3,
                    219.7,
                    220.1,
                    219.4,
                    221.0,
                    220.8,
                    219.2,
                    220.6,
                ],
            },
            "stage_4_authority_lookup": {
                "latency": [125.8, 127.2, 124.9, 126.5, 125.1, 127.0, 125.7, 126.1, 124.8, 126.3],
                "throughput": [89.2, 88.9, 89.5, 89.1, 88.8, 89.3, 89.0, 89.4, 88.7, 89.2],
            },
        }

        # Establish baselines
        print("Establishing performance baselines...")
        baselines = await establish_v7_pipeline_baselines(detector, historical_data)
        print(f"Established {len(baselines)} baselines")

        # Simulate some new measurements (with regression)
        print("\nSimulating performance measurements...")

        # Normal measurements
        detector.record_measurement("stage_1_region_detection", "latency", 45.8)
        detector.record_measurement("stage_1_region_detection", "latency", 46.2)

        # Regression measurements (20% slower)
        detector.record_measurement("stage_1_region_detection", "latency", 55.0)  # 20% regression
        detector.record_measurement("stage_1_region_detection", "latency", 54.8)
        detector.record_measurement("stage_1_region_detection", "latency", 55.2)

        # Detect regressions
        alerts = await detector.detect_regressions()

        print(f"\nDetected {len(alerts)} performance regression alerts:")
        for alert in alerts:
            print(
                f"  {alert.severity}: {alert.stage_name}/{alert.operation_type} "
                f"- {alert.variance_percentage:+.1f}% change"
            )

        # Generate report
        report = await detector.generate_performance_report(hours_back=1)
        print(f"\nPerformance report: {report['alert_summary']['total_alerts']} total alerts")

    asyncio.run(demo())
