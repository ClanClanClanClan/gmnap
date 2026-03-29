#!/usr/bin/env python3
"""
Tier 1 Comprehensive Validation Script

Validates regional detection accuracy against the Tier 1 comprehensive dataset.
Provides detailed statistical analysis with confidence intervals.

Usage:
    python3 scripts/testing/validate_tier1.py [--verbose] [--save-failures]
"""

import json
import math
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from src.regions.manager_optimized import RegionManager


def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple:
    """
    Calculate Wilson score confidence interval for binomial proportion.

    More accurate than normal approximation, especially for small samples
    or extreme probabilities.

    Args:
        successes: Number of correct classifications
        trials: Total number of attempts
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        (lower_bound, upper_bound, margin_of_error)
    """
    if trials == 0:
        return (0.0, 0.0, 0.0)

    p = successes / trials

    # Z-score for confidence level
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    denominator = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denominator
    margin = z * math.sqrt((p * (1 - p) / trials + z**2 / (4 * trials**2))) / denominator

    lower = center - margin
    upper = center + margin

    return (lower, upper, margin)


def validate_tier1(verbose: bool = False, save_failures: bool = False):
    """Run Tier 1 validation with comprehensive statistics."""

    print("=" * 80)
    print("GMNAP V7 - TIER 1 COMPREHENSIVE REGIONAL VALIDATION")
    print("=" * 80)
    print()

    # Load dataset
    dataset_file = Path("data/test_suites/tier1_regional_comprehensive.json")
    if not dataset_file.exists():
        print(f"❌ Dataset not found: {dataset_file}")
        print("   Run: python3 scripts/testing/generate_tier1_comprehensive.py")
        return

    with open(dataset_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_data = data["test_data"]
    total_tests = len(test_data)

    print(f"📁 Dataset: {dataset_file.name}")
    print(f"📊 Total entries: {total_tests}")
    print(f"🌍 Regions covered: {data['metadata']['regions_covered']}")
    print()

    # Initialize manager
    manager = RegionManager()

    # Track results
    results = {
        "total_correct": 0,
        "total_tested": 0,
        "by_region": defaultdict(lambda: {"correct": 0, "total": 0, "failures": []}),
    }

    # Run validation
    print("🔍 Running validation...")
    print()

    for i, entry in enumerate(test_data, 1):
        name = entry["CanonicalNative"]
        expected_region = entry["Region"].split("_")[0].upper()

        # Detect region
        detection = manager.detect_region({"CanonicalLatin": name})

        detected_region = detection.region_code.split("_")[0].upper() if detection else "NONE"
        is_correct = detected_region == expected_region

        # Record results
        results["by_region"][expected_region]["total"] += 1
        results["total_tested"] += 1

        if is_correct:
            results["by_region"][expected_region]["correct"] += 1
            results["total_correct"] += 1
        else:
            # Record failure
            failure = {
                "name": name,
                "expected": expected_region,
                "detected": detected_region,
                "confidence": detection.confidence if detection else 0.0,
                "method": detection.detection_method if detection else "none",
            }
            results["by_region"][expected_region]["failures"].append(failure)

            if verbose:
                print(f"❌ [{i}/{total_tests}] {name}")
                print(f"   Expected: {expected_region}, Got: {detected_region}")
                print(f"   Confidence: {failure['confidence']:.2f}, Method: {failure['method']}")
                print()

        # Progress indicator
        if i % 500 == 0:
            current_acc = (results["total_correct"] / results["total_tested"]) * 100
            print(
                f"   Progress: {i}/{total_tests} ({i/total_tests*100:.1f}%) - Current: {current_acc:.1f}%"
            )

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    # Overall statistics
    overall_acc = (results["total_correct"] / results["total_tested"]) * 100
    ci_low, ci_high, margin = wilson_score_interval(
        results["total_correct"], results["total_tested"]
    )

    print(f"📊 OVERALL ACCURACY: {overall_acc:.2f}%")
    print(f"   Correct: {results['total_correct']}/{results['total_tested']}")
    print(f"   95% CI: ({ci_low*100:.1f}%, {ci_high*100:.1f}%)")
    print(f"   Margin of Error: ±{margin*100:.1f}%")
    print()

    # Phase 1 target assessment
    target = 80.0
    if overall_acc >= target:
        status = "✅ PASS"
    else:
        status = "❌ FAIL"

    print(f"🎯 PHASE 1 TARGET (≥{target}%): {status}")
    print()

    # Per-region breakdown
    print("=" * 80)
    print("PER-REGION ACCURACY")
    print("=" * 80)
    print()
    print(f"{'Region':<8} {'Correct':<10} {'Total':<8} {'Accuracy':<10} {'95% CI':<20} {'Status'}")
    print("-" * 80)

    sorted_regions = sorted(results["by_region"].items(), key=lambda x: x[0])

    failed_regions = []
    for region, stats in sorted_regions:
        correct = stats["correct"]
        total = stats["total"]
        acc = (correct / total * 100) if total > 0 else 0.0

        ci_low, ci_high, margin = wilson_score_interval(correct, total)

        # Per-region target (60% minimum for Phase 1)
        region_target = 60.0
        if acc >= region_target:
            status = "✅"
        else:
            status = "❌"
            failed_regions.append((region, acc, total))

        print(
            f"{region:<8} {correct:>3}/{total:<5} {total:<8} {acc:>6.1f}%  "
            f"({ci_low*100:>5.1f}%, {ci_high*100:>5.1f}%)  {status}"
        )

    print()

    # Failed regions summary
    if failed_regions:
        print("=" * 80)
        print(f"⚠️  REGIONS BELOW MINIMUM THRESHOLD ({region_target}%)")
        print("=" * 80)
        print()
        for region, acc, total in failed_regions:
            failures = results["by_region"][region]["failures"]
            print(f"  {region}: {acc:.1f}% ({total} samples, {len(failures)} failures)")

            # Show top failure patterns
            if failures and verbose:
                print(f"    Top failures:")
                for fail in failures[:3]:
                    print(
                        f"      • {fail['name']} → {fail['detected']} "
                        f"(conf: {fail['confidence']:.2f}, method: {fail['method']})"
                    )
                print()

    # Statistical assessment
    print("=" * 80)
    print("STATISTICAL ASSESSMENT")
    print("=" * 80)
    print()

    # Sample size adequacy
    required_n = 3147  # For ±1% margin at 95% CI
    if results["total_tested"] >= required_n:
        print(f"✅ Sample size adequate for ±1% margin ({results['total_tested']} ≥ {required_n})")
    else:
        print(f"⚠️  Sample size below target ({results['total_tested']} < {required_n})")
        print(f"   Current margin: ±{margin*100:.1f}%")

    # Coverage completeness
    expected_regions = 37
    covered_regions = len(results["by_region"])
    if covered_regions >= expected_regions:
        print(f"✅ Regional coverage complete ({covered_regions}/{expected_regions})")
    else:
        print(f"❌ Regional coverage incomplete ({covered_regions}/{expected_regions})")

    print()

    # Save failures if requested
    if save_failures:
        save_failure_report(results)

    # Final verdict
    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print()

    if overall_acc >= target and len(failed_regions) <= 3:
        print("✅ VALIDATION PASSED")
        print(f"   Overall accuracy {overall_acc:.1f}% meets Phase 1 target (≥{target}%)")
        print(f"   {len(failed_regions)} regions below threshold (acceptable)")
    elif overall_acc >= target:
        print("⚠️  CONDITIONAL PASS")
        print(f"   Overall accuracy {overall_acc:.1f}% meets target")
        print(f"   But {len(failed_regions)} regions need improvement")
    else:
        print("❌ VALIDATION FAILED")
        print(f"   Overall accuracy {overall_acc:.1f}% below target (≥{target}%)")
        print(f"   Gap: {target - overall_acc:.1f} percentage points")

    print()

    return results


def save_failure_report(results: dict):
    """Save detailed failure analysis report."""
    output_dir = Path("data/validation_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"tier1_failures_{timestamp}.json"

    failure_data = {
        "timestamp": datetime.now().isoformat(),
        "overall_accuracy": (results["total_correct"] / results["total_tested"]) * 100,
        "total_failures": results["total_tested"] - results["total_correct"],
        "by_region": {},
    }

    for region, stats in results["by_region"].items():
        if stats["failures"]:
            failure_data["by_region"][region] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": (
                    (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
                ),
                "failures": stats["failures"],
            }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(failure_data, f, indent=2, ensure_ascii=False)

    print(f"💾 Failure report saved to: {output_file}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Tier 1 regional detection")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed failure output")
    parser.add_argument(
        "--save-failures", "-s", action="store_true", help="Save failure analysis report"
    )

    args = parser.parse_args()

    validate_tier1(verbose=args.verbose, save_failures=args.save_failures)
