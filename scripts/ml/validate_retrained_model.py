#!/usr/bin/env python3
"""
Validate Retrained fastText Model on Validation Set

Tests the retrained model (trained on 70% real data) on the held-out
validation set (15% = 1,472 profiles).

This is the critical test to determine:
- If ≥90%: Deploy Phase 2v3, skip XGBoost
- If <90%: Proceed to XGBoost meta-classifier

Expected improvement:
- Old model (100% synthetic training): 40.67% on real data
- New model (70% real training): Target 85-90% on real data
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


def load_model():
    """Load the retrained fastText model."""
    model_path = Path("data/ml_training/regional_classifier_v3_real.bin")

    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print("   Run: python3 scripts/ml/train_fasttext_on_real_data.py")
        sys.exit(1)

    return fasttext.load_model(str(model_path))


def validate_on_val_set(model, profiles):
    """
    Validate model on validation set.

    Args:
        model: Trained fastText model
        profiles: Validation profiles with ground truth regions

    Returns:
        dict with accuracy metrics
    """
    results = {
        "total": len(profiles),
        "correct": 0,
        "failures": [],
        "regional_stats": defaultdict(lambda: {"total": 0, "correct": 0}),
        "confidence_stats": [],
    }

    print(
        f"Validating on {len(profiles)} real mathematician names from validation set..."
    )
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
                    "country": profile.get("country_code", "Unknown"),
                }
            )

        # Track confidence
        results["confidence_stats"].append(
            {"confidence": confidence, "correct": is_correct}
        )

        # Progress
        if (i + 1) % 100 == 0 or (i + 1) == len(profiles):
            acc = results["correct"] / (i + 1) * 100
            print(f"  Progress: {i+1}/{len(profiles)} ({acc:.2f}% accurate)")

    # Calculate accuracy
    results["accuracy"] = (
        results["correct"] / results["total"] * 100 if results["total"] > 0 else 0
    )

    return results


def print_results(results):
    """Print detailed validation results."""
    print(f"\n{'='*80}")
    print("VALIDATION RESULTS (Held-Out Validation Set)")
    print(f"{'='*80}\n")

    print(
        f"Overall Accuracy: {results['correct']}/{results['total']} = {results['accuracy']:.2f}%"
    )
    print()

    # Regional breakdown
    print("Regional Performance:")
    sorted_regions = sorted(
        results["regional_stats"].items(), key=lambda x: x[1]["total"], reverse=True
    )

    for region, stats in sorted_regions:
        acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✅" if acc >= 90 else "⚠️" if acc >= 70 else "❌"
        print(f"  {status} {region}: {stats['correct']}/{stats['total']} = {acc:.1f}%")

    # Confidence analysis
    if results["confidence_stats"]:
        avg_conf = sum(s["confidence"] for s in results["confidence_stats"]) / len(
            results["confidence_stats"]
        )
        correct_conf = [
            s["confidence"] for s in results["confidence_stats"] if s["correct"]
        ]
        incorrect_conf = [
            s["confidence"] for s in results["confidence_stats"] if not s["correct"]
        ]

        print()
        print("Confidence Analysis:")
        print(f"  Average: {avg_conf:.3f}")
        if correct_conf:
            print(f"  Correct predictions: {sum(correct_conf)/len(correct_conf):.3f}")
        if incorrect_conf:
            print(
                f"  Incorrect predictions: {sum(incorrect_conf)/len(incorrect_conf):.3f}"
            )

    # Top failures
    if results["failures"]:
        print()
        print(f"Top 10 Failures (of {len(results['failures'])} total):")
        for i, failure in enumerate(results["failures"][:10], 1):
            print(f"  {i}. {failure['name']}")
            print(f"     Expected: {failure['expected']}, Got: {failure['detected']}")
            print(
                f"     Confidence: {failure['confidence']:.3f}, Country: {failure['country']}"
            )


def print_verdict(old_accuracy, new_accuracy):
    """Print verdict and next steps."""
    print(f"\n{'='*80}")
    print("VERDICT")
    print(f"{'='*80}\n")

    print(f"Old model (100% synthetic training):")
    print(f"  Real-world accuracy: {old_accuracy:.2f}%")
    print()
    print(f"New model (70% real training):")
    print(f"  Validation accuracy: {new_accuracy:.2f}%")
    print()
    print(f"Improvement: {new_accuracy - old_accuracy:+.2f} percentage points")
    print()

    if new_accuracy >= 90:
        print("✅ EXCELLENT: ≥90% accuracy on real data!")
        print("   Decision: DEPLOY Phase 2v3")
        print("   Next step: Test on held-out test set for final validation")
        print("   XGBoost: NOT NEEDED")
    elif new_accuracy >= 85:
        print("✅ GOOD: 85-90% accuracy on real data")
        print("   Decision: Phase 2v3 is production-ready")
        print("   Optional: Build XGBoost for marginal improvement (85% → 92%)")
    elif new_accuracy >= 70:
        print("⚠️  ACCEPTABLE: 70-85% accuracy")
        print("   Decision: Proceed to XGBoost meta-classifier")
        print("   Expected improvement: 70-85% → 90-95%")
    else:
        print("❌ NEEDS IMPROVEMENT: <70% accuracy")
        print("   Decision: Deep dive on failure patterns")
        print("   May need enhanced Phase 1 rules before XGBoost")

    print()


def main():
    """Validate retrained model on validation set."""
    print("=" * 80)
    print("VALIDATION: RETRAINED MODEL ON REAL MATHEMATICIAN DATA")
    print("=" * 80)
    print()

    # Load validation data
    print("Loading validation split...")
    profiles = load_validation_split()
    print(f"✅ Loaded {len(profiles)} validation profiles\n")

    # Load model
    print("Loading retrained model...")
    model = load_model()
    print(f"✅ Model loaded\n")

    # Validate
    results = validate_on_val_set(model, profiles)

    # Print results
    print_results(results)

    # Verdict (compare to old 40.67%)
    print_verdict(old_accuracy=40.67, new_accuracy=results["accuracy"])

    # Return 0 if ≥85%, else 1
    return 0 if results["accuracy"] >= 85 else 1


if __name__ == "__main__":
    sys.exit(main())
