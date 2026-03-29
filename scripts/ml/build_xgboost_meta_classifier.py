#!/usr/bin/env python3
"""
Build XGBoost Meta-Classifier (Phase 3 Final Step)

Combines Phase 1 (rules) + Phase 2 (ML) predictions with engineered features
to achieve 85-95% accuracy on real mathematician data.

Features:
1. Phase 1 rule prediction + confidence + method
2. Phase 2 ML top-3 predictions + confidences
3. Name features: length, has_cjk, has_cyrillic, has_arabic, etc.

The meta-classifier learns when to trust rules vs ML, addressing the
fundamental issue: Phase 2 ML classifies by etymology, Phase 1 may have
better signals for some cases.

Expected improvement: 68% → 85-95%
"""

import sys
import json
import pickle
import numpy as np
import xgboost as xgb
import fasttext
from pathlib import Path
from collections import Counter
import unicodedata
import regex  # For Unicode script detection

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.hybrid_classifier import HybridRegionClassifier


# Unicode script ranges for feature extraction
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

    return features


def extract_features(name, phase1_classifier, phase2_model):
    """
    Extract all features for meta-classifier.

    Returns:
        dict of features
    """
    features = {}

    # Phase 1 (Rules) prediction
    entry = {"CanonicalNative": name}
    phase1_result = phase1_classifier.detect_region(entry)

    features["phase1_confidence"] = phase1_result.confidence
    features["phase1_region"] = phase1_result.region_code
    features["phase1_method"] = phase1_result.detection_method

    # Encode phase1_method as numeric
    method_encoding = {"unicode_script": 1, "systematic_rules": 2, "fallback": 3, "default": 4}
    features["phase1_method_encoded"] = method_encoding.get(phase1_result.detection_method, 0)

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
        phase1_result.region_code.split("_")[0] == features["phase2_top1_region"].split("_")[0]
    )

    return features


def prepare_training_data(profiles, phase1_classifier, phase2_model):
    """
    Prepare training data for XGBoost.

    Args:
        profiles: List of profiles with name + region
        phase1_classifier: Phase 1 rule-based classifier
        phase2_model: Phase 2 fastText model

    Returns:
        X (features), y (labels), label_encoder
    """
    print(f"Extracting features from {len(profiles)} profiles...")

    X_dicts = []
    y_raw = []

    for i, profile in enumerate(profiles):
        if (i + 1) % 500 == 0:
            print(f"  Progress: {i+1}/{len(profiles)}")

        name = profile["name"]
        region = profile["region"]

        # Extract features
        feats = extract_features(name, phase1_classifier, phase2_model)

        X_dicts.append(feats)
        y_raw.append(region)

    print(f"✅ Extracted features from {len(X_dicts)} profiles\n")

    # Encode regions as integers
    unique_regions = sorted(set(y_raw))
    region_to_int = {r: i for i, r in enumerate(unique_regions)}
    int_to_region = {i: r for r, i in region_to_int.items()}

    y = np.array([region_to_int[r] for r in y_raw])

    # Convert feature dicts to DMatrix
    # We need to handle categorical features (region codes)
    # For simplicity, let's just use numeric features for now

    numeric_features = [
        "phase1_confidence",
        "phase1_method_encoded",
        "phase2_top1_conf",
        "phase2_top2_conf",
        "phase2_top3_conf",
        "name_length",
        "num_spaces",
        "num_hyphens",
        "num_periods",
        "has_cjk",
        "has_cyrillic",
        "has_arabic",
        "has_devanagari",
        "has_greek",
        "has_hebrew",
        "has_hangul",
        "has_hiragana",
        "has_katakana",
        "has_latin",
        "phase1_phase2_agree",
    ]

    X = np.zeros((len(X_dicts), len(numeric_features)))

    for i, feat_dict in enumerate(X_dicts):
        for j, feat_name in enumerate(numeric_features):
            val = feat_dict.get(feat_name, 0)
            # Convert bool to int
            if isinstance(val, bool):
                val = int(val)
            X[i, j] = val

    return X, y, int_to_region, numeric_features


def train_xgboost(X_train, y_train, X_val, y_val):
    """Train XGBoost classifier."""
    print("Training XGBoost meta-classifier...")
    print(f"  Train: {len(X_train)} samples")
    print(f"  Validation: {len(X_val)} samples")
    print()

    # Create DMatrix
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)

    # XGBoost parameters
    params = {
        "objective": "multi:softmax",
        "num_class": int(y_train.max() + 1),
        "max_depth": 6,
        "eta": 0.1,
        "eval_metric": "merror",
        "seed": 42,
    }

    print("XGBoost parameters:")
    for k, v in params.items():
        print(f"  {k}: {v}")
    print()

    # Train
    evals = [(dtrain, "train"), (dval, "val")]
    bst = xgb.train(
        params, dtrain, num_boost_round=100, evals=evals, early_stopping_rounds=10, verbose_eval=10
    )

    print()
    print(f"✅ Training complete (best iteration: {bst.best_iteration})")

    return bst


def save_model(model, label_encoder, feature_names):
    """Save XGBoost model and metadata."""
    output_dir = Path("data/ml_training")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = output_dir / "xgboost_meta_classifier.json"
    model.save_model(str(model_path))

    # Save metadata
    metadata_path = output_dir / "xgboost_metadata.pkl"
    metadata = {"label_encoder": label_encoder, "feature_names": feature_names}

    with open(metadata_path, "wb") as f:
        pickle.dump(metadata, f)

    print(f"✅ Saved model to {model_path}")
    print(f"✅ Saved metadata to {metadata_path}")


def main():
    """Build XGBoost meta-classifier."""
    print("=" * 80)
    print("BUILDING XGBOOST META-CLASSIFIER (Phase 3)")
    print("=" * 80)
    print()

    # Load train and validation splits
    print("Loading training and validation data...")
    train_path = Path("data/ml_training/train_split.json")
    val_path = Path("data/ml_training/val_split.json")

    with open(train_path) as f:
        train_profiles = json.load(f)["profiles"]

    with open(val_path) as f:
        val_profiles = json.load(f)["profiles"]

    print(f"✅ Train: {len(train_profiles)} profiles")
    print(f"✅ Validation: {len(val_profiles)} profiles\n")

    # Load Phase 1 and Phase 2 models
    print("Loading Phase 1 (rules) and Phase 2 (ML) models...")

    # Phase 1
    phase1 = HybridRegionClassifier(use_ml=False)

    # Phase 2
    phase2_model_path = Path("data/ml_training/regional_classifier_v3_real.bin")
    phase2 = fasttext.load_model(str(phase2_model_path))

    print(f"✅ Phase 1 loaded")
    print(f"✅ Phase 2 loaded\n")

    # Prepare training data
    print("Preparing training data...")
    X_train, y_train, label_encoder, feature_names = prepare_training_data(
        train_profiles, phase1, phase2
    )

    print("Preparing validation data...")
    X_val, y_val, _, _ = prepare_training_data(val_profiles, phase1, phase2)

    # Train XGBoost
    model = train_xgboost(X_train, y_train, X_val, y_val)

    # Save model
    print("\nSaving model...")
    save_model(model, label_encoder, feature_names)

    print(f"\n{'='*80}")
    print("✅ XGBOOST META-CLASSIFIER BUILT")
    print(f"{'='*80}\n")
    print("Next step: Validate on validation set")
    print("  python3 scripts/ml/validate_xgboost_model.py\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
