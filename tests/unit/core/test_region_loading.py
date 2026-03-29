import pytest

#!/usr/bin/env python3
"""
Test region loading directly.
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
def test_region_loading():
    """Test if regions are being loaded."""

    config = GMNAPConfig()
    pipeline = GMNAPPipeline(config)

    # Force initialization
    try:
        pipeline._stage_0_config()
    except Exception as e:
        print(f"Error during config stage: {e}")
        import traceback

        traceback.print_exc()

    print(f"Loaded {len(pipeline.region_manager._regions)} regions:")
    for code in sorted(pipeline.region_manager._regions.keys()):
        region = pipeline.region_manager._regions[code]
        print(f"  {code}: {region.__class__.__name__}")


if __name__ == "__main__":
    test_region_loading()
