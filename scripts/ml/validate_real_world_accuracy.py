#!/usr/bin/env python3
"""
Real-World Validation: Math Genealogy & Famous Mathematicians

Tests HybridRegionManager on REAL mathematician names to validate
97.54% accuracy holds beyond synthetic test data.

Three validation tiers:
1. Curated names (67 entries) - High-confidence real-world sample
2. Famous mathematicians (240 entries) - Historical mathematicians with ground truth
3. Math Genealogy sample (1000 entries) - Modern mathematician names

Expected outcome: ≥97% accuracy across all tiers
If <95%: Phase 3 (XGBoost ensemble) required
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.hybrid_region_manager import HybridRegionManager


class RealWorldValidator:
    """Validate HybridRegionManager on real mathematician data."""

    def __init__(self):
        self.manager = HybridRegionManager(
            use_security=False
        )  # Disable security for speed

    def load_curated_names(self) -> List[Dict]:
        """Load 67 curated real mathematician names."""
        data_path = Path("data/ml_training/real_mathematician_names.json")
        with open(data_path) as f:
            data = json.load(f)

        # Convert to standard format
        entries = []
        for entry in data["entries"]:
            entries.append(
                {
                    "CanonicalNative": entry["name"],
                    "Region": entry["region"],
                    "Source": "curated_real",
                }
            )
        return entries

    def load_famous_mathematicians(self) -> List[Dict]:
        """Load 240 famous mathematician names."""
        data_path = Path("data/test_datasets/mathematician_test_dataset.json")
        with open(data_path) as f:
            data = json.load(f)

        # Convert nested regional structure to flat list
        entries = []
        for region_name, region_entries in data["test_data"].items():
            for entry in region_entries:
                # Normalize region code (remove underscores, convert to uppercase)
                region_code = entry["region"].upper().replace("_", "")
                # Extract just the region prefix (e.g., A1 from A1_ANGLO_SPHERE)
                region_prefix = (
                    region_code.split("_")[0] if "_" in region_code else region_code[:2]
                )

                entries.append(
                    {
                        "CanonicalNative": entry["name"],
                        "Region": region_prefix,
                        "Source": "famous_mathematicians",
                        "Country": entry.get("country", "Unknown"),
                        "Name": entry["name"],
                    }
                )
        return entries

    def load_math_genealogy_sample(self, n: int = 1000) -> List[Dict]:
        """Load sample from 30K Math Genealogy dataset."""
        data_path = Path("data/ml_training/math_genealogy_30k.json")
        with open(data_path) as f:
            data = json.load(f)

        # Take first n entries
        entries = data["data"][:n]

        # Already in correct format
        return entries

    def validate_dataset(self, entries: List[Dict], dataset_name: str) -> Dict:
        """
        Validate accuracy on a dataset.

        Returns:
            dict with accuracy metrics and failure analysis
        """
        print(f"\n{'='*80}")
        print(f"VALIDATING: {dataset_name}")
        print(f"{'='*80}")
        print(f"Total entries: {len(entries)}\n")

        results = {
            "total": len(entries),
            "correct": 0,
            "failures": [],
            "regional_stats": defaultdict(lambda: {"total": 0, "correct": 0}),
            "confidence_stats": [],
        }

        for i, entry in enumerate(entries):
            # Detect region
            detection = self.manager.detect_region(entry)

            # Extract region codes (normalize)
            expected = (
                entry["Region"].upper().replace("_SYNTHETIC", "").replace("_", "")
            )
            detected = detection.region_code.upper().replace("_", "")

            # For famous mathematicians, region might be like "A1_ANGLO_SPHERE"
            # Extract just the prefix (A1, B1, etc.)
            expected_prefix = (
                expected.split("_")[0] if "_" in expected else expected[:2]
            )
            detected_prefix = (
                detected.split("_")[0] if "_" in detected else detected[:2]
            )

            # Track regional performance
            results["regional_stats"][expected_prefix]["total"] += 1

            # Check if correct
            is_correct = expected_prefix == detected_prefix

            if is_correct:
                results["correct"] += 1
                results["regional_stats"][expected_prefix]["correct"] += 1
            else:
                # Record failure for analysis
                results["failures"].append(
                    {
                        "name": entry["CanonicalNative"],
                        "expected": expected_prefix,
                        "detected": detected_prefix,
                        "confidence": detection.confidence,
                        "method": detection.detection_method,
                        "country": entry.get("Country", "Unknown"),
                    }
                )

            # Track confidence distribution
            results["confidence_stats"].append(
                {"confidence": detection.confidence, "correct": is_correct}
            )

            # Progress indicator
            if (i + 1) % 50 == 0 or (i + 1) == len(entries):
                acc = results["correct"] / (i + 1) * 100
                print(f"  Progress: {i+1}/{len(entries)} ({acc:.2f}% accurate so far)")

        # Calculate final accuracy
        results["accuracy"] = (
            results["correct"] / results["total"] * 100 if results["total"] > 0 else 0
        )

        return results

    def print_results(self, results: Dict, dataset_name: str):
        """Print detailed validation results."""
        print(f"\n{'-'*80}")
        print(f"RESULTS: {dataset_name}")
        print(f"{'-'*80}")
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
            status = "✅" if acc >= 95 else "⚠️" if acc >= 90 else "❌"
            print(
                f"  {status} {region}: {stats['correct']}/{stats['total']} = {acc:.1f}%"
            )

        # Confidence analysis
        avg_confidence = sum(
            s["confidence"] for s in results["confidence_stats"]
        ) / len(results["confidence_stats"])
        correct_conf = [
            s["confidence"] for s in results["confidence_stats"] if s["correct"]
        ]
        incorrect_conf = [
            s["confidence"] for s in results["confidence_stats"] if not s["correct"]
        ]

        print()
        print("Confidence Analysis:")
        print(f"  Average confidence: {avg_confidence:.3f}")
        if correct_conf:
            print(
                f"  Correct predictions: {sum(correct_conf)/len(correct_conf):.3f} avg"
            )
        if incorrect_conf:
            print(
                f"  Incorrect predictions: {sum(incorrect_conf)/len(incorrect_conf):.3f} avg"
            )

        # Top failures
        if results["failures"]:
            print()
            print(f"Top 10 Failures (of {len(results['failures'])} total):")
            for i, failure in enumerate(results["failures"][:10], 1):
                print(f"  {i}. {failure['name']}")
                print(
                    f"     Expected: {failure['expected']}, Got: {failure['detected']}"
                )
                print(
                    f"     Confidence: {failure['confidence']:.3f}, Method: {failure['method']}"
                )
                print(f"     Country: {failure['country']}")

    def determine_verdict(
        self, curated_acc: float, famous_acc: float, mgp_acc: float = None
    ) -> str:
        """
        Determine final verdict based on all validation results.

        Returns:
            verdict string with recommendation
        """
        print(f"\n{'='*80}")
        print("FINAL VERDICT")
        print(f"{'='*80}")
        print()
        print("Accuracy Summary:")
        print(f"  Curated names (67):         {curated_acc:.2f}%")
        print(f"  Famous mathematicians (240): {famous_acc:.2f}%")
        if mgp_acc:
            print(f"  Math Genealogy sample:      {mgp_acc:.2f}%")

        # Calculate weighted average (weight famous mathematicians more)
        if mgp_acc:
            avg_acc = curated_acc * 0.2 + famous_acc * 0.5 + mgp_acc * 0.3
        else:
            avg_acc = curated_acc * 0.3 + famous_acc * 0.7

        print()
        print(f"Weighted Average: {avg_acc:.2f}%")
        print()

        # Determine verdict
        if avg_acc >= 97.5:
            verdict = "✅ EXCELLENT"
            recommendation = """
