#!/usr/bin/env python3
"""
Comprehensive Evaluation with Top-K, Abstention, and Per-Script Analysis

Based on expert guidance (Oct 30, 2025):
- Top-3 accuracy: "operationally the more relevant success metric"
- Abstention: Return abstained=true if max(p) < τ (suggest τ≈0.55)
- Per-script subset evaluation: Latin vs Non-Latin breakdown

Expert's targets after relabeling:
- Overall accuracy ≥ 0.85 (macro‑F1 ≥ 0.82)
- Top‑3 ≥ 0.95
- Latin‑script subsets (A1/A2/A3/G1): ≥ 0.80
- Non‑Latin subsets (E1/E3/E4): ≥ 0.90
"""

import json
import sys
import fasttext
import unicodedata
import numpy as np
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


def detect_script(name: str) -> str:
    """Detect dominant script"""
    for char in name:
        if not char.strip():
            continue
        sname = unicodedata.name(char, "").split()[0]
        if any(
            x in sname
            for x in [
                "HANGUL",
                "CJK",
                "HIRAGANA",
                "KATAKANA",
                "CYRILLIC",
                "GREEK",
                "ARABIC",
                "DEVANAGARI",
                "BENGALI",
                "TAMIL",
                "TELUGU",
            ]
        ):
            return "Non-Latin"
    return "Latin"


