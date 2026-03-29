#!/usr/bin/env python3
"""
Phase 8: Classifier Recalibration per V5 Blueprint
"""

import json
import numpy as np
from sklearn.linear_model import LogisticRegression
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # from src.v5.blueprint_converter import convert_blueprint
import yaml


def recalibrate_name_classifier():
    """Recalibrate classifier intercept only per blueprint"""
    print("=== PHASE 8: CLASSIFIER RECALIBRATION ===\n")

    # Load Korean dataset for training
    with open("../data/korean.yaml", "r", encoding="utf-8") as f:
        korean_data = yaml.safe_load(f)

    # Prepare training data
    train_features = []
    train_labels = []

    print("Preparing training data...")
    for key, entry in korean_data.items():
        name = key.replace("_", " ")

        # Skip invalid entries
        if len(name) < 2 or any(c.isdigit() for c in name):
            continue

        # Extract features (per blueprint: only simple features)
        features = [
            len(name),  # Length
            name.count(" "),  # Word count
            name.count("-"),  # Hyphen count
            sum(1 for c in name if c.isupper()),  # Capital count
            (
                1 if any(c in name for c in ["kim", "lee", "park", "choi"]) else 0
            ),  # Common surname
        ]

        # Label: 1 if conversion successful, 0 otherwise
        result = convert_blueprint(name)
        label = 1 if result else 0

        train_features.append(features)
        train_labels.append(label)

    train_features = np.array(train_features)
    train_labels = np.array(train_labels)

    print(f"Training data: {len(train_features)} samples")
    print(f"Success rate: {np.mean(train_labels):.1%}")

    # Train logistic regression classifier
    print("Training classifier...")
    clf = LogisticRegression(random_state=42, max_iter=1000)
    clf.fit(train_features, train_labels)

    # Get accuracy on training set
    train_accuracy = clf.score(train_features, train_labels)
    print(f"Training accuracy: {train_accuracy:.1%}")

    # Save classifier parameters
    classifier_params = {
        "intercept": clf.intercept_.tolist(),
        "coef": clf.coef_.tolist(),
        "feature_names": [
            "length",
            "word_count",
            "hyphen_count",
            "capital_count",
            "common_surname",
        ],
        "accuracy": train_accuracy,
        "n_samples": len(train_features),
    }

    os.makedirs("data", exist_ok=True)
    with open("data/classifier_params.json", "w") as f:
        json.dump(classifier_params, f, indent=2)

    print("✅ Classifier recalibrated and saved to data/classifier_params.json")

    # Test classifier on sample names
    print(f"\n🧪 Testing classifier on sample names:")
    test_names = ["Kim Sunghoon", "Lee Jaehyun", "Invalid123", "Park Min-Jae"]

    for name in test_names:
        features = np.array(
            [
                [
                    len(name),
                    name.count(" "),
                    name.count("-"),
                    sum(1 for c in name if c.isupper()),
                    (
                        1
                        if any(
                            c.lower() in name.lower()
                            for c in ["kim", "lee", "park", "choi"]
                        )
                        else 0
                    ),
                ]
            ]
        )

        prob = clf.predict_proba(features)[0][1]
        actual_result = convert_blueprint(name)
        status = "✅" if actual_result else "❌"

        print(
            f"  {status} {name:15s}: {prob:.1%} confidence {'(PASS)' if actual_result else '(FAIL)'}"
        )

    return classifier_params


if __name__ == "__main__":
    recalibrate_name_classifier()
