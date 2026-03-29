#!/usr/bin/env python3
"""
from typing import List
from typing import Optional
from typing import Any
Comprehensive Performance Regression Test Harness

Provides statistical validation and edge case coverage for performance regression
detection in the GMNAP v7 pipeline system.
"""

import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from authorities.base import AuthorityFetcher, QuotaManager
    from src.core.pipeline_v7 import V7Pipeline
    from src.core.quality_gates import EnhancedQualityGates
    from src.regions.manager import RegionManager
except ImportError as e:
    pytest.skip(f"Pipeline components not available: {e}", allow_module_level=True)


@dataclass
class PerformanceMetric:
    """Single performance measurement"""

    operation: str
    duration_ms: float
    timestamp: datetime
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    entries_processed: int = 1
    metadata: Dict[str, Any] = None


@dataclass
class RegressionBaseline:
    """Performance baseline for regression detection"""

    operation: str
    mean_duration_ms: float
    std_deviation_ms: float
    percentile_95_ms: float
    sample_count: int
    last_updated: datetime
    confidence_interval: Tuple[float, float]


class StatisticalAnalyzer:
    """Statistical analysis for performance regression detection"""

    def __init__(self, confidence_level: float = 0.95, sensitivity: float = 0.15):
        self.confidence_level = confidence_level
        self.sensitivity = sensitivity  # 15% degradation threshold

    def analyze_regression(
        self, baseline: RegressionBaseline, current_samples: List[float]
    ) -> Dict[str, Any]:
        """
        Analyze current performance against baseline for regression.

        Uses statistical hypothesis testing to detect significant performance degradation.
        """
        if len(current_samples) < 3:
            return {
                "regression_detected": False,
                "confidence": 0.0,
                "reason": "Insufficient samples for statistical analysis",
            }

        current_mean = statistics.mean(current_samples)
        current_std = (
            statistics.stdev(current_samples) if len(current_samples) > 1 else 0
        )

        # Calculate percentage change
        percent_change = (
            (current_mean - baseline.mean_duration_ms) / baseline.mean_duration_ms * 100
        )

        # Statistical significance test (Welch's t-test approximation)
        pooled_variance = (baseline.std_deviation_ms**2) + (current_std**2)
        standard_error = (pooled_variance / len(current_samples)) ** 0.5

        if standard_error == 0:
            t_statistic = 0
        else:
            t_statistic = (current_mean - baseline.mean_duration_ms) / standard_error

        # Simple significance threshold (more sophisticated methods available)
        significance_threshold = 2.0  # Approximately 95% confidence
        is_significant = abs(t_statistic) > significance_threshold

        # Regression detection logic
        regression_detected = (
            percent_change
            > (self.sensitivity * 100)  # Performance degraded by threshold
            and is_significant  # Change is statistically significant
        )

        confidence = min(abs(t_statistic) / significance_threshold, 1.0)

        return {
            "regression_detected": regression_detected,
            "confidence": confidence,
            "percent_change": percent_change,
            "current_mean_ms": current_mean,
            "baseline_mean_ms": baseline.mean_duration_ms,
            "t_statistic": t_statistic,
            "is_significant": is_significant,
            "sample_count": len(current_samples),
            "analysis_timestamp": datetime.now().isoformat(),
        }

    def update_baseline(
        self, operation: str, samples: List[float]
    ) -> RegressionBaseline:
        """Update performance baseline with new samples"""
        if len(samples) < 5:
            raise ValueError("Need at least 5 samples to establish baseline")

        mean_duration = statistics.mean(samples)
        std_deviation = statistics.stdev(samples)
        percentile_95 = sorted(samples)[int(len(samples) * 0.95)]

        # Calculate confidence interval (95%)
        margin_of_error = 1.96 * (std_deviation / (len(samples) ** 0.5))
        confidence_interval = (
            mean_duration - margin_of_error,
            mean_duration + margin_of_error,
        )

        return RegressionBaseline(
            operation=operation,
            mean_duration_ms=mean_duration,
            std_deviation_ms=std_deviation,
            percentile_95_ms=percentile_95,
            sample_count=len(samples),
            last_updated=datetime.now(),
            confidence_interval=confidence_interval,
        )


