#!/usr/bin/env python3
"""Batch fix mappings to resolve failures."""

import shutil
import subprocess
from datetime import datetime

# Mappings to add (that don't conflict if we use proper positions)
mappings_to_add = [
    # For dice score fixes
    ("순", "sun", "1.0", "", "G"),  # Yu, Gwan-Sun
    ("병", "byung", "1.0", "", "G"),  # Lee, Byung-Hun
    ("헌", "hun", "1.0", "", "G"),  # Lee, Byung-Hun
    # For no_conversion fixes (if not conflicting)
    ("여", "yuh", "1.0", "", "G"),  # Youn, Yuh-Jung
]

# Create backup
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = "resources/rr_syllable_map.csv"
backup_path = f"{csv_path}.batch_backup_{timestamp}"
shutil.copy(csv_path, backup_path)
print(f"Created backup: {backup_path}")

# Add new mappings
added = 0
skipped = 0

with open(csv_path, "a", encoding="utf-8") as f:
    for hangul, roman, weight, context, pos in mappings_to_add:
        # Simple add - let's trust our analysis
        f.write(f"\n{hangul},{roman},{weight},{context},{pos}")
        print(f"Added: {roman} → {hangul} (pos={pos or 'general'})")
        added += 1

print(f"\nAdded {added} mappings")

# Rebuild FSTs
print("\nRebuilding FSTs...")
result = subprocess.run(["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True)
if result.returncode == 0:
    print("✓ FSTs rebuilt")
else:
    print(f"✗ FST rebuild failed: {result.stderr}")
    # Restore backup
    shutil.copy(backup_path, csv_path)
    print("Restored backup due to FST failure")
    exit(1)

# Test all our target names
print("\nTesting conversions...")
test_names = [
    ("Lee, Cheong-Jun", "이청준"),
    ("Yu, Gwan-Sun", "유관순"),
    ("Lee, Byung-Hun", "이병헌"),
    ("Youn, Yuh-Jung", "윤여정"),
    ("Choi, Min-Shik", "최민식"),
    ("So, Ji-Sub", "소지섭"),
]

import sys

sys.path.insert(0, "src")
# import converter

passed = 0
for name, expected in test_names:
    result = converter.eng2kor(name)
    if result == expected:
        print(f"  ✅ {name} → {result}")
        passed += 1
    else:
        print(f"  ❌ {name} → {result} (expected {expected})")

print(f"\nPassed {passed}/{len(test_names)} tests")

# Check for regressions
print("\nChecking for regressions...")
reg_result = subprocess.run(
    ["python3", "scripts/validate_regression.py"], capture_output=True, text=True
)
if reg_result.returncode != 0:
    print("⚠️  REGRESSIONS DETECTED!")
    print("Rolling back...")
    shutil.copy(backup_path, csv_path)
    subprocess.run(["python3", "scripts/build_fsts_multi.py"])
    print("Rolled back to backup")
else:
    print("✅ No regressions detected")
