#!/usr/bin/env python3
"""
Add missing 'ah' syllable to enable names like AhSung.
"""

import csv
import subprocess


def add_ah_mapping():
    """Add ah → 아 mapping to rr_syllable_map.csv."""
    filepath = "resources/rr_syllable_map.csv"

    # Check if already exists
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1] == "ah":
                print(f"'ah' mapping already exists: {row}")
                return False

    # Add new mapping
    print("Adding ah → 아 mapping")
    with open(filepath, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["아", "ah"])

    return True


def test_ah_names():
    """Test names containing 'ah'."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    from converter import eng2kor

    test_cases = ["AhSung", "Go_AhSung", "ah"]

    print("\nTesting 'ah' conversions:")
    for name in test_cases:
        result = eng2kor(name)
        print(f"  {name:15} → {result}")


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
    print("Adding 'ah' syllable mapping")
    print("=" * 50)

    # Get baseline
    print("Testing baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Add mapping
    if add_ah_mapping():
        # Update lexicon
        print("\nUpdating syllable lexicon...")
        subprocess.run(["python3", "src/syllable_lexicon_fixed.py"], capture_output=True, text=True)

        # Rebuild FSTs
        print("Rebuilding FSTs...")
        subprocess.run(["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True)

        # Test specific cases
        test_ah_names()

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
    else:
        print("\nNo changes needed.")


if __name__ == "__main__":
    main()
