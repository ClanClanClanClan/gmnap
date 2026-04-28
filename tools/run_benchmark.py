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


def generate_real_entries(n: int) -> list:
    """Take ``n`` real names from the curated genealogy enrichment.

    Used by the ``--real-names`` flag to characterize realistic-
    workload throughput. The synthetic benchmark is a worst case
    because no name matches a curated rule; with real names from the
    genealogy JSON, most will hit a signature suffix or surname
    dictionary entry, producing a much more representative number.
    """
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "data" / "genealogy_enrichment.json"
    if not path.exists():
        raise FileNotFoundError(
            f"genealogy enrichment not found at {path}; " "did you run `git lfs pull`?"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_global_id = payload.get("by_global_id") or {}
    # `by_global_id` maps GID -> canonical-name string.
    # Take a stable slice (sorted by GID) so reruns are deterministic.
    items = sorted(by_global_id.items())[:n]
    return [
        {
            "CanonicalLatin": canonical,
            "GlobalID": gid,
        }
        for gid, canonical in items
    ]


def get_rss_mb() -> float:
    """Get current RSS in MB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / (1024 * 1024)  # macOS returns bytes


async def run_pipeline(entries: list) -> dict:
    """Run V7 pipeline on entries."""
    from src.core.pipeline_v7 import PipelineMode, V7Pipeline

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    return await pipeline.process_batch(entries)


def benchmark(sizes: list[int], real_names: bool = False):
    """Run benchmarks for each size.

    ``real_names``: when True, sample from data/genealogy_enrichment.json
    instead of generating synthetic ``Surname{i}`` entries. The real-
    name path exercises rule fast-path matches and produces the
    realistic-workload throughput number.
    """
    label = "REAL names" if real_names else "synthetic"
    print(f"Mode: {label}")
    print()
    print(
        f"{'Size':>10} {'Elapsed':>10} {'Entries/s':>10} {'1M proj':>10} {'RSS MB':>8}"
    )
    print("-" * 55)

    for n in sizes:
        entries = generate_real_entries(n) if real_names else generate_entries(n)
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
    parser.add_argument(
        "--real-names",
        action="store_true",
        help=(
            "Use real names sampled from data/genealogy_enrichment.json "
            "instead of synthetic 'Surname{i}, Given{i}' entries. The "
            "real-name path is what production workload looks like; "
            "synthetic is the worst case. See "
            "docs/perf_characterization.md."
        ),
    )
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",")]
    print(f"GMNAP V7 Benchmark (OFFLINE mode, Python {sys.version.split()[0]})")
    print(f"Sizes: {sizes}")
    benchmark(sizes, real_names=args.real_names)


if __name__ == "__main__":
    main()
