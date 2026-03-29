#!/usr/bin/env python3
"""
Train fastText on Real Mathematician Data

Retrains Phase 2 ML classifier on:
- 69.7% real mathematician data (6,913 profiles with country-mapped regions)
- 30.3% synthetic data (3,000 samples for rare region coverage)

This addresses the catastrophic overfitting issue:
- Old model (100% synthetic): 97.54% synthetic test, 40.67% real-world
- New model (70% real): Should achieve 85-90% real-world accuracy

Training parameters optimized for name classification:
- lr=0.1: Learning rate
- epoch=25: Training iterations
- wordNgrams=2: Bigram features (captures name patterns)
- dim=100: Embedding dimension
- minn=3, maxn=6: Character n-grams (3-6 chars)
"""

import sys
import fasttext
from pathlib import Path


def train_model():
    """Train fastText model on real mathematician data."""
    input_path = Path("data/ml_training/real_mathematicians_train.txt")
    output_path = Path("data/ml_training/regional_classifier_v3_real.bin")

    print("=" * 80)
    print("TRAINING FASTTEXT ON REAL MATHEMATICIAN DATA")
    print("=" * 80)
    print()

    if not input_path.exists():
        print(f"❌ Training data not found: {input_path}")
        print("   Run: python3 scripts/ml/prepare_fasttext_training_data.py")
        return 1

    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print()

    print("Training parameters:")
    print("  lr=0.1 (learning rate)")
    print("  epoch=25 (training iterations)")
    print("  wordNgrams=2 (bigram features)")
    print("  dim=100 (embedding dimension)")
    print("  minn=3, maxn=6 (character n-grams)")
    print("  loss='softmax' (multi-class classification)")
    print()

    print("Training...")
    print("-" * 80)

    model = fasttext.train_supervised(
        input=str(input_path),
        lr=0.1,
        epoch=25,
        wordNgrams=2,
        dim=100,
        loss="softmax",
        minn=3,
        maxn=6,
        verbose=2,  # Show progress
    )

    print("-" * 80)
    print()

    # Save model
    print(f"Saving model to {output_path}...")
    model.save_model(str(output_path))
    print(f"✅ Model saved\n")

    # Quick validation on training data
    print("Quick self-test on training data:")
    test_result = model.test(str(input_path))
    n_samples, precision, recall = test_result
    print(f"  Samples: {n_samples}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall: {recall:.4f}")
    print()

    # Test on some examples
    print("Sample predictions:")
    test_names = [
        "John Smith",  # A1 (Anglo)
        "Hans Mueller",  # A2 (German)
        "Jean Dubois",  # A2 (French)
        "Juan Rodriguez",  # G1 (Latin America)
        "Wang Wei",  # E1 (Sinophone)
        "Tanaka Yuki",  # E3 (Japan)
        "Kim Min-jun",  # E4 (Korea)
        "Ivan Petrov",  # B1 (East Slavic)
    ]

    for name in test_names:
        pred = model.predict(name, k=1)
        region = pred[0][0].replace("__label__", "")
        confidence = pred[1][0]
        print(f"  {name:20s} → {region} ({confidence:.3f})")

    print()
    print("=" * 80)
    print("✅ TRAINING COMPLETE")
    print("=" * 80)
    print()
    print(f"Model saved to: {output_path}")
    print()
    print("Next steps:")
    print("  1. Validate on validation set:")
    print("     python3 scripts/ml/validate_retrained_model.py")
    print()
    print("  2. If ≥90% on validation, test on held-out test set")
    print("  3. If <90%, proceed to XGBoost meta-classifier")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(train_model())
