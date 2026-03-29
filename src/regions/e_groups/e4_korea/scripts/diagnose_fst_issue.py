#!/usr/bin/env python3
"""Diagnose why FST additions cause regressions."""
import csv
import subprocess
import tempfile
import shutil
from pathlib import Path


def diagnose_fst_build():
    """Diagnose FST build issues."""
    # Count current mappings
    count_before = 0
    with open("resources/rr_syllable_map.csv", "r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and not row[0].startswith("#"):
                count_before += 1

    print(f"Current mappings in CSV: {count_before}")

    # Test a known good name
    print("\nTesting known good conversions before change:")
    test_names = [
        ("Kim, Jong-Un", "김정은"),
        ("Lee, Sang-Hwa", "이상화"),
        ("Park, Chan-Ho", "박찬호"),
    ]

    import sys

    sys.path.insert(0, "src")
    # import converter

    for name, expected in test_names:
        result = converter.eng2kor(name)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {name} → {result} (expected {expected})")

    # Now test with a temporary addition
    with tempfile.TemporaryDirectory() as tmpdir:
        # Backup and modify
        csv_backup = Path("resources/rr_syllable_map.csv.diagnose")
        shutil.copy("resources/rr_syllable_map.csv", csv_backup)

        try:
            # Add one mapping
            with open("resources/rr_syllable_map.csv", "a", encoding="utf-8") as f:
                f.write("\n싸이,psy,1.0,,S")

            # Count after
            count_after = 0
            with open("resources/rr_syllable_map.csv", "r", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if len(row) >= 2 and not row[0].startswith("#"):
                        count_after += 1

            print(f"\nAfter adding mapping: {count_after} (added {count_after - count_before})")

            # Check CSV for duplicates or issues
            print("\nChecking for CSV issues...")
            mappings = {}
            line_num = 0
            with open("resources/rr_syllable_map.csv", "r", encoding="utf-8") as f:
                for row in csv.reader(f):
                    line_num += 1
                    if len(row) >= 2 and not row[0].startswith("#"):
                        key = (row[0], row[1], row[4] if len(row) > 4 else "")
                        if key in mappings:
                            print(f"  ⚠️  Duplicate at line {line_num}: {key}")
                        mappings[key] = line_num

            # Rebuild FSTs
            print("\nRebuilding FSTs...")
            result = subprocess.run(
                ["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True
            )

            if result.returncode != 0:
                print(f"FST build failed: {result.stderr}")
                return

            # Reload converter to get new FSTs
            import importlib

            importlib.reload(converter)

            # Test same names again
            print("\nTesting same names after FST rebuild:")
            for name, expected in test_names:
                result = converter.eng2kor(name)
                status = "✅" if result == expected else "❌"
                print(f"  {status} {name} → {result} (expected {expected})")

            # Test the new name
            psy_result = converter.eng2kor("Psy")
            print(f"\nNew mapping test: Psy → {psy_result} (expected 싸이)")

        finally:
            # Restore
            shutil.copy(csv_backup, "resources/rr_syllable_map.csv")
            csv_backup.unlink()
            print("\n✓ Restored original CSV")


if __name__ == "__main__":
    diagnose_fst_build()
