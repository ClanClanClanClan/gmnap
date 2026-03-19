#!/usr/bin/env python3
"""
Benchmark live authority enrichment with OFFLINE=0.

Measures real API call latencies, throughput, and failure rates for each
authority source tier. Compares against OFFLINE=1 baseline.

Usage:
    # Baseline (cache-only)
    OFFLINE=1 python3 tools/benchmark_live_enrichment.py

    # Live enrichment (requires network + API keys)
    OFFLINE=0 python3 tools/benchmark_live_enrichment.py

    # Specific tiers only
    OFFLINE=0 python3 tools/benchmark_live_enrichment.py --tiers 0,1

    # Custom sample size
    OFFLINE=0 python3 tools/benchmark_live_enrichment.py --samples 50
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# Ensure project root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.authority.manager_tier01 import (
    OFFLINE,
    TIER_HANDLERS,
    enrich_by_tiers,
)


# Representative test entries covering diverse regions and name types
SAMPLE_ENTRIES = [
    {"CanonicalLatin": "Wang, Wei", "BirthYear": 1970, "CountryCodes": ["CN"],
     "DetectedRegion": "E1", "LanguageOfPublication": ["zh"]},
    {"CanonicalLatin": "Tanaka, Hiroshi", "BirthYear": 1965, "CountryCodes": ["JP"],
     "DetectedRegion": "E3", "LanguageOfPublication": ["ja"]},
    {"CanonicalLatin": "Mueller, Hans", "BirthYear": 1960, "CountryCodes": ["DE"],
     "DetectedRegion": "B1", "LanguageOfPublication": ["de"]},
    {"CanonicalLatin": "Smith, John", "BirthYear": 1975, "CountryCodes": ["US"],
     "DetectedRegion": "A1", "LanguageOfPublication": ["en"]},
    {"CanonicalLatin": "Kim, Jong-un", "BirthYear": 1980, "CountryCodes": ["KR"],
     "DetectedRegion": "E4", "LanguageOfPublication": ["ko"]},
    {"CanonicalLatin": "Ivanov, Sergei", "BirthYear": 1968, "CountryCodes": ["RU"],
     "DetectedRegion": "B2", "LanguageOfPublication": ["ru"]},
    {"CanonicalLatin": "Al-Rashid, Ahmad", "BirthYear": 1972, "CountryCodes": ["SA"],
     "DetectedRegion": "C3", "LanguageOfPublication": ["ar"]},
    {"CanonicalLatin": "da Silva, Maria", "BirthYear": 1985, "CountryCodes": ["BR"],
     "DetectedRegion": "A2", "LanguageOfPublication": ["pt"]},
    {"CanonicalLatin": "Dupont, Pierre", "BirthYear": 1978, "CountryCodes": ["FR"],
     "DetectedRegion": "A2", "LanguageOfPublication": ["fr"]},
    {"CanonicalLatin": "Patel, Ramesh", "BirthYear": 1982, "CountryCodes": ["IN"],
     "DetectedRegion": "D1", "LanguageOfPublication": ["hi"]},
]


@dataclass
class TierBenchmark:
    """Benchmark results for a single tier."""
    tier: int
    total_entries: int = 0
    total_time_s: float = 0.0
    per_entry_times: List[float] = field(default_factory=list)
    hits: int = 0
    misses: int = 0
    errors: int = 0
    sources_hit: Dict[str, int] = field(default_factory=dict)

    @property
    def avg_time_ms(self) -> float:
        if not self.per_entry_times:
            return 0.0
        return statistics.mean(self.per_entry_times) * 1000

    @property
    def p95_time_ms(self) -> float:
        if not self.per_entry_times:
            return 0.0
        sorted_times = sorted(self.per_entry_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)] * 1000

    @property
    def throughput_per_s(self) -> float:
        if self.total_time_s <= 0:
            return 0.0
        return self.total_entries / self.total_time_s

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


async def benchmark_tier(entries: List[Dict], tier: int) -> TierBenchmark:
    """Benchmark a single tier of authority enrichment."""
    bench = TierBenchmark(tier=tier, total_entries=len(entries))

    t0 = time.perf_counter()
    for entry in entries:
        et0 = time.perf_counter()
        try:
            enriched = await enrich_by_tiers([entry.copy()], tiers=[tier])
            et1 = time.perf_counter()
            bench.per_entry_times.append(et1 - et0)

            # Count hits from enrichment
            e = enriched[0] if enriched else {}
            authority_ids = e.get("AuthorityIDs", {})
            sources = e.get("_authority_sources", [])
            if authority_ids or sources:
                bench.hits += 1
                for src in sources:
                    bench.sources_hit[src] = bench.sources_hit.get(src, 0) + 1
            else:
                bench.misses += 1
        except Exception as ex:
            et1 = time.perf_counter()
            bench.per_entry_times.append(et1 - et0)
            bench.errors += 1
            print(f"  ERROR tier {tier}, entry {entry.get('CanonicalLatin')}: {ex}")

    bench.total_time_s = time.perf_counter() - t0
    return bench


async def run_benchmark(tiers: List[int], samples: int) -> Dict:
    """Run the full benchmark suite."""
    # Expand sample entries if needed
    entries = (SAMPLE_ENTRIES * ((samples // len(SAMPLE_ENTRIES)) + 1))[:samples]

    print(f"=" * 70)
    print(f"GMNAP Authority Enrichment Benchmark")
    print(f"=" * 70)
    print(f"  OFFLINE mode : {'ON (cache-only)' if OFFLINE else 'OFF (live API calls)'}")
    print(f"  Sample size  : {len(entries)} entries")
    print(f"  Tiers        : {tiers}")
    print(f"  Sources/tier :")
    for t in tiers:
        sources = [name for name, _ in TIER_HANDLERS.get(t, [])]
        print(f"    Tier {t}: {', '.join(sources)}")
    print(f"-" * 70)

    results = {}
    for tier in tiers:
        print(f"\nBenchmarking Tier {tier}...")
        bench = await benchmark_tier(entries, tier)
        results[f"tier_{tier}"] = bench

        print(f"  Entries     : {bench.total_entries}")
        print(f"  Total time  : {bench.total_time_s:.2f}s")
        print(f"  Avg/entry   : {bench.avg_time_ms:.1f}ms")
        print(f"  P95/entry   : {bench.p95_time_ms:.1f}ms")
        print(f"  Throughput  : {bench.throughput_per_s:.1f} entries/s")
        print(f"  Hits/Misses : {bench.hits}/{bench.misses} ({bench.hit_rate:.1%} hit rate)")
        print(f"  Errors      : {bench.errors}")
        if bench.sources_hit:
            print(f"  Sources hit : {bench.sources_hit}")

    # Full pipeline benchmark (all tiers combined)
    print(f"\n{'=' * 70}")
    print("Full Pipeline Benchmark (all requested tiers)...")
    t0 = time.perf_counter()
    try:
        enriched = await enrich_by_tiers(
            [e.copy() for e in entries], tiers=tiers
        )
        full_time = time.perf_counter() - t0
    except Exception as ex:
        full_time = time.perf_counter() - t0
        print(f"  ERROR: {ex}")
        enriched = []

    print(f"  Total time      : {full_time:.2f}s")
    print(f"  Entries          : {len(entries)}")
    if full_time > 0:
        throughput = len(entries) / full_time
        projected_1m = (1_000_000 / throughput) / 60 if throughput > 0 else float("inf")
        print(f"  Throughput       : {throughput:.1f} entries/s")
        print(f"  Projected 1M    : {projected_1m:.1f} min")
    print(f"{'=' * 70}")

    # Summary JSON
    summary = {
        "offline": OFFLINE,
        "samples": len(entries),
        "tiers": tiers,
        "tier_results": {},
        "full_pipeline": {
            "total_time_s": full_time,
            "entries": len(entries),
            "throughput_per_s": len(entries) / full_time if full_time > 0 else 0,
        },
    }
    for key, bench in results.items():
        summary["tier_results"][key] = {
            "total_time_s": bench.total_time_s,
            "avg_time_ms": bench.avg_time_ms,
            "p95_time_ms": bench.p95_time_ms,
            "throughput_per_s": bench.throughput_per_s,
            "hit_rate": bench.hit_rate,
            "hits": bench.hits,
            "misses": bench.misses,
            "errors": bench.errors,
            "sources_hit": bench.sources_hit,
        }

    # Write results to file
    out_path = Path("cache/benchmark_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nResults written to {out_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Benchmark live authority enrichment")
    parser.add_argument("--tiers", type=str, default="0,1,2",
                        help="Comma-separated tier numbers (default: 0,1,2)")
    parser.add_argument("--samples", type=int, default=10,
                        help="Number of sample entries (default: 10)")
    args = parser.parse_args()

    tiers = [int(t.strip()) for t in args.tiers.split(",")]
    asyncio.run(run_benchmark(tiers, args.samples))


if __name__ == "__main__":
    main()
