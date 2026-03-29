#!/usr/bin/env python3
"""
Fix 중 → 정 error pattern by cleaning up jung/joong mappings.
"""

import csv
import subprocess
from collections import defaultdict


def analyze_jung_mappings():
    """Analyze current jung/joong mappings."""
    filepath = "resources/rr_syllable_map.csv"

    jung_mappings = defaultdict(list)
    joong_mappings = defaultdict(list)

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                if row[1] == "jung":
                    jung_mappings[row[0]].append(row)
                elif row[1] == "joong":
                    joong_mappings[row[0]].append(row)

    print("Current jung mappings:")
    for hangul, rows in sorted(jung_mappings.items()):
        print(f"  {hangul} → jung ({len(rows)} entries)")

    print("\nCurrent joong mappings:")
    for hangul, rows in sorted(joong_mappings.items()):
        print(f"  {hangul} → joong ({len(rows)} entries)")

    return jung_mappings, joong_mappings


def fix_jung_mappings():
    """Fix jung mappings to ensure 중 maps to joong, not jung."""
    filepath = "resources/rr_syllable_map.csv"

    # Read all mappings
    mappings = []
    changes = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                # Fix: 중 should map to joong, not jung
                if row[0] == "중" and row[1] == "jung":
                    changes.append((row, ["중", "joong"]))
                    mappings.append(["중", "joong"])
                # Fix: 정 should map to jung/jeong, not joong
                elif row[0] == "정" and row[1] == "joong":
                    changes.append((row, ["정", "jung"]))
                    mappings.append(["정", "jung"])
                else:
                    mappings.append(row)

    if changes:
        print(f"\nMaking {len(changes)} changes:")
        for old, new in changes:
            print(f"  {old} → {new}")

        # Write back
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(mappings)

        return True

    return False


def test_jung_conversions():
    """Test jung-related conversions."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    # from converter import eng2kor

    test_cases = [
        ("JungGeun", "중근"),  # 중 in middle
        ("Jung", "정"),  # Jung as surname
        ("JinJung", "진중"),  # 중 at end
        ("JungHo", "정호"),  # 정 at start
    ]

    print("\nTesting jung conversions:")
    for eng, expected in test_cases:
        actual = eng2kor(eng)
        correct = actual == expected
        print(
            f"  {eng:15} → {actual:10} {'✓' if correct else '✗ (expected ' + expected + ')'}"
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
    print("Fixing jung/joong mapping issue")
    print("=" * 50)

    # Analyze current state
    analyze_jung_mappings()

    # Get baseline
    print("\nTesting baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Apply fix
    if fix_jung_mappings():
        # Rebuild FSTs
        print("\nRebuilding FSTs...")
        subprocess.run(
            ["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True
        )

        # Test conversions
        test_jung_conversions()

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
