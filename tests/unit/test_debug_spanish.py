import pytest

#!/usr/bin/env python3
"""
Debug Spanish/Portuguese detection.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os

os.environ["GMNAP_TEST_MODE"] = "true"
from src.regions.manager import RegionManager


@pytest.mark.timeout(15)
def test_spanish_detection():
    """Debug why Spanish names go to A2 instead of G1."""

    manager = RegionManager()

    test_names = ["García, María", "Silva, José"]

    for name in test_names:
        print(f"\n=== Testing {name} ===")

        test_entry = {
            "GlobalID": f"test_{name.replace(', ', '_')}",
            "CanonicalLatin": name,
        }

        # Test surname detection
        result = manager._detect_by_surname(test_entry)
        if result:
            print(
                f"Surname detection: {result.region_code} (confidence: {result.confidence})"
            )
            print(f"Method: {result.detection_method}")
            print(f"Metadata: {result.metadata}")
        else:
            print("Surname detection: NONE")

        # Test script detection
        script_result = manager._detect_by_script(test_entry)
        if script_result:
            print(f"Script detection: {script_result.region_code}")

        # Test full detection
        full_result = manager.detect_region(test_entry)
        print(
            f"Final result: {full_result.region_code} (confidence: {full_result.confidence})"
        )
        print(f"Method: {full_result.detection_method}")
        print(f"Metadata: {full_result.metadata}")


if __name__ == "__main__":
    test_spanish_detection()
