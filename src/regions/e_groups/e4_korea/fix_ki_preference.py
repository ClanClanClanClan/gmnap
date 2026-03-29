#!/usr/bin/env python3
"""
Fix ki → 키 preference issue. Should prefer 기 for Korean names.
"""

import csv
import subprocess


def analyze_ki_mappings():
    """Check current ki/gi mappings."""
    filepath = "resources/rr_syllable_map.csv"

    ki_mappings = []
    gi_mappings = []
    key_mappings = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[1] == "ki":
                    ki_mappings.append(row)
                elif row[1] == "gi":
                    gi_mappings.append(row)
                elif row[1] == "key":
                    key_mappings.append(row)

    print("Current 'ki' mappings:")
    for row in ki_mappings:
        print(f"  {row}")

    print("\nCurrent 'gi' mappings:")
    for row in gi_mappings[:5]:  # Just first 5
        print(f"  {row}")

    print("\nCurrent 'key' mappings:")
    for row in key_mappings:
        print(f"  {row}")

    return ki_mappings


def fix_ki_mappings():
    """Ensure 기,ki is preferred over 키,ki."""
    filepath = "resources/rr_syllable_map.csv"

    # Read all mappings
    mappings = []
    removed = []
    has_gi_ki = False

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[0] == "기" and row[1] == "ki":
                    has_gi_ki = True
                    mappings.append(row)
                elif row[0] == "키" and row[1] == "ki":
                    # Remove this - 키 should map to 'key' not 'ki'
                    removed.append(row)
                    print(f"Removing: {row}")
                else:
                    mappings.append(row)

    # Add 기,ki if missing
    if not has_gi_ki:
        mappings.append(["기", "ki"])
        print("Adding: ['기', 'ki']")

    if removed or not has_gi_ki:
        # Write back
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(mappings)

        print(f"\nMade {len(removed) + (1 if not has_gi_ki else 0)} changes")
        return True

    print("\nNo changes needed")
    return False


def test_ki_conversions():
    """Test ki-related conversions."""
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    # from converter import eng2kor

    test_cases = [
        ("Ki", "기"),
        ("KiMoon", "기문"),
        ("Ban_KiMoon", "반기문"),
        ("KiMin", "기민"),
        ("MiKi", "미기"),
    ]

    print("\nTesting 'ki' conversions:")
    for eng, expected in test_cases:
        actual = eng2kor(eng)
        correct = actual == expected
        print(
            f"  {eng:20} → {actual:10} {'✓' if correct else '✗ expected ' + expected}"
        )


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
    print("Fixing ki → 키 preference issue")
    print("=" * 50)

    # Analyze current state
    analyze_ki_mappings()

    # Get baseline
    print("\nTesting baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Fix mapping
    if fix_ki_mappings():
        # Rebuild FSTs
        print("\nRebuilding FSTs...")
        subprocess.run(
            ["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True
        )

        # Test specific cases
        test_ki_conversions()

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
    else:
        print("\nNo changes made.")


if __name__ == "__main__":
    main()
