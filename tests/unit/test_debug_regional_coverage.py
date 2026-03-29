import pytest

#!/usr/bin/env python3
"""
Debug regional coverage registration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.pipeline_v6 import GMNAPPipeline
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


def debug_regional_coverage():
    """Debug what regions are actually registered."""

    print("=== Regional Coverage Debug ===")

    config = GMNAPConfig()
    pipeline = GMNAPPipeline(config)

    registered_regions = set(pipeline.region_manager._regions.keys())

    print(f"Total registered regions: {len(registered_regions)}")
    print(f"Registered regions: {sorted(registered_regions)}")

    v7_regions = [
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "B1",
        "B2",
        "B3",
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7",
        "C8",
        "C9",
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
        "E7",
        "F1",
        "F2",
        "F3",
        "F4",
        "G1",
        "H1",
        "R0",
        "Z0",
    ]

    print(f"\nExpected v7 regions: {len(v7_regions)}")
    print(f"Expected regions: {sorted(v7_regions)}")

    print(f"\nRegistered but not expected: {registered_regions - set(v7_regions)}")
    print(f"Expected but not registered: {set(v7_regions) - registered_regions}")


if __name__ == "__main__":
    debug_regional_coverage()
