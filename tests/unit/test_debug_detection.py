import pytest

#!/usr/bin/env python3
"""
Debug script to test region detection for specific names.
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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig

# Test names that are failing
test_names = [
    "Newton, Isaac",  # Should be A1
    "Sierpiński, Wacław",  # Should be B2
    "Erdős, Paul",  # Should be A2 (Hungarian)
    "Wang, Xiaoming",  # Should be E1
    "Kim, Min-su",  # Should be E4
]


@pytest.mark.timeout(15)
def test_detection():
    """Test region detection for problem names."""

    # Create manager
    config = GMNAPConfig()
    manager = RegionManager(Path("./config"))

    print("Testing region detection...\n")

    for name in test_names:
        entry = {"CanonicalLatin": name}
        result = manager.detect_region(entry)

        print(
            f"{name:25} -> {result.region_code} (confidence: {result.confidence:.2f})"
        )
        print(f"  Method: {result.detection_method}")
        print(f"  Metadata: {result.metadata}")
        print()


if __name__ == "__main__":
    test_detection()
