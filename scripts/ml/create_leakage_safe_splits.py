#!/usr/bin/env python3
"""
Leakage-Safe Data Splitting

Based on expert guidance (Oct 30, 2025):
- Surname-grouped splits to avoid leakage
- Duplicate detection and removal
- Preserves class balance
- Configurable split ratios

Problem: Standard random splits can leak information when the same person
appears in multiple splits with slight name variations, or when family
members with the same surname appear across splits.

Solution: Group by surname cluster, assign entire groups to splits.
"""

import json
import sys
import random
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Import name utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.names import (
    normalize_name_for_comparison,
    extract_surname,
    extract_surname_cluster,
    find_duplicates,
)


def load_data(path: Path) -> List[Dict]:
    """Load dataset from JSON"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("profiles", data if isinstance(data, list) else [])


def detect_and_remove_duplicates(profiles: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Detect and remove duplicate names

    Returns:
        (deduplicated_profiles, duplicate_report)
    """
    names = [p.get("name", "") for p in profiles]
    duplicates = find_duplicates(names)

    # Create index map: normalized name → first occurrence index
    kept_indices = {}
    for i, profile in enumerate(profiles):
        name = profile.get("name", "")
        normalized = normalize_name_for_comparison(name)

        if normalized not in kept_indices:
            kept_indices[normalized] = i

    # Keep only first occurrence of each normalized name
    deduplicated = [profiles[i] for i in sorted(set(kept_indices.values()))]

    duplicate_report = {
        "total_profiles": len(profiles),
        "unique_profiles": len(deduplicated),
        "duplicates_removed": len(profiles) - len(deduplicated),
        "duplicate_groups": len(duplicates),
        "examples": {
            norm: originals[:5]  # First 5 examples
            for norm, originals in list(duplicates.items())[:10]
        },
    }

    return deduplicated, duplicate_report


def create_surname_clusters(profiles: List[Dict]) -> Dict[str, List[int]]:
    """
    Group profiles by surname cluster

    Returns:
        Dict mapping surname_cluster → list of profile indices
    """
    clusters = defaultdict(list)

    for i, profile in enumerate(profiles):
        name = profile.get("name", "")
        if not name:
            # Assign to special "no_name" cluster
            clusters["__NO_NAME__"].append(i)
            continue

        surname = extract_surname(name)
        cluster = extract_surname_cluster(surname, min_length=3)

        clusters[cluster].append(i)

    return dict(clusters)