def evaluate_comprehensive(
    model_path: Path,
    test_path: Path,
    calibration_path: Path = None,
    abstention_threshold: float = 0.55,
):
    """Comprehensive evaluation with all metrics"""

    print("=" * 80)
    print("COMPREHENSIVE EVALUATION")
    print("=" * 80)

    # Load model
    print(f"\n[1/5] Loading model...")
    model = fasttext.load_model(str(model_path))
    print(f"  Model: {model_path.name}")

    # Load calibration if available
    temperature = None
    if calibration_path and calibration_path.exists():
        with open(calibration_path, "r") as f:
            calib = json.load(f)
            temperature = calib["calibration"]["temperature"]
        print(f"  Calibration: T = {temperature:.3f}")

    # Load test data
    print(f"\n[2/5] Loading test data...")
    with open(test_path, "r") as f:
        data = json.load(f)
    profiles = data.get("profiles", data if isinstance(data, list) else [])
    print(f"  Test set: {len(profiles):,} profiles")

    # Evaluate
    print(f"\n[3/5] Computing predictions (top-3 + abstention)...")

    results = {
        "total": 0,
        "correct_top1": 0,
        "correct_top3": 0,
        "abstained": 0,
        "by_script": defaultdict(
            lambda: {"total": 0, "correct_top1": 0, "correct_top3": 0, "abstained": 0}
        ),
        "by_region": defaultdict(lambda: {"total": 0, "correct_top1": 0, "correct_top3": 0}),
        "predictions": [],
    }

    for profile in profiles:
        name = profile.get("name", "").strip()
        true_region = profile.get("region")

        if not name or not true_region:
            continue

        # Predict top-3
        labels, probs = model.predict(name, k=3)
        top1_region = labels[0].replace("__label__", "")
        top3_regions = [l.replace("__label__", "") for l in labels]
        top1_prob = float(probs[0])

        # Apply temperature scaling if available
        if temperature:
            # Approximate: scale probability
            # More accurate would be to scale logits, but fastText doesn't expose them
            # This is a simplified approximation
            top1_prob = top1_prob ** (1 / temperature)

        # Check abstention
        should_abstain = top1_prob < abstention_threshold

        # Detect script
        script = detect_script(name)

        # Record result
        results["total"] += 1
        results["by_script"][script]["total"] += 1
        results["by_region"][true_region]["total"] += 1

        is_top1_correct = top1_region == true_region
        is_top3_correct = true_region in top3_regions

        if not should_abstain:
            if is_top1_correct:
                results["correct_top1"] += 1
                results["by_script"][script]["correct_top1"] += 1
                results["by_region"][true_region]["correct_top1"] += 1

            if is_top3_correct:
                results["correct_top3"] += 1
                results["by_script"][script]["correct_top3"] += 1
                results["by_region"][true_region]["correct_top3"] += 1
        else:
            results["abstained"] += 1
            results["by_script"][script]["abstained"] += 1

        results["predictions"].append(
            {
                "name": name,
                "true_region": true_region,
                "top1": top1_region,
                "top3": top3_regions,
                "top1_prob": top1_prob,
                "correct_top1": is_top1_correct,
                "correct_top3": is_top3_correct,
                "abstained": should_abstain,
                "script": script,
            }
        )

    # Compute metrics
    print(f"\n[4/5] Computing metrics...")

    non_abstained = results["total"] - results["abstained"]

    overall_top1 = results["correct_top1"] / non_abstained * 100 if non_abstained > 0 else 0
    overall_top3 = results["correct_top3"] / non_abstained * 100 if non_abstained > 0 else 0
    abstention_rate = results["abstained"] / results["total"] * 100

    print(f"\n  Overall (excluding abstentions):")
    print(f"    Top-1 accuracy: {overall_top1:.2f}% ({results['correct_top1']}/{non_abstained})")
    print(f"    Top-3 accuracy: {overall_top3:.2f}% ({results['correct_top3']}/{non_abstained})")
    print(
        f"    Abstention rate: {abstention_rate:.1f}% ({results['abstained']}/{results['total']})"
    )

    print(f"\n  Per-Script Breakdown:")
    for script in ["Latin", "Non-Latin"]:
        stats = results["by_script"][script]
        if stats["total"] > 0:
            non_ab = stats["total"] - stats["abstained"]
            top1 = stats["correct_top1"] / non_ab * 100 if non_ab > 0 else 0
            top3 = stats["correct_top3"] / non_ab * 100 if non_ab > 0 else 0
            ab_rate = stats["abstained"] / stats["total"] * 100
            print(
                f"    {script:12s}: Top-1: {top1:5.1f}%  Top-3: {top3:5.1f}%  Abstained: {ab_rate:4.1f}%  (n={stats['total']})"
            )

    print(f"\n  Top-10 Regions by Sample Size:")
    sorted_regions = sorted(
        results["by_region"].items(), key=lambda x: x[1]["total"], reverse=True
    )[:10]
    for region, stats in sorted_regions:
        if stats["total"] > 0:
            top1 = stats["correct_top1"] / stats["total"] * 100
            top3 = stats["correct_top3"] / stats["total"] * 100
            print(
                f"    {region:4s}: Top-1: {top1:5.1f}%  Top-3: {top3:5.1f}%  (n={stats['total']})"
            )

    # Compare to expert targets
    print(f"\n[5/5] Comparison to Expert Targets:")
    print(f"  Metric                      | Target   | Achieved | Status")
    print(f"  --------------------------- | -------- | -------- | ------")
    print(
        f"  Overall Top-1 accuracy      | ≥85.0%   | {overall_top1:6.2f}% | {'✅ PASS' if overall_top1 >= 85 else '⚠️  CLOSE' if overall_top1 >= 80 else '❌ MISS'}"
    )
    print(
        f"  Top-3 accuracy              | ≥95.0%   | {overall_top3:6.2f}% | {'✅ PASS' if overall_top3 >= 95 else '⚠️  CLOSE' if overall_top3 >= 90 else '❌ MISS'}"
    )

    latin_top1 = (
        results["by_script"]["Latin"]["correct_top1"]
        / (results["by_script"]["Latin"]["total"] - results["by_script"]["Latin"]["abstained"])
        * 100
        if (results["by_script"]["Latin"]["total"] - results["by_script"]["Latin"]["abstained"]) > 0
        else 0
    )
    print(
        f"  Latin scripts (A1/A2/A3/G1) | ≥80.0%   | {latin_top1:6.2f}% | {'✅ PASS' if latin_top1 >= 80 else '⚠️  CLOSE' if latin_top1 >= 75 else '❌ MISS'}"
    )

    non_latin_top1 = (
        results["by_script"]["Non-Latin"]["correct_top1"]
        / (
            results["by_script"]["Non-Latin"]["total"]
            - results["by_script"]["Non-Latin"]["abstained"]
        )
        * 100
        if (
            results["by_script"]["Non-Latin"]["total"]
            - results["by_script"]["Non-Latin"]["abstained"]
        )
        > 0
        else 0
    )
    if results["by_script"]["Non-Latin"]["total"] > 10:
        print(
            f"  Non-Latin scripts (E1/E3/E4)| ≥90.0%   | {non_latin_top1:6.2f}% | {'✅ PASS' if non_latin_top1 >= 90 else '⚠️  CLOSE' if non_latin_top1 >= 85 else '❌ MISS'}"
        )
    else:
        print(
            f"  Non-Latin scripts (E1/E3/E4)| ≥90.0%   | N/A (n={results['by_script']['Non-Latin']['total']}) | ⚠️  TOO FEW"
        )

    print("\n" + "=" * 80)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python evaluate_comprehensive.py <model.bin> <test.json> [--calibration calib.json] [--threshold 0.55]"
        )
        print("\nExample:")
        print("  python evaluate_comprehensive.py \\")
        print("    data/ml_training/regional_classifier_v5_etymology.bin \\")
        print("    data/ml_training/test_split_etymo.json \\")
        print("    --calibration reports/calibration_v5.json \\")
        print("    --threshold 0.55")
        sys.exit(1)

    model_path = Path(sys.argv[1])
    test_path = Path(sys.argv[2])

    calibration_path = None
    if "--calibration" in sys.argv:
        idx = sys.argv.index("--calibration")
        calibration_path = Path(sys.argv[idx + 1])

    threshold = 0.55
    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        threshold = float(sys.argv[idx + 1])

    evaluate_comprehensive(model_path, test_path, calibration_path, threshold)
