#!/usr/bin/env python3
"""
Fix heon → 훈 preference issue. Should prefer 헌 for most cases.
"""

import csv
import subprocess


def analyze_heon_mappings():
    """Check current heon/hun mappings."""
    filepath = "resources/rr_syllable_map.csv"

    heon_mappings = []
    hun_mappings = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[1] == "heon":
                    heon_mappings.append(row)
                elif row[1] == "hun":
                    hun_mappings.append(row)

    print("Current 'heon' mappings:")
    for row in heon_mappings:
        print(f"  {row}")

    print("\nCurrent 'hun' mappings:")
    for row in hun_mappings:
        print(f"  {row}")

    return heon_mappings, hun_mappings


def fix_heon_mappings():
    """Ensure 헌,heon exists and remove 훈,heon if present."""
    filepath = "resources/rr_syllable_map.csv"

    # Read all mappings
    mappings = []
    removed = []
    has_heon_to_heon = False

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[0] == "헌" and row[1] == "heon":
                    has_heon_to_heon = True
                    mappings.append(row)
                elif row[0] == "훈" and row[1] == "heon":
                    # Remove this wrong mapping
                    removed.append(row)
                    print(f"Removing: {row}")
                else:
                    mappings.append(row)

    # Add 헌,heon if missing
    if not has_heon_to_heon:
        mappings.append(["헌", "heon"])
        print("Adding: ['헌', 'heon']")

    if removed or not has_heon_to_heon:
        # Write back
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(mappings)

        print(f"\nMade {len(removed) + (1 if not has_heon_to_heon else 0)} changes")
        return True

    print("\nNo changes needed")
    return False


def test_heon_conversions():
    """Test heon-related conversions."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    from converter import eng2kor

    test_cases = [
        ("Heon", "헌"),
        ("HeonChul", "헌철"),
        ("SiHeon", "시헌"),
        ("YeonHeon", "연헌"),
        ("Hun", "훈"),  # This should still be 훈
    ]

    print("\nTesting 'heon' conversions:")
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
    print("Fixing heon → 훈 preference issue")
    print("=" * 50)

    # Analyze current state
    analyze_heon_mappings()

    # Get baseline
    print("\nTesting baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Fix mapping
    if fix_heon_mappings():
        # Update lexicon
        print("\nUpdating syllable lexicon...")
        subprocess.run(["python3", "src/syllable_lexicon_fixed.py"], capture_output=True, text=True)

        # Rebuild FSTs
        print("Rebuilding FSTs...")
        subprocess.run(["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True)

        # Test specific cases
        test_heon_conversions()

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
