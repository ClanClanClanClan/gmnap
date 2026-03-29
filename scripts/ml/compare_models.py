#!/usr/bin/env python3
"""
Model Comparison Script: v4 vs v5

Performs side-by-side comparison of v4 (affiliation) and v5 (etymology) models
on the same test dataset to validate improvement claims.

Features:
- Head-to-head accuracy comparison
- Per-region breakdown
- Confusion matrix analysis
- Agreement/disagreement analysis
- Statistical significance testing
- Detailed error analysis

Usage:
    python3 scripts/ml/compare_models.py \\
        --test-data data/ml_training/test_profiles.json \\
        --model-v4 data/ml_training/regional_classifier_v4_optimized.bin \\
        --model-v5 data/ml_training/regional_classifier_v5_etymology.bin \\
        --output reports/ml/comparison_v4_v5.json
"""

import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import fasttext
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.regional_classifier_v5 import RegionalClassifierV5


def load_test_data(test_path: str) -> List[Dict]:
    """Load test profiles"""
    with open(test_path, "r", encoding="utf-8") as f:
        return json.load(f)


def predict_v4(model_v4: fasttext.FastText._FastText, name: str) -> Tuple[str, float]:
    """Predict using v4 model (no calibration)"""
    labels, probs = model_v4.predict(name, k=1)
    region = labels[0].replace("__label__", "")
    confidence = float(probs[0])
    return region, confidence


def predict_v5(
    classifier_v5: RegionalClassifierV5, name: str
) -> Tuple[str, float, bool]:
    """Predict using v5 model (with calibration and abstention)"""
    result = classifier_v5.predict(name, k=1)

    if result["abstained"]:
        return None, None, True

    return result["region_top1"], result["region_top1_confidence"], False


def compute_accuracy(predictions: List[Tuple[str, str]]) -> float:
    """Compute accuracy from (predicted, true) pairs"""
    if not predictions:
        return 0.0
    correct = sum(1 for pred, true in predictions if pred == true)
    return correct / len(predictions)


def compute_per_region_metrics(predictions: List[Tuple[str, str]]) -> Dict:
    """Compute per-region precision, recall, F1"""
    from collections import defaultdict

    # Group by true region
    by_true_region = defaultdict(list)
    for pred, true in predictions:
        by_true_region[true].append(pred)

    # Group by predicted region
    by_pred_region = defaultdict(list)
    for pred, true in predictions:
        by_pred_region[pred].append(true)

    metrics = {}
    for region in sorted(set(r for _, r in predictions)):
        true_positives = sum(1 for p in by_true_region[region] if p == region)
        false_negatives = sum(1 for p in by_true_region[region] if p != region)
        false_positives = sum(1 for t in by_pred_region[region] if t != region)

        # Precision
        if true_positives + false_positives > 0:
            precision = true_positives / (true_positives + false_positives)
        else:
            precision = 0.0

        # Recall
        if true_positives + false_negatives > 0:
            recall = true_positives / (true_positives + false_negatives)
        else:
            recall = 0.0

        # F1
        if precision + recall > 0:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = 0.0

        metrics[region] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": len(by_true_region[region]),
        }

    return metrics


def analyze_agreement(
    v4_preds: List[str], v5_preds: List[str], true_labels: List[str]
) -> Dict:
    """Analyze where v4 and v5 agree/disagree"""
    both_correct = 0
    both_incorrect = 0
    v4_correct_v5_incorrect = 0
    v5_correct_v4_incorrect = 0

    for v4, v5, true in zip(v4_preds, v5_preds, true_labels):
        v4_correct = v4 == true
        v5_correct = v5 == true

        if v4_correct and v5_correct:
            both_correct += 1
        elif not v4_correct and not v5_correct:
            both_incorrect += 1
        elif v4_correct and not v5_correct:
            v4_correct_v5_incorrect += 1
        elif v5_correct and not v4_correct:
            v5_correct_v4_incorrect += 1

    total = len(v4_preds)

    return {
        "both_correct": both_correct,
        "both_correct_pct": both_correct / total * 100,
        "both_incorrect": both_incorrect,
        "both_incorrect_pct": both_incorrect / total * 100,
        "v4_correct_v5_incorrect": v4_correct_v5_incorrect,
        "v4_correct_v5_incorrect_pct": v4_correct_v5_incorrect / total * 100,
        "v5_correct_v4_incorrect": v5_correct_v4_incorrect,
        "v5_correct_v4_incorrect_pct": v5_correct_v4_incorrect / total * 100,
        "agreement_rate": (both_correct + both_incorrect) / total * 100,
    }


