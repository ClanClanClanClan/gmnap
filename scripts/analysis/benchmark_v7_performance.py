#!/usr/bin/env python3
"""
GMNAP V7 Performance Benchmark Suite
Measures performance against V7 specification SLAs
"""

import asyncio
import json
import psutil
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import random
import string
import gc

# V7 Specification SLAs
V7_SLAS = {
    "Quick": {
        "runtime_per_1M": 35 * 60,  # 35 minutes in seconds
        "peak_rss_gb": 6,
        "streaming_chunk_size": 8000,
        "duplicate_external_id_pct_max": 0.10,
        "graph_coherence_score_min": 0.85,
        "idempotent_diff_bytes_max": 0,
    },
    "Full": {
        "runtime_per_1M": 70 * 60,  # 70 minutes in seconds
        "peak_rss_gb": 6,
        "streaming_chunk_size": 8000,
        "duplicate_external_id_pct_max": 0.05,
        "graph_coherence_score_min": 0.92,
        "idempotent_diff_bytes_max": 0,
    },
    "Extreme": {
        "runtime_per_1M": None,  # No SLA
        "peak_rss_gb": 8,
        "streaming_chunk_size": 8000,
        "duplicate_external_id_pct_max": 0.0,
        "graph_coherence_score_min": 0.97,
        "idempotent_diff_bytes_max": 0,
    },
}


