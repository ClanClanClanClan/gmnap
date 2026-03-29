#!/usr/bin/env python3
"""
Retrain fastText with Optimized Hyperparameters

The current model achieves only 68.14% validation accuracy vs expected 93-95%.
This script retrains with improved parameters for name classification.

CRITICAL CHANGES:
1. epoch: 25 → 100 (more training iterations)
2. lr: 0.1 → 0.5 (higher learning rate for small dataset)
3. wordNgrams: 2 → 3 (trigram features)
4. minn/maxn: 3-6 → 2-5 (better character ngrams for names)
5. dim: 100 → 200 (larger embeddings)
6. loss: 'softmax' → 'ova' (one-vs-all for imbalanced classes)

Expected improvement: 68.14% → 85-90%
"""

import sys
import fasttext
from pathlib import Path
from datetime import datetime


def train_optimized_model():
    """Train fastText model with optimized hyperparameters."""
    input_path = Path("data/ml_training/real_mathematicians_train.txt")
    output_path = Path("data/ml_training/regional_classifier_v4_optimized.bin")

    print("=" * 80)
    print("RETRAINING FASTTEXT WITH OPTIMIZED HYPERPARAMETERS")
    print("=" * 80)
    print()
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not input_path.exists():
        print(f"❌ Training data not found: {input_path}")
        print("   Run: python3 scripts/ml/prepare_fasttext_training_data.py")
        return 1

    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print()

    # Optimized parameters for name classification
    params = {
        "lr": 0.5,  # Higher learning rate (was 0.1)
        "epoch": 100,  # More epochs (was 25)
        "wordNgrams": 3,  # Trigrams (was 2)
        "dim": 200,  # Larger embeddings (was 100)
        "loss": "ova",  # One-vs-all for imbalanced classes (was softmax)
        "minn": 2,  # Shorter min n-gram (was 3)
        "maxn": 5,  # Shorter max n-gram (was 6)
        "verbose": 2,  # Show progress
        "thread": 8,  # Parallel threads
    }

    print("OPTIMIZED TRAINING PARAMETERS:")
    print(f"  lr={params['lr']} (was 0.1) - Higher learning rate for small dataset")
    print(f"  epoch={params['epoch']} (was 25) - More training iterations")
    print(f"  wordNgrams={params['wordNgrams']} (was 2) - Trigram features")
    print(f"  dim={params['dim']} (was 100) - Larger embeddings")
    print(f"  loss='{params['loss']}' (was 'softmax') - Better for imbalanced classes")
    print(f"  minn={params['minn']}, maxn={params['maxn']} (was 3-6) - Optimized for names")
    print()

    print("Training...")
    print("-" * 80)

    model = fasttext.train_supervised(input=str(input_path), **params)

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
    print(f"  Precision: {precision:.4f} ({precision*100:.1f}%)")
    print(f"  Recall: {recall:.4f} ({recall*100:.1f}%)")
    print()

    if precision < 0.90:
        print("⚠️  Warning: Training accuracy < 90% suggests underfitting")
        print("   Consider increasing epochs or learning rate")
    elif precision > 0.99:
        print("⚠️  Warning: Training accuracy > 99% suggests potential overfitting")
        print("   Check validation accuracy carefully")
    else:
        print("✅ Training accuracy looks healthy (90-99%)")
    print()

    # Test on sample names
    print("Sample predictions:")
    test_names = [
        ("John Smith", "A1"),  # English
        ("Hans Mueller", "A2"),  # German
        ("Jean Dubois", "A2"),  # French
        ("Juan Rodriguez", "G1"),  # Spanish
        ("Wang Wei", "E1"),  # Chinese
        ("Tanaka Yuki", "E3"),  # Japanese
        ("Kim Min-jun", "E4"),  # Korean
        ("Ivan Petrov", "B1"),  # Russian
        ("Miguel Cruz", "G1"),  # Latin American
        ("José García", "G1"),  # Spanish
    ]

    correct = 0
    for name, expected in test_names:
        pred = model.predict(name, k=1)
        region = pred[0][0].replace("__label__", "")
        confidence = pred[1][0]

        is_correct = region == expected
        if is_correct:
            correct += 1

        status = "✅" if is_correct else "❌"
        print(f"  {status} {name:20s} → {region} ({confidence:.3f}) [expected: {expected}]")

    print()
    print(f"Sample test accuracy: {correct}/{len(test_names)} = {correct/len(test_names)*100:.1f}%")
    print()

    print("=" * 80)
    print("✅ TRAINING COMPLETE")
    print("=" * 80)
    print()
    print(f"Model saved to: {output_path}")
    print()
    print("Next steps:")
    print("  1. Validate on validation set:")
    print("     python3 scripts/ml/validate_optimized_model.py")
    print()
    print("  2. Expected improvement:")
    print("     Old (v3): 68.14% validation accuracy")
    print("     New (v4): Target 85-90% validation accuracy")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(train_optimized_model())
