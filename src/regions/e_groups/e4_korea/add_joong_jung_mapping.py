#!/usr/bin/env python3
"""
Add jung → 중 mapping to rr_syllable_map to handle the ambiguity.
Currently only 정 → jung exists.
"""

import csv
import subprocess


def add_jung_to_joong():
    """Add jung → 중 mapping to rr_syllable_map.csv."""
    filepath = "resources/rr_syllable_map.csv"

    # Read current mappings
    mappings = []
    exists = False

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            mappings.append(row)
            if len(row) >= 2 and row[0] == "중" and row[1] == "jung":
                exists = True

    if exists:
        print("Mapping 중,jung already exists")
        return False

    # Add new mapping
    mappings.append(["중", "jung"])
    print("Adding 중,jung mapping")

    # Sort and write back
    mappings.sort(key=lambda x: (x[0], x[1] if len(x) > 1 else ""))

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(mappings)

    return True


def test_jung_names():
    """Test specific jung-containing names."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    from converter import eng2kor

    test_cases = [
        ("An_JungGeun", "안중근"),
        ("JinJung", "진중"),
        ("Jung", "정"),  # Just Jung alone should still be 정
    ]

    print("\nTesting jung conversions:")
    for eng, expected in test_cases:
        actual = eng2kor(eng)
        if actual == expected:
            print(f"  {eng:15} → {actual} ✓")
        else:
            print(f"  {eng:15} → {actual} ✗ (expected {expected})")


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
    print("Adding jung → 중 mapping")
    print("=" * 50)

    # Get baseline
    print("Testing baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    # Add mapping
    if add_jung_to_joong():
        # Rebuild FSTs
        print("\nRebuilding FSTs...")
        subprocess.run(["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True)

        # Test specific cases
        test_jung_names()

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