class V7PerformanceBenchmark:
    """Performance benchmark suite for V7 pipeline"""

    def __init__(self, mode: str = "Quick"):
        """Initialize benchmark suite"""
        self.mode = mode
        self.sla = V7_SLAS[mode]
        self.results = {}
        self.start_time = None
        self.peak_memory = 0

    def generate_test_data(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate synthetic test data for benchmarking

        Args:
            count: Number of entries to generate

        Returns:
            List of test entries
        """
        print(f"Generating {count} synthetic entries...")
        entries = []

        # Common names for realistic distribution
        first_names = [
            "John",
            "Mary",
            "David",
            "Sarah",
            "Michael",
            "Emma",
            "Robert",
            "Lisa",
            "James",
            "Jennifer",
            "William",
            "Linda",
            "Richard",
            "Patricia",
            "Charles",
            "Barbara",
            "Thomas",
            "Susan",
            "Christopher",
            "Jessica",
            "José",
            "María",
            "李",
            "王",
            "张",
            "刘",
            "陈",
            "杨",
            "黄",
            "赵",
            "Pierre",
            "Marie",
            "Jean",
            "François",
            "Hans",
            "Anna",
            "Ivan",
            "Olga",
        ]

        last_names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
            "Rodriguez",
            "Martinez",
            "Hernandez",
            "Lopez",
            "Gonzalez",
            "Wilson",
            "Anderson",
            "Thomas",
            "Taylor",
            "Moore",
            "Jackson",
            "Martin",
            "Lee",
            "Wang",
            "Zhang",
            "Liu",
            "Chen",
            "Yang",
            "Huang",
            "Zhao",
            "Wu",
            "Müller",
            "Schmidt",
            "Schneider",
            "Fischer",
            "Meyer",
            "Wagner",
            "Ivanov",
            "Petrov",
            "Sidorov",
            "Dupont",
            "Moreau",
            "Laurent",
        ]

        scripts = ["Latin", "Latin", "Latin", "Cyrillic", "Han", "Arabic", "Greek"]
        regions = [
            "A1",
            "A2",
            "A3",
            "B1",
            "B2",
            "B3",
            "C1",
            "C2",
            "C3",
            "D1",
            "E1",
            "E4",
        ]

        for i in range(count):
            first = random.choice(first_names)
            last = random.choice(last_names)

            entry = {
                "GlobalID": f"bench-{i:08d}",
                "CanonicalLatin": f"{last}, {first}",
                "CanonicalNative": f"{last}, {first}" if random.random() > 0.3 else "",
                "Type": "Individual",
                "BirthYear": random.randint(1920, 2000),
                "DetectedScript": random.choice(scripts),
                "DetectedRegion": random.choice(regions),
            }

            # Add some with external IDs (for duplicate detection)
            if random.random() > 0.7:
                entry["ExternalIDs"] = [
                    {
                        "type": "ORCID",
                        "value": f"0000-000{random.randint(1,9)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                    }
                ]

            # Add some with affiliations
            if random.random() > 0.5:
                entry["Affiliations"] = [
                    {
                        "institution": f"University of {random.choice(['Oxford', 'Cambridge', 'MIT', 'Stanford', 'ETH'])}",
                        "country": random.choice(["US", "GB", "CH", "FR", "DE"]),
                    }
                ]

            entries.append(entry)

        return entries

    async def benchmark_pipeline_stages(self, entries: List[Dict]) -> Dict[str, Any]:
        """
        Benchmark individual pipeline stages

        Returns:
            Performance metrics for each stage
        """
        stage_metrics = {}

        # Stage 2: Region Detection
        print("\nBenchmarking Stage 2: Region Detection...")
        start = time.time()
        from src.pipeline.stage2_detect_region import detect_region

        for entry in entries[:1000]:  # Sample
            region, script = detect_region(entry)
            entry["DetectedRegion"] = region
            entry["DetectedScript"] = script
        elapsed = time.time() - start
        stage_metrics["stage2_region_detection"] = {
            "time_per_1k": elapsed,
            "throughput": 1000 / elapsed if elapsed > 0 else 0,
        }

        # Stage 3: Region Hooks
        print("Benchmarking Stage 3: Region Hooks...")
        start = time.time()
        from src.pipeline.stage3_region_hooks import apply_region_hooks

        _ = apply_region_hooks(entries[:1000])
        elapsed = time.time() - start
        stage_metrics["stage3_region_hooks"] = {
            "time_per_1k": elapsed,
            "throughput": 1000 / elapsed if elapsed > 0 else 0,
        }

        # Stage 6: Graph Consistency
        print("Benchmarking Stage 6: Graph Consistency...")
        start = time.time()
        from src.pipeline.stage6_graph_consistency import enforce_graph_coherence_gate

        try:
            _, metrics = enforce_graph_coherence_gate(entries[:1000], self.mode)
            stage_metrics["stage6_graph_consistency"] = {
                "time_per_1k": time.time() - start,
                "coherence_score": metrics.get("coherence_score", 0),
            }
        except Exception as e:
            stage_metrics["stage6_graph_consistency"] = {"error": str(e)}

        # Stage 8: Global Validation
        print("Benchmarking Stage 8: Global Validation...")
        start = time.time()
        from src.pipeline.stage8_global_validate import global_validate

        try:
            _, metrics = global_validate(entries[:1000], self.mode)
            stage_metrics["stage8_validation"] = {
                "time_per_1k": time.time() - start,
                "schema_errors": metrics.get("schema_errors", 0),
                "roundtrip_failures": metrics.get("roundtrip_failures", 0),
            }
        except Exception as e:
            stage_metrics["stage8_validation"] = {"error": str(e)[:100]}

        # Stage 11: Idempotency
        print("Benchmarking Stage 11: Idempotency...")
        start = time.time()
        from src.pipeline.stage11_idempotency_check import idempotency_check

        _, metrics = idempotency_check(entries[:100], mode="self", strict=False)
        stage_metrics["stage11_idempotency"] = {
            "time_per_100": time.time() - start,
            "diff_bytes": metrics.get("idempotency_diff_bytes", -1),
        }

        return stage_metrics

    async def benchmark_authority_apis(self) -> Dict[str, Any]:
        """
        Benchmark authority API performance

        Returns:
            API performance metrics
        """
        api_metrics = {}

        test_names = ["T. Tao", "Maryam Mirzakhani", "Cédric Villani"]

        # Crossref API
        print("\nBenchmarking Crossref API...")
        try:
            from src.authorities.crossref import CrossrefAPI

            start = time.time()
            async with CrossrefAPI() as api:
                for name in test_names:
                    results = await api.search_author(name, limit=5)
                elapsed = time.time() - start
                stats = api.get_stats()
                api_metrics["crossref"] = {
                    "requests": stats["request_count"],
                    "time_total": elapsed,
                    "time_per_request": (
                        elapsed / stats["request_count"]
                        if stats["request_count"] > 0
                        else 0
                    ),
                    "daily_quota": stats["daily_quota"],
                }
        except Exception as e:
            api_metrics["crossref"] = {"error": str(e)[:100]}

        # OpenAlex API
        print("Benchmarking OpenAlex API...")
        try:
            from src.authorities.openalex import OpenAlexAPI

            start = time.time()
            async with OpenAlexAPI() as api:
                for name in test_names:
                    results = await api.search_authors(name, limit=5)
                elapsed = time.time() - start
                stats = api.get_stats()
                api_metrics["openalex"] = {
                    "requests": stats["request_count"],
                    "time_total": elapsed,
                    "time_per_request": (
                        elapsed / stats["request_count"]
                        if stats["request_count"] > 0
                        else 0
                    ),
                    "daily_quota": stats["daily_quota"],
                }
        except Exception as e:
            api_metrics["openalex"] = {"error": str(e)[:100]}

        # ORCID API
        print("Benchmarking ORCID API...")
        try:
            from src.authorities.orcid import ORCIDAPI

            start = time.time()
            async with ORCIDAPI() as api:
                for name in test_names:
                    parts = name.split()
                    orcids = await api.search_by_name(parts[0], parts[-1], limit=3)
                elapsed = time.time() - start
                stats = api.get_stats()
                api_metrics["orcid"] = {
                    "requests": stats["request_count"],
                    "time_total": elapsed,
                    "time_per_request": (
                        elapsed / stats["request_count"]
                        if stats["request_count"] > 0
                        else 0
                    ),
                    "daily_quota": stats["daily_quota"],
                }
        except Exception as e:
            api_metrics["orcid"] = {"error": str(e)[:100]}

        return api_metrics

    def benchmark_memory(self, entries: List[Dict]) -> Dict[str, Any]:
        """
        Benchmark memory usage

        Returns:
            Memory usage metrics
        """
        print("\nBenchmarking memory usage...")

        # Start memory tracking
        tracemalloc.start()
        gc.collect()

        # Get initial memory
        process = psutil.Process()
        initial_rss = process.memory_info().rss / (1024 * 1024 * 1024)  # GB

        # Process entries in chunks (simulate streaming)
        chunk_size = self.sla["streaming_chunk_size"]
        chunks_processed = 0
        peak_rss = initial_rss

        for i in range(0, len(entries), chunk_size):
            chunk = entries[i : i + chunk_size]

            # Simulate processing
            _ = json.dumps(chunk)
            _ = json.loads(json.dumps(chunk))

            chunks_processed += 1
            current_rss = process.memory_info().rss / (1024 * 1024 * 1024)
            peak_rss = max(peak_rss, current_rss)

            # Force garbage collection periodically
            if chunks_processed % 10 == 0:
                gc.collect()

        # Get memory snapshot
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")[:10]

        tracemalloc.stop()

        return {
            "initial_rss_gb": initial_rss,
            "peak_rss_gb": peak_rss,
            "rss_increase_gb": peak_rss - initial_rss,
            "chunks_processed": chunks_processed,
            "chunk_size": chunk_size,
            "sla_peak_rss_gb": self.sla["peak_rss_gb"],
            "within_sla": peak_rss <= self.sla["peak_rss_gb"],
        }

    async def run_comprehensive_benchmark(
        self, entry_count: int = 10000
    ) -> Dict[str, Any]:
        """
        Run comprehensive performance benchmark

        Args:
            entry_count: Number of entries to test with

        Returns:
            Complete benchmark results
        """
        print(f"\n{'='*70}")
        print(f"V7 PERFORMANCE BENCHMARK - {self.mode} Mode")
        print(f"Testing with {entry_count:,} entries")
        print(f"{'='*70}")

        self.start_time = time.time()
        results = {
            "mode": self.mode,
            "entry_count": entry_count,
            "start_time": datetime.utcnow().isoformat(),
            "sla": self.sla,
        }

        # Generate test data
        entries = self.generate_test_data(entry_count)

        # Benchmark pipeline stages
        results["pipeline_stages"] = await self.benchmark_pipeline_stages(entries)

        # Benchmark authority APIs
        results["authority_apis"] = await self.benchmark_authority_apis()

        # Benchmark memory usage
        results["memory"] = self.benchmark_memory(entries)

        # Calculate overall metrics
        total_time = time.time() - self.start_time
        results["overall"] = {
            "total_time_seconds": total_time,
            "throughput_per_second": entry_count / total_time if total_time > 0 else 0,
            "estimated_time_per_1M": (
                (total_time / entry_count) * 1_000_000 if entry_count > 0 else 0
            ),
        }

        # Check SLA compliance
        results["sla_compliance"] = self.check_sla_compliance(results)

        return results

    def check_sla_compliance(self, results: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check if performance meets V7 SLAs

        Returns:
            SLA compliance status
        """
        compliance = {}

        # Runtime SLA (if defined)
        if self.sla["runtime_per_1M"]:
            estimated_1M = results["overall"]["estimated_time_per_1M"]
            compliance["runtime"] = estimated_1M <= self.sla["runtime_per_1M"]
        else:
            compliance["runtime"] = True  # No SLA for Extreme mode

        # Memory SLA
        peak_memory = results["memory"]["peak_rss_gb"]
        compliance["memory"] = peak_memory <= self.sla["peak_rss_gb"]

        # Idempotency SLA
        idemp_bytes = (
            results["pipeline_stages"]
            .get("stage11_idempotency", {})
            .get("diff_bytes", -1)
        )
        compliance["idempotency"] = idemp_bytes <= self.sla["idempotent_diff_bytes_max"]

        # Graph coherence SLA
        coherence = (
            results["pipeline_stages"]
            .get("stage6_graph_consistency", {})
            .get("coherence_score", 0)
        )
        compliance["graph_coherence"] = (
            coherence >= self.sla["graph_coherence_score_min"]
        )

        # Overall compliance
        compliance["overall"] = all(compliance.values())

        return compliance

    def print_results(self, results: Dict[str, Any]):
        """Print formatted benchmark results"""
        print(f"\n{'='*70}")
        print("BENCHMARK RESULTS")
        print(f"{'='*70}")

        # Overall performance
        print(f"\n📊 Overall Performance:")
        print(f"  Total time: {results['overall']['total_time_seconds']:.2f} seconds")
        print(
            f"  Throughput: {results['overall']['throughput_per_second']:.0f} entries/second"
        )
        print(
            f"  Estimated for 1M: {results['overall']['estimated_time_per_1M']/60:.1f} minutes"
        )
        if self.sla["runtime_per_1M"]:
            print(f"  SLA for 1M: {self.sla['runtime_per_1M']/60:.0f} minutes")

        # Memory usage
        print(f"\n💾 Memory Usage:")
        mem = results["memory"]
        print(f"  Initial RSS: {mem['initial_rss_gb']:.2f} GB")
        print(f"  Peak RSS: {mem['peak_rss_gb']:.2f} GB")
        print(f"  SLA limit: {mem['sla_peak_rss_gb']} GB")
        print(f"  Within SLA: {'✅' if mem['within_sla'] else '❌'}")

        # Pipeline stages
        print(f"\n⚙️ Pipeline Stage Performance:")
        for stage, metrics in results["pipeline_stages"].items():
            if "error" not in metrics:
                if "time_per_1k" in metrics:
                    print(f"  {stage}: {metrics['time_per_1k']:.3f}s per 1k entries")
                elif "time_per_100" in metrics:
                    print(f"  {stage}: {metrics['time_per_100']:.3f}s per 100 entries")

        # Authority APIs
        print(f"\n🌐 Authority API Performance:")
        for api, metrics in results["authority_apis"].items():
            if "error" not in metrics:
                print(f"  {api}:")
                print(f"    Requests: {metrics.get('requests', 0)}")
                print(f"    Avg time: {metrics.get('time_per_request', 0):.3f}s")
                print(f"    Daily quota: {metrics.get('daily_quota', 'N/A'):,}")

        # SLA Compliance
        print(f"\n✅ SLA Compliance:")
        compliance = results["sla_compliance"]
        for check, passed in compliance.items():
            if check != "overall":
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  {check}: {status}")

        print(f"\n{'='*70}")
        overall = "✅ ALL SLAs MET" if compliance["overall"] else "❌ SOME SLAs FAILED"
        print(f"OVERALL: {overall}")
        print(f"{'='*70}")

    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save benchmark results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_{self.mode}_{timestamp}.json"

        path = Path("benchmarks") / filename
        path.parent.mkdir(exist_ok=True)

        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\nResults saved to: {path}")
        return path


async def main():
    """Run performance benchmarks"""
    import sys

    # Parse arguments
    mode = sys.argv[1] if len(sys.argv) > 1 else "Quick"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10000

    if mode not in ["Quick", "Full", "Extreme"]:
        print(f"Invalid mode: {mode}")
        print(
            "Usage: python benchmark_v7_performance.py [Quick|Full|Extreme] [entry_count]"
        )
        return 1

    # Run benchmark
    benchmark = V7PerformanceBenchmark(mode)
    results = await benchmark.run_comprehensive_benchmark(count)

    # Print results
    benchmark.print_results(results)

    # Save results
    benchmark.save_results(results)

    # Return exit code based on SLA compliance
    return 0 if results["sla_compliance"]["overall"] else 1


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
