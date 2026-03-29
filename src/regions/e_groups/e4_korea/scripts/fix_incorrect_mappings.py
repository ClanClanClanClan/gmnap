#!/usr/bin/env python3
"""Identify and fix incorrect mappings causing dice score failures."""

import csv
import shutil
from datetime import datetime

# Known incorrect mappings from our analysis
incorrect_mappings = [
    ("선", "sun"),  # Should be 순
    ("븅", "byung"),  # Should be 병
    ("훈", "hun"),  # Should be 헌
    ("정", "cheong"),  # Conflicts with 청
]

# Backup CSV
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"resources/rr_syllable_map.csv.fix_backup_{timestamp}"
shutil.copy("resources/rr_syllable_map.csv", backup_path)
print(f"Created backup: {backup_path}")

# Read all rows
rows = []
removed_count = 0
modified_count = 0

with open("resources/rr_syllable_map.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 2:
            hangul = row[0]
            roman = row[1]

            # Check if this is an incorrect mapping
            should_remove = False
            for wrong_han, wrong_rom in incorrect_mappings:
                if hangul == wrong_han and roman == wrong_rom:
                    should_remove = True
                    print(f"Removing incorrect: {hangul},{roman}")
                    removed_count += 1
                    break

            if not should_remove:
                # Special case: boost 청,cheong weight
                if hangul == "청" and roman == "cheong":
                    if len(row) > 2:
                        row[2] = "2.0"  # Boost weight
                        print(f"Boosted weight: {hangul},{roman} → 2.0")
                        modified_count += 1

                rows.append(row)
        else:
            rows.append(row)

# Write back
with open("resources/rr_syllable_map.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"\nSummary:")
print(f"- Removed {removed_count} incorrect mappings")
print(f"- Modified {modified_count} mappings")
print(f"- Total rows: {len(rows)}")

# Rebuild FSTs
import subprocess

print("\nRebuilding FSTs...")
result = subprocess.run(
    ["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True
)
if result.returncode == 0:
    print("✓ FSTs rebuilt successfully")
else:
    print(f"✗ FST rebuild failed: {result.stderr}")

# Test the fixes
print("\nTesting fixes...")
test_result = subprocess.run(
    [
        "python3",
        "-c",
        """import sys; sys.path.insert(0, 'src'); # import converter
print('Lee, Cheong-Jun:', converter.eng2kor('Lee, Cheong-Jun'))
print('Yu, Gwan-Sun:', converter.eng2kor('Yu, Gwan-Sun'))
print('Lee, Byung-Hun:', converter.eng2kor('Lee, Byung-Hun'))""",
    ],
    capture_output=True,
    text=True,
)
print(test_result.stdout)
