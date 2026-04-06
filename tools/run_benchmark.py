#!/usr/bin/env python3
"""GMNAP V7 Pipeline Benchmark.

Generates synthetic entries across all 37 regions, runs the pipeline
in OFFLINE mode, and reports throughput and memory usage.

Usage:
    PYTHONPATH=. python3 tools/run_benchmark.py --sizes 1000,10000,100000
"""

import argparse
import asyncio
import os
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["OFFLINE"] = "1"
os.environ["GMNAP_NO_NETWORK"] = "1"


def generate_entries(n: int) -> list:
    """Generate n synthetic entries across all 37 regions."""
    from src.regions.base import TERRITORY_TO_REGION

    ccs = list(set(TERRITORY_TO_REGION.keys()))
    entries = []
    for i in range(n):
        cc = ccs[i % len(ccs)]
        region = TERRITORY_TO_REGION[cc]
        entries.append(
            {
                "CanonicalLatin": f"Surname{i}, Given{i}",
                "CountryCodes": [cc],
                "BirthYear": 1950 + (i % 70),
                "GlobalID": f"bench-{i:08d}",
            }
        )
    return entries


def get_rss_mb() -> float:
    """Get current RSS in MB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / (1024 * 1024)  # macOS returns bytes


async def run_pipeline(entries: list) -> dict:
    """Run V7 pipeline on entries."""
    from src.core.pipeline_v7 import PipelineMode, V7Pipeline

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    return await pipeline.process_batch(entries)


def benchmark(sizes: list[int]):
    """Run benchmarks for each size."""
    print(
        f"{'Size':>10} {'Elapsed':>10} {'Entries/s':>10} {'1M proj':>10} {'RSS MB':>8}"
    )
    print("-" * 55)

    for n in sizes:
        entries = generate_entries(n)
        rss_before = get_rss_mb()

        start = time.perf_counter()
        try:
            asyncio.run(run_pipeline(entries))
        except Exception as e:
            print(f"{n:>10} ERROR: {e}")
            continue
        elapsed = time.perf_counter() - start

        rss_after = get_rss_mb()
        eps = n / elapsed if elapsed > 0 else 0
        proj_1m = 1_000_000 / eps / 60 if eps > 0 else float("inf")

        print(
            f"{n:>10,} {elapsed:>9.1f}s {eps:>9.0f}/s {proj_1m:>8.1f}min {rss_after:>7.1f}"
        )


def main():
    parser = argparse.ArgumentParser(description="GMNAP V7 Pipeline Benchmark")
    parser.add_argument(
        "--sizes",
        default="1000,10000",
        help="Comma-separated batch sizes (default: 1000,10000)",
    )
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",")]
    print(f"GMNAP V7 Benchmark (OFFLINE mode, Python {sys.version.split()[0]})")
    print(f"Sizes: {sizes}\n")
    benchmark(sizes)


if __name__ == "__main__":
    main()
