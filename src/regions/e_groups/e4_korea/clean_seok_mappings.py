#!/usr/bin/env python3
"""
Clean up seok mappings to ensure 석 is the primary mapping.
Remove incorrect mappings like 섞,seok and 섴,seok.
"""

import csv
import subprocess
from collections import defaultdict


def clean_seok_mappings():
    """Clean up seok mappings in rr_syllable_map.csv."""
    filepath = "resources/rr_syllable_map.csv"

    # Read all mappings
    mappings = []
    seok_mappings = defaultdict(list)

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                mappings.append(row)
                if row[1] == "seok":
                    seok_mappings[row[0]].append(row)

    print("Current seok mappings:")
    for hangul, rows in seok_mappings.items():
        print(f"  {hangul}: {len(rows)} entries")

    # Remove duplicates and wrong mappings
    cleaned_mappings = []
    seen = set()
    removed = []

    for row in mappings:
        key = tuple(row[:2])  # (hangul, romanization)

        # Skip duplicates
        if key in seen:
            removed.append(("duplicate", row))
            continue

        # Skip wrong seok mappings (keep only 석,seok)
        if len(row) >= 2 and row[1] == "seok" and row[0] != "석":
            removed.append(("wrong_seok", row))
            continue

        seen.add(key)
        cleaned_mappings.append(row)

    print(f"\nRemoving {len(removed)} entries:")
    for reason, row in removed[:10]:
        print(f"  {reason}: {row}")
    if len(removed) > 10:
        print(f"  ... and {len(removed) - 10} more")

    # Write back
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(cleaned_mappings)

    print(f"\nCleaned: {len(mappings)} → {len(cleaned_mappings)} entries")
    return True


def test_accuracy():
    """Get current accuracy numbers."""
    # Test mathematician
    result = subprocess.run(
        ["python3", "scripts/validate.py"], capture_output=True, text=True
    )
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
    print("Cleaning seok mappings")
    print("=" * 50)

    # Get baseline
    print("Testing baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Clean mappings
    clean_seok_mappings()

    # Rebuild FSTs
    print("\nRebuilding FSTs...")
    subprocess.run(
        ["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True
    )

    # Test new accuracy
    print("\nTesting new accuracy...")
    math_after, div_after = test_accuracy()
    print(f"  Mathematician: {math_after}/733")
    print(f"  Diverse: {div_after}/200")

    # Report results
    print("\n" + "=" * 50)
    print("Results:")
    print(
        f"  Mathematician: {math_before} → {math_after} ({math_after - math_before:+d})"
    )
    print(f"  Diverse: {div_before} → {div_after} ({div_after - div_before:+d})")

    if math_after >= math_before:
        print("\n✅ No regression in mathematician accuracy")
    else:
        print("\n⚠️  Mathematician accuracy dropped!")


if __name__ == "__main__":
    main()
