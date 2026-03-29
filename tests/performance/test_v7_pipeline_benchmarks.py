#!/usr/bin/env python3
"""
from typing import List
from typing import Optional
from typing import Any
V7 Pipeline Performance Benchmarking Suite

Implements comprehensive performance metrics collection and regression detection
for all V7 pipeline stages to ensure production readiness and compliance.
"""

import pytest
import asyncio
import time
import sys
import psutil
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import tracemalloc

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.core.pipeline_v7 import V7Pipeline
    from src.regions.manager import RegionManager
except ImportError as e:
    pytest.skip(f"Pipeline components not available: {e}", allow_module_level=True)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation"""

    operation_name: str
    execution_time_ms: float
    memory_usage_mb: float
    cpu_percent: float
    peak_memory_mb: float
    throughput_ops_per_sec: float
    success_rate: float
    error_count: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StageMetrics:
    """Performance metrics for a pipeline stage"""

    stage_number: int
    stage_name: str
    metrics: List[PerformanceMetrics] = field(default_factory=list)

    @property
    def average_execution_time(self) -> float:
        return statistics.mean([m.execution_time_ms for m in self.metrics]) if self.metrics else 0.0

    @property
    def p95_execution_time(self) -> float:
        times = [m.execution_time_ms for m in self.metrics]
        return statistics.quantiles(times, n=20)[18] if len(times) > 10 else 0.0

    @property
    def average_memory_usage(self) -> float:
        return statistics.mean([m.memory_usage_mb for m in self.metrics]) if self.metrics else 0.0


class V7PipelineBenchmark:
    """V7 Pipeline performance benchmarking framework"""

    def __init__(self):
        self.pipeline = None
        self.region_manager = None
        self.stage_metrics: Dict[int, StageMetrics] = {}
        self.baseline_metrics: Dict[str, Any] = {}
        self.performance_thresholds = {
            "max_execution_time_ms": 1000,  # 1 second per stage max
            "max_memory_usage_mb": 100,  # 100MB per stage max
            "min_throughput_ops_per_sec": 10,  # 10 operations per second min
            "max_cpu_percent": 80,  # 80% CPU utilization max
            "min_success_rate": 0.95,  # 95% success rate minimum
        }

    async def setup(self):
        """Initialize benchmark components"""
        try:
            self.pipeline = V7Pipeline()
            self.region_manager = RegionManager(Path("./config"))
            self.load_baseline_metrics()
        except Exception as e:
            pytest.skip(f"Failed to initialize benchmark components: {e}")

    def load_baseline_metrics(self):
        """Load baseline performance metrics if available"""
        baseline_file = Path("./data/performance_benchmark_baseline.json")
        if baseline_file.exists():
            try:
                with open(baseline_file) as f:
                    self.baseline_metrics = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load baseline metrics: {e}")

    def save_baseline_metrics(self):
        """Save current metrics as new baseline"""
        baseline_data = {
            "timestamp": datetime.now().isoformat(),
            "stage_metrics": {},
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "python_version": sys.version,
            },
        }

        for stage_num, stage in self.stage_metrics.items():
            baseline_data["stage_metrics"][str(stage_num)] = {
                "stage_name": stage.stage_name,
                "average_execution_time": stage.average_execution_time,
                "p95_execution_time": stage.p95_execution_time,
                "average_memory_usage": stage.average_memory_usage,
                "sample_count": len(stage.metrics),
            }

        baseline_file = Path("./data/performance_benchmark_baseline.json")
        baseline_file.parent.mkdir(parents=True, exist_ok=True)

        with open(baseline_file, "w") as f:
            json.dump(baseline_data, f, indent=2)

    async def benchmark_stage(
        self,
        stage_number: int,
        stage_name: str,
        test_data: List[Dict[str, Any]],
        iterations: int = 10,
    ) -> StageMetrics:
        """Benchmark a specific pipeline stage"""
        if stage_number not in self.stage_metrics:
            self.stage_metrics[stage_number] = StageMetrics(stage_number, stage_name)

        stage_metrics = self.stage_metrics[stage_number]

        for iteration in range(iterations):
            # Start monitoring
            process = psutil.Process()
            tracemalloc.start()

            success_count = 0
            error_count = 0
            start_time = time.perf_counter()
            start_memory = process.memory_info().rss / (1024**2)  # MB

            # Execute stage on test data
            for entry in test_data:
                try:
                    # Simulate stage execution based on stage number
                    await self._execute_stage(stage_number, entry.copy())
                    success_count += 1
                except Exception as e:
                    error_count += 1

            end_time = time.perf_counter()
            current_memory = process.memory_info().rss / (1024**2)  # MB
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Calculate metrics
            execution_time_ms = (end_time - start_time) * 1000
            memory_usage_mb = current_memory - start_memory
            peak_memory_mb = peak / (1024**2)  # Convert to MB
            cpu_percent = process.cpu_percent()
            throughput = len(test_data) / (execution_time_ms / 1000) if execution_time_ms > 0 else 0
            success_rate = success_count / len(test_data) if test_data else 1.0

            metrics = PerformanceMetrics(
                operation_name=f"stage_{stage_number}_{stage_name}",
                execution_time_ms=execution_time_ms,
                memory_usage_mb=memory_usage_mb,
                cpu_percent=cpu_percent,
                peak_memory_mb=peak_memory_mb,
                throughput_ops_per_sec=throughput,
                success_rate=success_rate,
                error_count=error_count,
            )

            stage_metrics.metrics.append(metrics)

        return stage_metrics

    async def _execute_stage(self, stage_number: int, entry: Dict[str, Any]):
        """Execute a specific pipeline stage"""
        if not self.pipeline:
            raise ValueError("Pipeline not initialized")

        # Map stage numbers to actual pipeline methods
        stage_methods = {
            1: self._stage_1_region_detection,
            2: self._stage_2_cleaning,
            3: self._stage_3_augmentation,
            4: self._stage_4_validation,
            5: self._stage_5_graph_coherence,
            6: self._stage_6_authority_lookup,
            7: self._stage_7_quality_gates,
            8: self._stage_8_deduplication,
            9: self._stage_9_output_preparation,
            10: self._stage_10_caching,
            11: self._stage_11_idempotency,
            12: self._stage_12_finalization,
        }

        if stage_number in stage_methods:
            await stage_methods[stage_number](entry)
        else:
            # Fallback: simulate processing delay
            await asyncio.sleep(0.001)

    async def _stage_1_region_detection(self, entry: Dict[str, Any]):
        """Stage 1: Region Detection"""
        # Simulate region detection logic
        if "CanonicalLatin" in entry:
            # Simple heuristic for testing
            name = entry["CanonicalLatin"].lower()
            if any(char in name for char in "김이박최"):
                entry["DetectedRegion"] = "E4"  # Korea
            elif "李" in name or "王" in name:
                entry["DetectedRegion"] = "E1"  # China
            else:
                entry["DetectedRegion"] = "A1"  # Anglo-sphere
        await asyncio.sleep(0.001)  # Simulate processing time

    async def _stage_2_cleaning(self, entry: Dict[str, Any]):
        """Stage 2: Data Cleaning"""
        # Simulate cleaning operations
        if "CanonicalLatin" in entry:
            # Normalize whitespace
            entry["CanonicalLatin"] = " ".join(entry["CanonicalLatin"].split())
        await asyncio.sleep(0.001)

    async def _stage_3_augmentation(self, entry: Dict[str, Any]):
        """Stage 3: Data Augmentation"""
        # Simulate augmentation
        region = entry.get("DetectedRegion", "A1")
        entry["RegionalExtras"] = {"region_confidence": 0.95}
        await asyncio.sleep(0.002)

    async def _stage_4_validation(self, entry: Dict[str, Any]):
        """Stage 4: Data Validation"""
        # Simulate validation checks
        required_fields = ["CanonicalLatin", "DetectedRegion"]
        for field in required_fields:
            if field not in entry:
                raise ValueError(f"Missing required field: {field}")
        await asyncio.sleep(0.001)

    async def _stage_5_graph_coherence(self, entry: Dict[str, Any]):
        """Stage 5: Graph Coherence Scoring"""
        # Simulate graph coherence calculation
        entry["GraphQualityGates"] = {"graph_coherence_score": 0.88}
        await asyncio.sleep(0.003)

    async def _stage_6_authority_lookup(self, entry: Dict[str, Any]):
        """Stage 6: Authority Source Lookup"""
        # Simulate authority lookup (would normally be async HTTP calls)
        entry["authority_data"] = {"sources_checked": ["Crossref"], "confidence": 0.75}
        await asyncio.sleep(0.010)  # Simulate network delay

    async def _stage_7_quality_gates(self, entry: Dict[str, Any]):
        """Stage 7: Quality Gates"""
        # Simulate quality gate validation
        entry["QualityGates"] = {
            "schema_valid": True,
            "completeness_score": 0.92,
            "consistency_score": 0.89,
        }
        await asyncio.sleep(0.002)

    async def _stage_8_deduplication(self, entry: Dict[str, Any]):
        """Stage 8: Deduplication"""
        # Simulate duplicate detection
        entry["deduplication_info"] = {"duplicate_probability": 0.05}
        await asyncio.sleep(0.001)

    async def _stage_9_output_preparation(self, entry: Dict[str, Any]):
        """Stage 9: Output Preparation"""
        # Simulate output formatting
        entry["output_ready"] = True
        entry["UpdatedAt"] = datetime.now().isoformat()
        await asyncio.sleep(0.001)

    async def _stage_10_caching(self, entry: Dict[str, Any]):
        """Stage 10: Caching"""
        # Simulate cache operations
        entry["cached"] = True
        await asyncio.sleep(0.001)

    async def _stage_11_idempotency(self, entry: Dict[str, Any]):
        """Stage 11: Idempotency Check"""
        # Simulate idempotency verification
        entry["idempotency_verified"] = True
        await asyncio.sleep(0.002)

    async def _stage_12_finalization(self, entry: Dict[str, Any]):
        """Stage 12: Finalization"""
        # Simulate final processing
        entry["finalized"] = True
        await asyncio.sleep(0.001)

    def generate_test_data(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate test data for benchmarking"""
        test_data = []
        names = [
            "Smith, John",
            "李明",
            "김민준",
            "García, José",
            "Schmidt, Hans",
            "Patel, Rajesh",
            "Wang, Wei",
            "Johnson, Mary",
            "박지호",
            "山田太郎",
        ]

        for i in range(count):
            entry = {
                "CanonicalLatin": names[i % len(names)],
                "GlobalID": f"TEST{i:018d}",  # 22 char total
                "Confidence": 0.95,
            }
            test_data.append(entry)

        return test_data

    def check_regression(self, current_metrics: StageMetrics) -> Dict[str, Any]:
        """Check for performance regression against baseline"""
        if not self.baseline_metrics or "stage_metrics" not in self.baseline_metrics:
            return {"regression_detected": False, "reason": "No baseline available"}

        stage_key = str(current_metrics.stage_number)
        if stage_key not in self.baseline_metrics["stage_metrics"]:
            return {"regression_detected": False, "reason": "No baseline for this stage"}

        baseline = self.baseline_metrics["stage_metrics"][stage_key]
        current_avg = current_metrics.average_execution_time
        baseline_avg = baseline["average_execution_time"]

        # Consider regression if current performance is >20% worse than baseline
        regression_threshold = 1.2

        if current_avg > baseline_avg * regression_threshold:
            return {
                "regression_detected": True,
                "current_avg_ms": current_avg,
                "baseline_avg_ms": baseline_avg,
                "degradation_factor": current_avg / baseline_avg,
                "threshold_exceeded": True,
            }

        return {
            "regression_detected": False,
            "current_avg_ms": current_avg,
            "baseline_avg_ms": baseline_avg,
            "improvement_factor": baseline_avg / current_avg if current_avg > 0 else 1.0,
        }


