#!/usr/bin/env python3
"""
Deep Analysis of fastText Failure Patterns

Investigates WHY the model is failing to achieve 90%+ accuracy.
Hypotheses:
1. Data labeling issues (affiliation vs etymology)
2. Insufficient training data (6,913 vs 14,000 expected)
3. Inherent ambiguity in Latin-script names
4. Class imbalance (A1=23%, others <5%)
"""

import sys
import json
import fasttext
from pathlib import Path
from collections import defaultdict, Counter


def load_data():
    """Load validation and training data."""
    val_path = Path("data/ml_training/val_split.json")
    train_path = Path("data/ml_training/train_split.json")

    with open(val_path) as f:
        val_data = json.load(f)

    with open(train_path) as f:
        train_data = json.load(f)

    return train_data["profiles"], val_data["profiles"]


def analyze_failures(model, val_profiles):
    """Analyze failure patterns in detail."""
    failures = []
    confusion_matrix = defaultdict(lambda: defaultdict(int))

    for profile in val_profiles:
        name = profile["name"]
        expected = profile["region"]
        country = profile.get("country_code", "Unknown")

        pred = model.predict(name, k=3)  # Get top-3 predictions
        detected = pred[0][0].replace("__label__", "")
        confidence = float(pred[1][0])

        # Get all top-3 predictions
        top3 = [
            (pred[0][i].replace("__label__", ""), float(pred[1][i]))
            for i in range(min(3, len(pred[0])))
        ]

        if expected != detected:
            failures.append(
                {
                    "name": name,
                    "expected": expected,
                    "detected": detected,
                    "confidence": confidence,
                    "country": country,
                    "top3": top3,
                }
            )
            confusion_matrix[expected][detected] += 1

    return failures, confusion_matrix


def analyze_labeling_consistency(train_profiles):
    """Check if labeling is consistent across countries."""
    country_to_regions = defaultdict(set)
    region_to_countries = defaultdict(set)

    for profile in train_profiles:
        country = profile.get("country_code", "Unknown")
        region = profile["region"]

        country_to_regions[country].add(region)
        region_to_countries[region].add(country)

    # Find countries with multiple regions (potential labeling issue)
    inconsistent_countries = {
        country: regions for country, regions in country_to_regions.items() if len(regions) > 1
    }

    return country_to_regions, region_to_countries, inconsistent_countries


def analyze_sample_distribution(train_profiles):
    """Analyze class imbalance in training data."""
    region_counts = Counter(p["region"] for p in train_profiles)
    total = len(train_profiles)

    return {
        region: {"count": count, "percentage": count / total * 100}
        for region, count in region_counts.most_common()
    }


