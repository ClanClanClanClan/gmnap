#!/usr/bin/env python3
"""
OPTIMIZED: Generate 50k synthetic names in <5 minutes.

Optimizations:
- Pre-compute all possible combinations
- Batch sampling instead of iterative loops
- Allow duplicates (removed in post-processing)
- Vectorized operations
"""

import sys
import random
import json
from pathlib import Path
from collections import defaultdict
from itertools import product

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import _STRONG, _MEDIUM

# Regional targets
REGIONAL_TARGETS = {
    "A4": 2000,
    "C1": 1800,
    "C9": 1800,  # Problem regions
    "A1": 1500,
    "A2": 1500,
    "A3": 1200,
    "A5": 1000,
    "B1": 1500,
    "B2": 1200,
    "B3": 1200,
    "C2": 1500,
    "C3": 1500,
    "C4": 1200,
    "C5": 1200,
    "C6": 1500,
    "C7": 1200,
    "C8": 1000,
    "D1": 1500,
    "D2": 1200,
    "D3": 1500,
    "D4": 1200,
    "D5": 1200,
    "E1": 1500,
    "E2": 1500,
    "E3": 1200,
    "E4": 1500,
    "E5": 1200,
    "E6": 1000,
    "E7": 1200,
    "F1": 1200,
    "F2": 1200,
    "F3": 1000,
    "F4": 1000,
    "G1": 1500,
    "H1": 800,
}

EAST_ASIAN = {"E1", "E2", "E3", "E4"}


def generate_all_combinations(region):
    """Pre-compute ALL possible name combinations for a region."""
    strong = _STRONG.get(region, {})
    medium = _MEDIUM.get(region, {})

    surnames = list(strong.get("surnames", set()) | medium.get("surnames", set()))
    givens = list(strong.get("given_frag", set()))
    particles = list(strong.get("particles", set()) | medium.get("particles", set()))
    prefixes = list(strong.get("surname_prefix", set()))

    # Fallback if empty
    if not givens:
        givens = ["alex", "david", "maria", "john", "anna", "thomas"]
    if not surnames:
        surnames = ["smith", "jones", "brown", "garcia", "martinez"]

    combinations = []

    # Simple: Given + Surname
    for g, s in product(givens, surnames):
        if region in EAST_ASIAN:
            name = f"{s.title()} {g.title()}"
        else:
            name = f"{g.title()} {s.title()}"
        combinations.append(name)

    # With particles (20% of combinations)
    if particles:
        for g, s, p in product(
            givens[: len(givens) // 5], surnames[: len(surnames) // 5], particles
        ):
            if region not in EAST_ASIAN:
                name = f"{g.title()} {p.lower()} {s.title()}"
                combinations.append(name)

    # With prefixes (20% of combinations)
    if prefixes:
        for g, s, pref in product(
            givens[: len(givens) // 5], surnames[: len(surnames) // 5], prefixes
        ):
            if region not in EAST_ASIAN:
                name = f"{g.title()} {pref}{s}".title()
                combinations.append(name)

    return combinations


def generate_region_fast(region, target):
    """Fast generation: sample from pre-computed combinations."""
    print(f"  {region}: ", end="", flush=True)

    # Pre-compute all combinations
    all_combos = generate_all_combinations(region)

    if len(all_combos) == 0:
        print(f"⚠️  No data (skipped)")
        return []

    # Sample with replacement if needed (allows duplicates)
    if len(all_combos) < target:
        # Not enough combinations, sample with replacement
        samples = random.choices(all_combos, k=target)
    else:
        # Enough combinations, sample without replacement
        samples = random.sample(all_combos, target)

    # Remove duplicates (deduplicate)
    unique = list(set(samples))

    # If deduplication reduced count, fill back up
    while len(unique) < target and len(unique) < len(all_combos):
        remaining = [c for c in all_combos if c not in unique]
        if not remaining:
            break
        needed = min(target - len(unique), len(remaining))
        unique.extend(random.sample(remaining, needed))

    print(f"✅ {len(unique):,} names")
    return unique[:target]


def main():
    print("=" * 70)
    print("OPTIMIZED SYNTHETIC DATASET GENERATOR (50k names)")
    print("=" * 70)
    print()

    total_target = sum(REGIONAL_TARGETS.values())
    print(f"Target: {total_target:,} names across {len(REGIONAL_TARGETS)} regions")
    print(f"Method: Pre-computed combinations + fast sampling")
    print()

    import time

    start_time = time.time()

    all_data = []
    stats = defaultdict(int)

    print("Generating...")
    for region, target in sorted(REGIONAL_TARGETS.items()):
        names = generate_region_fast(region, target)

        for name in names:
            all_data.append(
                {
                    "CanonicalNative": name,
                    "Region": region,
                    "Source": "synthetic_optimized",
                    "Method": "combination_sampling",
                }
            )
            stats[region] += 1

    elapsed = time.time() - start_time

    print()
    print("=" * 70)
    print(f"✅ GENERATION COMPLETE: {len(all_data):,} names in {elapsed:.1f}s")
    print(f"   Speed: {len(all_data)/elapsed:.0f} names/second")
    print("=" * 70)
    print()

    # Statistics
    print("Regional Distribution:")
    for region in sorted(stats.keys()):
        count = stats[region]
        target = REGIONAL_TARGETS[region]
        pct = (count / len(all_data)) * 100
        status = "✅" if count >= target * 0.95 else "⚠️"
        print(f"  {status} {region}: {count:5,} / {target:,} ({pct:5.2f}%)")
    print()

    # Save
    output_dir = Path("data/ml_training")
    output_dir.mkdir(exist_ok=True, parents=True)

    output_file = output_dir / "synthetic_50k.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "total": len(all_data),
                    "regions": len(stats),
                    "generation_time_seconds": elapsed,
                    "method": "optimized_combination_sampling",
                },
                "data": all_data,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"✅ Saved to: {output_file}")
    print()

    # Samples
    print("Sample names (3 per region):")
    for region in sorted(stats.keys())[:10]:  # Show first 10 regions
        region_names = [d["CanonicalNative"] for d in all_data if d["Region"] == region]
        samples = random.sample(region_names, min(3, len(region_names)))
        print(f"  {region}: {', '.join(samples)}")
    print(f"  ... ({len(stats)-10} more regions)")
    print()

    print("=" * 70)
    print("Next: Fetch real-world names from Math Genealogy")
    print("  python3 scripts/ml/fetch_real_names.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