class PerformanceRegressionHarness:
    """Comprehensive performance regression test harness"""

    def __init__(self, baseline_file: Optional[Path] = None):
        self.baseline_file = baseline_file or Path("cache/performance_baselines.json")
        self.baselines: Dict[str, RegressionBaseline] = {}
        self.analyzer = StatisticalAnalyzer()
        self.current_session_metrics: List[PerformanceMetric] = []

        # Load existing baselines
        self._load_baselines()

    def _load_baselines(self):
        """Load performance baselines from file"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file) as f:
                    data = json.load(f)

                for op, baseline_data in data.items():
                    self.baselines[op] = RegressionBaseline(
                        operation=op,
                        mean_duration_ms=baseline_data["mean_duration_ms"],
                        std_deviation_ms=baseline_data["std_deviation_ms"],
                        percentile_95_ms=baseline_data["percentile_95_ms"],
                        sample_count=baseline_data["sample_count"],
                        last_updated=datetime.fromisoformat(
                            baseline_data["last_updated"]
                        ),
                        confidence_interval=tuple(baseline_data["confidence_interval"]),
                    )
            except Exception as e:
                print(f"Warning: Could not load baselines: {e}")

    def _save_baselines(self):
        """Save performance baselines to file"""
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for op, baseline in self.baselines.items():
            data[op] = {
                "mean_duration_ms": baseline.mean_duration_ms,
                "std_deviation_ms": baseline.std_deviation_ms,
                "percentile_95_ms": baseline.percentile_95_ms,
                "sample_count": baseline.sample_count,
                "last_updated": baseline.last_updated.isoformat(),
                "confidence_interval": list(baseline.confidence_interval),
            }

        with open(self.baseline_file, "w") as f:
            json.dump(data, f, indent=2)

    async def measure_operation(
        self, operation_name: str, operation_func, *args, **kwargs
    ) -> PerformanceMetric:
        """
        Measure performance of an operation with statistical recording.
        """
        start_time = time.perf_counter()
        start_timestamp = datetime.now()

        try:
            # Execute the operation
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Still record the failed operation for analysis
            metric = PerformanceMetric(
                operation=operation_name,
                duration_ms=duration_ms,
                timestamp=start_timestamp,
                entries_processed=0,
                metadata={"error": str(e), "failed": True},
            )
            self.current_session_metrics.append(metric)
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine entries processed based on result type
        entries_processed = 1
        if isinstance(result, (list, tuple)):
            entries_processed = len(result)
        elif isinstance(result, dict) and "entries_processed" in result:
            entries_processed = result["entries_processed"]

        metric = PerformanceMetric(
            operation=operation_name,
            duration_ms=duration_ms,
            timestamp=start_timestamp,
            entries_processed=entries_processed,
            metadata={"success": True},
        )

        self.current_session_metrics.append(metric)
        return metric

    def establish_baseline(
        self, operation: str, num_samples: int = 20
    ) -> RegressionBaseline:
        """
        Establish performance baseline for an operation by running multiple samples.
        """
        # Get recent metrics for this operation
        operation_metrics = [
            m for m in self.current_session_metrics if m.operation == operation
        ]

        if len(operation_metrics) < num_samples:
            raise ValueError(
                f"Need {num_samples} samples, only have {len(operation_metrics)}"
            )

        # Use the most recent samples
        recent_samples = operation_metrics[-num_samples:]
        durations = [m.duration_ms for m in recent_samples]

        baseline = self.analyzer.update_baseline(operation, durations)
        self.baselines[operation] = baseline
        self._save_baselines()

        return baseline

    def check_regression(self, operation: str, min_samples: int = 5) -> Dict[str, Any]:
        """
        Check for performance regression in recent measurements.
        """
        if operation not in self.baselines:
            return {
                "regression_detected": False,
                "reason": f"No baseline established for operation: {operation}",
            }

        # Get recent metrics for this operation
        recent_metrics = [
            m for m in self.current_session_metrics if m.operation == operation
        ][-min_samples:]

        if len(recent_metrics) < min_samples:
            return {
                "regression_detected": False,
                "reason": f"Insufficient recent samples: {len(recent_metrics)} < {min_samples}",
            }

        current_durations = [m.duration_ms for m in recent_metrics]
        baseline = self.baselines[operation]

        return self.analyzer.analyze_regression(baseline, current_durations)

    def generate_regression_report(self) -> Dict[str, Any]:
        """Generate comprehensive regression analysis report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "session_metrics_count": len(self.current_session_metrics),
            "operations_analyzed": list(self.baselines.keys()),
            "regression_analysis": {},
            "summary": {
                "regressions_detected": 0,
                "operations_tested": 0,
                "average_performance_change": 0.0,
            },
        }

        performance_changes = []

        for operation in self.baselines.keys():
            analysis = self.check_regression(operation)
            report["regression_analysis"][operation] = analysis

            if "percent_change" in analysis:
                performance_changes.append(analysis["percent_change"])

            if analysis.get("regression_detected"):
                report["summary"]["regressions_detected"] += 1

            if analysis.get("sample_count", 0) > 0:
                report["summary"]["operations_tested"] += 1

        if performance_changes:
            report["summary"]["average_performance_change"] = statistics.mean(
                performance_changes
            )

        return report