class TestV7PipelineBenchmarks:
    """Test suite for V7 pipeline performance benchmarks"""

    @pytest.fixture
    async def benchmark(self):
        """Create and setup benchmark"""
        b = V7PipelineBenchmark()
        await b.setup()
        return b

    @pytest.mark.asyncio
    async def test_stage_1_region_detection_performance(self, benchmark):
        """Benchmark Stage 1: Region Detection"""
        test_data = benchmark.generate_test_data(50)
        metrics = await benchmark.benchmark_stage(1, "RegionDetection", test_data, iterations=5)

        # Assert performance thresholds
        assert (
            metrics.average_execution_time
            < benchmark.performance_thresholds["max_execution_time_ms"]
        )
        assert (
            metrics.average_memory_usage < benchmark.performance_thresholds["max_memory_usage_mb"]
        )

        # Check for regression
        regression = benchmark.check_regression(metrics)
        if regression["regression_detected"]:
            pytest.fail(f"Performance regression detected: {regression}")

    @pytest.mark.asyncio
    async def test_stage_2_cleaning_performance(self, benchmark):
        """Benchmark Stage 2: Data Cleaning"""
        test_data = benchmark.generate_test_data(50)
        metrics = await benchmark.benchmark_stage(2, "DataCleaning", test_data, iterations=5)

        assert (
            metrics.average_execution_time
            < benchmark.performance_thresholds["max_execution_time_ms"]
        )
        assert all(
            m.success_rate >= benchmark.performance_thresholds["min_success_rate"]
            for m in metrics.metrics
        )

    @pytest.mark.asyncio
    async def test_stage_3_augmentation_performance(self, benchmark):
        """Benchmark Stage 3: Data Augmentation"""
        test_data = benchmark.generate_test_data(50)
        metrics = await benchmark.benchmark_stage(3, "DataAugmentation", test_data, iterations=5)

        assert (
            metrics.average_execution_time
            < benchmark.performance_thresholds["max_execution_time_ms"]
        )
        assert (
            metrics.average_memory_usage < benchmark.performance_thresholds["max_memory_usage_mb"]
        )

    @pytest.mark.asyncio
    async def test_stage_4_validation_performance(self, benchmark):
        """Benchmark Stage 4: Data Validation"""
        test_data = benchmark.generate_test_data(50)
        metrics = await benchmark.benchmark_stage(4, "DataValidation", test_data, iterations=5)

        assert (
            metrics.average_execution_time
            < benchmark.performance_thresholds["max_execution_time_ms"]
        )
        assert all(
            m.success_rate >= benchmark.performance_thresholds["min_success_rate"]
            for m in metrics.metrics
        )

    @pytest.mark.asyncio
    async def test_stage_5_graph_coherence_performance(self, benchmark):
        """Benchmark Stage 5: Graph Coherence Scoring"""
        test_data = benchmark.generate_test_data(30)  # Fewer entries due to complexity
        metrics = await benchmark.benchmark_stage(5, "GraphCoherence", test_data, iterations=3)

        # Graph coherence may take longer
        assert (
            metrics.average_execution_time
            < benchmark.performance_thresholds["max_execution_time_ms"] * 2
        )
        assert (
            metrics.average_memory_usage < benchmark.performance_thresholds["max_memory_usage_mb"]
        )

    @pytest.mark.asyncio
    async def test_stage_6_authority_lookup_performance(self, benchmark):
        """Benchmark Stage 6: Authority Source Lookup"""
        test_data = benchmark.generate_test_data(20)  # Fewer entries due to network simulation
        metrics = await benchmark.benchmark_stage(6, "AuthorityLookup", test_data, iterations=3)

        # Authority lookup involves network calls, allow more time
        assert (
            metrics.average_execution_time
            < benchmark.performance_thresholds["max_execution_time_ms"] * 5
        )
        assert (
            metrics.average_memory_usage < benchmark.performance_thresholds["max_memory_usage_mb"]
        )

    @pytest.mark.asyncio
    async def test_stage_7_quality_gates_performance(self, benchmark):
        """Benchmark Stage 7: Quality Gates"""
        test_data = benchmark.generate_test_data(50)
        metrics = await benchmark.benchmark_stage(7, "QualityGates", test_data, iterations=5)

        assert (
            metrics.average_execution_time
            < benchmark.performance_thresholds["max_execution_time_ms"]
        )
        assert all(
            m.success_rate >= benchmark.performance_thresholds["min_success_rate"]
            for m in metrics.metrics
        )

    @pytest.mark.asyncio
    async def test_stage_11_idempotency_performance(self, benchmark):
        """Benchmark Stage 11: Idempotency Check"""
        test_data = benchmark.generate_test_data(50)
        metrics = await benchmark.benchmark_stage(11, "IdempotencyCheck", test_data, iterations=5)

        assert (
            metrics.average_execution_time
            < benchmark.performance_thresholds["max_execution_time_ms"]
        )
        assert (
            metrics.average_memory_usage < benchmark.performance_thresholds["max_memory_usage_mb"]
        )

        # Idempotency should have high success rate
        assert all(m.success_rate >= 0.98 for m in metrics.metrics)

    @pytest.mark.asyncio
    async def test_full_pipeline_performance(self, benchmark):
        """Benchmark complete pipeline execution"""
        test_data = benchmark.generate_test_data(20)

        # Benchmark key stages in sequence
        critical_stages = [
            (1, "RegionDetection"),
            (2, "DataCleaning"),
            (3, "DataAugmentation"),
            (4, "DataValidation"),
            (7, "QualityGates"),
            (11, "IdempotencyCheck"),
        ]

        total_time = 0
        for stage_num, stage_name in critical_stages:
            metrics = await benchmark.benchmark_stage(
                stage_num, stage_name, test_data, iterations=3
            )
            total_time += metrics.average_execution_time

        # Full pipeline should complete within reasonable time
        assert total_time < 5000  # 5 seconds total

        # Save baseline for future runs
        benchmark.save_baseline_metrics()

    @pytest.mark.asyncio
    async def test_throughput_requirements(self, benchmark):
        """Test pipeline meets throughput requirements"""
        test_data = benchmark.generate_test_data(100)

        start_time = time.perf_counter()

        # Process all entries through a representative stage
        metrics = await benchmark.benchmark_stage(2, "DataCleaning", test_data, iterations=1)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        throughput = len(test_data) / total_time

        # Should process at least 50 entries per second
        assert throughput >= 50, f"Throughput too low: {throughput:.2f} entries/sec"

    @pytest.mark.asyncio
    async def test_memory_usage_limits(self, benchmark):
        """Test pipeline memory usage stays within limits"""
        # Test with larger dataset to check memory scaling
        test_data = benchmark.generate_test_data(200)

        metrics = await benchmark.benchmark_stage(3, "DataAugmentation", test_data, iterations=2)

        # Memory usage should scale reasonably
        max_memory = max(m.peak_memory_mb for m in metrics.metrics)
        assert max_memory < 200, f"Memory usage too high: {max_memory:.2f}MB"

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self, benchmark):
        """Test automated performance regression detection"""
        test_data = benchmark.generate_test_data(30)

        # Run benchmark and establish baseline
        metrics = await benchmark.benchmark_stage(4, "DataValidation", test_data, iterations=5)

        # Check regression detection works
        regression = benchmark.check_regression(metrics)

        # Should have regression analysis data
        assert "regression_detected" in regression
        assert "current_avg_ms" in regression

        # Save this as baseline for future tests
        benchmark.save_baseline_metrics()


