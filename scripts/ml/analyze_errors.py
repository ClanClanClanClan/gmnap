#!/usr/bin/env python3
"""
Error Analysis Tools

Systematic analysis of ML classifier misclassifications to identify improvement opportunities.

Features:
- Confusion matrix
- Per-region error rates
- Error pattern detection
- Confidence distribution of errors
- Common misclassification pairs
- Error categorization (phonological, script-based, etc.)

Usage:
    python3 scripts/ml/analyze_errors.py \\
        --model data/ml_training/regional_classifier_v5_etymology.bin \\
        --test-data data/ml_training/test_profiles.json \\
        --output reports/ml/error_analysis.json
"""

import sys
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.regional_classifier_v5 import RegionalClassifierV5


class ErrorAnalyzer:
    """Systematic error analysis"""

    def __init__(self, classifier: RegionalClassifierV5, test_data: List[Dict]):
        self.classifier = classifier
        self.test_data = test_data
        self.errors = []
        self.correct = []

    def run_predictions(self):
        """Run predictions and collect errors"""
        print(f"\nRunning predictions on {len(self.test_data)} test samples...")

        for profile in self.test_data:
            name = profile["name"]
            true_region = profile["region"]

            result = self.classifier.predict(name, k=3)

            if result["abstained"]:
                # Skip abstained predictions
                continue

            predicted_region = result["region_top1"]
            confidence = result["region_top1_confidence"]

            if predicted_region == true_region:
                self.correct.append(
                    {
                        "name": name,
                        "region": true_region,
                        "confidence": confidence,
                        "topk": result["topk"],
                    }
                )
            else:
                self.errors.append(
                    {
                        "name": name,
                        "true_region": true_region,
                        "predicted_region": predicted_region,
                        "confidence": confidence,
                        "topk": result["topk"],
                    }
                )

        print(f"  ✅ Complete: {len(self.correct)} correct, {len(self.errors)} errors")

    def confusion_matrix(self) -> Dict:
        """Build confusion matrix"""
        print("\n" + "=" * 80)
        print("CONFUSION MATRIX")
        print("=" * 80)

        # Get all regions
        all_regions = sorted(
            set(
                [e["true_region"] for e in self.errors]
                + [e["predicted_region"] for e in self.errors]
                + [c["region"] for c in self.correct]
            )
        )

        # Initialize matrix
        matrix = defaultdict(lambda: defaultdict(int))

        # Fill matrix
        for error in self.errors:
            matrix[error["true_region"]][error["predicted_region"]] += 1

        for correct in self.correct:
            matrix[correct["region"]][correct["region"]] += 1

        # Print top confusions
        confusions = []
        for true_r in all_regions:
            for pred_r in all_regions:
                if true_r != pred_r and matrix[true_r][pred_r] > 0:
                    confusions.append((true_r, pred_r, matrix[true_r][pred_r]))

        confusions.sort(key=lambda x: x[2], reverse=True)

        print("\nTop 20 Confusion Pairs (True → Predicted):")
        for true_r, pred_r, count in confusions[:20]:
            print(f"  {true_r} → {pred_r}: {count} errors")

        return {
            "matrix": {true_r: dict(matrix[true_r]) for true_r in all_regions},
            "top_confusions": [
                {"true": t, "predicted": p, "count": c} for t, p, c in confusions[:20]
            ],
        }

    def per_region_error_rates(self) -> Dict:
        """Compute per-region error rates"""
        print("\n" + "=" * 80)
        print("PER-REGION ERROR RATES")
        print("=" * 80)

        region_stats = defaultdict(lambda: {"correct": 0, "errors": 0})

        for error in self.errors:
            region_stats[error["true_region"]]["errors"] += 1

        for correct in self.correct:
            region_stats[correct["region"]]["correct"] += 1

        # Compute rates
        rates = []
        for region in sorted(region_stats.keys()):
            stats = region_stats[region]
            total = stats["correct"] + stats["errors"]
            error_rate = stats["errors"] / total if total > 0 else 0
            accuracy = stats["correct"] / total if total > 0 else 0

            rates.append(
                {
                    "region": region,
                    "total": total,
                    "correct": stats["correct"],
                    "errors": stats["errors"],
                    "error_rate": error_rate,
                    "accuracy": accuracy,
                }
            )

        # Sort by error rate (highest first)
        rates.sort(key=lambda x: x["error_rate"], reverse=True)

        print("\nRegions with Highest Error Rates:")
        for rate_info in rates[:15]:
            print(
                f"  {rate_info['region']:4}: {rate_info['error_rate']:.1%} error rate "
                f"({rate_info['errors']}/{rate_info['total']} errors)"
            )

        return {"per_region": rates}

    def confidence_distribution(self) -> Dict:
        """Analyze confidence distribution of errors vs correct"""
        print("\n" + "=" * 80)
        print("CONFIDENCE DISTRIBUTION")
        print("=" * 80)

        error_confidences = [e["confidence"] for e in self.errors if e["confidence"]]
        correct_confidences = [c["confidence"] for c in self.correct if c["confidence"]]

        if error_confidences and correct_confidences:
            print(f"\nErrors (n={len(error_confidences)}):")
            print(f"  Mean confidence: {np.mean(error_confidences):.3f}")
            print(f"  Median confidence: {np.median(error_confidences):.3f}")
            print(f"  Std dev: {np.std(error_confidences):.3f}")

            print(f"\nCorrect (n={len(correct_confidences)}):")
            print(f"  Mean confidence: {np.mean(correct_confidences):.3f}")
            print(f"  Median confidence: {np.median(correct_confidences):.3f}")
            print(f"  Std dev: {np.std(correct_confidences):.3f}")

            # High-confidence errors (overconfident mistakes)
            high_conf_errors = [e for e in self.errors if e["confidence"] > 0.80]
            if high_conf_errors:
                print(f"\n⚠️  High-confidence errors (>0.80): {len(high_conf_errors)}")
                print("  Examples:")
                for error in high_conf_errors[:5]:
                    print(
                        f"    '{error['name']}': {error['true_region']} → {error['predicted_region']} "
                        f"(confidence: {error['confidence']:.3f})"
                    )

        return {
            "errors": {
                "mean": float(np.mean(error_confidences)) if error_confidences else 0,
                "median": (
                    float(np.median(error_confidences)) if error_confidences else 0
                ),
                "std": float(np.std(error_confidences)) if error_confidences else 0,
            },
            "correct": {
                "mean": (
                    float(np.mean(correct_confidences)) if correct_confidences else 0
                ),
                "median": (
                    float(np.median(correct_confidences)) if correct_confidences else 0
                ),
                "std": float(np.std(correct_confidences)) if correct_confidences else 0,
            },
            "high_confidence_errors": (
                [
                    {
                        "name": e["name"],
                        "true": e["true_region"],
                        "predicted": e["predicted_region"],
                        "confidence": e["confidence"],
                    }
                    for e in high_conf_errors[:10]
                ]
                if high_conf_errors
                else []
            ),
        }

    def categorize_errors(self) -> Dict:
        """Categorize errors by type"""
        print("\n" + "=" * 80)
        print("ERROR CATEGORIZATION")
        print("=" * 80)

        categories = defaultdict(list)

        for error in self.errors:
            true_r = error["true_region"]
            pred_r = error["predicted_region"]

            # Categorize by region group
            true_group = true_r[0] if len(true_r) > 0 else "X"
            pred_group = pred_r[0] if len(pred_r) > 0 else "X"

            if true_group == pred_group:
                # Within-group error (e.g., A1 → A2)
                categories["within_group"].append(error)
            else:
                # Cross-group error (e.g., A1 → E1)
                categories["cross_group"].append(error)

                # Specific cross-group patterns
                key = f"{true_group}_to_{pred_group}"
                categories[key].append(error)

        # Print summary
        print(
            f"\nWithin-group errors (same letter group): {len(categories['within_group'])}"
        )
        print(
            f"Cross-group errors (different letter group): {len(categories['cross_group'])}"
        )

        print("\nMost common cross-group patterns:")
        cross_patterns = [
            (k, len(v))
            for k, v in categories.items()
            if k not in ["within_group", "cross_group"] and len(v) > 0
        ]
        cross_patterns.sort(key=lambda x: x[1], reverse=True)

        for pattern, count in cross_patterns[:10]:
            print(f"  {pattern}: {count} errors")

        return {
            "within_group_count": len(categories["within_group"]),
            "cross_group_count": len(categories["cross_group"]),
            "cross_group_patterns": [
                {"pattern": p, "count": c} for p, c in cross_patterns[:10]
            ],
        }

    def top_k_recovery(self) -> Dict:
        """Analyze if true region appears in top-k"""
        print("\n" + "=" * 80)
        print("TOP-K RECOVERY ANALYSIS")
        print("=" * 80)

        in_top3 = 0
        in_top5 = 0
        not_in_topk = 0

        for error in self.errors:
            true_region = error["true_region"]
            topk_regions = [item["region"] for item in error["topk"]]

            if true_region in topk_regions[:3]:
                in_top3 += 1
            if (
                true_region in topk_regions[:5]
                if len(topk_regions) >= 5
                else topk_regions
            ):
                in_top5 += 1
            if true_region not in topk_regions:
                not_in_topk += 1

        total = len(self.errors)

        print(f"\nOf {total} errors:")
        print(f"  True region in top-3: {in_top3} ({in_top3/total:.1%})")
        print(f"  True region in top-5: {in_top5} ({in_top5/total:.1%})")
        print(f"  True region NOT in top-k: {not_in_topk} ({not_in_topk/total:.1%})")

        return {
            "total_errors": total,
            "in_top3": in_top3,
            "in_top3_pct": in_top3 / total if total > 0 else 0,
            "in_top5": in_top5,
            "in_top5_pct": in_top5 / total if total > 0 else 0,
            "not_in_topk": not_in_topk,
            "not_in_topk_pct": not_in_topk / total if total > 0 else 0,
        }

    def analyze_all(self) -> Dict:
        """Run all analyses"""
        self.run_predictions()

        confusion = self.confusion_matrix()
        per_region = self.per_region_error_rates()
        confidence_dist = self.confidence_distribution()
        categorization = self.categorize_errors()
        topk_recovery = self.top_k_recovery()

        print("\n" + "=" * 80)
        print("ANALYSIS SUMMARY")
        print("=" * 80)

        total_predictions = len(self.correct) + len(self.errors)
        accuracy = len(self.correct) / total_predictions if total_predictions > 0 else 0

        print(f"\nTotal predictions: {total_predictions}")
        print(f"Correct: {len(self.correct)} ({accuracy:.2%})")
        print(f"Errors: {len(self.errors)} ({1-accuracy:.2%})")

        return {
            "summary": {
                "total_predictions": total_predictions,
                "correct": len(self.correct),
                "errors": len(self.errors),
                "accuracy": accuracy,
                "error_rate": 1 - accuracy,
            },
            "confusion_matrix": confusion,
            "per_region_error_rates": per_region,
            "confidence_distribution": confidence_dist,
            "error_categorization": categorization,
            "topk_recovery": topk_recovery,
        }


def main():
    parser = argparse.ArgumentParser(description="Analyze ML classifier errors")
    parser.add_argument(
        "--model",
        default="data/ml_training/regional_classifier_v5_etymology.bin",
        help="Model file",
    )
    parser.add_argument(
        "--test-data",
        default="data/ml_training/test_profiles.json",
        help="Test dataset",
    )
    parser.add_argument(
        "--output", default="reports/ml/error_analysis.json", help="Output JSON file"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("ERROR ANALYSIS")
    print("=" * 80)

    # Load model
    print(f"\nLoading model: {args.model}")
    classifier = RegionalClassifierV5(model_path=args.model)
    print("  ✅ Model loaded")

    # Load test data
    print(f"\nLoading test data: {args.test_data}")
    with open(args.test_data, "r", encoding="utf-8") as f:
        test_data = json.load(f)
    print(f"  ✅ Loaded {len(test_data)} test samples")

    # Run analysis
    analyzer = ErrorAnalyzer(classifier, test_data)
    report = analyzer.analyze_all()

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Error analysis saved to: {output_path}")

    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
