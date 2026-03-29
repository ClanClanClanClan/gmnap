import pytest

#!/usr/bin/env python3
"""Debug Korean CSV path resolution"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("🔍 DEBUGGING KOREAN CSV PATH RESOLUTION")
print("=" * 60)

# Test the lookup function directly
try:
    from src.regions.e_groups.e4_korea.src.lookup import rom2han

    print("PASS Lookup function imported")

    # This should trigger the path resolution
    lookup_table = rom2han()
    print(f"PASS Lookup table loaded with {len(lookup_table)} entries")

    # Test a few lookups
    test_cases = ["kim", "park", "lee", "jung"]
    for case in test_cases:
        result = lookup_table.get(case)
        print(f"   {case} -> {result}")

except FileNotFoundError as e:
    print(f"FAIL CSV file not found: {e}")

    # Check which paths exist
    possible_paths = [
        Path(__file__).parent / "src/regions/e_groups/e4_korea/resources/rr_syllable_map.csv",
        Path("src/regions/e_groups/e4_korea/resources/rr_syllable_map.csv"),
        Path(
            "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/regions/e_groups/e4_korea/resources/rr_syllable_map.csv"
        ),
    ]

    print("\n🔍 Checking paths:")
    for path in possible_paths:
        exists = path.exists()
        size = f" ({path.stat().st_size} bytes)" if exists else ""
        print(f"   {'PASS' if exists else 'FAIL'} {path}{size}")

except Exception as e:
    print(f"💥 Unexpected error: {e}")
    import traceback

    traceback.print_exc()
