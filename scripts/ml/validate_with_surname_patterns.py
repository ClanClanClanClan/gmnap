#!/usr/bin/env python3
"""
Phase 3.2 Validation: Test Surname Pattern Enhancement

Validates the impact of adding surname pattern detection to Phase 1.
Expected improvement: 71% → 85-90% on real data.

Test Strategy:
1. Baseline: Phase 1 + Phase 2 without surname patterns
2. Enhanced: Phase 1 + Phase 2 + Surname patterns
3. Measure improvement on A1, A2, G1 (Latin-script regions)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.hybrid_classifier import HybridRegionClassifier, DetectionResult
from src.regions.surname_patterns import get_surname_detector


def validate_with_surname_enhancement(test_profiles, use_patterns=True):
    """
    Validate detection accuracy with optional surname pattern enhancement.

    Args:
        test_profiles: List of {name, region} dicts
        use_patterns: Whether to use surname pattern detection

    Returns:
        Dictionary with accuracy statistics
    """
    classifier = HybridRegionClassifier()
    surname_detector = get_surname_detector() if use_patterns else None

    correct = 0
    total = 0
    region_correct = defaultdict(int)
    region_total = defaultdict(int)
    region_improvements = defaultdict(list)

    for profile in test_profiles:
        name = profile["name"]
        true_region = profile["region"].split("_")[0].upper()

        # Get Phase 1 + Phase 2 prediction
        entry = {"CanonicalLatin": name}
        phase1_result = classifier.phase1.detect_region(entry)
        phase2_results = []

        if classifier.use_ml and classifier.phase2:
            try:
                pred = classifier.phase2.predict(name, k=3)
                for j in range(min(3, len(pred[0]))):
                    ml_region = pred[0][j].replace("__label__", "")
                    ml_conf = float(pred[1][j])
                    phase2_results.append(
                        DetectionResult(
                            region_code=ml_region,
                            confidence=ml_conf,
                            detection_method="phase2",
                            metadata={},
                        )
                    )
            except:
                pass

        # Default prediction (Phase 1 or Phase 2)
        if phase1_result.region_code in classifier.PHASE1_PREFERRED:
            predicted_region = phase1_result.region_code.split("_")[0].upper()
            base_confidence = phase1_result.confidence
        elif phase2_results:
            predicted_region = phase2_results[0].region_code.split("_")[0].upper()
            base_confidence = phase2_results[0].confidence
        else:
            predicted_region = phase1_result.region_code.split("_")[0].upper()
            base_confidence = phase1_result.confidence

        # Enhanced: Apply surname patterns if enabled
        if use_patterns and surname_detector:
            surname_match = surname_detector.get_best_match(name)
            if surname_match:
                pattern_region, pattern_conf, _ = surname_match

                # Override if surname pattern is high confidence
                # and contradicts current prediction
                if pattern_conf >= 0.85 and pattern_region != predicted_region:
                    # Surname pattern takes precedence
                    predicted_region = pattern_region

        # Check if correct
        is_correct = predicted_region == true_region
        region_total[true_region] += 1
        if is_correct:
            region_correct[true_region] += 1
            correct += 1

        total += 1

    # Calculate accuracy
    overall_accuracy = correct / total if total > 0 else 0

    # Per-region accuracy
    region_accuracy = {}
    for region in sorted(region_total.keys()):
        if region_total[region] > 0:
            acc = region_correct[region] / region_total[region]
            region_accuracy[region] = {
                "accuracy": acc,
                "correct": region_correct[region],
                "total": region_total[region],
            }

    return {
        "overall_accuracy": overall_accuracy,
        "correct": correct,
        "total": total,
        "region_accuracy": region_accuracy,
    }


def main():
    print("=" * 80)
    print("Phase 3.2: Surname Pattern Enhancement Validation")
    print("=" * 80)
    print()

    # Load test data
    test_file = Path(__file__).parent.parent.parent / "data" / "ml_training" / "test_split.json"
    print(f"Loading test data from: {test_file}")

    with open(test_file) as f:
        test_data = json.load(f)

    test_profiles = test_data.get("profiles", [])
    print(f"✅ Loaded {len(test_profiles)} test profiles")
    print()

    # Validate BASELINE (without surname patterns)
    print("=" * 80)
    print("BASELINE: Phase 1 + Phase 2 (No Surname Patterns)")
    print("=" * 80)
    print()

    baseline_results = validate_with_surname_enhancement(test_profiles, use_patterns=False)

    print(f"Overall Accuracy: {baseline_results['overall_accuracy']*100:.2f}%")
    print(f"Correct: {baseline_results['correct']}/{baseline_results['total']}")
    print()

    print("Critical Region Performance:")
    for region in ["A1", "A2", "G1", "E1", "E3"]:
        if region in baseline_results["region_accuracy"]:
            stats = baseline_results["region_accuracy"][region]
            print(f"  {region}: {stats['accuracy']*100:.1f}% ({stats['correct']}/{stats['total']})")
    print()

    # Validate ENHANCED (with surname patterns)
    print("=" * 80)
    print("ENHANCED: Phase 1 + Phase 2 + Surname Patterns")
    print("=" * 80)
    print()

    enhanced_results = validate_with_surname_enhancement(test_profiles, use_patterns=True)

    print(f"Overall Accuracy: {enhanced_results['overall_accuracy']*100:.2f}%")
    print(f"Correct: {enhanced_results['correct']}/{enhanced_results['total']}")
    print()

    print("Critical Region Performance:")
    for region in ["A1", "A2", "G1", "E1", "E3"]:
        if region in enhanced_results["region_accuracy"]:
            stats = enhanced_results["region_accuracy"][region]
            print(f"  {region}: {stats['accuracy']*100:.1f}% ({stats['correct']}/{stats['total']})")
    print()

    # Calculate improvement
    print("=" * 80)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 80)
    print()

    baseline_acc = baseline_results["overall_accuracy"] * 100
    enhanced_acc = enhanced_results["overall_accuracy"] * 100
    improvement = enhanced_acc - baseline_acc

    print(f"Overall Improvement: +{improvement:.2f}pp ({baseline_acc:.2f}% → {enhanced_acc:.2f}%)")
    print()

    print("Per-Region Improvements:")
    for region in ["A1", "A2", "G1"]:  # Latin-script regions
        if (
            region in baseline_results["region_accuracy"]
            and region in enhanced_results["region_accuracy"]
        ):
            baseline_acc = baseline_results["region_accuracy"][region]["accuracy"] * 100
            enhanced_acc = enhanced_results["region_accuracy"][region]["accuracy"] * 100
            improvement = enhanced_acc - baseline_acc

            status = "✅" if improvement >= 5.0 else ("⚠️" if improvement >= 2.0 else "❌")
            print(
                f"  {region}: +{improvement:.1f}pp ({baseline_acc:.1f}% → {enhanced_acc:.1f}%) {status}"
            )
    print()

    # Goal assessment
    print("=" * 80)
    print("GOAL ASSESSMENT")
    print("=" * 80)
    print()

    target_acc = 90.0
    current_acc = enhanced_results["overall_accuracy"] * 100
    gap = target_acc - current_acc

    if current_acc >= target_acc:
        print(f"✅ GOAL ACHIEVED: {current_acc:.2f}% ≥ {target_acc}%")
        print("   Ready for production deployment")
    elif current_acc >= 85.0:
        print(f"⚠️ CLOSE TO GOAL: {current_acc:.2f}% (gap: {gap:.2f}pp)")
        print(f"   Consider deploying with known limitations")
    else:
        print(f"❌ BELOW GOAL: {current_acc:.2f}% (gap: {gap:.2f}pp)")
        print(f"   Additional enhancements needed")

    print()

    # Detailed per-region breakdown
    print("=" * 80)
    print("DETAILED PER-REGION BREAKDOWN (Enhanced)")
    print("=" * 80)
    print()

    for region in sorted(enhanced_results["region_accuracy"].keys()):
        stats = enhanced_results["region_accuracy"][region]
        if stats["total"] >= 10:  # Only show regions with 10+ samples
            acc = stats["accuracy"] * 100
            status = "✅" if acc >= 85 else ("⚠️" if acc >= 70 else "❌")
            print(f"{region}: {acc:.1f}% ({stats['correct']}/{stats['total']}) {status}")

    print()


if __name__ == "__main__":
    main()
