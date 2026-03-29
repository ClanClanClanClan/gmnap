#!/usr/bin/env python3
"""
Temperature Scaling Calibration

Based on expert guidance (Oct 30, 2025):
- Purpose: Stabilize confidence estimates for Latin-script classes
- Method: Temperature scaling (divide logits by temperature T)
- Recommended: T ≈ 1.1-1.3
- Tune on validation ECE (Expected Calibration Error)

Implementation:
1. Load model predictions + true labels
2. Compute optimal temperature T on validation set
3. Apply temperature scaling to calibrate probabilities
4. Measure ECE before/after
"""

import json
import sys
import fasttext
import numpy as np
from pathlib import Path
from scipy.optimize import minimize_scalar
from typing import Dict, List, Tuple


def load_model_and_data(model_path: Path, val_path: Path) -> Tuple[any, List[Dict]]:
    """Load fastText model and validation data"""
    model = fasttext.load_model(str(model_path))

    with open(val_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data.get("profiles", data if isinstance(data, list) else [])
    return model, profiles


def get_predictions(model, profiles: List[Dict], k: int = 10) -> List[Dict]:
    """Get model predictions with all class probabilities"""
    predictions = []

    for profile in profiles:
        name = profile.get("name", "").strip()
        true_region = profile.get("region")

        if not name or not true_region:
            continue

        # Get top-k predictions
        labels, probs = model.predict(name, k=k)

        # Convert to dict
        pred_dict = {}
        for label, prob in zip(labels, probs):
            region = label.replace("__label__", "")
            pred_dict[region] = float(prob)

        predictions.append(
            {
                "name": name,
                "true_region": true_region,
                "predictions": pred_dict,
                "top1": labels[0].replace("__label__", ""),
                "top1_prob": float(probs[0]),
            }
        )

    return predictions


def compute_ece(predictions: List[Dict], num_bins: int = 10) -> float:
    """
    Compute Expected Calibration Error

    ECE measures how well confidence estimates match actual accuracy
    Lower is better (perfect calibration = 0)
    """
    # Extract confidences and correctness
    confidences = []
    correctness = []

    for pred in predictions:
        conf = pred["top1_prob"]
        correct = 1.0 if pred["top1"] == pred["true_region"] else 0.0
        confidences.append(conf)
        correctness.append(correct)

    confidences = np.array(confidences)
    correctness = np.array(correctness)

    # Create bins
    bins = np.linspace(0, 1, num_bins + 1)

    ece = 0.0
    for i in range(num_bins):
        # Find predictions in this bin
        bin_mask = (confidences > bins[i]) & (confidences <= bins[i + 1])

        if np.sum(bin_mask) == 0:
            continue

        # Average confidence and accuracy in bin
        bin_conf = np.mean(confidences[bin_mask])
        bin_acc = np.mean(correctness[bin_mask])
        bin_size = np.sum(bin_mask)

        # Add weighted difference to ECE
        ece += (bin_size / len(predictions)) * abs(bin_conf - bin_acc)

    return ece


def apply_temperature_scaling(
    predictions: List[Dict], temperature: float
) -> List[Dict]:
    """
    Apply temperature scaling to predictions

    New probabilities = softmax(logits / T)
    T > 1: softens probabilities (more uncertain)
    T < 1: sharpens probabilities (more confident)
    """
    calibrated = []

    for pred in predictions:
        # Get all probabilities
        probs = np.array(list(pred["predictions"].values()))
        regions = list(pred["predictions"].keys())

        # Convert to logits (inverse softmax)
        # p = exp(logit) / sum(exp(logit))
        # logit = log(p) + C (constant cancels in softmax)
        logits = np.log(probs + 1e-10)

        # Apply temperature
        scaled_logits = logits / temperature

        # Convert back to probabilities
        exp_logits = np.exp(
            scaled_logits - np.max(scaled_logits)
        )  # Subtract max for numerical stability
        calibrated_probs = exp_logits / np.sum(exp_logits)

        # Create new prediction dict
        new_pred = pred.copy()
        new_pred["predictions"] = {
            r: float(p) for r, p in zip(regions, calibrated_probs)
        }
        new_pred["top1_prob"] = float(calibrated_probs[regions.index(pred["top1"])])
        new_pred["temperature"] = temperature

        calibrated.append(new_pred)

    return calibrated


def find_optimal_temperature(predictions: List[Dict]) -> float:
    """Find temperature that minimizes ECE on validation set"""

    def objective(T):
        calibrated = apply_temperature_scaling(predictions, T)
        return compute_ece(calibrated)

    # Search in range [0.5, 3.0]
    result = minimize_scalar(objective, bounds=(0.5, 3.0), method="bounded")
    return result.x


def calibrate_model(
    model_path: Path, val_path: Path, output_path: Path, temperature: float = None
):
    """
    Calibrate model using temperature scaling

    If temperature is None, find optimal on validation set
    """

    print("=" * 80)
    print("TEMPERATURE SCALING CALIBRATION")
    print("=" * 80)

    # Load model and data
    print(f"\n[1/5] Loading model and validation data...")
    model, profiles = load_model_and_data(model_path, val_path)
    print(f"  Model: {model_path}")
    print(f"  Validation: {len(profiles):,} profiles")

    # Get predictions
    print(f"\n[2/5] Computing predictions...")
    predictions = get_predictions(model, profiles, k=10)
    print(f"  Predictions: {len(predictions):,}")

    # Measure baseline ECE
    print(f"\n[3/5] Measuring baseline calibration...")
    baseline_ece = compute_ece(predictions)
    baseline_acc = (
        sum(1 for p in predictions if p["top1"] == p["true_region"])
        / len(predictions)
        * 100
    )
    print(f"  Baseline ECE: {baseline_ece:.4f}")
    print(f"  Baseline accuracy: {baseline_acc:.2f}%")

    # Find or use specified temperature
    print(
        f"\n[4/5] {'Finding' if temperature is None else 'Using'} optimal temperature..."
    )
    if temperature is None:
        optimal_T = find_optimal_temperature(predictions)
        print(f"  Optimal T: {optimal_T:.3f}")
    else:
        optimal_T = temperature
        print(f"  Specified T: {optimal_T:.3f}")

    # Apply calibration
    calibrated = apply_temperature_scaling(predictions, optimal_T)
    calibrated_ece = compute_ece(calibrated)
    calibrated_acc = (
        sum(1 for p in calibrated if p["top1"] == p["true_region"])
        / len(calibrated)
        * 100
    )

    print(f"\n  Calibrated ECE: {calibrated_ece:.4f}")
    print(f"  Calibrated accuracy: {calibrated_acc:.2f}%")
    print(
        f"  ECE improvement: {(baseline_ece - calibrated_ece) / baseline_ece * 100:.1f}%"
    )

    # Save results
    print(f"\n[5/5] Saving calibration results...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "calibration": {
            "method": "temperature_scaling",
            "temperature": optimal_T,
            "baseline_ece": baseline_ece,
            "calibrated_ece": calibrated_ece,
            "ece_improvement_pct": (baseline_ece - calibrated_ece) / baseline_ece * 100,
        },
        "accuracy": {"baseline": baseline_acc, "calibrated": calibrated_acc},
        "predictions": calibrated,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {output_path}")

    print("\n" + "=" * 80)
    print(f"CALIBRATION COMPLETE")
    print(f"  Temperature: {optimal_T:.3f}")
    print(
        f"  ECE: {baseline_ece:.4f} → {calibrated_ece:.4f} ({(baseline_ece - calibrated_ece) / baseline_ece * 100:+.1f}%)"
    )
    print("=" * 80)

    return optimal_T, calibrated_ece


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python calibrate.py <model.bin> <val.json> <output.json> [--temperature T]"
        )
        print("\nExample:")
        print(
            "  python calibrate.py data/ml_training/regional_classifier_v5_etymology.bin \\"
        )
        print("                      data/ml_training/val_split_etymo.json \\")
        print("                      reports/calibration.json")
        print("\nOr specify temperature:")
        print("  python calibrate.py ... --temperature 1.2")
        sys.exit(1)

    model_path = Path(sys.argv[1])
    val_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    temperature = None
    if "--temperature" in sys.argv:
        idx = sys.argv.index("--temperature")
        temperature = float(sys.argv[idx + 1])

    calibrate_model(model_path, val_path, output_path, temperature)