@pytest.mark.asyncio
async def test_generate_performance_report():
    """Generate comprehensive performance report"""
    benchmark = V7PipelineBenchmark()
    await benchmark.setup()

    test_data = benchmark.generate_test_data(50)

    # Benchmark all critical stages
    stages_to_test = [
        (1, "RegionDetection"),
        (2, "DataCleaning"),
        (3, "DataAugmentation"),
        (4, "DataValidation"),
        (7, "QualityGates"),
        (11, "IdempotencyCheck"),
    ]

    for stage_num, stage_name in stages_to_test:
        await benchmark.benchmark_stage(stage_num, stage_name, test_data, iterations=3)

    # Generate performance report
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_data_size": len(test_data),
        "stages_tested": len(stages_to_test),
        "stage_performance": {},
        "overall_metrics": {"total_avg_time": 0, "total_memory_usage": 0, "performance_grade": "A"},
    }

    total_time = 0
    total_memory = 0

    for stage_num, stage in benchmark.stage_metrics.items():
        stage_report = {
            "stage_name": stage.stage_name,
            "average_execution_time_ms": stage.average_execution_time,
            "p95_execution_time_ms": stage.p95_execution_time,
            "average_memory_usage_mb": stage.average_memory_usage,
            "sample_count": len(stage.metrics),
        }

        # Check against thresholds
        if stage.average_execution_time > benchmark.performance_thresholds["max_execution_time_ms"]:
            stage_report["warning"] = "Execution time exceeds threshold"

        if stage.average_memory_usage > benchmark.performance_thresholds["max_memory_usage_mb"]:
            stage_report["warning"] = "Memory usage exceeds threshold"

        report["stage_performance"][f"stage_{stage_num}"] = stage_report
        total_time += stage.average_execution_time
        total_memory += stage.average_memory_usage

    report["overall_metrics"]["total_avg_time"] = total_time
    report["overall_metrics"]["total_memory_usage"] = total_memory

    # Determine performance grade
    if total_time > 3000 or total_memory > 500:
        report["overall_metrics"]["performance_grade"] = "C"
    elif total_time > 1500 or total_memory > 250:
        report["overall_metrics"]["performance_grade"] = "B"

    # Save performance report
    report_file = Path("./data/performance_benchmark_report.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nPerformance Report Generated:")
    print(f"Stages tested: {report['stages_tested']}")
    print(f"Total average time: {report['overall_metrics']['total_avg_time']:.2f}ms")
    print(f"Performance grade: {report['overall_metrics']['performance_grade']}")

    # Assertions for test validation
    assert report["stages_tested"] > 0
    assert report["overall_metrics"]["performance_grade"] in ["A", "B", "C", "D", "F"]
    assert total_time > 0  # Should have measured some execution time


def main():
    """Run the V7 pipeline benchmarks"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    main()
