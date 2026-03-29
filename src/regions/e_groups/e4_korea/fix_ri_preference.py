#!/usr/bin/env python3
"""
Fix ri → 이 preference issue. Should prefer 리 for most cases.
"""

import csv
import subprocess


def analyze_ri_mappings():
    """Check current ri/i mappings."""
    filepath = "resources/rr_syllable_map.csv"

    ri_mappings = []
    i_mappings = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[1] == "ri":
                    ri_mappings.append(row)
                elif row[1] == "i" and row[0] in ["이", "리"]:
                    i_mappings.append(row)

    print("Current 'ri' mappings:")
    for row in ri_mappings:
        print(f"  {row}")

    print("\nRelevant 'i' mappings:")
    for row in i_mappings:
        print(f"  {row}")

    return ri_mappings, i_mappings


def fix_ri_mappings():
    """Ensure 리,ri exists and remove 이,ri if present."""
    filepath = "resources/rr_syllable_map.csv"

    # Read all mappings
    mappings = []
    has_ri_to_ri = False
    removed = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[0] == "리" and row[1] == "ri":
                    has_ri_to_ri = True
                    mappings.append(row)
                elif row[0] == "이" and row[1] == "ri":
                    # Remove this wrong mapping
                    removed.append(row)
                    print(f"Removing: {row}")
                else:
                    mappings.append(row)

    # Add 리,ri if missing
    if not has_ri_to_ri:
        mappings.append(["리", "ri"])
        print("Adding: ['리', 'ri']")

    if removed or not has_ri_to_ri:
        # Write back
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(mappings)

        print(f"\nMade {len(removed) + (1 if not has_ri_to_ri else 0)} changes")
        return True

    print("\nNo changes needed")
    return False


def test_ri_conversions():
    """Test ri-related conversions."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    # from converter import eng2kor

    test_cases = [
        ("YuRi", "유리"),
        ("Jang_YuRi", "장유리"),
        ("Ri", "리"),
        ("GuRi", "구리"),
        ("HyeRi", "혜리"),
    ]

    print("\nTesting 'ri' conversions:")
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
    print("Fixing ri → 이 preference issue")
    print("=" * 50)

    # Analyze current state
    analyze_ri_mappings()

    # Get baseline
    print("\nTesting baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Fix mapping
    if fix_ri_mappings():
        # Update lexicon
        print("\nUpdating syllable lexicon...")
        subprocess.run(
            ["python3", "src/syllable_lexicon_fixed.py"], capture_output=True, text=True
        )

        # Rebuild FSTs
        print("Rebuilding FSTs...")
        subprocess.run(
            ["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True
        )

        # Test specific cases
        test_ri_conversions()

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
