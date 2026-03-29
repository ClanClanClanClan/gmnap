#!/usr/bin/env python3
"""
Fix the seok priority issue by removing 섞,seok mapping from rr_syllable_map.csv
since 섞 should map to sseok (or some other variant).
"""

import csv
import subprocess
import shutil
from datetime import datetime


def backup_file(filepath):
    """Create a backup of the file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"Backed up to {backup_path}")
    return backup_path


def remove_wrong_seok_mapping():
    """Remove 섞,seok from rr_syllable_map.csv"""
    filepath = "resources/rr_syllable_map.csv"

    # Backup first
    backup_path = backup_file(filepath)

    # Read all mappings
    mappings = []
    removed = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0] == "섞" and row[1] == "seok":
                removed.append(row)
                print(f"Removing: {row}")
            else:
                mappings.append(row)

    if not removed:
        print("No wrong mappings found.")
        return False

    # Write back
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(mappings)

    print(f"Removed {len(removed)} wrong mappings")
    return True


def test_seok_conversion():
    """Test if seok converts correctly."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    # from converter import eng2kor

    test_cases = [
        ("SeokJin", "석진"),
        ("HoSeok", "호석"),
        ("JaeSeok", "재석"),
        ("SeokYeol", "석열"),
    ]

    print("\nTesting seok conversions:")
    all_correct = True

    for eng, expected in test_cases:
        actual = eng2kor(eng)
        correct = actual == expected
        all_correct &= correct
        print(f"  {eng:15} → {actual:10} {'✓' if correct else '✗ (expected ' + expected + ')'}")

    return all_correct


def main():
    print("Fixing seok priority issue")
    print("=" * 50)

    # Remove wrong mapping
    if not remove_wrong_seok_mapping():
        return

    # Rebuild FSTs
    print("\nRebuilding FSTs...")
    subprocess.run(["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True)

    # Test the fix
    if test_seok_conversion():
        print("\n✅ Fix successful!")
    else:
        print("\n❌ Fix didn't work as expected")


if __name__ == "__main__":
    main()
