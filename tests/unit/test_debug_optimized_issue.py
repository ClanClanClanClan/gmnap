import pytest

#!/usr/bin/env python3
"""
Debug why optimized manager is returning 0% classification.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_optimized_manager():
    """Test the optimized region manager."""

    print("=== Testing Optimized RegionManager ===")

    manager = RegionManager()

    # Check if regions loaded
    print(f"\nImplemented regions: {manager.IMPLEMENTED_REGIONS}")
    print(f"Registered regions: {len(manager._regions)}")
    print(f"Regions loaded: {manager._regions_loaded}")

    # Force load regions
    manager._ensure_regions_loaded()
    print(f"\nAfter ensure_regions_loaded:")
    print(f"Registered regions: {len(manager._regions)}")
    print(f"Region codes: {sorted(manager._regions.keys())}")

    # Test detection
    test_cases = [
        {"CanonicalLatin": "Newton, Isaac"},
        {"CanonicalLatin": "García, María"},
        {"CanonicalLatin": "Wang, Xiaoming"},
    ]

    for test in test_cases:
        print(f"\nTesting: {test['CanonicalLatin']}")

        # Use public API method for detection
        result = manager.detect_region(test)
        print(f"Result: {result.region_code} (confidence: {result.confidence})")
        print(f"Method: {result.detection_method}")


if __name__ == "__main__":
    test_optimized_manager()