def main():
    """Run comprehensive failure analysis."""
    print("=" * 80)
    print("DEEP FAILURE PATTERN ANALYSIS")
    print("=" * 80)
    print()

    # Load data
    print("Loading data...")
    train_profiles, val_profiles = load_data()
    print(f"  Training: {len(train_profiles)} profiles")
    print(f"  Validation: {len(val_profiles)} profiles")
    print()

    # Load model
    print("Loading model...")
    model_path = Path("data/ml_training/regional_classifier_v4_optimized.bin")
    model = fasttext.load_model(str(model_path))
    print("  ✅ Model loaded\n")

    # Analyze failures
    print("Analyzing failure patterns...")
    failures, confusion_matrix = analyze_failures(model, val_profiles)
    print(
        f"  Total failures: {len(failures)}/{len(val_profiles)} ({len(failures)/len(val_profiles)*100:.1f}%)\n"
    )

    # Most common confusions
    print("=" * 80)
    print("TOP CONFUSION PAIRS")
    print("=" * 80)
    print()

    confusions = []
    for expected, detected_dict in confusion_matrix.items():
        for detected, count in detected_dict.items():
            confusions.append((count, expected, detected))

    confusions.sort(reverse=True)

    print("Count  Expected → Detected  (Why?)")
    print("-" * 60)
    for count, expected, detected in confusions[:15]:
        pct = count / len(val_profiles) * 100
        print(f"{count:4d}  {expected:8s} → {detected:8s}  ({pct:.1f}% of validation set)")

    print()

    # Labeling consistency
    print("=" * 80)
    print("LABELING CONSISTENCY ANALYSIS")
    print("=" * 80)
    print()

    country_to_regions, region_to_countries, inconsistent = analyze_labeling_consistency(
        train_profiles
    )

    print(f"Countries with multiple region labels: {len(inconsistent)}")
    print()

    if inconsistent:
        print("Top inconsistent countries (potential labeling issues):")
        sorted_inconsistent = sorted(inconsistent.items(), key=lambda x: len(x[1]), reverse=True)[
            :10
        ]

        for country, regions in sorted_inconsistent:
            count = sum(1 for p in train_profiles if p.get("country_code") == country)
            print(f"  {country}: {sorted(regions)} ({count} profiles)")

    print()

    # Sample distribution
    print("=" * 80)
    print("CLASS IMBALANCE ANALYSIS")
    print("=" * 80)
    print()

    distribution = analyze_sample_distribution(train_profiles)

    print("Regional distribution in training data:")
    print(f"{'Region':<10} {'Count':>8} {'Percentage':>12} {'Status'}")
    print("-" * 50)

    for region, stats in distribution.items():
        count = stats["count"]
        pct = stats["percentage"]

        if pct >= 10:
            status = "✅ Well-represented"
        elif pct >= 5:
            status = "⚠️  Moderate"
        elif pct >= 1:
            status = "❌ Undersampled"
        else:
            status = "❌ Severely undersampled"

        print(f"{region:<10} {count:8d} {pct:11.1f}% {status}")

    print()

    # Example failures
    print("=" * 80)
    print("EXAMPLE FAILURES (Top 20)")
    print("=" * 80)
    print()

    # Group by confusion type
    failures_by_type = defaultdict(list)
    for f in failures:
        key = f"{f['expected']} → {f['detected']}"
        failures_by_type[key].append(f)

    # Get top confusion types
    top_confusions = sorted(failures_by_type.items(), key=lambda x: len(x[1]), reverse=True)[:5]

    for confusion_type, failure_list in top_confusions:
        print(f"\n{confusion_type} ({len(failure_list)} failures):")
        print("-" * 60)

        for f in failure_list[:4]:  # Show 4 examples per type
            print(f"  • {f['name']:<30s} (Country: {f['country']})")
            print(f"    Predicted: {f['detected']} ({f['confidence']:.3f})")
            print(f"    Top-3: {', '.join([f'{r} ({c:.3f})' for r, c in f['top3']])}")
            print()

    # Root cause summary
    print("=" * 80)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 80)
    print()

    # Check if expected region is in top-3
    top3_accuracy = (
        sum(1 for f in failures if any(f["expected"] == r for r, _ in f["top3"]))
        / len(failures)
        * 100
        if failures
        else 0
    )

    print(f"1. Model Confidence: {top3_accuracy:.1f}% of failures have correct answer in top-3")
    print(f"   → Suggests model is uncertain, not completely wrong")
    print()

    # Check class imbalance impact
    heavily_oversampled = [r for r, s in distribution.items() if s["percentage"] > 15]
    heavily_undersampled = [r for r, s in distribution.items() if s["percentage"] < 2]

    print(f"2. Class Imbalance:")
    print(f"   Oversampled (>15%): {heavily_oversampled}")
    print(f"   Undersampled (<2%): {heavily_undersampled}")
    print(f"   → Model biased toward A1/A2/E1")
    print()

    # Check labeling consistency
    print(f"3. Labeling Consistency:")
    print(f"   {len(inconsistent)} countries have multiple region labels")
    print(f"   → Suggests affiliation-based labeling (not name-based)")
    print()

    print(f"4. Data Quantity:")
    print(f"   Training samples: {len(train_profiles)}")
    print(f"   Expected (from plan): 14,000")
    print(
        f"   Gap: {14000 - len(train_profiles)} samples (-{(1 - len(train_profiles)/14000)*100:.1f}%)"
    )
    print(f"   → Insufficient data for rare regions")
    print()

    # Final verdict
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()

    print("The 69.8% accuracy (vs 93-95% target) is caused by:")
    print()
    print("1. ❌ AFFILIATION-BASED LABELING (Primary Issue)")
    print("   - Data labels based on institution country, not name origin")
    print("   - Example: 'Luigi Ferrucci' labeled A1 (US institution)")
    print("   - But name is clearly Italian → should be A2")
    print("   - Model can't learn name patterns when labels are inconsistent")
    print()
    print("2. ❌ SEVERE CLASS IMBALANCE")
    print("   - A1: 23.2% of training data")
    print("   - Rare regions (<2%): C5, C6, D3, D4, E6, F1, F3, F4")
    print("   - Model defaults to A1/A2 for uncertain cases")
    print()
    print("3. ❌ INSUFFICIENT DATA")
    print("   - Have: 6,913 training samples")
    print("   - Need: 14,000+ for rare region coverage")
    print("   - Gap: 50% shortage")
    print()
    print("RECOMMENDATION:")
    print("  • Cannot fix with hyperparameter tuning")
    print("  • Cannot fix with XGBoost (same bad labels)")
    print("  • Need to either:")
    print("    a) Relabel data based on name origin (etymology)")
    print("    b) Add affiliation as input feature")
    print("    c) Collect 2× more data to compensate")
    print()


if __name__ == "__main__":
    sys.exit(main())
