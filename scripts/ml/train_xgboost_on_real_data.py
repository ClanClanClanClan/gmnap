#!/usr/bin/env python3
"""
Phase 3: Train XGBoost Meta-Classifier on REAL Collected Data

This script trains the XGBoost meta-classifier on the 6,913 real mathematician
profiles collected from OpenAlex, not on synthetic test data.

Expected improvement: 40% → 90%+ on real-world mathematician names
"""

import json
import sys
import numpy as np
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost not installed. Install with: pip install xgboost")
    sys.exit(1)

from src.regions.hybrid_classifier import HybridRegionClassifier


class SimpleFeatureExtractor:
    """Simplified feature extractor for real data training."""

    REGIONS = [
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "B1",
        "B2",
        "B3",
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7",
        "C8",
        "C9",
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
        "E7",
        "F1",
        "F2",
        "F3",
        "F4",
        "G1",
        "H1",
        "R0",
    ]

    def extract_features(self, name: str, phase1_result, phase2_results) -> list:
        """
        Extract features from name + Phase 1 + Phase 2 predictions.

        Returns 40 features:
        - Phase 1 confidence (1)
        - Phase 1 region one-hot (37)
        - Phase 2 top-1 confidence (1)
        - Phase 1/Phase 2 agreement flag (1)
        """
        features = []

        # Phase 1 confidence
        features.append(phase1_result.confidence)

        # Phase 1 region one-hot (37 features)
        p1_region = phase1_result.region_code.split("_")[0].upper()
        for region in self.REGIONS:
            features.append(1.0 if p1_region == region else 0.0)

        # Phase 2 top-1 confidence
        p2_conf = phase2_results[0].confidence if phase2_results else 0.0
        features.append(p2_conf)

        # Agreement flag
        if phase2_results:
            p2_region = phase2_results[0].region_code.split("_")[0].upper()
            agreement = 1.0 if p1_region == p2_region else 0.0
        else:
            agreement = 0.0
        features.append(agreement)

        return features

    def _region_to_ordinal(self, region_code: str) -> int:
        """Map region code to ordinal (0-36)."""
        region = region_code.split("_")[0].upper()
        try:
            return self.REGIONS.index(region)
        except ValueError:
            return len(self.REGIONS) - 1  # Default to R0


def main():
    print("=" * 80)
    print("Phase 3: Training XGBoost on REAL Collected Data")
    print("=" * 80)
    print()

    # Initialize classifier
    print("Initializing hybrid classifier...")
    classifier = HybridRegionClassifier()
    feature_extractor = SimpleFeatureExtractor()
    print()

    # Load REAL training data
    train_file = Path(__file__).parent.parent.parent / "data" / "ml_training" / "train_split.json"
    test_file = Path(__file__).parent.parent.parent / "data" / "ml_training" / "test_split.json"

    print(f"Loading training data from: {train_file}")
    with open(train_file) as f:
        train_data = json.load(f)
    train_profiles = train_data.get("profiles", [])
    print(f"✅ Loaded {len(train_profiles)} training profiles")
    print()

    print(f"Loading test data from: {test_file}")
    with open(test_file) as f:
        test_data = json.load(f)
    test_profiles = test_data.get("profiles", [])
    print(f"✅ Loaded {len(test_profiles)} test profiles")
    print()

    # Extract features for training set
    print("Extracting features from training data...")
    X_train = []
    y_train = []

    for i, profile in enumerate(train_profiles):
        if (i + 1) % 1000 == 0:
            print(f"  Processed {i+1}/{len(train_profiles)} training profiles...")

        # Create entry format
        entry = {"CanonicalLatin": profile["name"]}

        # Get predictions
        phase1_result = classifier.phase1.detect_region(entry)
        phase2_results = []

        if classifier.use_ml and classifier.phase2:
            try:
                pred = classifier.phase2.predict(profile["name"], k=3)
                for j in range(min(3, len(pred[0]))):
                    from src.regions.hybrid_classifier import DetectionResult

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

        # Extract features
        features = feature_extractor.extract_features(
            profile["name"], phase1_result, phase2_results
        )
        X_train.append(features)

        # Label (from real data ground truth)
        y_train.append(feature_extractor._region_to_ordinal(profile["region"]))

    print(f"  Processed {len(train_profiles)}/{len(train_profiles)} training profiles")
    print()

    # Extract features for test set
    print("Extracting features from test data...")
    X_test = []
    y_test = []

    for i, profile in enumerate(test_profiles):
        if (i + 1) % 500 == 0:
            print(f"  Processed {i+1}/{len(test_profiles)} test profiles...")

        # Create entry format
        entry = {"CanonicalLatin": profile["name"]}

        # Get predictions
        phase1_result = classifier.phase1.detect_region(entry)
        phase2_results = []

        if classifier.use_ml and classifier.phase2:
            try:
                pred = classifier.phase2.predict(profile["name"], k=3)
                for j in range(min(3, len(pred[0]))):
                    from src.regions.hybrid_classifier import DetectionResult

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

        # Extract features
        features = feature_extractor.extract_features(
            profile["name"], phase1_result, phase2_results
        )
        X_test.append(features)

        # Label
        y_test.append(feature_extractor._region_to_ordinal(profile["region"]))

    print(f"  Processed {len(test_profiles)}/{len(test_profiles)} test profiles")
    print()

    X_train = np.array(X_train)
    y_train = np.array(y_train)
    X_test = np.array(X_test)
    y_test = np.array(y_test)

    print(f"Training set: {X_train.shape}")
    print(f"Test set: {X_test.shape}")
    print()

    # Train XGBoost
    print("Training XGBoost meta-classifier...")
    print()

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    # XGBoost parameters
    params = {
        "objective": "multi:softprob",
        "num_class": len(feature_extractor.REGIONS),
        "max_depth": 6,
        "eta": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "mlogloss",
        "seed": 42,
    }

    # Train with early stopping
    evals = [(dtrain, "train"), (dtest, "test")]
    bst = xgb.train(
        params, dtrain, num_boost_round=100, evals=evals, early_stopping_rounds=10, verbose_eval=10
    )

    print()
    print("Training complete!")
    print()

    # Evaluate
    print("=" * 80)
    print("EVALUATION ON REAL DATA")
    print("=" * 80)
    print()

    # Test accuracy
    preds = bst.predict(dtest)
    pred_labels = np.argmax(preds, axis=1)
    accuracy = (pred_labels == y_test).mean()

    print(f"Test accuracy: {accuracy*100:.2f}%")
    print()

    # Per-region accuracy
    region_correct = defaultdict(int)
    region_total = defaultdict(int)

    for true_label, pred_label in zip(y_test, pred_labels):
        region = feature_extractor.REGIONS[true_label]
        region_total[region] += 1
        if true_label == pred_label:
            region_correct[region] += 1

    print("Per-region accuracy:")
    for region in sorted(region_total.keys()):
        if region_total[region] > 0:
            acc = region_correct[region] / region_total[region] * 100
            print(f"  {region}: {acc:.1f}% ({region_correct[region]}/{region_total[region]})")
    print()

    # Save model
    model_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "ml_training"
        / "xgboost_metaclassifier_real.json"
    )
    bst.save_model(str(model_file))

    print(f"Model saved to: {model_file}")
    print()

    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Validate on full real-world dataset")
    print("2. Compare with Phase 1 + Phase 2 baselines")
    print("3. Deploy if accuracy ≥ 90%")
    print()


if __name__ == "__main__":
    if not XGBOOST_AVAILABLE:
        print("XGBoost is required. Install with: pip install xgboost")
        sys.exit(1)
    main()
