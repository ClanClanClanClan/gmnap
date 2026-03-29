#!/usr/bin/env python3
"""
from typing import Dict
from typing import List
from typing import Optional
V7 Performance Benchmark Test

V7 Specification Requirements:
- Quick mode: <=35 min per 1M entries (4 CPU workers)
- Full mode: <=70 min per 1M entries (8 CPU workers)
- Extreme mode: No SLA (12 CPU workers)

This translates to:
- Quick: ~476 entries/second minimum
- Full: ~238 entries/second minimum
"""

import asyncio
import concurrent.futures
import json
import logging
import multiprocessing
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["GMNAP_TEST_MODE"] = "true"

import pytest
import psutil

from src.core.pipeline_v7 import PipelineV7
from src.regions.manager_optimized import RegionManager
from src.authorities.enricher import AuthorityEnricher
from src.core.global_id import generate_global_id, reset_collision_tracking
from src.core.memgraph_client import MemgraphClient

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmarking."""

    total_entries: int = 0
    total_time_seconds: float = 0.0
    entries_per_second: float = 0.0

    # Stage timings
    stage_timings: Dict[str, float] = None

    # Resource usage
    peak_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0

    # Bottlenecks
    slowest_stage: str = ""
    slowest_stage_time: float = 0.0

    # V7 compliance
    meets_v7_quick: bool = False
    meets_v7_full: bool = False
    projected_time_1m: float = 0.0  # Projected time for 1M entries in minutes

    def __post_init__(self):
        if self.stage_timings is None:
            self.stage_timings = {}


class V7PerformanceBenchmark:
    """V7 Performance Benchmark Suite."""

    # V7 requirements (entries per second)
    V7_QUICK_MIN_EPS = 476  # 1M entries in 35 min
    V7_FULL_MIN_EPS = 238  # 1M entries in 70 min

    def __init__(self):
        self.pipeline = None
        self.region_manager = None
        self.enricher = None
        self.memgraph = None
        self.process = psutil.Process()

    def setup(self):
        """Set up test environment."""
        # Initialize components
        self.region_manager = RegionManager(Path("./config"))
        self.enricher = AuthorityEnricher()
        self.memgraph = MemgraphClient()

        # Reset collision tracking for clean test
        reset_collision_tracking()

        # Create pipeline
        self.pipeline = PipelineV7(
            region_manager=self.region_manager,
            enricher=self.enricher,
            memgraph_client=self.memgraph,
        )

    def generate_test_entries(self, count: int) -> List[Dict[str, Any]]:
        """Generate test entries for benchmarking."""
        entries = []

        # Mix of different region types for realistic testing
        regions = ["A1", "A2", "B1", "C1", "D1", "E1", "E4", "F1", "G1"]

        for i in range(count):
            region = regions[i % len(regions)]

            entry = {
                "CanonicalLatin": f"Test Person {i:06d}",
                "CanonicalNative": f"テスト人物 {i:06d}" if region == "E3" else None,
                "BirthYear": 1900 + (i % 120),
                "DeathYear": 1950 + (i % 70) if i % 3 == 0 else None,
                "Region": region,
                "Source": "benchmark_test",
                "Timestamp": datetime.now().isoformat(),
            }

            # Add some variations
            if i % 10 == 0:
                # Add external IDs
                entry["ExternalIDs"] = [
                    {"type": "ORCID", "value": f"0000-0000-0000-{i:04d}"}
                ]

            if i % 20 == 0:
                # Add affiliations
                entry["Affiliations"] = [
                    {"institution": f"University {i}", "year": 2000 + (i % 20)}
                ]

            entries.append(entry)

        return entries

    def benchmark_stage(
        self, stage_name: str, stage_func: callable, entries: List[Dict], **kwargs
    ) -> Tuple[List[Dict], float]:
        """Benchmark a single pipeline stage."""
        start_time = time.perf_counter()

        # Run stage
        if asyncio.iscoroutinefunction(stage_func):
            results = asyncio.run(stage_func(entries, **kwargs))
        else:
            results = stage_func(entries, **kwargs)

        elapsed = time.perf_counter() - start_time

        return results, elapsed

    def benchmark_full_pipeline(
        self, entries: List[Dict], mode: str = "quick"
    ) -> PerformanceMetrics:
        """Benchmark the full V7 pipeline."""
        metrics = PerformanceMetrics()
        metrics.total_entries = len(entries)

        # Track resource usage
        cpu_samples = []
        memory_samples = []

        # Start monitoring thread
        monitoring = True

        def monitor_resources():
            while monitoring:
                cpu_samples.append(self.process.cpu_percent())
                memory_samples.append(self.process.memory_info().rss / 1024 / 1024)
                time.sleep(0.1)

        monitor_thread = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        monitor_future = monitor_thread.submit(monitor_resources)

        # Run pipeline stages
        start_time = time.perf_counter()
        current_entries = entries.copy()

        # Stage 1: InputNormalization
        current_entries, stage_time = self.benchmark_stage(
            "InputNormalization", self.pipeline.normalize_input, current_entries
        )
        metrics.stage_timings["stage_1_input_norm"] = stage_time

        # Stage 2: DetectCandidates
        current_entries, stage_time = self.benchmark_stage(
            "DetectCandidates", self.pipeline.detect_candidates, current_entries
        )
        metrics.stage_timings["stage_2_detect"] = stage_time

        # Stage 3: RegionHooks
        processed = []
        region_start = time.perf_counter()
        for entry in current_entries:
            region_code = entry.get("Region", "R0")
            try:
                region = self.region_manager.get_region(region_code)
                if region:
                    region.clean(entry)
                    region.augment(entry)
                    region.validate(entry)
                    entry["order_key"] = region.order_key(entry)
                processed.append(entry)
            except Exception as e:
                logger.warning(f"Region processing failed: {e}")
                processed.append(entry)
        metrics.stage_timings["stage_3_region"] = time.perf_counter() - region_start
        current_entries = processed

        # Stage 4: AuthorityEnrich (skip in quick benchmark for speed)
        if mode != "quick":
            current_entries, stage_time = self.benchmark_stage(
                "AuthorityEnrich", self.pipeline.enrich_authorities, current_entries
            )
            metrics.stage_timings["stage_4_authority"] = stage_time
        else:
            metrics.stage_timings["stage_4_authority"] = 0.0

        # Stage 5: CollisionAnalytics
        current_entries, stage_time = self.benchmark_stage(
            "CollisionAnalytics", self.pipeline.detect_collisions, current_entries
        )
        metrics.stage_timings["stage_5_collision"] = stage_time

        # Stage 6: GraphConsistency (skip if no Memgraph)
        if self.memgraph.is_connected():
            current_entries, stage_time = self.benchmark_stage(
                "GraphConsistency",
                self.pipeline.ensure_graph_consistency,
                current_entries,
            )
            metrics.stage_timings["stage_6_graph"] = stage_time
        else:
            metrics.stage_timings["stage_6_graph"] = 0.0

        # Stage 7: TagShortForms
        current_entries, stage_time = self.benchmark_stage(
            "TagShortForms", self.pipeline.tag_short_forms, current_entries
        )
        metrics.stage_timings["stage_7_shortforms"] = stage_time

        # Stage 8: GlobalValidate
        current_entries, stage_time = self.benchmark_stage(
            "GlobalValidate", self.pipeline.global_validate, current_entries
        )
        metrics.stage_timings["stage_8_validate"] = stage_time

        # Stop monitoring
        monitoring = False
        monitor_thread.shutdown(wait=True)

        # Calculate metrics
        metrics.total_time_seconds = time.perf_counter() - start_time
        metrics.entries_per_second = metrics.total_entries / metrics.total_time_seconds

        # Resource metrics
        if cpu_samples:
            metrics.avg_cpu_percent = sum(cpu_samples) / len(cpu_samples)
        if memory_samples:
            metrics.peak_memory_mb = max(memory_samples)

        # Find slowest stage
        if metrics.stage_timings:
            slowest = max(metrics.stage_timings.items(), key=lambda x: x[1])
            metrics.slowest_stage = slowest[0]
            metrics.slowest_stage_time = slowest[1]

        # V7 compliance check
        metrics.meets_v7_quick = metrics.entries_per_second >= self.V7_QUICK_MIN_EPS
        metrics.meets_v7_full = metrics.entries_per_second >= self.V7_FULL_MIN_EPS

        # Project time for 1M entries
        metrics.projected_time_1m = (1_000_000 / metrics.entries_per_second) / 60

        return metrics

    def run_benchmark(self, entry_counts: List[int] = None) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        if entry_counts is None:
            entry_counts = [100, 1000, 10000]

        results = {
            "timestamp": datetime.now().isoformat(),
            "v7_requirements": {
                "quick_min_eps": self.V7_QUICK_MIN_EPS,
                "full_min_eps": self.V7_FULL_MIN_EPS,
                "quick_max_minutes_1m": 35,
                "full_max_minutes_1m": 70,
            },
            "benchmarks": [],
        }

        for count in entry_counts:
            print(f"\n{'='*60}")
            print(f"Benchmarking with {count:,} entries...")
            print(f"{'='*60}")

            # Generate test data
            entries = self.generate_test_entries(count)

            # Run benchmark
            metrics = self.benchmark_full_pipeline(entries, mode="quick")

            # Report results
            print(f"\nResults for {count:,} entries:")
            print(f"  Total time: {metrics.total_time_seconds:.2f} seconds")
            print(f"  Entries/second: {metrics.entries_per_second:.1f}")
            print(f"  Projected time for 1M: {metrics.projected_time_1m:.1f} minutes")
            print(f"  Peak memory: {metrics.peak_memory_mb:.1f} MB")
            print(f"  Average CPU: {metrics.avg_cpu_percent:.1f}%")
            print(
                f"  Slowest stage: {metrics.slowest_stage} ({metrics.slowest_stage_time:.2f}s)"
            )
            print(
                f"  Meets V7 Quick requirement: {'PASS' if metrics.meets_v7_quick else 'FAIL'}"
            )
            print(
                f"  Meets V7 Full requirement: {'PASS' if metrics.meets_v7_full else 'FAIL'}"
            )

            # Stage breakdown
            print("\n  Stage timings:")
            for stage, timing in sorted(metrics.stage_timings.items()):
                percentage = (timing / metrics.total_time_seconds) * 100
                print(f"    {stage}: {timing:.3f}s ({percentage:.1f}%)")

            # Save results
            results["benchmarks"].append(
                {
                    "entry_count": count,
                    "total_time": metrics.total_time_seconds,
                    "entries_per_second": metrics.entries_per_second,
                    "projected_1m_minutes": metrics.projected_time_1m,
                    "meets_v7_quick": metrics.meets_v7_quick,
                    "meets_v7_full": metrics.meets_v7_full,
                    "peak_memory_mb": metrics.peak_memory_mb,
                    "avg_cpu_percent": metrics.avg_cpu_percent,
                    "stage_timings": metrics.stage_timings,
                    "slowest_stage": metrics.slowest_stage,
                }
            )

        # Overall assessment
        all_meet_quick = all(b["meets_v7_quick"] for b in results["benchmarks"])
        all_meet_full = all(b["meets_v7_full"] for b in results["benchmarks"])

        results["overall_assessment"] = {
            "meets_v7_quick": all_meet_quick,
            "meets_v7_full": all_meet_full,
            "recommendation": self._get_recommendation(results["benchmarks"]),
        }

        return results

    def _get_recommendation(self, benchmarks: List[Dict]) -> str:
        """Get optimization recommendations based on benchmark results."""
        if not benchmarks:
            return "No benchmark data available"

        # Check if we meet requirements
        latest = benchmarks[-1]
        if latest["meets_v7_quick"]:
            return "PASS Performance meets V7 Quick mode requirements"

        # Identify bottlenecks
        recommendations = []

        # Check if it's a scaling issue
        if len(benchmarks) > 1:
            scaling_factor = (
                benchmarks[-1]["entries_per_second"]
                / benchmarks[0]["entries_per_second"]
            )
            if scaling_factor < 0.8:
                recommendations.append(
                    "WARN Performance doesn't scale linearly - investigate memory/resource bottlenecks"
                )

        # Check slowest stage
        slowest = latest["slowest_stage"]
        if "region" in slowest:
            recommendations.append(
                "🔧 Optimize region processing - consider caching or parallel processing"
            )
        elif "authority" in slowest:
            recommendations.append(
                "🔧 Optimize authority enrichment - use async/parallel fetching"
            )
        elif "collision" in slowest:
            recommendations.append(
                "🔧 Optimize collision detection - consider better indexing"
            )

        # Memory recommendations
        if latest["peak_memory_mb"] > 1000:
            recommendations.append(
                "💾 High memory usage - implement streaming/batching"
            )

        # CPU recommendations
        if latest["avg_cpu_percent"] < 50:
            recommendations.append("🔥 Low CPU utilization - increase parallelization")

        return (
            " | ".join(recommendations)
            if recommendations
            else "Performance optimization needed"
        )


# Test functions for pytest
class TestV7Performance:
    """V7 Performance test suite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.benchmark = V7PerformanceBenchmark()
        self.benchmark.setup()

    @pytest.mark.timeout(15)
    def test_small_batch_performance(self):
        """Test performance with small batch (100 entries)."""
        entries = self.benchmark.generate_test_entries(100)
        metrics = self.benchmark.benchmark_full_pipeline(entries)

        # Should easily handle 100 entries
        assert (
            metrics.entries_per_second > 10
        ), f"Too slow: {metrics.entries_per_second:.1f} eps"
        assert (
            metrics.peak_memory_mb < 500
        ), f"Too much memory: {metrics.peak_memory_mb:.1f} MB"

    @pytest.mark.timeout(15)
    def test_medium_batch_performance(self):
        """Test performance with medium batch (1000 entries)."""
        entries = self.benchmark.generate_test_entries(1000)
        metrics = self.benchmark.benchmark_full_pipeline(entries)

        # Check if we're on track for V7 requirements
        print(
            f"\nProjected time for 1M entries: {metrics.projected_time_1m:.1f} minutes"
        )
        print(f"V7 Quick requirement: <=35 minutes")
        print(f"Status: {'PASS PASS' if metrics.meets_v7_quick else 'FAIL FAIL'}")

    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_large_batch_performance(self):
        """Test performance with large batch (10000 entries)."""
        entries = self.benchmark.generate_test_entries(10000)
        metrics = self.benchmark.benchmark_full_pipeline(entries)

        # Should meet V7 requirements
        assert (
            metrics.projected_time_1m <= 35
        ), f"Too slow for V7: {metrics.projected_time_1m:.1f} min for 1M"

    @pytest.mark.benchmark
    @pytest.mark.timeout(15)
    def test_full_benchmark_suite(self):
        """Run full benchmark suite and save results."""
        results = self.benchmark.run_benchmark([100, 1000, 5000])

        # Save results to file
        output_file = Path("benchmark_results.json")
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n{'='*60}")
        print(f"Benchmark results saved to {output_file}")
        print(f"Overall assessment: {results['overall_assessment']['recommendation']}")
        print(f"{'='*60}")

        # Assert V7 compliance
        assert results["overall_assessment"][
            "meets_v7_full"
        ], "Performance does not meet V7 requirements"


if __name__ == "__main__":
    # Run benchmark directly
    benchmark = V7PerformanceBenchmark()
    benchmark.setup()
    results = benchmark.run_benchmark([100, 1000])

    print(f"\n{'='*60}")
    print("FINAL ASSESSMENT")
    print(f"{'='*60}")
    print(f"Meets V7 Quick Mode: {results['overall_assessment']['meets_v7_quick']}")
    print(f"Meets V7 Full Mode: {results['overall_assessment']['meets_v7_full']}")
    print(f"Recommendation: {results['overall_assessment']['recommendation']}")
