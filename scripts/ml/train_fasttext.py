#!/usr/bin/env python3
"""
Train fastText model for regional name classification.
"""
import fasttext
import time
from pathlib import Path


def train_model(train_file, params):
    """Train fastText supervised model."""
    print("Training fastText model...")
    print(f"  Input: {train_file}")
    print(f"  Parameters:")
    for k, v in params.items():
        print(f"    {k}: {v}")
    print()

    start = time.time()

    model = fasttext.train_supervised(input=str(train_file), **params)

    elapsed = time.time() - start

    print(f"✅ Training complete in {elapsed:.1f}s")
    return model, elapsed


def evaluate_model(model, test_file):
    """Evaluate model on test set."""
    print(f"\n📊 Evaluating on: {test_file}")

    n_samples, precision, recall = model.test(str(test_file))

    # fastText returns precision@1 and recall@1
    accuracy = precision  # For single-label, precision@1 = accuracy

    print(f"  Samples: {n_samples}")
    print(f"  Accuracy (P@1): {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"  Recall@1: {recall:.4f}")

    return {"n_samples": n_samples, "precision": precision, "recall": recall, "accuracy": accuracy}


def test_predictions(model, test_cases):
    """Test model on specific examples."""
    print("\n🧪 Sample Predictions:")
    for name, expected in test_cases:
        pred = model.predict(name, k=3)
        labels = [l.replace("__label__", "") for l in pred[0]]
        probs = pred[1]

        top_pred = labels[0]
        top_prob = probs[0]

        status = "✅" if top_pred == expected else "❌"
        print(f"  {status} {name:30} → {top_pred} ({top_prob:.3f}) [expected: {expected}]")
        print(f"      Top 3: {', '.join(f'{l}:{p:.2f}' for l, p in zip(labels, probs))}")


def main():
    print("=" * 70)
    print("PHASE 2: fastText MODEL TRAINING")
    print("=" * 70)
    print()

    # Configuration
    data_dir = Path("data/ml_training")
    train_file = data_dir / "train.txt"
    val_file = data_dir / "val.txt"
    test_file = data_dir / "test.txt"

    # Hyperparameters (optimized for name classification)
    params = {
        "dim": 100,  # Embedding dimension
        "epoch": 25,  # Training epochs
        "lr": 0.5,  # Learning rate
        "wordNgrams": 3,  # Character n-grams (1-3)
        "loss": "softmax",  # Multi-class classification
        "thread": 4,  # Parallel threads
        "verbose": 2,  # Verbosity
    }

    # Train model
    model, train_time = train_model(train_file, params)

    # Evaluate on validation set
    val_results = evaluate_model(model, val_file)

    # Evaluate on test set
    test_results = evaluate_model(model, test_file)

    # Test on specific examples
    test_cases = [
        ("Vladimir Putin", "B1"),
        ("Zhang Wei", "E1"),
        ("John Smith", "A1"),
        ("José García", "G1"),
        ("Yuki Tanaka", "E3"),
        ("Ahmed Al-Otaibi", "C4"),
        ("Indranil Biswas", "D3"),
        ("Emily O'Brien", "A1"),  # A4 edge case
        ("Kiri Thomas", "A4"),
    ]

    test_predictions(model, test_cases)

    # Save model
    model_file = data_dir / "regional_classifier.bin"
    model.save_model(str(model_file))

    print()
    print("=" * 70)
    print("✅ MODEL TRAINING COMPLETE")
    print("=" * 70)
    print()
    print(f"Training time: {train_time:.1f}s")
    print(f"Model saved to: {model_file}")
    print()
    print(f"Validation accuracy: {val_results['accuracy']*100:.2f}%")
    print(f"Test accuracy: {test_results['accuracy']*100:.2f}%")
    print()
    print("=" * 70)
    print("Next: Integrate into RegionManager and validate on Tier 1")
    print("  python3 scripts/ml/validate_phase2.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
