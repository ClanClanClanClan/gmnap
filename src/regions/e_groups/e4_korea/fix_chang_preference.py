#!/usr/bin/env python3
"""
Fix chang → 장 preference issue. Should prefer 창 for most cases.
"""

import csv
import subprocess


def analyze_chang_mappings():
    """Check current chang/jang mappings."""
    filepath = "resources/rr_syllable_map.csv"

    chang_mappings = []
    jang_mappings = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[1] == "chang":
                    chang_mappings.append(row)
                elif row[1] == "jang":
                    jang_mappings.append(row)

    print("Current 'chang' mappings:")
    for row in chang_mappings:
        print(f"  {row}")

    print("\nCurrent 'jang' mappings:")
    for row in jang_mappings:
        print(f"  {row}")

    return chang_mappings


def fix_chang_mappings():
    """Remove 장,chang mapping to let 창,chang be preferred."""
    filepath = "resources/rr_syllable_map.csv"

    # Read all mappings
    mappings = []
    removed = []
    has_chang_to_chang = False

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[0] == "창" and row[1] == "chang":
                    has_chang_to_chang = True
                    mappings.append(row)
                elif row[0] == "장" and row[1] == "chang":
                    # Remove this wrong mapping
                    removed.append(row)
                    print(f"Removing: {row}")
                else:
                    mappings.append(row)

    # Add 창,chang if missing
    if not has_chang_to_chang:
        mappings.append(["창", "chang"])
        print("Adding: ['창', 'chang']")

    if removed or not has_chang_to_chang:
        # Write back
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(mappings)

        print(f"\nMade {len(removed) + (1 if not has_chang_to_chang else 0)} changes")
        return True

    print("\nNo changes needed")
    return False


def test_chang_conversions():
    """Test chang-related conversions."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    from converter import eng2kor

    test_cases = [
        ("Chang", "창"),
        ("ChangMin", "창민"),
        ("Shim_ChangMin", "심창민"),
        ("HyunChang", "현창"),
        ("SeonChang", "선창"),
    ]

    print("\nTesting 'chang' conversions:")
    for eng, expected in test_cases:
        actual = eng2kor(eng)
        correct = actual == expected
        print(f"  {eng:20} → {actual:10} {'✓' if correct else '✗ expected ' + expected}")


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
    print("Fixing chang → 장 preference issue")
    print("=" * 50)

    # Analyze current state
    analyze_chang_mappings()

    # Get baseline
    print("\nTesting baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Fix mapping
    if fix_chang_mappings():
        # Rebuild FSTs
        print("\nRebuilding FSTs...")
        subprocess.run(["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True)

        # Test specific cases
        test_chang_conversions()

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
        print("\nNo changes made.")


if __name__ == "__main__":
    main()
