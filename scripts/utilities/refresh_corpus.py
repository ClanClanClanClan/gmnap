#!/usr/bin/env python3
"""
Monthly corpus refresh script for anti-overfitting
Downloads fresh Korean corpus data and rebuilds frequency tables
"""

import os
import json
import shutil
import subprocess
from datetime import datetime
from datasets import load_dataset
import argparse


def backup_current_data():
    """Backup current syllable frequency data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"data/backups/corpus_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)

    # Backup current files
    files_to_backup = [
        "data/syllable_freq.json",
        "data/roman2hangul.fst",
        "data/rr_table.csv",
        "data/mr_table.csv",
        "data/yale_table.csv",
        "data/mltr_table.csv",
    ]

    for file_path in files_to_backup:
        if os.path.exists(file_path):
            shutil.copy2(file_path, backup_dir)
            print(f"Backed up {file_path}")

    return backup_dir


def download_fresh_corpus():
    """Download fresh Korean corpus data"""
    corpus_dir = "data/corp/fresh"
    os.makedirs(corpus_dir, exist_ok=True)

    print("Downloading fresh Korean corpus data...")

    # Download datasets with rotation
    datasets_config = [
        {"name": "lcw99/cc100-ko-only", "split": "train[:100000]"},  # Sample 100k lines
        {"name": "mc4", "config": "ko", "split": "train[:50000]"},  # Sample 50k lines
    ]

    for dataset_config in datasets_config:
        try:
            print(f"Downloading {dataset_config['name']}...")

            # Load dataset
            if "config" in dataset_config:
                ds = load_dataset(
                    dataset_config["name"],
                    dataset_config["config"],
                    split=dataset_config["split"],
                    cache_dir=corpus_dir,
                )
            else:
                ds = load_dataset(
                    dataset_config["name"],
                    split=dataset_config["split"],
                    cache_dir=corpus_dir,
                )

            # Save to text file
            output_file = f"{corpus_dir}/{dataset_config['name'].replace('/', '_')}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                for item in ds:
                    text = item.get("text", "") or item.get("content", "")
                    if text:
                        f.write(text + "\n")

            print(f"Saved {len(ds)} items to {output_file}")

        except Exception as e:
            print(f"Error downloading {dataset_config['name']}: {e}")
            continue

    return corpus_dir


def rebuild_frequency_tables():
    """Rebuild syllable frequency tables with fresh data"""
    print("Rebuilding syllable frequency tables...")

    # Run syllable counting script
    result = subprocess.run(
        ["python", "scripts/count_syllables.py", "data/corp/fresh/*.txt"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error counting syllables: {result.stderr}")
        return False

    print("Syllable frequencies updated")

    # Rebuild WFST components
    print("Rebuilding WFST components...")

    scripts_to_run = ["src/v5/generate_tables.py", "src/v5/fst_helpers.py"]

    for script in scripts_to_run:
        result = subprocess.run(["python", script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running {script}: {result.stderr}")
            return False
        print(f"Successfully rebuilt {script}")

    return True


def validate_rebuilt_system():
    """Validate that rebuilt system maintains accuracy"""
    print("Validating rebuilt system...")

    # Run accuracy check
    result = subprocess.run(
        [
            "python",
            "scripts/evaluate_roundtrip.py",
            "-i",
            "data/korean.yaml",
            "-t",
            "0.97",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✅ Validation passed - accuracy maintained")
        return True
    else:
        print("❌ Validation failed - accuracy degraded")
        print(result.stdout)
        return False


def rotate_test_set(current_yaml_path, rotation_pct=0.1):
    """Rotate portion of test set to prevent overfitting"""
    import yaml
    import random

    # Load current test set
    with open(current_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Calculate rotation size
    total_entries = len(data)
    n_rotate = int(total_entries * rotation_pct)

    print(
        f"Rotating {n_rotate} out of {total_entries} test entries ({rotation_pct:.1%})"
    )

    # Select entries to rotate (stratified by name length)
    entries_by_length = {}
    for entry_id, entry in data.items():
        canonical = entry.get("CanonicalLatin", "")
        length_bucket = len(canonical) // 5  # Group by length buckets
        if length_bucket not in entries_by_length:
            entries_by_length[length_bucket] = []
        entries_by_length[length_bucket].append(entry_id)

    # Select entries to rotate from each bucket
    entries_to_rotate = []
    for bucket, entry_ids in entries_by_length.items():
        bucket_rotate_count = max(1, int(len(entry_ids) * rotation_pct))
        rotated = random.sample(entry_ids, min(bucket_rotate_count, len(entry_ids)))
        entries_to_rotate.extend(rotated)

    # Move rotated entries to archive
    timestamp = datetime.now().strftime("%Y%m%d")
    archive_path = f"data/test_archive_{timestamp}.yaml"

    archived_entries = {}
    for entry_id in entries_to_rotate:
        archived_entries[entry_id] = data.pop(entry_id)

    # Save archived entries
    with open(archive_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(archived_entries, f, allow_unicode=True)

    # Save updated test set
    with open(current_yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)

    print(f"Archived {len(archived_entries)} entries to {archive_path}")
    print(f"Updated test set now has {len(data)} entries")


def run_corpus_refresh():
    """Run complete corpus refresh process"""
    print("=== Korean Corpus Refresh (Anti-overfitting) ===")
    print(f"Started at: {datetime.now()}")

    try:
        # Step 1: Backup current data
        backup_dir = backup_current_data()
        print(f"✅ Backed up current data to {backup_dir}")

        # Step 2: Download fresh corpus
        corpus_dir = download_fresh_corpus()
        print(f"✅ Downloaded fresh corpus to {corpus_dir}")

        # Step 3: Rebuild frequency tables
        if rebuild_frequency_tables():
            print("✅ Rebuilt frequency tables")
        else:
            raise Exception("Failed to rebuild frequency tables")

        # Step 4: Validate system
        if validate_rebuilt_system():
            print("✅ System validation passed")
        else:
            print("❌ System validation failed - reverting...")
            # Restore backup
            for file_name in os.listdir(backup_dir):
                shutil.copy2(os.path.join(backup_dir, file_name), f"data/{file_name}")
            raise Exception("Validation failed - reverted to backup")

        # Step 5: Rotate test set
        rotate_test_set("data/korean.yaml", rotation_pct=0.1)
        print("✅ Rotated 10% of test set")

        print("🎉 Corpus refresh completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Corpus refresh failed: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Refresh Korean corpus for anti-overfitting"
    )
    parser.add_argument(
        "--rotation-pct",
        type=float,
        default=0.1,
        help="Percentage of test set to rotate (default: 0.1)",
    )
    parser.add_argument(
        "--validate", action="store_true", help="Run validation after refresh"
    )

    args = parser.parse_args()

    success = run_corpus_refresh()
    exit(0 if success else 1)
