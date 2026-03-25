#!/usr/bin/env python3
"""
Fix sun → 순 preference issue. Should prefer 선 for most Korean names.
"""

import csv
import subprocess


def analyze_sun_mappings():
    """Check current sun mappings in detail."""
    filepath = "resources/rr_syllable_map.csv"

    sun_mappings = []
    seon_mappings = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[1] == "sun":
                    sun_mappings.append(row)
                elif row[1] == "seon":
                    seon_mappings.append(row)

    print("Current 'sun' mappings:")
    for row in sun_mappings:
        print(f"  {row}")

    print("\nCurrent 'seon' mappings:")
    for row in seon_mappings:
        print(f"  {row}")

    return sun_mappings


def remove_wrong_sun_mapping():
    """Remove 순,sun mapping to let 선,sun be used."""
    filepath = "resources/rr_syllable_map.csv"

    # Read all mappings
    mappings = []
    removed = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0] == "순" and row[1] == "sun":
                removed.append(row)
                print(f"Removing: {row}")
            else:
                mappings.append(row)

    if removed:
        # Write back
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(mappings)

        print(f"\nRemoved {len(removed)} wrong mappings")
        return True

    print("\nNo 순,sun mapping found to remove")
    return False


def test_sun_conversions():
    """Test sun-related conversions."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    from converter import eng2kor

    test_cases = [
        ("EuiSun", "의선"),
        ("Chung_EuiSun", "정의선"),
        ("SunWoo", "선우"),
        ("Sun", "선"),
        ("GoSeon", "고선"),
    ]

    print("\nTesting 'sun' conversions:")
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
    print("Fixing sun → 순 preference issue")
    print("=" * 50)

    # Analyze current state
    analyze_sun_mappings()

    # Get baseline
    print("\nTesting baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Fix mapping
    if remove_wrong_sun_mapping():
        # Rebuild FSTs
        print("\nRebuilding FSTs...")
        subprocess.run(["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True)

        # Test specific cases
        test_sun_conversions()

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

        if math_after >= math_before:
            print("\n✅ No regression!")
        else:
            print("\n⚠️  Some regression detected")
    else:
        print("\nNo changes made.")


if __name__ == "__main__":
    main()