RECOMMENDATION: Phase 2 COMPLETE - Deploy to Production

Real-world accuracy (≥97.5%) matches synthetic test accuracy (97.54%).
System is robust across different data distributions.

Next Steps:
1. Update CLAUDE.md with real-world validation results
2. Deploy HybridRegionManager to production
3. Setup monitoring for ongoing accuracy tracking
4. Phase 3 (XGBoost ensemble) NOT NEEDED

Status: PRODUCTION READY ✅
"""
        elif avg_acc >= 95.0:
            verdict = "✅ GOOD"
            recommendation = """
RECOMMENDATION: Phase 2 COMPLETE (with monitoring)

Real-world accuracy (≥95%) meets target, slightly below synthetic (97.54%).
Small domain shift detected but within acceptable bounds.

Next Steps:
1. Deploy to production with enhanced monitoring
2. Track failure patterns in production
3. Phase 3 (XGBoost ensemble) OPTIONAL for additional 1-2pp gain
4. Consider retraining on real mathematician data

Status: PRODUCTION READY with monitoring ⚠️
"""
        elif avg_acc >= 90.0:
            verdict = "⚠️ ACCEPTABLE"
            recommendation = """
RECOMMENDATION: Consider Phase 3 Improvements

Real-world accuracy (90-95%) shows notable domain shift from synthetic (97.54%).
System works but has room for improvement.