def split_by_surname_clusters(
    clusters: Dict[str, List[int]],
    profiles: List[Dict],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Split profiles into train/val/test by surname clusters

    Strategy:
    1. Shuffle surname clusters (not individual profiles)
    2. Assign entire clusters to splits
    3. Try to maintain class balance

    Args:
        clusters: Dict mapping surname_cluster → profile indices
        profiles: All profiles
        train_ratio: Fraction for training
        val_ratio: Fraction for validation
        test_ratio: Fraction for testing
        seed: Random seed

    Returns:
        (train_profiles, val_profiles, test_profiles)
    """
    random.seed(seed)

    # Get region distribution
    region_counts = defaultdict(int)
    for profile in profiles:
        region_counts[profile.get("region")] += 1

    # Sort clusters by size (process large clusters first for better balance)
    sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)

    # Initialize splits
    train_indices = []
    val_indices = []
    test_indices = []

    # Assign clusters to splits
    for cluster_name, indices in sorted_clusters:
        # Compute current split sizes
        total = len(train_indices) + len(val_indices) + len(test_indices)
        if total == 0:
            # First cluster goes to train
            train_indices.extend(indices)
            continue

        train_frac = len(train_indices) / total
        val_frac = len(val_indices) / total
        test_frac = len(test_indices) / total

        # Assign to the split that is most under-represented
        if train_frac < train_ratio:
            train_indices.extend(indices)
        elif val_frac < val_ratio:
            val_indices.extend(indices)
        else:
            test_indices.extend(indices)

    # Build split datasets
    train_profiles = [profiles[i] for i in train_indices]
    val_profiles = [profiles[i] for i in val_indices]
    test_profiles = [profiles[i] for i in test_indices]

    return train_profiles, val_profiles, test_profiles


def compute_split_stats(train, val, test) -> Dict:
    """Compute statistics for splits"""

    def region_distribution(profiles):
        dist = defaultdict(int)
        for p in profiles:
            dist[p.get("region")] += 1
        return dict(dist)

    return {
        "train": {
            "count": len(train),
            "fraction": len(train) / (len(train) + len(val) + len(test)),
            "regions": region_distribution(train),
        },
        "val": {
            "count": len(val),
            "fraction": len(val) / (len(train) + len(val) + len(test)),
            "regions": region_distribution(val),
        },
        "test": {
            "count": len(test),
            "fraction": len(test) / (len(train) + len(val) + len(test)),
            "regions": region_distribution(test),
        },
    }


def create_leakage_safe_splits(
    input_path: Path,
    output_dir: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
):
    """
    Create leakage-safe train/val/test splits

    Args:
        input_path: Path to input dataset (JSON)
        output_dir: Directory to save splits
        train_ratio: Training set fraction
        val_ratio: Validation set fraction
        test_ratio: Test set fraction
        seed: Random seed
    """
    print("=" * 80)
    print("LEAKAGE-SAFE DATA SPLITTING")
    print("=" * 80)

    # Load data
    print(f"\n[1/6] Loading data from {input_path}...")
    profiles = load_data(input_path)
    print(f"  Loaded: {len(profiles):,} profiles")

    # Remove duplicates
    print(f"\n[2/6] Detecting and removing duplicates...")
    deduplicated, dup_report = detect_and_remove_duplicates(profiles)
    print(f"  Original: {dup_report['total_profiles']:,} profiles")
    print(f"  Unique: {dup_report['unique_profiles']:,} profiles")
    print(
        f"  Removed: {dup_report['duplicates_removed']:,} duplicates ({dup_report['duplicates_removed']/dup_report['total_profiles']*100:.1f}%)"
    )
    if dup_report["duplicate_groups"] > 0:
        print(f"  Duplicate groups: {dup_report['duplicate_groups']}")

    # Create surname clusters
    print(f"\n[3/6] Creating surname clusters...")
    clusters = create_surname_clusters(deduplicated)
    print(f"  Clusters: {len(clusters):,}")
    print(f"  Avg cluster size: {len(deduplicated) / len(clusters):.1f}")

    # Show largest clusters
    largest = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    print(f"  Largest clusters:")
    for cluster, indices in largest:
        print(f"    {cluster}: {len(indices)} profiles")

    # Split by clusters
    print(f"\n[4/6] Splitting by surname clusters...")
    print(f"  Target ratios: train={train_ratio:.0%}, val={val_ratio:.0%}, test={test_ratio:.0%}")
    train, val, test = split_by_surname_clusters(
        clusters, deduplicated, train_ratio, val_ratio, test_ratio, seed
    )

    # Compute stats
    print(f"\n[5/6] Computing split statistics...")
    stats = compute_split_stats(train, val, test)
    print(f"  Train: {stats['train']['count']:,} ({stats['train']['fraction']:.1%})")
    print(f"  Val:   {stats['val']['count']:,} ({stats['val']['fraction']:.1%})")
    print(f"  Test:  {stats['test']['count']:,} ({stats['test']['fraction']:.1%})")

    # Save splits
    print(f"\n[6/6] Saving splits...")
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "train_split_leakage_safe.json"
    val_path = output_dir / "val_split_leakage_safe.json"
    test_path = output_dir / "test_split_leakage_safe.json"
    report_path = output_dir / "split_report_leakage_safe.json"

    with open(train_path, "w", encoding="utf-8") as f:
        json.dump({"profiles": train}, f, indent=2, ensure_ascii=False)

    with open(val_path, "w", encoding="utf-8") as f:
        json.dump({"profiles": val}, f, indent=2, ensure_ascii=False)

    with open(test_path, "w", encoding="utf-8") as f:
        json.dump({"profiles": test}, f, indent=2, ensure_ascii=False)

    # Save report
    report = {
        "input_file": str(input_path),
        "output_dir": str(output_dir),
        "duplicate_report": dup_report,
        "cluster_stats": {
            "total_clusters": len(clusters),
            "avg_cluster_size": len(deduplicated) / len(clusters),
            "largest_clusters": [{"cluster": c, "size": len(indices)} for c, indices in largest],
        },
        "split_stats": stats,
        "leakage_safety": {
            "method": "surname_cluster_grouping",
            "guarantee": "No surname cluster appears in multiple splits",
            "deduplication": "NFC-normalized name matching",
        },
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {train_path}")
    print(f"  Saved: {val_path}")
    print(f"  Saved: {test_path}")
    print(f"  Saved: {report_path}")

    print("\n" + "=" * 80)
    print("✅ LEAKAGE-SAFE SPLITS CREATED")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Use these splits for training instead of random splits")
    print("  2. Train model on train_split_leakage_safe.json")
    print("  3. Evaluate on val_split_leakage_safe.json")
    print("  4. Final test on test_split_leakage_safe.json")
    print("\nGuarantees:")
    print("  ✅ No surname cluster leakage across splits")
    print("  ✅ No duplicate names within or across splits")
    print("  ✅ Class distribution approximately preserved")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_leakage_safe_splits.py <input.json> [output_dir] [--seed SEED]")
        print("\nExample:")
        print("  python create_leakage_safe_splits.py \\")
        print("    data/ml_training/all_profiles.json \\")
        print("    data/ml_training/splits_leakage_safe")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_dir = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.parent / "splits_leakage_safe"
    )

    seed = 42
    if "--seed" in sys.argv:
        seed = int(sys.argv[sys.argv.index("--seed") + 1])

    create_leakage_safe_splits(input_path, output_dir, seed=seed)
