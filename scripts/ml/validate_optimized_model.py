#!/usr/bin/env python3
"""
Validate Optimized fastText Model (v4) on Validation Set

Compares:
- v3 (original): 68.14% validation accuracy
- v4 (optimized): Target 85-90% validation accuracy
"""

import sys
import json
import fasttext
from pathlib import Path
from collections import defaultdict


def load_validation_split():
    """Load the validation split (1,472 profiles)."""
    val_path = Path("data/ml_training/val_split.json")

    with open(val_path) as f:
        data = json.load(f)

    return data["profiles"]


def load_model(model_path):
    """Load a fastText model."""
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        sys.exit(1)

    return fasttext.load_model(str(model_path))


def validate_model(model, profiles, model_name):
    """Validate model on profiles."""
    results = {
        "total": len(profiles),
        "correct": 0,
        "failures": [],
        "regional_stats": defaultdict(lambda: {"total": 0, "correct": 0}),
    }

    print(f"Validating {model_name} on {len(profiles)} profiles...")
    print()

    for i, profile in enumerate(profiles):
        name = profile["name"]
        expected_region = profile["region"]

        # Predict
        pred = model.predict(name, k=1)
        detected_region = pred[0][0].replace("__label__", "")
        confidence = float(pred[1][0])

        # Track regional performance
        results["regional_stats"][expected_region]["total"] += 1

        # Check correctness
        is_correct = expected_region == detected_region

        if is_correct:
            results["correct"] += 1
            results["regional_stats"][expected_region]["correct"] += 1
        else:
            results["failures"].append(
                {
                    "name": name,
                    "expected": expected_region,
                    "detected": detected_region,
                    "confidence": confidence,
                }
            )

        # Progress
        if (i + 1) % 100 == 0 or (i + 1) == len(profiles):
            acc = results["correct"] / (i + 1) * 100
            print(f"  Progress: {i+1}/{len(profiles)} ({acc:.2f}% accurate)")

    results["accuracy"] = results["correct"] / results["total"] * 100 if results["total"] > 0 else 0

    return results


def print_comparison(v3_results, v4_results):
    """Print side-by-side comparison."""
    print(f"\n{'='*80}")
    print("VALIDATION COMPARISON: v3 vs v4 OPTIMIZED")
    print(f"{'='*80}\n")

    print(f"Overall Accuracy:")
    print(f"  v3 (original):  {v3_results['accuracy']:.2f}%")
    print(f"  v4 (optimized): {v4_results['accuracy']:.2f}%")
    improvement = v4_results["accuracy"] - v3_results["accuracy"]
    print(f"  Improvement:    {improvement:+.2f}pp")
    print()

    # Regional comparison
    print("Regional Performance Comparison:")
    print(f"{'Region':<8} {'v3':>8} {'v4':>8} {'Δ':>8} {'Status':<10}")
    print("-" * 48)

    all_regions = sorted(
        set(v3_results["regional_stats"].keys()) | set(v4_results["regional_stats"].keys())
    )

    for region in all_regions:
        v3_stats = v3_results["regional_stats"].get(region, {"total": 0, "correct": 0})
        v4_stats = v4_results["regional_stats"].get(region, {"total": 0, "correct": 0})

        if v3_stats["total"] == 0:
            continue

        v3_acc = (v3_stats["correct"] / v3_stats["total"] * 100) if v3_stats["total"] > 0 else 0
        v4_acc = (v4_stats["correct"] / v4_stats["total"] * 100) if v4_stats["total"] > 0 else 0
        delta = v4_acc - v3_acc

        if delta >= 10:
            status = "✅ Much better"
        elif delta >= 5:
            status = "✅ Better"
        elif delta >= -5:
            status = "→ Similar"
        else:
            status = "❌ Worse"

        print(f"{region:<8} {v3_acc:7.1f}% {v4_acc:7.1f}% {delta:+7.1f}pp {status:<10}")

    print()

    # Key metrics
    print("Key Metrics:")
    print(f"  v3: {v3_results['correct']}/{v3_results['total']} correct")
    print(f"  v4: {v4_results['correct']}/{v4_results['total']} correct")
    print(f"  Improvement: +{v4_results['correct'] - v3_results['correct']} correct predictions")
    print()

    # Verdict
    print(f"{'='*80}")
    print("VERDICT")
    print(f"{'='*80}\n")

    if v4_results["accuracy"] >= 90:
        print("✅ EXCELLENT: v4 achieves ≥90% validation accuracy!")
        print("   Decision: DEPLOY v4 model")
        print("   Next: Test on held-out test set")
    elif v4_results["accuracy"] >= 85:
        print("✅ GOOD: v4 achieves 85-90% validation accuracy")
        print("   Decision: v4 is production-ready")
        print("   Optional: XGBoost for further improvement")
    elif v4_results["accuracy"] > v3_results["accuracy"]:
        print(f"⚠️  IMPROVED: v4 is better than v3 (+{improvement:.1f}pp)")
        print(f"   But still below 85% target ({v4_results['accuracy']:.1f}%)")
        print("   Decision: Use v4, consider additional enhancements")
    else:
        print("❌ NO IMPROVEMENT: v4 performs similar to or worse than v3")
        print("   Decision: Stick with v3, investigate other approaches")

    print()


def main():
    """Compare v3 and v4 models."""
    print("=" * 80)
    print("VALIDATION: v3 (Original) vs v4 (Optimized)")
    print("=" * 80)
    print()

    # Load validation data
    print("Loading validation split...")
    profiles = load_validation_split()
    print(f"✅ Loaded {len(profiles)} validation profiles\n")

    # Load models
    v3_path = Path("data/ml_training/regional_classifier_v3_real.bin")
    v4_path = Path("data/ml_training/regional_classifier_v4_optimized.bin")

    print("Loading models...")
    v3_model = load_model(v3_path)
    v4_model = load_model(v4_path)
    print(f"✅ Models loaded\n")

    print("=" * 80)
    print()

    # Validate v3
    v3_results = validate_model(v3_model, profiles, "v3 (original)")
    print()

    # Validate v4
    v4_results = validate_model(v4_model, profiles, "v4 (optimized)")

    # Print comparison
    print_comparison(v3_results, v4_results)

    # Return 0 if v4 is better, else 1
    return 0 if v4_results["accuracy"] > v3_results["accuracy"] else 1


if __name__ == "__main__":
    sys.exit(main())