Next Steps:
1. Analyze failure patterns in detail
2. Consider Phase 3 (XGBoost meta-classifier) to improve 3-5pp
3. Retrain Phase 2 on real mathematician data
4. Enhanced feature engineering

Status: Phase 3 RECOMMENDED ⚠️
"""
        else:
            verdict = "❌ NEEDS IMPROVEMENT"
            recommendation = """
RECOMMENDATION: Phase 3 REQUIRED

Real-world accuracy (<90%) shows significant domain shift.
Major gap between synthetic test (97.54%) and real data.

Immediate Actions:
1. IMPLEMENT Phase 3 (XGBoost meta-classifier)
2. Retrain on real mathematician data
3. Analyze systematic failure patterns
4. Consider additional regional rules

Status: Phase 3 REQUIRED before production ❌
"""

        print(f"Verdict: {verdict}")
        print(recommendation)

        return verdict


def main():
    print("=" * 80)
    print("REAL-WORLD VALIDATION: HYBRID REGION MANAGER")
    print("=" * 80)
    print()
    print("Testing HybridRegionManager (97.54% on synthetic data)")
    print("on REAL mathematician names to validate robustness.")
    print()

    validator = RealWorldValidator()

    # Tier 1: Curated names (67 entries)
    curated_entries = validator.load_curated_names()
    curated_results = validator.validate_dataset(
        curated_entries, "Curated Real Mathematician Names (67)"
    )
    validator.print_results(curated_results, "Curated Names")

    # Tier 2: Famous mathematicians (240 entries)
    famous_entries = validator.load_famous_mathematicians()
    famous_results = validator.validate_dataset(
        famous_entries, "Famous Mathematicians (240)"
    )
    validator.print_results(famous_results, "Famous Mathematicians")

    # Tier 3: Math Genealogy sample (1000 entries)
    print("\n" + "=" * 80)
    print("Loading Math Genealogy sample (1000 entries)...")
    mgp_entries = validator.load_math_genealogy_sample(n=1000)
    mgp_results = validator.validate_dataset(
        mgp_entries, "Math Genealogy Sample (1000)"
    )
    validator.print_results(mgp_results, "Math Genealogy Sample")

    # Final verdict
    verdict = validator.determine_verdict(
        curated_results["accuracy"], famous_results["accuracy"], mgp_results["accuracy"]
    )

    # Return exit code
    avg_acc = (
        curated_results["accuracy"] * 0.2
        + famous_results["accuracy"] * 0.5
        + mgp_results["accuracy"] * 0.3
    )

    if avg_acc >= 95.0:
        return 0  # Success
    else:
        return 1  # Needs improvement


if __name__ == "__main__":
    sys.exit(main())
