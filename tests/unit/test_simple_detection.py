import pytest

#!/usr/bin/env python3
"""
Test region detection without full pipeline.
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


@pytest.mark.timeout(15)
def test_simple_detection():
    """Test region detection for specific names."""

    config = GMNAPConfig()
    pipeline = GMNAPPipeline(config)

    # Initialize pipeline
    pipeline._stage_0_config()

    test_entries = {
        "Newton, Isaac": {"CanonicalLatin": "Newton, Isaac"},
        "Wang, Xiaoming": {"CanonicalLatin": "Wang, Xiaoming"},
        "Chebyshev, Pafnuty": {"CanonicalLatin": "Chebyshev, Pafnuty"},
        "Gauss, Carl Friedrich": {"CanonicalLatin": "Gauss, Carl Friedrich"},
    }

    print("Testing region detection:\n")

    for name, entry in test_entries.items():
        result = pipeline.region_manager.detect_region(entry)
        print(f"{name}:")
        print(f"  Region: {result.region_code}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Method: {result.detection_method}")
        print(f"  Metadata: {result.metadata}")
        print()


if __name__ == "__main__":
    test_simple_detection()