def statistical_significance(v4_correct: List[bool], v5_correct: List[bool]) -> Dict:
    """McNemar's test for paired classifier comparison"""
    # Contingency table
    # b = v5 correct, v4 incorrect
    # c = v4 correct, v5 incorrect
    b = sum(1 for v4, v5 in zip(v4_correct, v5_correct) if not v4 and v5)
    c = sum(1 for v4, v5 in zip(v4_correct, v5_correct) if v4 and not v5)

    # McNemar's test statistic
    if b + c == 0:
        return {
            "b": b,
            "c": c,
            "statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "interpretation": "No disagreements between models",
        }

    # Chi-squared with continuity correction
    statistic = (abs(b - c) - 1) ** 2 / (b + c)

    # Critical value for alpha=0.05 is 3.841
    p_value_approx = 0.05 if statistic > 3.841 else 0.5  # Rough approximation
    significant = statistic > 3.841

    interpretation = (
        f"v5 significantly better (b={b}, c={c})"
        if significant and b > c
        else (
            f"v4 significantly better (b={b}, c={c})"
            if significant and c > b
            else f"No significant difference (b={b}, c={c})"
        )
    )

    return {
        "b": b,
        "c": c,
        "statistic": statistic,
        "p_value_approx": p_value_approx,
        "significant": significant,
        "interpretation": interpretation,
    }


def error_analysis(
    v4_preds: List[str], v5_preds: List[str], true_labels: List[str], names: List[str]
) -> Dict:
    """Analyze errors made by each model"""
    v4_errors = []
    v5_errors = []
    v5_fixed_v4_errors = []
    v5_introduced_errors = []

    for v4, v5, true, name in zip(v4_preds, v5_preds, true_labels, names):
        if v4 != true:
            v4_errors.append(
                {"name": name, "predicted": v4, "true": true, "v5_fixed": (v5 == true)}
            )
            if v5 == true:
                v5_fixed_v4_errors.append(
                    {"name": name, "v4_predicted": v4, "true": true}
                )

        if v5 != true:
            v5_errors.append(
                {
                    "name": name,
                    "predicted": v5,
                    "true": true,
                    "v4_correct": (v4 == true),
                }
            )
            if v4 == true:
                v5_introduced_errors.append(
                    {"name": name, "v5_predicted": v5, "true": true}
                )

    return {
        "v4_error_count": len(v4_errors),
        "v5_error_count": len(v5_errors),
        "v5_fixed_count": len(v5_fixed_v4_errors),
        "v5_introduced_count": len(v5_introduced_errors),
        "v5_fixed_examples": v5_fixed_v4_errors[:10],  # Top 10
        "v5_introduced_examples": v5_introduced_errors[:10],  # Top 10
        "net_improvement": len(v5_fixed_v4_errors) - len(v5_introduced_errors),
    }


