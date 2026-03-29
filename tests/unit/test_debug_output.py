import pytest

#!/usr/bin/env python3
"""
Debug test output to see why names are MISSING.
"""

import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.core.pipeline_v6 import GMNAPPipeline

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


@pytest.mark.timeout(15)
def test_debug_output():
    """Debug why names are returning MISSING."""

    test_mathematicians = {
        "Newton, Isaac": "A1",
        "Wang, Xiaoming": "E1",
        "Chebyshev, Pafnuty": "B1",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test data
        test_data = {}
        for name, expected_region in test_mathematicians.items():
            test_data[name] = {
                "GlobalID": f"test_{name.replace(', ', '_')}",
                "CanonicalLatin": name,
            }

        test_file = tmpdir / "mathematicians.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_data, f)

        # Run pipeline
        config = GMNAPConfig()
        pipeline = GMNAPPipeline(config)

        try:
            pipeline.run(tmpdir)

            # Check output files
            output_files = list(Path(config.cache.cache_dir).glob("output/*.yaml"))
            print(f"Output files found: {len(output_files)}")

            if output_files:
                # Read results from the latest output file
                latest_file = sorted(output_files)[-1]
                print(f"Reading from: {latest_file}")

                with open(latest_file, "r") as f:
                    results = yaml.safe_load(f)

                print(f"\nResults type: {type(results)}")
                if results:
                    print(f"Number of entries: {len(results)}")
                    print("\nContent:")
                    for key, value in results.items():
                        print(f"\n{key}:")
                        if isinstance(value, dict):
                            print(
                                f"  RegionCode: {value.get('RegionCode', 'NOT_FOUND')}"
                            )
                            print(f"  Keys: {list(value.keys())[:10]}")
                        else:
                            print(f"  Value type: {type(value)}")
                else:
                    print("Results is None or empty")
            else:
                print("No output files found!")

        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_debug_output()
