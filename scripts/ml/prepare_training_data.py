#!/usr/bin/env python3
"""
Prepare training data for Phase 2 ML models from Tier 1 dataset.
"""
import json
import random
from pathlib import Path


def load_tier1_data():
    """Load Tier 1 comprehensive test dataset."""
    with open("data/test_suites/tier1_regional_comprehensive.json") as f:
        data = json.load(f)
    return data["test_data"]


def normalize_region_code(region_str):
    """Normalize region code (e.g., 'a1_synthetic' -> 'A1')."""
    return region_str.split("_")[0].upper()


def create_fasttext_format(test_cases, output_file):
    """
    Convert dataset to fastText format:
    __label__<region> <name>
    """
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in test_cases:
            name = entry["CanonicalNative"]
            region = normalize_region_code(entry["Region"])
            # fastText format: __label__<class> <text>
            f.write(f"__label__{region} {name}\n")

    print(f"✅ Created fastText training file: {output_file}")
    print(f"   Total examples: {len(test_cases)}")


def split_train_test(test_cases, train_ratio=0.8, random_seed=42):
    """Split dataset into train and test sets."""
    random.seed(random_seed)

    # Shuffle
    shuffled = test_cases.copy()
    random.shuffle(shuffled)

    # Split
    split_idx = int(len(shuffled) * train_ratio)
    train = shuffled[:split_idx]
    test = shuffled[split_idx:]

    return train, test


def main():
    print("=" * 60)
    print("PHASE 2: ML TRAINING DATA PREPARATION")
    print("=" * 60)
    print()

    # Load data
    print("Loading Tier 1 dataset...")
    test_cases = load_tier1_data()
    print(f"✅ Loaded {len(test_cases)} names")
    print()

    # Analyze distribution
    region_counts = {}
    for entry in test_cases:
        region = normalize_region_code(entry["Region"])
        region_counts[region] = region_counts.get(region, 0) + 1

    print(f"Regional distribution ({len(region_counts)} regions):")
    for region in sorted(region_counts.keys()):
        count = region_counts[region]
        print(f"  {region}: {count:4} names")
    print()

    # Create train/test split
    print("Creating 80/20 train/test split...")
    train, test = split_train_test(test_cases, train_ratio=0.8)
    print(f"✅ Train: {len(train)} names")
    print(f"✅ Test:  {len(test)} names")
    print()

    # Create output directory
    output_dir = Path("data/ml_training")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Save fastText format
    print("Creating fastText training files...")
    create_fasttext_format(train, output_dir / "train.txt")
    create_fasttext_format(test, output_dir / "test.txt")
    print()

    # Save JSON format (for XGBoost later)
    print("Saving JSON format...")
    with open(output_dir / "train.json", "w") as f:
        json.dump(train, f, indent=2)
    with open(output_dir / "test.json", "w") as f:
        json.dump(test, f, indent=2)
    print(f"✅ Saved train.json and test.json")
    print()

    print("=" * 60)
    print("✅ DATA PREPARATION COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Train fastText model: python3 scripts/ml/train_fasttext.py")
    print("2. Evaluate model: python3 scripts/ml/evaluate_fasttext.py")


if __name__ == "__main__":
    main()