def main():
    parser = argparse.ArgumentParser(description="Compare v4 vs v5 models")
    parser.add_argument(
        "--test-data",
        default="data/ml_training/test_profiles.json",
        help="Test dataset JSON file",
    )
    parser.add_argument(
        "--model-v4",
        default="data/ml_training/regional_classifier_v4_optimized.bin",
        help="v4 model file",
    )
    parser.add_argument(
        "--model-v5",
        default="data/ml_training/regional_classifier_v5_etymology.bin",
        help="v5 model file",
    )
    parser.add_argument(
        "--output", default="reports/ml/comparison_v4_v5.json", help="Output JSON file"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("MODEL COMPARISON: v4 vs v5")
    print("=" * 80)

    # Load test data
    print(f"\nLoading test data: {args.test_data}")
    test_profiles = load_test_data(args.test_data)
    print(f"  ✅ Loaded {len(test_profiles)} test profiles")

    # Load models
    print(f"\nLoading v4 model: {args.model_v4}")
    model_v4 = fasttext.load_model(args.model_v4)
    print(f"  ✅ v4 model loaded")

    print(f"\nLoading v5 model: {args.model_v5}")
    classifier_v5 = RegionalClassifierV5(model_path=args.model_v5)
    print(f"  ✅ v5 model loaded")

    # Run predictions
    print("\nRunning predictions...")
    v4_predictions = []
    v5_predictions = []
    v5_abstentions = []
    names = []
    true_labels = []

    for profile in test_profiles:
        name = profile["name"]
        true_region = profile["region"]

        # v4 prediction
        v4_region, v4_conf = predict_v4(model_v4, name)

        # v5 prediction
        v5_region, v5_conf, abstained = predict_v5(classifier_v5, name)

        if not abstained:
            v4_predictions.append((v4_region, true_region))
            v5_predictions.append((v5_region, true_region))
            names.append(name)
            true_labels.append(true_region)
        else:
            v5_abstentions.append(
                {"name": name, "true_region": true_region, "v4_region": v4_region}
            )

    print(f"  ✅ Predictions complete")
    print(f"     v4: {len(v4_predictions)} predictions")
    print(
        f"     v5: {len(v5_predictions)} predictions ({len(v5_abstentions)} abstained)"
    )

    # Compute metrics
    print("\nComputing metrics...")

    v4_accuracy = compute_accuracy(v4_predictions)
    v5_accuracy = compute_accuracy(v5_predictions)
    improvement_pp = (v5_accuracy - v4_accuracy) * 100

    print(f"\n  {'v4 Accuracy:':<30} {v4_accuracy:.2%}")
    print(f"  {'v5 Accuracy:':<30} {v5_accuracy:.2%}")
    print(f"  {'Improvement:':<30} {improvement_pp:+.2f}pp")

    # Per-region metrics
    print("\nComputing per-region metrics...")
    v4_per_region = compute_per_region_metrics(v4_predictions)
    v5_per_region = compute_per_region_metrics(v5_predictions)

    # Agreement analysis
    print("\nAnalyzing agreement...")
    v4_preds = [p for p, _ in v4_predictions]
    v5_preds = [p for p, _ in v5_predictions]
    agreement = analyze_agreement(v4_preds, v5_preds, true_labels)

    print(
        f"  {'Both correct:':<40} {agreement['both_correct']} ({agreement['both_correct_pct']:.1f}%)"
    )
    print(
        f"  {'Both incorrect:':<40} {agreement['both_incorrect']} ({agreement['both_incorrect_pct']:.1f}%)"
    )
    print(
        f"  {'v4 correct, v5 incorrect:':<40} {agreement['v4_correct_v5_incorrect']} ({agreement['v4_correct_v5_incorrect_pct']:.1f}%)"
    )
    print(
        f"  {'v5 correct, v4 incorrect:':<40} {agreement['v5_correct_v4_incorrect']} ({agreement['v5_correct_v4_incorrect_pct']:.1f}%)"
    )
    print(f"  {'Agreement rate:':<40} {agreement['agreement_rate']:.1f}%")

    # Statistical significance
    print("\nTesting statistical significance...")
    v4_correct = [p == t for p, t in v4_predictions]
    v5_correct = [p == t for p, t in v5_predictions]
    sig_test = statistical_significance(v4_correct, v5_correct)

    print(f"  {sig_test['interpretation']}")
    print(f"  McNemar statistic: {sig_test['statistic']:.2f}")
    print(f"  Significant (α=0.05): {sig_test['significant']}")

    # Error analysis
    print("\nAnalyzing errors...")
    errors = error_analysis(v4_preds, v5_preds, true_labels, names)

    print(f"  {'v4 errors:':<40} {errors['v4_error_count']}")
    print(f"  {'v5 errors:':<40} {errors['v5_error_count']}")
    print(f"  {'v5 fixed v4 errors:':<40} {errors['v5_fixed_count']}")
    print(f"  {'v5 introduced new errors:':<40} {errors['v5_introduced_count']}")
    print(f"  {'Net improvement:':<40} {errors['net_improvement']} errors")

    # Build comparison report
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "test_data": {
            "file": args.test_data,
            "total_profiles": len(test_profiles),
            "compared_profiles": len(v4_predictions),
            "v5_abstained": len(v5_abstentions),
        },
        "models": {
            "v4": {
                "file": args.model_v4,
                "accuracy": v4_accuracy,
                "label_policy": "affiliation",
            },
            "v5": {
                "file": args.model_v5,
                "accuracy": v5_accuracy,
                "label_policy": "etymology",
                "abstention_rate": len(v5_abstentions) / len(test_profiles),
            },
        },
        "comparison": {
            "improvement_pp": improvement_pp,
            "improvement_pct": (
                (v5_accuracy / v4_accuracy - 1) * 100 if v4_accuracy > 0 else 0
            ),
            "winner": (
                "v5"
                if v5_accuracy > v4_accuracy
                else "v4" if v4_accuracy > v5_accuracy else "tie"
            ),
        },
        "agreement": agreement,
        "statistical_significance": sig_test,
        "error_analysis": errors,
        "per_region_v4": v4_per_region,
        "per_region_v5": v5_per_region,
        "v5_abstentions": v5_abstentions[:20],  # Top 20 abstentions
    }

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Comparison report saved to: {output_path}")

    # Summary
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(f"\n{'Model':<10} {'Accuracy':<12} {'Label Policy':<20} {'Status'}")
    print(f"{'-'*10} {'-'*12} {'-'*20} {'-'*20}")
    print(f"{'v4':<10} {v4_accuracy:<12.2%} {'affiliation':<20} Baseline")
    print(
        f"{'v5':<10} {v5_accuracy:<12.2%} {'etymology':<20} +{improvement_pp:.2f}pp improvement"
    )

    print(
        f"\nVerdict: v5 is {'SIGNIFICANTLY BETTER' if sig_test['significant'] and improvement_pp > 0 else 'BETTER' if improvement_pp > 0 else 'EQUIVALENT'}"
    )
    print(f"Confidence: {'HIGH' if sig_test['significant'] else 'MEDIUM'}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
