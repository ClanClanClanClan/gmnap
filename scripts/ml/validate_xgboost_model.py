#!/usr/bin/env python3
"""
Validate XGBoost Meta-Classifier

Tests if the meta-classifier improves upon Phase 2 alone.

Current status:
- Phase 1 (rules): ~91% on synthetic, unknown on real
- Phase 2 (ML): 97.54% on synthetic, 68.14% on real
- XGBoost: Training suggests 27% on real (WORSE!)

This script will determine if XGBoost helps or hurts.
"""

import sys
import json
import pickle
import numpy as np
import xgboost as xgb
import fasttext
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.hybrid_classifier import HybridRegionClassifier


def load_metadata():
    """Load label encoder and feature names."""
    metadata_path = Path("data/ml_training/xgboost_metadata.pkl")

    with open(metadata_path, "rb") as f:
        metadata = pickle.load(f)

    return metadata["label_encoder"], metadata["feature_names"]


def load_xgboost_model():
    """Load trained XGBoost model."""
    model_path = Path("data/ml_training/xgboost_meta_classifier.json")
    bst = xgb.Booster()
    bst.load_model(str(model_path))
    return bst


# Import feature extraction from training script
import unicodedata


def get_script_features(name):
    """Extract Unicode script features from name."""
    features = {
        "has_cjk": False,
        "has_cyrillic": False,
        "has_arabic": False,
        "has_devanagari": False,
        "has_greek": False,
        "has_hebrew": False,
        "has_hangul": False,
        "has_hiragana": False,
        "has_katakana": False,
        "has_latin": False,
    }

    for char in name:
        try:
            script = unicodedata.name(char, "").split()[0] if char.strip() else ""

            if any(x in script for x in ["CJK", "IDEOGRAPH"]):
                features["has_cjk"] = True
            elif "CYRILLIC" in script:
                features["has_cyrillic"] = True
            elif "ARABIC" in script:
                features["has_arabic"] = True
            elif "DEVANAGARI" in script:
                features["has_devanagari"] = True
            elif "GREEK" in script:
                features["has_greek"] = True
            elif "HEBREW" in script:
                features["has_hebrew"] = True
            elif "HANGUL" in script:
                features["has_hangul"] = True
            elif "HIRAGANA" in script:
                features["has_hiragana"] = True
            elif "KATAKANA" in script:
                features["has_katakana"] = True
            elif "LATIN" in script:
                features["has_latin"] = True
        except:
            pass

    return features


def extract_features(name, phase1_classifier, phase2_model, feature_names):
    """Extract features for a single name."""
    features = {}

    # Phase 1 (Rules) prediction
    entry = {"CanonicalNative": name}
    try:
        phase1_result = phase1_classifier.detect_region(entry)
    except:
        # Fallback if security validation fails
        from src.regions.base import RegionDetectionResult

        phase1_result = RegionDetectionResult(
            region_code="A1", confidence=0.5, detection_method="fallback", metadata={}
        )

    features["phase1_confidence"] = phase1_result.confidence
    features["phase1_region"] = phase1_result.region_code
    features["phase1_method"] = phase1_result.detection_method

    # Encode phase1_method as numeric
    method_encoding = {
        "unicode_script": 1,
        "systematic_rules": 2,
        "fallback": 3,
        "default": 4,
    }
    features["phase1_method_encoded"] = method_encoding.get(
        phase1_result.detection_method, 0
    )

    # Phase 2 (ML) top-3 predictions
    phase2_pred = phase2_model.predict(name, k=3)

    for i in range(3):
        if i < len(phase2_pred[0]):
            region = phase2_pred[0][i].replace("__label__", "")
            conf = float(phase2_pred[1][i])
            features[f"phase2_top{i+1}_region"] = region
            features[f"phase2_top{i+1}_conf"] = conf
        else:
            features[f"phase2_top{i+1}_region"] = "NONE"
            features[f"phase2_top{i+1}_conf"] = 0.0

    # Name features
    features["name_length"] = len(name)
    features["num_spaces"] = name.count(" ")
    features["num_hyphens"] = name.count("-")
    features["num_periods"] = name.count(".")

    # Script features
    script_feats = get_script_features(name)
    features.update(script_feats)

    # Agreement features
    features["phase1_phase2_agree"] = (
        phase1_result.region_code.split("_")[0]
        == features["phase2_top1_region"].split("_")[0]
    )

    # Convert to numpy array in correct order
    feature_vec = np.zeros(len(feature_names))
    for i, feat_name in enumerate(feature_names):
        val = features.get(feat_name, 0)
        if isinstance(val, bool):
            val = int(val)
        feature_vec[i] = val

    return feature_vec, features["phase2_top1_region"]


