#!/usr/bin/env python3
"""
Rollback problematic English syllables and add only complete English names.
"""

import csv
import subprocess
import json


def rollback_batch(batch_file):
    """Remove entries added in a batch."""
    # Load batch record
    with open(batch_file, "r", encoding="utf-8") as f:
        batch = json.load(f)

    # Read current mappings
    filepath = "resources/rr_syllable_map.csv"
    mappings = []
    removed = 0

    # Create set of additions for fast lookup
    to_remove = {(add["hangul"], add["romanization"]) for add in batch["additions"]}

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and (row[0], row[1]) in to_remove:
                removed += 1
            else:
                mappings.append(row)

    # Write back
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(mappings)

    print(f"Rolled back {removed} entries from {batch_file}")
    return removed


def add_safe_english_names():
    """Add only complete English names, not syllables."""
    filepath = "resources/rr_syllable_map.csv"

    # Only full names to avoid conflicts
    SAFE_ENGLISH_NAMES = {
        "david": "데이비드",
        "sarah": "사라",
        "grace": "그레이스",
        "eugene": "유진",
        "joseph": "요셉",
        "michelle": "미셸",
        "james": "제임스",
        "jessica": "제시카",
        "peter": "피터",
    }

    # Check existing
    existing = set()
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                existing.add((row[0], row[1]))

    # Add new safe mappings
    added = 0
    with open(filepath, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for eng, kor in SAFE_ENGLISH_NAMES.items():
            if (kor, eng) not in existing:
                writer.writerow([kor, eng])
                added += 1

    print(f"Added {added} safe English name mappings")
    return added


def test_accuracy():
    """Get current accuracy numbers."""
    # Test mathematician
    result = subprocess.run(["python3", "scripts/validate.py"], capture_output=True, text=True)
    math_pass = int(result.stdout.split()[0].split("/")[0])

    # Test diverse
    result = subprocess.run(
        ["python3", "scripts/test_diverse_dataset.py"], capture_output=True, text=True
    )
    for line in result.stdout.split("\n"):
        if "Diverse Dataset:" in line and "%" in line:
            percent = float(line.split()[-2].rstrip("%"))
            div_pass = int(percent * 200 / 100)
            break
    else:
        div_pass = 0

    return math_pass, div_pass


def main():
    print("Rolling back problematic English syllables")
    print("=" * 50)

    # Get current state
    print("Current accuracy:")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Rollback the problematic batch
    print("\nRolling back batch...")
    rollback_batch("batch_additions_20250729_160111.json")

    # Add only safe mappings
    print("\nAdding safe English names only...")
    add_safe_english_names()

    # Update lexicon
    print("\nUpdating syllable lexicon...")
    subprocess.run(["python3", "src/syllable_lexicon_fixed.py"], capture_output=True, text=True)

    # Rebuild FSTs
    print("Rebuilding FSTs...")
    subprocess.run(["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True)

    # Test new accuracy
    print("\nTesting new accuracy...")
    math_after, div_after = test_accuracy()
    print(f"  Mathematician: {math_after}/733")
    print(f"  Diverse: {div_after}/200")

    # Report results
    print("\n" + "=" * 50)
    print("Results:")
    print(f"  Mathematician: {math_before} → {math_after} ({math_after - math_before:+d})")
    print(f"  Diverse: {div_before} → {div_after} ({div_after - div_before:+d})")


if __name__ == "__main__":
    main()
