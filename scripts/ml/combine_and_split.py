#!/usr/bin/env python3
"""
Combine synthetic + real-world datasets and create train/val/test splits.
"""
import json
import random
from pathlib import Path
from collections import defaultdict


def load_dataset(file_path):
    """Load a dataset JSON file."""
    with open(file_path) as f:
        data = json.load(f)
    return data["data"]


def create_stratified_split(data, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42):
    """
    Create stratified train/val/test splits maintaining regional balance.
    """
    random.seed(seed)

    # Group by region
    by_region = defaultdict(list)
    for entry in data:
        region = entry["Region"]
        by_region[region].append(entry)

    train, val, test = [], [], []

    # Split each region proportionally
    for region, entries in by_region.items():
        # Shuffle within region
        random.shuffle(entries)

        n = len(entries)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train.extend(entries[:n_train])
        val.extend(entries[n_train : n_train + n_val])
        test.extend(entries[n_train + n_val :])

    # Final shuffle
    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)

    return train, val, test


def save_fasttext_format(data, output_file):
    """Save in fastText format: __label__<region> <name>"""
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in data:
            region = entry["Region"]
            name = entry["CanonicalNative"]
            f.write(f"__label__{region} {name}\n")


def main():
    print("=" * 70)
    print("DATASET COMBINATION & SPLITTING")
    print("=" * 70)
    print()

    # Load datasets
    print("Loading datasets...")
    synthetic = load_dataset("data/ml_training/synthetic_50k.json")
    real_world = load_dataset("data/ml_training/math_genealogy_30k.json")

    print(f"  ✅ Synthetic: {len(synthetic):,} names")
    print(f"  ✅ Real-world: {len(real_world):,} names")
    print()

    # Combine
    combined = synthetic + real_world
    print(f"✅ Combined total: {len(combined):,} names")
    print()

    # Regional statistics
    region_counts = defaultdict(int)
    for entry in combined:
        region_counts[entry["Region"]] += 1

    print(f"Regional distribution ({len(region_counts)} regions):")
    for region in sorted(region_counts.keys()):
        count = region_counts[region]
        pct = (count / len(combined)) * 100
        print(f"  {region}: {count:5,} ({pct:5.2f}%)")
    print()

    # Create splits
    print("Creating stratified 80/10/10 train/val/test splits...")
    train, val, test = create_stratified_split(combined)

    print(f"  ✅ Train: {len(train):,} names")
    print(f"  ✅ Val:   {len(val):,} names")
    print(f"  ✅ Test:  {len(test):,} names")
    print()

    # Save JSON format
    output_dir = Path("data/ml_training")
    output_dir.mkdir(exist_ok=True, parents=True)

    with open(output_dir / "train.json", "w") as f:
        json.dump(train, f, indent=2, ensure_ascii=False)
    with open(output_dir / "val.json", "w") as f:
        json.dump(val, f, indent=2, ensure_ascii=False)
    with open(output_dir / "test.json", "w") as f:
        json.dump(test, f, indent=2, ensure_ascii=False)

    print("✅ Saved JSON splits: train.json, val.json, test.json")

    # Save fastText format
    save_fasttext_format(train, output_dir / "train.txt")
    save_fasttext_format(val, output_dir / "val.txt")
    save_fasttext_format(test, output_dir / "test.txt")

    print("✅ Saved fastText format: train.txt, val.txt, test.txt")
    print()

    # Statistics per split
    for split_name, split_data in [("Train", train), ("Val", val), ("Test", test)]:
        split_regions = defaultdict(int)
        for entry in split_data:
            split_regions[entry["Region"]] += 1

        print(f"{split_name} split regional coverage: {len(split_regions)}/37 regions")

    print()
    print("=" * 70)
    print("✅ DATASET PREPARATION COMPLETE")
    print("=" * 70)
    print()
    print(f"Combined dataset: {len(combined):,} names")
    print(f"  - Synthetic: {len(synthetic):,} ({len(synthetic)/len(combined)*100:.1f}%)")
    print(f"  - Real-world: {len(real_world):,} ({len(real_world)/len(combined)*100:.1f}%)")
    print()
    print("Ready for training:")
    print("  python3 scripts/ml/train_fasttext.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
