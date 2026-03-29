#!/usr/bin/env python3
"""
Fix wrong mappings that are causing incorrect conversions.
"""

import csv
import subprocess


def fix_mappings():
    """Fix specific wrong mappings in rr_syllable_map.csv."""
    filepath = "resources/rr_syllable_map.csv"

    # Read all mappings
    mappings = []
    changes = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                # Fix chong mapping
                if row[0] == "총" and row[1] == "chong":
                    # Change to 청,chong
                    new_row = ["청", "chong"]
                    mappings.append(new_row)
                    changes.append((row, new_row))
                # Remove wrong kyo mapping
                elif row[0] == "쿄" and row[1] == "kyo":
                    # Skip this - we want 교,kyo to be used
                    changes.append((row, None))
                # Check sun mappings
                elif row[1] == "sun":
                    print(f"Found sun mapping: {row}")
                    mappings.append(row)
                else:
                    mappings.append(row)

    # Also need to check if we have the right mappings
    has_cheong_chong = any(r[0] == "청" and r[1] == "chong" for r in mappings)
    has_seon_sun = any(r[0] == "선" and r[1] == "sun" for r in mappings)

    if not has_cheong_chong:
        mappings.append(["청", "chong"])
        changes.append((None, ["청", "chong"]))

    if not has_seon_sun:
        mappings.append(["선", "sun"])
        changes.append((None, ["선", "sun"]))

    print(f"Making {len(changes)} changes:")
    for old, new in changes:
        if old and new:
            print(f"  Change: {old} → {new}")
        elif old and not new:
            print(f"  Remove: {old}")
        elif not old and new:
            print(f"  Add: {new}")

    # Write back
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(mappings)

    return len(changes) > 0


def test_specific_conversions():
    """Test the specific problem cases."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    # from converter import eng2kor

    test_cases = [
        ("ChongWei", "청위"),
        ("Lee_ChongWei", "이청위"),
        ("EuiSun", "의선"),
        ("Chung_EuiSun", "정의선"),
        ("HyeKyo", "혜교"),
        ("Song_HyeKyo", "송혜교"),
    ]

    print("\nTesting specific conversions:")
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
    print("Fixing wrong mappings")
    print("=" * 50)

    # Get baseline
    print("Testing baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Fix mappings
    if fix_mappings():
        # Rebuild FSTs
        print("\nRebuilding FSTs...")
        subprocess.run(
            ["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True
        )

        # Test specific cases
        test_specific_conversions()

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
        print("\nNo changes needed.")


if __name__ == "__main__":
    main()
