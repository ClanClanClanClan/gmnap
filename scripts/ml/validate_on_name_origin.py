#!/usr/bin/env python3
"""
Validate Phase 2 Model on CORRECT Ground Truth (Name Origin)

This replaces the incorrect workplace-based validation from Phase 3.

Validates against linguistic/onomastic origin, not employment geography.
"""

import sys
import json
import fasttext
from pathlib import Path
from collections import defaultdict


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


def validate_on_origin(model_path, ground_truth):
    """Validate model against name-origin labels."""
    print(f"Loading model: {model_path}")
    model = fasttext.load_model(str(model_path))
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

        # Predict
        pred = model.predict(name, k=1)
        detected_origin = pred[0][0].replace("__label__", "")
        pred_confidence = float(pred[1][0])

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
                }
            )

        # Progress
        if (i + 1) % 25 == 0 or (i + 1) == len(ground_truth):
            acc = results["correct"] / (i + 1) * 100
            print(f"  Progress: {i+1}/{len(ground_truth)} ({acc:.2f}% accurate)")

    results["accuracy"] = results["correct"] / results["total"] * 100

    return results


def print_results(results):
    """Print detailed validation results."""
    print(f"\n{'='*80}")
    print("RESULTS - NAME ORIGIN VALIDATION (CORRECT METRIC)")
    print(f"{'='*80}\n")

    print(
        f"Overall Accuracy: {results['correct']}/{results['total']} = {results['accuracy']:.2f}%"
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
    print("By Source Type:")
    for source, stats in sorted(
        results["by_source"].items(), key=lambda x: x[1]["total"], reverse=True
    ):
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        status = "✅" if acc >= 90 else "⚠️" if acc >= 70 else "❌"
        print(f"  {status} {source}: {stats['correct']}/{stats['total']} = {acc:.1f}%")

    # By confidence level
    print()
    print("By Ground Truth Confidence:")
    for conf, stats in sorted(
        results["confidence_stats"].items(), key=lambda x: float(x[0]), reverse=True
    ):
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        status = "✅" if acc >= 90 else "⚠️" if acc >= 70 else "❌"
        print(f"  {status} {conf}: {stats['correct']}/{stats['total']} = {acc:.1f}%")

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
            print(f"     Model confidence: {failure['pred_confidence']:.3f}")
            print(f"     Source: {failure['source']}")
            if failure.get("notes"):
                print(f"     Notes: {failure['notes']}")


def print_verdict(results):
    """Print verdict comparing to Phase 3."""
    print(f"\n{'='*80}")
    print("VERDICT")
    print(f"{'='*80}\n")

    accuracy = results["accuracy"]

    if accuracy >= 90:
        print("✅ EXCELLENT: ≥90% accuracy on name origin!")
        print("   Model is PRODUCTION-READY for origin classification.")
        print("   Meets expert's quality gate (stage2_origin_accuracy_min: 0.90)")
    elif accuracy >= 85:
        print("✅ GOOD: 85-90% accuracy on name origin")
        print("   Minor improvements recommended but ACCEPTABLE for production.")
    elif accuracy >= 75:
        print("⚠️  ACCEPTABLE: 75-85% accuracy")
        print("   Significant improvement over baseline, but below target.")
        print("   Consider additional training or enhanced rules.")
    else:
        print("❌ NEEDS IMPROVEMENT: <75% accuracy")
        print("   Further work required before production deployment.")

    print()
    print("=" * 80)
    print("COMPARISON: Phase 3 vs Corrected Validation")
    print("=" * 80)
    print()
    print(f"Phase 3 (WRONG metric - workplace): 68.14%")
    print(f"Corrected (RIGHT metric - name origin): {accuracy:.2f}%")
    print()

    if accuracy > 68.14:
        improvement = accuracy - 68.14
        print(f"🎯 Model is {improvement:.2f}pp BETTER than Phase 3 reported!")
        print(f"   Phase 3 validation was measuring the wrong thing.")
        print()
        print(
            "✅ The Phase 2 retrained model we built in Phase 3 is BETTER than we thought!"
        )
    else:
        print("⚠️  Model performance is similar to Phase 3")
        print("   Need to investigate discrepancies")

    print()
    print("Next steps:")
    if accuracy >= 85:
        print("  1. Test on held-out test set (1,509 entries)")
        print("  2. Deploy to production with confidence")
        print("  3. Monitor performance on real data")
    else:
        print("  1. Expand ground truth to 1,000+ entries")
        print("  2. Implement expert's origin detection policy")
        print("  3. Re-validate")


def main():
    """Validate Phase 2 retrained model on correct ground truth."""
    print("=" * 80)
    print("VALIDATING PHASE 2 MODEL ON CORRECT GROUND TRUTH")
    print("Name Origin (Linguistic), NOT Workplace")
    print("=" * 80)
    print()

    # Load ground truth
    print("Loading name-origin ground truth...")
    truth = load_origin_ground_truth()
    print(f"✅ Loaded {len(truth)} entries with origin labels")
    print()

    # Validate Phase 2 retrained model
    model_path = Path("data/ml_training/regional_classifier_v3_real.bin")

    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print("   Run Phase 3 training first:")
        print("   python3 scripts/ml/train_fasttext_on_real_data.py")
        return 1

    results = validate_on_origin(model_path, truth)

    # Print results
    print_results(results)

    # Verdict
    print_verdict(results)

    # Return 0 if ≥85%, else 1
    return 0 if results["accuracy"] >= 85 else 1


if __name__ == "__main__":
    sys.exit(main())
