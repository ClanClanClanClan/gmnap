import pytest

#!/usr/bin/env python3
"""
Test classification directly to debug issues.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.core.pipeline_v6 import GMNAPPipeline

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import tempfile

import yaml

from src.core.config import GMNAPConfig


@pytest.mark.timeout(60)  # bumped from 15s — pipeline subprocess on
# 2-core GHA runners legitimately needs ~25-40s; 15s was tight enough
# that thermal throttling or queue contention failed the assertion.
def test_direct_classification():
    """Test classification of specific names."""

    test_names = {
        "Newton, Isaac": {"GlobalID": "test_newton", "CanonicalLatin": "Newton, Isaac"},
        "Wang, Xiaoming": {"GlobalID": "test_wang", "CanonicalLatin": "Wang, Xiaoming"},
        "Chebyshev, Pafnuty": {
            "GlobalID": "test_chebyshev",
            "CanonicalLatin": "Chebyshev, Pafnuty",
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test file
        test_file = tmpdir / "test.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_names, f)

        # Run pipeline
        config = GMNAPConfig()
        pipeline = GMNAPPipeline(config)

        try:
            result = pipeline.run(tmpdir)
            print(f"Pipeline result: {result}")

            # Check internal entries
            print(f"\nInternal entries: {len(pipeline._entries)}")
            for name, entry in pipeline._entries.items():
                region = entry.get("_region", "NOT_SET")
                error = entry.get("_region_error", "")
                print(f"\n{name}:")
                print(f"  _region: {region}")
                if error:
                    print(f"  _region_error: {error}")
                print(f"  Entry keys: {list(entry.keys())}")

            # Check output files
            output_dir = Path(config.cache.cache_dir) / "output"
            if output_dir.exists():
                output_files = list(output_dir.glob("*.yaml"))
                print(f"\nOutput files: {output_files}")

                if output_files:
                    with open(output_files[0], "r") as f:
                        output_data = yaml.safe_load(f)

                    print("\nOutput data:")
                    for name, data in output_data.items():
                        print(f"\n{name}:")
                        print(f"  RegionCode: {data.get('RegionCode', 'MISSING')}")
                        print(f"  Keys: {list(data.keys())}")

        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_direct_classification()
