#!/usr/bin/env python3
"""
Add missing syllables to fix segmentation issues.
"""

import csv
import json
import subprocess
from datetime import datetime

# Missing syllables causing segmentation issues
MISSING_SYLLABLES = {
    # Fix ChongWei segmentation
    "chong": "총",  # For ChongWei → 청위
    "wei": "위",  # For ChongWei
    # Fix JungKook segmentation
    "kook": "국",  # For JungKook → 정국
    # Fix HyunMoo segmentation
    "moo": "무",  # For HyunMoo → 현무
    # Fix EuiSun segmentation
    "eui": "의",  # For EuiSun → 의선
    # Fix HyeKyo
    "kyo": "교",  # For HyeKyo → 혜교 (not 쿄)
    # Other common syllables
    "seon": "선",  # For various names
    "chun": "춘",  # For ChunHyang
}


def create_batch_record():
    """Create a record of additions for reversibility."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    record = {"timestamp": timestamp, "type": "segmentation_fixes", "additions": []}
    return record


def add_missing_syllables():
    """Add missing syllables to rr_syllable_map.csv."""
    filepath = "resources/rr_syllable_map.csv"
    record = create_batch_record()

    # Check existing
    existing = set()
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                existing.add((row[0], row[1]))

    # Add new mappings
    added = []
    with open(filepath, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for rom, han in MISSING_SYLLABLES.items():
            if (han, rom) not in existing:
                writer.writerow([han, rom])
                added.append([han, rom])
                record["additions"].append({"hangul": han, "romanization": rom})
                print(f"  Added: {han},{rom}")

    # Save record
    record_file = f'segmentation_fixes_{record["timestamp"]}.json'
    with open(record_file, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"\nAdded {len(added)} syllable mappings")
    print(f"Record saved to {record_file}")

    return len(added) > 0


def test_segmentation_fixes():
    """Test if segmentation is fixed."""
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    # from converter import eng2kor
    from segment import segment

    test_cases = [
        ("ChongWei", "청위", ["chong", "wei"]),
        ("JungKook", "정국", ["jung", "kook"]),
        ("HyunMoo", "현무", ["hyun", "moo"]),
        ("EuiSun", "의선", ["eui", "sun"]),
        ("HyeKyo", "혜교", ["hye", "kyo"]),
        ("ChunHyang", "춘향", ["chun", "hyang"]),
    ]

    print("\nTesting segmentation fixes:")
    for eng, expected_han, expected_seg in test_cases:
        actual_seg = segment(eng.lower())
        actual_han = eng2kor(eng)

        seg_ok = actual_seg == expected_seg
        han_ok = actual_han == expected_han

        print(f"\n{eng}:")
        print(
            f"  Segmentation: {actual_seg} {'✓' if seg_ok else '✗ expected ' + str(expected_seg)}"
        )
        print(
            f"  Conversion: {actual_han} {'✓' if han_ok else '✗ expected ' + expected_han}"
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
    print("Fixing segmentation issues")
    print("=" * 50)

    # Get baseline
    print("Testing baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")

    print("\nAdding missing syllables:")

    # Add mappings
    if add_missing_syllables():
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

        # Test specific fixes
        test_segmentation_fixes()

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