def validate_xgboost(model, label_encoder, feature_names, phase1, phase2, profiles):
    """Validate XGBoost on profiles."""
    results = {
        "total": len(profiles),
        "correct": 0,
        "phase2_correct": 0,  # Track Phase 2 alone performance
        "failures": [],
        "regional_stats": defaultdict(lambda: {"total": 0, "correct": 0}),
    }

    print(f"Validating XGBoost on {len(profiles)} profiles...")
    print()

    for i, profile in enumerate(profiles):
        name = profile["name"]
        expected_region = profile["region"]

        # Extract features
        feature_vec, phase2_prediction = extract_features(
            name, phase1, phase2, feature_names
        )

        # XGBoost prediction
        dtest = xgb.DMatrix(feature_vec.reshape(1, -1))
        pred_int = int(model.predict(dtest)[0])
        detected_region = label_encoder[pred_int]

        # Track regional performance
        results["regional_stats"][expected_region]["total"] += 1

        # Check correctness
        is_correct = expected_region == detected_region
        phase2_correct = expected_region == phase2_prediction

        if is_correct:
            results["correct"] += 1
            results["regional_stats"][expected_region]["correct"] += 1

        if phase2_correct:
            results["phase2_correct"] += 1

        if not is_correct:
            results["failures"].append(
                {
                    "name": name,
                    "expected": expected_region,
                    "xgboost_pred": detected_region,
                    "phase2_pred": phase2_prediction,
                    "country": profile.get("country_code", "Unknown"),
                }
            )

        # Progress
        if (i + 1) % 100 == 0 or (i + 1) == len(profiles):
            acc = results["correct"] / (i + 1) * 100
            phase2_acc = results["phase2_correct"] / (i + 1) * 100
            print(
                f"  Progress: {i+1}/{len(profiles)} (XGBoost: {acc:.2f}%, Phase2: {phase2_acc:.2f}%)"
            )

    # Calculate accuracy
    results["accuracy"] = results["correct"] / results["total"] * 100
    results["phase2_accuracy"] = results["phase2_correct"] / results["total"] * 100

    return results


def print_results(results):
    """Print validation results."""
    print(f"\n{'='*80}")
    print("XGBOOST VALIDATION RESULTS")
    print(f"{'='*80}\n")

    print(
        f"XGBoost accuracy: {results['correct']}/{results['total']} = {results['accuracy']:.2f}%"
    )
    print(
        f"Phase 2 alone: {results['phase2_correct']}/{results['total']} = {results['phase2_accuracy']:.2f}%"
    )
    print()

    delta = results["accuracy"] - results["phase2_accuracy"]
    if delta > 0:
        print(f"✅ XGBoost improvement: +{delta:.2f}pp")
    else:
        print(f"❌ XGBoost degradation: {delta:.2f}pp")

    print()
    print("Regional Performance:")
    sorted_regions = sorted(
        results["regional_stats"].items(), key=lambda x: x[1]["total"], reverse=True
    )

    for region, stats in sorted_regions:
        acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✅" if acc >= 90 else "⚠️" if acc >= 70 else "❌"
        print(f"  {status} {region}: {stats['correct']}/{stats['total']} = {acc:.1f}%")


def main():
    """Validate XGBoost meta-classifier."""
    print("=" * 80)
    print("VALIDATING XGBOOST META-CLASSIFIER")
    print("=" * 80)
    print()

    # Load validation data
    val_path = Path("data/ml_training/val_split.json")
    with open(val_path) as f:
        profiles = json.load(f)["profiles"]

    print(f"✅ Loaded {len(profiles)} validation profiles\n")

    # Load models
    print("Loading models...")
    label_encoder, feature_names = load_metadata()
    xgb_model = load_xgboost_model()
    phase1 = HybridRegionClassifier(use_ml=False)
    phase2 = fasttext.load_model("data/ml_training/regional_classifier_v3_real.bin")

    print(f"✅ Loaded XGBoost + Phase 1 + Phase 2\n")

    # Validate
    results = validate_xgboost(
        xgb_model, label_encoder, feature_names, phase1, phase2, profiles
    )

    # Print results
    print_results(results)

    print(f"\n{'='*80}")
    print("VERDICT")
    print(f"{'='*80}\n")

    if results["accuracy"] >= 90:
        print("✅ EXCELLENT: XGBoost achieves ≥90%!")
        print("   Phase 3 complete, ready for final test set validation")
    elif results["accuracy"] >= results["phase2_accuracy"]:
        print("✅ IMPROVEMENT: XGBoost better than Phase 2 alone")
        print(f"   {results['phase2_accuracy']:.2f}% → {results['accuracy']:.2f}%")
    else:
        print("❌ DEGRADATION: XGBoost worse than Phase 2 alone")
        print(f"   {results['phase2_accuracy']:.2f}% → {results['accuracy']:.2f}%")
        print("   Recommendation: Use Phase 2 alone, skip XGBoost")

    return 0


if __name__ == "__main__":
    sys.exit(main())
