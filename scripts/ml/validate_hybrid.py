#!/usr/bin/env python3
"""
Validate Hybrid Classifier on Tier 1 Holdout Dataset

Compares:
- Phase 1 (rule-based) - 91.36% baseline
- Phase 2 (ML fastText) - 91.91% baseline
- Hybrid (Phase 1 + Phase 2) - Expected: 94-95%
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.hybrid_classifier import HybridRegionClassifier
from src.regions.manager_optimized import RegionManager
import fasttext


def validate_phase1(tier1_data):
    """Validate Phase 1 (rule-based) on Tier 1."""
    print("Validating Phase 1 (Rule-Based)...")

    manager = RegionManager()
    correct = 0
    total = 0
    by_region = defaultdict(lambda: {"correct": 0, "total": 0})

    for entry in tier1_data:
        expected = entry["Region"].split("_")[0].upper()
        result = manager.detect_region(entry)
        detected = result.region_code

        total += 1
        by_region[expected]["total"] += 1

        if detected == expected:
            correct += 1
            by_region[expected]["correct"] += 1

    accuracy = (correct / total) * 100 if total > 0 else 0
    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "by_region": dict(by_region),
    }


def validate_phase2(tier1_data, model_path):
    """Validate Phase 2 (ML) on Tier 1."""
    print("Validating Phase 2 (ML fastText)...")

    model = fasttext.load_model(model_path)
    correct = 0
    total = 0
    by_region = defaultdict(lambda: {"correct": 0, "total": 0})

    for entry in tier1_data:
        name = entry["CanonicalNative"]
        expected = entry["Region"].split("_")[0].upper()

        try:
            pred = model.predict(name, k=1)
            detected = pred[0][0].replace("__label__", "")

            total += 1
            by_region[expected]["total"] += 1

            if detected == expected:
                correct += 1
                by_region[expected]["correct"] += 1
        except:
            continue

    accuracy = (correct / total) * 100 if total > 0 else 0
    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "by_region": dict(by_region),
    }


def validate_hybrid(tier1_data, model_path):
    """Validate Hybrid (Phase 1 + Phase 2) on Tier 1."""
    print("Validating Hybrid (Phase 1 + Phase 2)...")

    classifier = HybridRegionClassifier(fasttext_model_path=model_path)
    correct = 0
    total = 0
    by_region = defaultdict(lambda: {"correct": 0, "total": 0})
    method_counts = defaultdict(int)
    failures = []

    for entry in tier1_data:
        expected = entry["Region"].split("_")[0].upper()
        result = classifier.detect_region(entry)
        detected = result.region_code

        total += 1
        by_region[expected]["total"] += 1
        method_counts[result.detection_method] += 1

        if detected == expected:
            correct += 1
            by_region[expected]["correct"] += 1
        else:
            if len(failures) < 50:
                failures.append(
                    {
                        "name": entry["CanonicalNative"],
                        "expected": expected,
                        "detected": detected,
                        "confidence": result.confidence,
                        "method": result.detection_method,
                    }
                )

    accuracy = (correct / total) * 100 if total > 0 else 0
    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "by_region": dict(by_region),
        "method_counts": dict(method_counts),
        "failures": failures,
    }


def main():
    print("=" * 80)
    print("HYBRID CLASSIFIER VALIDATION")
    print("=" * 80)
    print()

    # Load Tier 1 dataset
    tier1_file = Path("data/test_suites/tier1_regional_comprehensive.json")
    if not tier1_file.exists():
        print(f"❌ Tier 1 dataset not found: {tier1_file}")
        return

    with open(tier1_file) as f:
        tier1_json = json.load(f)
        tier1_data = tier1_json["test_data"]

    print(f"Loaded Tier 1 dataset: {len(tier1_data):,} names")
    print()

    # Model path
    model_path = "data/ml_training/regional_classifier.bin"

    # Run validations
    phase1_results = validate_phase1(tier1_data)
    print(f"  ✅ Phase 1: {phase1_results['accuracy']:.2f}%")
    print()

    phase2_results = validate_phase2(tier1_data, model_path)
    print(f"  ✅ Phase 2: {phase2_results['accuracy']:.2f}%")
    print()

    hybrid_results = validate_hybrid(tier1_data, model_path)
    print(f"  ✅ Hybrid:  {hybrid_results['accuracy']:.2f}%")
    print()

    # Overall Comparison
    print("=" * 80)
    print("OVERALL COMPARISON")
    print("=" * 80)
    print()

    print(
        f"Phase 1 (Rules):     {phase1_results['accuracy']:6.2f}% ({phase1_results['correct']:,}/{phase1_results['total']:,})"
    )
    print(
        f"Phase 2 (ML):        {phase2_results['accuracy']:6.2f}% ({phase2_results['correct']:,}/{phase2_results['total']:,})"
    )
    print(
        f"Hybrid (Combined):   {hybrid_results['accuracy']:6.2f}% ({hybrid_results['correct']:,}/{hybrid_results['total']:,})"
    )
    print()

    improvement_vs_p1 = hybrid_results["accuracy"] - phase1_results["accuracy"]
    improvement_vs_p2 = hybrid_results["accuracy"] - phase2_results["accuracy"]

    print(f"Improvement vs Phase 1: {improvement_vs_p1:+.2f} percentage points")
    print(f"Improvement vs Phase 2: {improvement_vs_p2:+.2f} percentage points")
    print()

    # Method Distribution
    print("Hybrid Method Distribution:")
    total_predictions = sum(hybrid_results["method_counts"].values())
    for method, count in sorted(hybrid_results["method_counts"].items()):
        pct = (count / total_predictions) * 100
        print(f"  {method:25} {count:5,} ({pct:5.1f}%)")
    print()

    # Regional Comparison
    print("=" * 80)
    print("PER-REGION COMPARISON")
    print("=" * 80)
    print()

    all_regions = sorted(
        set(
            list(phase1_results["by_region"].keys())
            + list(phase2_results["by_region"].keys())
            + list(hybrid_results["by_region"].keys())
        )
    )

    # Categorize improvements
    hybrid_wins = []
    phase1_wins = []
    phase2_wins = []

    for region in all_regions:
        p1_stats = phase1_results["by_region"].get(region, {"correct": 0, "total": 0})
        p2_stats = phase2_results["by_region"].get(region, {"correct": 0, "total": 0})
        h_stats = hybrid_results["by_region"].get(region, {"correct": 0, "total": 0})

        p1_acc = (
            (p1_stats["correct"] / p1_stats["total"] * 100)
            if p1_stats["total"] > 0
            else 0
        )
        p2_acc = (
            (p2_stats["correct"] / p2_stats["total"] * 100)
            if p2_stats["total"] > 0
            else 0
        )
        h_acc = (
            (h_stats["correct"] / h_stats["total"] * 100) if h_stats["total"] > 0 else 0
        )

        best = max(p1_acc, p2_acc)

        if h_acc > best:
            hybrid_wins.append((region, p1_acc, p2_acc, h_acc))
        elif h_acc < p1_acc and h_acc < p2_acc:
            # Hybrid worse than both
            print(
                f"  ⚠️  {region}: Hybrid ({h_acc:.1f}%) worse than P1 ({p1_acc:.1f}%) and P2 ({p2_acc:.1f}%)"
            )
        elif abs(h_acc - best) < 0.1:
            # Hybrid matches best
            if p1_acc >= p2_acc:
                phase1_wins.append((region, p1_acc, p2_acc, h_acc))
            else:
                phase2_wins.append((region, p1_acc, p2_acc, h_acc))

    print(f"HYBRID BEATS BOTH ({len(hybrid_wins)} regions):")
    for region, p1, p2, h in sorted(hybrid_wins, key=lambda x: -x[3]):
        best_prev = max(p1, p2)
        improvement = h - best_prev
        print(
            f"  🎯 {region}: {h:5.1f}% (P1: {p1:5.1f}%, P2: {p2:5.1f}%, +{improvement:.1f}pp)"
        )
    print()

    print(f"HYBRID MATCHES PHASE 1 ({len(phase1_wins)} regions):")
    for region, p1, p2, h in sorted(phase1_wins, key=lambda x: -x[3])[:10]:
        print(f"  ✅ {region}: {h:5.1f}% (P1: {p1:5.1f}%, P2: {p2:5.1f}%)")
    if len(phase1_wins) > 10:
        print(f"  ... and {len(phase1_wins)-10} more")
    print()

    print(f"HYBRID MATCHES PHASE 2 ({len(phase2_wins)} regions):")
    for region, p1, p2, h in sorted(phase2_wins, key=lambda x: -x[3])[:10]:
        print(f"  ✅ {region}: {h:5.1f}% (P1: {p1:5.1f}%, P2: {p2:5.1f}%)")
    if len(phase2_wins) > 10:
        print(f"  ... and {len(phase2_wins)-10} more")
    print()

    # Sample Failures
    print("=" * 80)
    print("SAMPLE HYBRID FAILURES (First 20)")
    print("=" * 80)
    print()

    for i, failure in enumerate(hybrid_results["failures"][:20], 1):
        print(
            f"{i:2}. {failure['name']:30} expected={failure['expected']:<3} detected={failure['detected']:<3} "
            f"conf={failure['confidence']:.3f} [{failure['method']}]"
        )

    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print()

    # Final summary
    if hybrid_results["accuracy"] >= 94.0:
        print("🎉 SUCCESS: Hybrid achieves target ≥94% accuracy!")
    elif hybrid_results["accuracy"] >= 93.0:
        print("✅ GOOD: Hybrid achieves ≥93% accuracy (close to target)")
    else:
        print(
            f"⚠️  BELOW TARGET: Hybrid at {hybrid_results['accuracy']:.2f}% (target: 94%)"
        )

    print()


if __name__ == "__main__":
    main()