class TestPerformanceRegressionHarness:
    """Test suite for the performance regression harness"""

    @pytest.fixture
    def harness(self):
        """Create test harness with temporary baseline file"""
        test_baseline_file = Path("cache/test_performance_baselines.json")
        harness = PerformanceRegressionHarness(test_baseline_file)
        yield harness
        # Cleanup
        if test_baseline_file.exists():
            test_baseline_file.unlink()

    @pytest.fixture
    async def pipeline(self):
        """Create V7 pipeline for testing"""
        try:
            return V7Pipeline()
        except Exception as e:
            pytest.skip(f"Pipeline not available: {e}")

    @pytest.fixture
    async def quality_gates(self):
        """Create quality gates for testing"""
        try:
            return EnhancedQualityGates()
        except Exception as e:
            pytest.skip(f"Quality gates not available: {e}")

    @pytest.mark.asyncio
    async def test_measure_async_operation(self, harness):
        """Test measurement of async operations"""

        async def test_operation(delay_ms: int = 10):
            await asyncio.sleep(delay_ms / 1000)
            return {"processed": 5}

        metric = await harness.measure_operation(
            "test_async", test_operation, delay_ms=50
        )

        assert metric.operation == "test_async"
        assert metric.duration_ms >= 45  # Should be at least the sleep time
        assert metric.entries_processed == 5
        assert metric.metadata["success"] is True

    @pytest.mark.timeout(15)
    def test_measure_sync_operation(self, harness):
        """Test measuring a synchronous operation."""

        @pytest.mark.timeout(15)
        def test_operation(items: int = 3):
            time.sleep(0.01)  # Simulate work
            return list(range(items))

        # Use asyncio.run to run the async measurement
        async def run_test():
            return await harness.measure_operation("test_sync", test_operation, items=7)

        metric = asyncio.run(run_test())

        assert metric.operation == "test_sync"
        assert metric.duration_ms >= 8  # Should be at least the sleep time
        assert metric.entries_processed == 7  # Length of returned list

    @pytest.mark.asyncio
    async def test_establish_baseline(self, harness):
        """Test baseline establishment"""

        # Generate sample measurements
        async def consistent_operation():
            await asyncio.sleep(0.01)  # Consistent 10ms operation
            return [1, 2, 3]

        # Take multiple measurements
        for _ in range(25):
            await harness.measure_operation("consistent_op", consistent_operation)

        # Establish baseline
        baseline = harness.establish_baseline("consistent_op", num_samples=20)

        assert baseline.operation == "consistent_op"
        assert baseline.mean_duration_ms >= 8  # Should be around 10ms
        assert baseline.sample_count == 20
        assert baseline.std_deviation_ms >= 0
        assert len(baseline.confidence_interval) == 2

    @pytest.mark.asyncio
    async def test_regression_detection(self, harness):
        """Test regression detection with statistical analysis"""

        # Create baseline with fast operations
        async def fast_operation():
            await asyncio.sleep(0.005)  # 5ms
            return True

        # Generate baseline samples
        for _ in range(20):
            await harness.measure_operation("regression_test", fast_operation)

        harness.establish_baseline("regression_test", num_samples=15)

        # Now simulate performance regression
        async def slow_operation():
            await asyncio.sleep(0.020)  # 20ms - 4x slower
            return True

        # Generate regressed samples
        for _ in range(10):
            await harness.measure_operation("regression_test", slow_operation)

        # Check for regression
        analysis = harness.check_regression("regression_test")

        assert "regression_detected" in analysis
        assert "confidence" in analysis
        assert "percent_change" in analysis

        # Should detect significant regression
        if analysis["percent_change"] > 50:  # 4x slower = 300% increase
            assert analysis["regression_detected"] is True

    @pytest.mark.asyncio
    async def test_quality_gates_performance(self, harness, quality_gates):
        """Test performance measurement of quality gates"""
        if not quality_gates:
            pytest.skip("Quality gates not available")

        test_entry = {
            "CanonicalLatin": "Smith, John William",
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.95,
            "LanguageOfPublication": ["eng"],
            "CountryCodes": ["US"],
        }

        # Measure quality gate validation performance
        for _ in range(10):
            await harness.measure_operation(
                "quality_gates_validation", quality_gates.validate_entry, test_entry
            )

        # Check that measurements were recorded
        gate_metrics = [
            m
            for m in harness.current_session_metrics
            if m.operation == "quality_gates_validation"
        ]

        assert len(gate_metrics) == 10
        assert all(m.duration_ms > 0 for m in gate_metrics)
        assert all(m.metadata.get("success") is True for m in gate_metrics)

    @pytest.mark.asyncio
    async def test_edge_case_error_handling(self, harness):
        """Test performance measurement with operation failures"""

        async def failing_operation():
            await asyncio.sleep(0.01)
            raise ValueError("Simulated failure")

        # Measure failing operation
        with pytest.raises(ValueError):
            await harness.measure_operation("failing_op", failing_operation)

        # Check that failure was recorded
        failure_metrics = [
            m for m in harness.current_session_metrics if m.operation == "failing_op"
        ]

        assert len(failure_metrics) == 1
        assert failure_metrics[0].metadata["failed"] is True
        assert "error" in failure_metrics[0].metadata
        assert failure_metrics[0].entries_processed == 0

    @pytest.mark.timeout(15)
    def test_statistical_analyzer(self):
        """Test statistical analysis methods"""
        analyzer = StatisticalAnalyzer(sensitivity=0.20)  # 20% threshold

        # Create mock baseline
        baseline = RegressionBaseline(
            operation="test",
            mean_duration_ms=100.0,
            std_deviation_ms=10.0,
            percentile_95_ms=115.0,
            sample_count=50,
            last_updated=datetime.now(),
            confidence_interval=(95.0, 105.0),
        )

        # Test with no regression (similar performance)
        stable_samples = [98, 102, 99, 101, 100, 103, 97]
        stable_analysis = analyzer.analyze_regression(baseline, stable_samples)

        assert stable_analysis["regression_detected"] is False
        assert abs(stable_analysis["percent_change"]) < 5  # Should be small change

        # Test with clear regression (much slower)
        regressed_samples = [150, 155, 148, 152, 160, 145, 158]  # ~50% slower
        regressed_analysis = analyzer.analyze_regression(baseline, regressed_samples)

        assert regressed_analysis["regression_detected"] is True
        assert (
            regressed_analysis["percent_change"] > 20
        )  # Should be significant increase
        assert regressed_analysis["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_comprehensive_regression_report(self, harness):
        """Test comprehensive regression reporting"""
        # Set up multiple operations with different performance characteristics
        operations = [
            ("fast_op", 0.005),  # 5ms
            ("medium_op", 0.015),  # 15ms
            ("slow_op", 0.030),  # 30ms
        ]

        # Generate baseline data
        for op_name, delay in operations:

            async def timed_operation(d=delay):
                await asyncio.sleep(d)
                return True

            # Generate samples for baseline
            for _ in range(15):
                await harness.measure_operation(op_name, timed_operation)

            # Establish baseline
            harness.establish_baseline(op_name, num_samples=12)

        # Introduce regression in one operation
        async def regressed_operation():
            await asyncio.sleep(0.025)  # Slower than 5ms baseline
            return True

        for _ in range(8):
            await harness.measure_operation("fast_op", regressed_operation)

        # Generate regression report
        report = harness.generate_regression_report()

        assert "timestamp" in report
        assert "session_metrics_count" in report
        assert "regression_analysis" in report
        assert "summary" in report

        assert len(report["operations_analyzed"]) == 3
        assert report["summary"]["operations_tested"] > 0

        # Should detect regression in fast_op
        if "fast_op" in report["regression_analysis"]:
            fast_op_analysis = report["regression_analysis"]["fast_op"]
            if fast_op_analysis.get("sample_count", 0) >= 5:
                assert "regression_detected" in fast_op_analysis


# Integration tests with actual GMNAP components
class TestGMNAPPerformanceIntegration:
    """Integration tests for GMNAP performance regression detection"""

    @pytest.fixture
    def harness(self):
        """Create integration test harness"""
        return PerformanceRegressionHarness(Path("cache/integration_baselines.json"))

    @pytest.mark.asyncio
    async def test_region_manager_performance(self, harness):
        """Test region manager loading performance"""
        try:
            from pathlib import Path as PathlibPath

            from src.regions.manager import RegionManager

            # Measure region manager initialization
            await harness.measure_operation(
                "region_manager_init", lambda: RegionManager(PathlibPath("./config"))
            )

            manager = RegionManager(PathlibPath("./config"))

            # Measure individual region loading
            test_regions = ["A1", "E1", "C1", "D1", "G1"]
            for region_code in test_regions:
                await harness.measure_operation(
                    f"region_load_{region_code}", manager.get_region, region_code
                )

            # Verify measurements were taken
            init_metrics = [
                m
                for m in harness.current_session_metrics
                if m.operation == "region_manager_init"
            ]
            assert len(init_metrics) > 0

        except ImportError:
            pytest.skip("Region manager not available for integration test")

    @pytest.mark.asyncio
    async def test_pipeline_stage_performance(self, harness):
        """Test individual pipeline stage performance"""
        try:
            from src.core.pipeline_v7 import V7Pipeline

            pipeline = V7Pipeline()

            # Test entry for pipeline stages
            test_entry = {
                "CanonicalLatin": "Smith, John",
                "GlobalID": "TESTENTRYABCDEFGHIJKLMN",
                "DetectedRegion": "A1",
            }

            # Measure key pipeline stages if they exist
            pipeline_stages = [
                ("stage_1", "region_detection"),
                ("stage_3", "schema_validation"),
                ("stage_7", "quality_gates"),
            ]

            for stage_name, stage_desc in pipeline_stages:
                if hasattr(pipeline, stage_name):
                    stage_method = getattr(pipeline, stage_name)
                    await harness.measure_operation(
                        f"pipeline_{stage_desc}", stage_method, test_entry
                    )

        except ImportError:
            pytest.skip("Pipeline not available for integration test")


def main():
    """Run performance regression tests"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    main()
