import pytest

#!/usr/bin/env python3
"""
Quick test to verify the pipeline fix works
"""

import sys

sys.path.insert(
    0, "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src"
)

from src.core.pipeline import GMNAPPipeline


@pytest.mark.timeout(15)
def test_key_cases():
    """Test the key problematic cases"""
    pipeline = GMNAPPipeline()

    test_cases = [
        ("Rényi, Alfréd", "A2", "Hungarian accent issue"),
        ("Lee, Min-Ho", "E4", "Korean hyphen issue"),
        ("Hájek, Petr", "B2", "Czech -> Spanish issue"),
        ("Kim, Jong-Un", "E4", "Korean basic test"),
        ("Yang, Lei", "E1", "Chinese basic test"),
    ]

    results = []
    for name, expected, description in test_cases:
        try:
            entry = {"CanonicalLatin": name}
            result = pipeline.process_entry(entry)
            actual = result.get("RegionCode", "ERROR")
            status = "PASS" if actual == expected else "FAIL"
            results.append((name, expected, actual, status, description))
            print(f"{status} {name}: Expected {expected}, Got {actual} ({description})")
        except Exception as e:
            results.append((name, expected, f"ERROR: {str(e)}", "FAIL", description))
            print(f"FAIL {name}: ERROR: {str(e)} ({description})")

    passed = sum(1 for r in results if r[3] == "PASS")
    total = len(results)

    print(f"\n📊 Quick Test Results: {passed}/{total} ({passed/total*100:.1f}%)")

    return passed == total


if __name__ == "__main__":
    test_key_cases()
