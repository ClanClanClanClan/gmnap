
#!/usr/bin/env python3
"""
Test ULTRAFIX Phase 8 error handling
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

print("🛡️ TESTING ERROR HANDLING FIXES")
print("=" * 60)

manager = RegionManager()

# Test cases that previously crashed
test_cases = [
    (None, "None input"),
    ({}, "Empty dict"),
    ({"name": None}, "None name"),
    ({"name": ""}, "Empty string name"),
    ({"name": "   "}, "Whitespace only name"),
    ({"name": 123}, "Numeric name"),
    ({"name": []}, "List as name"),
    ({"not_name": "value"}, "Missing name field"),
    ("not a dict", "String instead of dict"),
    (123, "Number instead of dict"),
    ([], "List instead of dict"),
]

passed = 0
failed = 0

for test_input, description in test_cases:
    try:
        result = manager.detect_region(test_input)
        if result.region_code == "Z0" and result.detection_method == "error_quarantine":
            print(
                f"PASS {description}: Properly quarantined - {result.metadata.get('quarantine_reason')}"
            )
            passed += 1
        else:
            print(
                f"FAIL {description}: Unexpected result - {result.region_code} ({result.detection_method})"
            )
            failed += 1
    except Exception as e:
        print(f"FAIL {description}: CRASHED with {type(e).__name__}: {e}")
        failed += 1

print(f"\n📊 Results: {passed}/{len(test_cases)} passed")
if failed == 0:
    print("PASS ERROR HANDLING FIXED! No crashes detected.")
else:
    print(f"FAIL {failed} test cases still failing")
