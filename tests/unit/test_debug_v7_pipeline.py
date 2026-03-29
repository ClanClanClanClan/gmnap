import pytest

#!/usr/bin/env python3
"""
Debug v7 mathematician classification in pipeline.
"""

import sys
import tempfile
import yaml
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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os

os.environ["GMNAP_TEST_MODE"] = "true"
from src.regions.manager import RegionManager


@pytest.mark.timeout(30)
def test_debug_v7_pipeline():
    """Debug why v7 mathematicians return MISSING."""

    # Test a few key mathematicians that should classify
    test_mathematicians = {
        "Newton, Isaac": "A1",
        "Euler, Leonhard": "A2",
        "Wang, Xiaoming": "E1",
        "Tanaka, Yoshio": "E3",
        "Chebyshev, Pafnuty": "B1",
        "Al-Khwarizmi, Muhammad ibn Musa": "C3",
        "Ramanujan, Srinivasa": "D1",  # Should fail - no D1 region
    }

    # First test direct detection
    print("=== Testing Direct Region Detection ===")
    manager = RegionManager()

    for name, expected in test_mathematicians.items():
        test_entry = {
            "GlobalID": f"test_{name.replace(', ', '_')}",
            "CanonicalLatin": name,
        }

        result = manager.detect_region(test_entry)
        print(f"\n{name}:")
        if result:
            print(f"  Detected: {result.region_code} (confidence: {result.confidence})")
            print(f"  Method: {result.detection_method}")
            print(f"  Metadata: {result.metadata}")
        else:
            print("  NOT DETECTED")
        print(f"  Expected: {expected}")

    print("\n\n=== Testing Full Pipeline ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test data
        test_data = {}
        for name, expected_region in test_mathematicians.items():
            test_data[name] = {
                "GlobalID": f"test_{name.replace(', ', '_').replace(' ', '_')}",
                "CanonicalLatin": name,
            }

        test_file = tmpdir / "mathematicians.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_data, f)

        # Run pipeline
        config = GMNAPConfig()
        pipeline = GMNAPPipeline(config)

        try:
            result = pipeline.run(tmpdir)
            print(f"\nPipeline result: {result}")

            # Check output files
            output_files = list(Path(config.cache.cache_dir).glob("output/*.yaml"))
            print(f"\nOutput files found: {len(output_files)}")

            if output_files:
                # Read results from the latest output file
                latest_file = sorted(output_files)[-1]
                print(f"Reading from: {latest_file}")

                with open(latest_file, "r") as f:
                    results = yaml.safe_load(f)

                if results:
                    print(f"\nProcessed entries: {len(results)}")
                    for key, entry in results.items():
                        region_code = entry.get("RegionCode", "MISSING")
                        print(f"\n{key}: {region_code}")
                        if region_code == "MISSING":
                            print(f"  Full entry: {list(entry.keys())}")

        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_debug_v7_pipeline()
