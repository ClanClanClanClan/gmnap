#!/usr/bin/env python3
"""
Validate Phase 3 Fixes on Correct Ground Truth (Name Origin)

Tests the complete detection pipeline including:
1. Hybrid name detection (CJK surname + Anglo given)
2. Affiliation tie-breaking for ambiguous families

This validates the RegionManager with Phase 3 fixes, NOT just the fastText model.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.manager_optimized import RegionManager


def load_origin_ground_truth():
    """Load curated name-origin ground truth."""
    truth_path = Path("data/ml_training/origin_truth.jsonl")

    if not truth_path.exists():
        print(f"❌ Ground truth not found: {truth_path}")
        print("   Run: python3 scripts/ml/build_name_origin_ground_truth.py")
        sys.exit(1)

    truth = []
    with open(truth_path, encoding="utf-8") as f:
        for line in f:
            truth.append(json.loads(line))

    return truth


def validate_with_region_manager(ground_truth):
    """Validate using complete RegionManager pipeline (includes Phase 3 fixes)."""
    print(f"Initializing RegionManager with Phase 3 fixes...")
    manager = RegionManager()
    print()

    results = {
        "total": len(ground_truth),
        "correct": 0,
        "regional_stats": defaultdict(lambda: {"total": 0, "correct": 0}),
        "confidence_stats": defaultdict(lambda: {"total": 0, "correct": 0}),
        "failures": [],
        "by_source": defaultdict(lambda: {"total": 0, "correct": 0}),
    }

    print(f"Validating on {len(ground_truth)} entries...")
    print()

    for i, entry in enumerate(ground_truth):
        name = entry["name"]
        expected_origin = entry["origin"]
        source = entry.get("source", "unknown")
        entry_confidence = entry.get("confidence", 0.0)
        affiliation = entry.get("affiliation")

        # Create entry dict for RegionManager
        manager_entry = {"CanonicalNative": name, "CanonicalLatin": name}

        # Add affiliation if present (for tie-breaking)
        if affiliation:
            manager_entry["Affiliations"] = [{"country": affiliation}]

        # Detect using complete pipeline (includes hybrid detection + affiliation tie-breaking)
        result = manager.detect_region(manager_entry)
        detected_origin = result.region_code
        pred_confidence = result.confidence

        # Track
        results["regional_stats"][expected_origin]["total"] += 1
        results["by_source"][source]["total"] += 1

        # Confidence buckets
        conf_bucket = f"{entry_confidence:.1f}"
        results["confidence_stats"][conf_bucket]["total"] += 1

        # Check
        is_correct = expected_origin == detected_origin

        if is_correct:
            results["correct"] += 1
            results["regional_stats"][expected_origin]["correct"] += 1
            results["by_source"][source]["correct"] += 1
            results["confidence_stats"][conf_bucket]["correct"] += 1
        else:
            results["failures"].append(
                {
                    "name": name,
                    "native": entry.get("native"),
                    "expected_origin": expected_origin,
                    "detected_origin": detected_origin,
                    "pred_confidence": pred_confidence,
                    "entry_confidence": entry_confidence,
                    "source": source,
                    "notes": entry.get("notes", ""),
                    "detection_method": result.detection_method,
                    "metadata": result.metadata,
                }
            )

        # Progress
        if (i + 1) % 25 == 0 or (i + 1) == len(ground_truth):
            acc = results["correct"] / (i + 1) * 100
            print(f"  Progress: {i+1}/{len(ground_truth)} ({acc:.2f}% accurate)")

    results["accuracy"] = results["correct"] / results["total"] * 100

    return results


def print_results(results, baseline_acc=80.72):
    """Print detailed validation results."""
    print(f"\n{'='*80}")
    print("RESULTS - PHASE 3 FIXES VALIDATION (WITH REGIONMANAGER)")
    print(f"{'='*80}\n")

    print(
        f"Overall Accuracy: {results['correct']}/{results['total']} = {results['accuracy']:.2f}%"
    )

    if results["accuracy"] > baseline_acc:
        improvement = results["accuracy"] - baseline_acc
        print(
            f"🎯 IMPROVEMENT: +{improvement:.2f}pp over Phase 2 baseline ({baseline_acc}%)"
        )
    else:
        regression = baseline_acc - results["accuracy"]
        print(
            f"⚠️  REGRESSION: -{regression:.2f}pp vs Phase 2 baseline ({baseline_acc}%)"
        )

    print()

    # Regional breakdown
    print("Regional Performance:")
    for region, stats in sorted(
        results["regional_stats"].items(), key=lambda x: x[1]["total"], reverse=True
    ):
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        status = "✅" if acc >= 90 else "⚠️" if acc >= 70 else "❌"
        print(f"  {status} {region}: {stats['correct']}/{stats['total']} = {acc:.1f}%")

    # By source type
    print()
    print("By Source Type (CRITICAL FIXES):")
    for source, stats in sorted(
        results["by_source"].items(), key=lambda x: x[1]["total"], reverse=True
    ):
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        status = "✅" if acc >= 90 else "⚠️" if acc >= 70 else "❌"

        # Highlight critical fixes
        marker = ""
        if source == "hybrid_surname_primary":
            marker = " 🔧 FIX 1: Hybrid names"
        elif source == "spanish_latam_affiliation":
            marker = " 🔧 FIX 2: G1 tie-break"

        print(
            f"  {status} {source}: {stats['correct']}/{stats['total']} = {acc:.1f}%{marker}"
        )

    # Failures
    if results["failures"]:
        print()
        print(f"Top 10 Failures (of {len(results['failures'])} total):")
        for i, failure in enumerate(results["failures"][:10], 1):
            print(f"\n  {i}. {failure['name']}")
            if failure.get("native"):
                print(f"     Native: {failure['native']}")
            print(
                f"     Expected: {failure['expected_origin']}, Got: {failure['detected_origin']}"
            )
            print(f"     Confidence: {failure['pred_confidence']:.3f}")
            print(f"     Method: {failure['detection_method']}")
            print(f"     Source: {failure['source']}")
            if failure.get("notes"):
                print(f"     Notes: {failure['notes']}")


def main():
    """Validate Phase 3 fixes using complete RegionManager pipeline."""
    print("=" * 80)
    print("VALIDATING PHASE 3 FIXES WITH REGIONMANAGER")
    print("Hybrid Detection + Affiliation Tie-Breaking")
    print("=" * 80)
    print()

    # Load ground truth
    print("Loading name-origin ground truth...")
    truth = load_origin_ground_truth()
    print(f"✅ Loaded {len(truth)} entries with origin labels")
    print()

    # Validate with RegionManager (includes Phase 3 fixes)
    results = validate_with_region_manager(truth)

    # Print results
    print_results(results, baseline_acc=80.72)

    # Verdict
    print(f"\n{'='*80}")
    print("VERDICT")
    print(f"{'='*80}\n")

    accuracy = results["accuracy"]
    baseline = 80.72

    if accuracy >= baseline + 5:
        print(f"✅ SIGNIFICANT IMPROVEMENT: {accuracy:.2f}% (baseline: {baseline}%)")
        print(f"   Phase 3 fixes working as expected!")
    elif accuracy >= baseline + 2:
        print(f"✅ MODERATE IMPROVEMENT: {accuracy:.2f}% (baseline: {baseline}%)")
        print(f"   Phase 3 fixes showing positive impact")
    elif accuracy >= baseline - 2:
        print(f"⚠️  MARGINAL CHANGE: {accuracy:.2f}% (baseline: {baseline}%)")
        print(f"   Phase 3 fixes may need adjustment")
    else:
        print(f"❌ REGRESSION: {accuracy:.2f}% (baseline: {baseline}%)")
        print(f"   Phase 3 fixes need debugging")

    return 0 if accuracy >= baseline else 1


if __name__ == "__main__":
    sys.exit(main())
