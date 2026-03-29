#!/usr/bin/env python3
"""
Phase 2 ML - Day 1: Top-K Accuracy Validation

Test hybrid classifier with top-k predictions to measure:
1. Top-1 accuracy (single best prediction)
2. Top-3 accuracy (correct answer in top 3)
3. Ambiguity distribution (how often is top-1 vs top-3 needed)

This validates the ultrathink prediction: top-3 accuracy should be 96-98%.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.hybrid_classifier import HybridRegionClassifier


def main():
    print("=" * 80)
    print("TOP-K ACCURACY VALIDATION")
    print("=" * 80)
    print()

    # Initialize hybrid classifier
    print("Initializing hybrid classifier...")
    classifier = HybridRegionClassifier()
    print()

    # Load test data
    test_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "test_suites"
        / "tier1_regional_comprehensive.json"
    )

    with open(test_file) as f:
        test_data = json.load(f)

    test_entries = test_data["test_data"]
    total = len(test_entries)

    print(f"Loaded {total} test entries")
    print()

    # Test metrics
    top1_correct = 0
    top3_correct = 0
    top1_only = []  # Correct in top-1
    top3_only = []  # Correct in top-3 but not top-1
    top3_miss = []  # Not in top-3

    by_region_stats = defaultdict(
        lambda: {"total": 0, "top1": 0, "top3": 0, "predictions": []}
    )

    # Process each entry
    print("Processing entries...")
    for i, entry in enumerate(test_entries):
        if (i + 1) % 500 == 0:
            print(f"  Processed {i+1}/{total} entries...")

        name = entry["CanonicalNative"]
        # Normalize region code: strip _synthetic suffix and convert to uppercase
        expected_region = entry["Region"].upper().replace("_SYNTHETIC", "")

        # Get top-3 predictions
        topk_results = classifier.detect_region_topk(entry, k=3)

        # Extract region codes
        top1_region = topk_results[0].region_code if topk_results else None
        top3_regions = [r.region_code for r in topk_results]

        # Check matches (prefix matching for flexibility)
        top1_match = (
            top1_region is not None
            and top1_region.split("_")[0] == expected_region.split("_")[0]
        )
        top3_match = any(
            r.split("_")[0] == expected_region.split("_")[0] for r in top3_regions
        )

        if top1_match:
            top1_correct += 1
            top3_correct += 1
            top1_only.append(entry)
        elif top3_match:
            top3_correct += 1
            top3_only.append(
                {
                    "entry": entry,
                    "predicted_top1": top1_region,
                    "predicted_top3": top3_regions,
                    "confidences": [r.confidence for r in topk_results],
                }
            )
        else:
            top3_miss.append(
                {
                    "entry": entry,
                    "predicted_top3": top3_regions,
                    "confidences": [r.confidence for r in topk_results],
                }
            )

        # Track per-region stats
        by_region_stats[expected_region]["total"] += 1
        if top1_match:
            by_region_stats[expected_region]["top1"] += 1
        if top3_match:
            by_region_stats[expected_region]["top3"] += 1
        by_region_stats[expected_region]["predictions"].append(
            {
                "name": name,
                "top1": top1_region,
                "top3": top3_regions,
                "top1_correct": top1_match,
                "top3_correct": top3_match,
            }
        )

    print(f"  Processed {total}/{total} entries")
    print()

    # Calculate accuracies
    top1_accuracy = (top1_correct / total) * 100
    top3_accuracy = (top3_correct / total) * 100

    print("=" * 80)
    print("OVERALL RESULTS")
    print("=" * 80)
    print()
    print(f"Total entries: {total}")
    print()
    print(f"Top-1 Accuracy: {top1_accuracy:.2f}% ({top1_correct}/{total})")
    print(f"Top-3 Accuracy: {top3_accuracy:.2f}% ({top3_correct}/{total})")
    print()
    print(f"Top-3 improvement: +{top3_accuracy - top1_accuracy:.2f}pp")
    print(f"Top-3 miss rate: {100 - top3_accuracy:.2f}% ({len(top3_miss)}/{total})")
    print()

    # Ambiguity analysis
    ambiguous_count = len(top3_only)
    ambiguous_pct = (ambiguous_count / total) * 100

    print("=" * 80)
    print("AMBIGUITY ANALYSIS")
    print("=" * 80)
    print()
    print(
        f"Unambiguous (top-1 correct): {len(top1_only)} ({(len(top1_only)/total)*100:.2f}%)"
    )
    print(f"Ambiguous (top-3 only): {ambiguous_count} ({ambiguous_pct:.2f}%)")
    print(
        f"Misclassified (not in top-3): {len(top3_miss)} ({(len(top3_miss)/total)*100:.2f}%)"
    )
    print()

    # Show examples of ambiguous cases
    if top3_only:
        print("AMBIGUOUS CASES (correct in top-3 but not top-1):")
        print("-" * 80)
        for case in top3_only[:10]:
            entry = case["entry"]
            print(
                f"  {entry['CanonicalNative']:30} Expected: {entry['Region']:3} "
                f"Got: {case['predicted_top1']:3} "
                f"Top-3: {', '.join(case['predicted_top3'])}"
            )
        if len(top3_only) > 10:
            print(f"  ... and {len(top3_only) - 10} more")
        print()

    # Per-region breakdown (worst performing)
    print("=" * 80)
    print("PER-REGION BREAKDOWN (worst performing first)")
    print("=" * 80)
    print()

    region_accs = []
    for region, stats in by_region_stats.items():
        if stats["total"] > 0:
            top1_acc = (stats["top1"] / stats["total"]) * 100
            top3_acc = (stats["top3"] / stats["total"]) * 100
            region_accs.append((region, stats["total"], top1_acc, top3_acc))

    region_accs.sort(key=lambda x: x[2])  # Sort by top-1 accuracy

    print(f"{'Region':<8} {'Count':>6} {'Top-1%':>8} {'Top-3%':>8} {'Δ':>6}")
    print("-" * 80)
    for region, count, top1_acc, top3_acc in region_accs[:15]:
        delta = top3_acc - top1_acc
        print(
            f"{region:<8} {count:>6} {top1_acc:>7.1f}% {top3_acc:>7.1f}% {delta:>+5.1f}%"
        )

    print()

    # Save detailed results
    output_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "analysis"
        / "topk_validation_results.json"
    )
    output_file.parent.mkdir(exist_ok=True, parents=True)

    with open(output_file, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_entries": total,
                    "top1_accuracy": top1_accuracy,
                    "top3_accuracy": top3_accuracy,
                    "improvement": top3_accuracy - top1_accuracy,
                    "ambiguous_count": ambiguous_count,
                    "ambiguous_percent": ambiguous_pct,
                },
                "by_region": {
                    region: {
                        "total": stats["total"],
                        "top1_correct": stats["top1"],
                        "top3_correct": stats["top3"],
                        "top1_accuracy": (
                            (stats["top1"] / stats["total"] * 100)
                            if stats["total"] > 0
                            else 0
                        ),
                        "top3_accuracy": (
                            (stats["top3"] / stats["total"] * 100)
                            if stats["total"] > 0
                            else 0
                        ),
                    }
                    for region, stats in by_region_stats.items()
                },
                "ambiguous_cases": top3_only[:100],  # Save first 100 for analysis
                "top3_misses": top3_miss[:50],  # Save first 50 misses
            },
            f,
            indent=2,
        )

    print(f"Detailed results saved to: {output_file}")
    print()

    # Validation against ultrathink predictions
    print("=" * 80)
    print("ULTRATHINK PREDICTION VALIDATION")
    print("=" * 80)
    print()

    ultrathink_top3_prediction = 96.21  # From ultrathink_true_accuracy.md

    if abs(top3_accuracy - ultrathink_top3_prediction) < 1.0:
        print(
            f"✅ Top-3 accuracy {top3_accuracy:.2f}% MATCHES ultrathink prediction ({ultrathink_top3_prediction}%)"
        )
    elif top3_accuracy > ultrathink_top3_prediction:
        print(
            f"🎉 Top-3 accuracy {top3_accuracy:.2f}% EXCEEDS ultrathink prediction ({ultrathink_top3_prediction}%)"
        )
    else:
        diff = ultrathink_top3_prediction - top3_accuracy
        print(
            f"⚠️  Top-3 accuracy {top3_accuracy:.2f}% is {diff:.2f}pp below prediction ({ultrathink_top3_prediction}%)"
        )

    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
