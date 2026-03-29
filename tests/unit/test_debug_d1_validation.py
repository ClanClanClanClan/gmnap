import pytest

#!/usr/bin/env python3
"""
Debug D1 validation issues.
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
import sys
from pathlib import Path

from src.core.config import GMNAPConfig

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.d_groups.d1_south_asia_hindi_belt import D1_SouthAsiaHindiBelt


@pytest.mark.timeout(30)
def test_d1_validation():
    """Test D1 validation with Indian names."""

    region = D1_SouthAsiaHindiBelt()

    test_names = ["Ramanujan, Srinivasa", "Bose, Satyendra Nath"]

    for name in test_names:
        print(f"\n=== Testing D1 validation for {name} ===")

        test_entry = {
            "GlobalID": f"test_{name.replace(', ', '_')}",
            "CanonicalLatin": name,
        }

        try:
            # Test cleaning
            region.clean(test_entry)
            print(f"PASS Clean: {test_entry}")

            # Test augmentation
            region.augment(test_entry)
            print(f"PASS Augment: RegionCode = {test_entry.get('RegionCode')}")
            print(f"   RegionalExtras: {test_entry.get('RegionalExtras', {})}")

            # Test validation
            region.validate(test_entry)
            print("PASS Validation: PASSED")

        except Exception as e:
            print(f"FAIL Error: {e}")
            import traceback

            traceback.print_exc()


@pytest.mark.timeout(30)
def test_d1_pipeline():
    """Test D1 in full pipeline."""

    test_names = ["Ramanujan, Srinivasa", "Bose, Satyendra Nath"]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test data
        test_data = {}
        for name in test_names:
            test_data[name] = {
                "GlobalID": f"test_{name.replace(', ', '_')}",
                "CanonicalLatin": name,
            }

        test_file = tmpdir / "indian_names.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_data, f)

        # Run pipeline
        config = GMNAPConfig()
        pipeline = GMNAPPipeline(config)

        try:
            result = pipeline.run(tmpdir)
            print("\n=== Pipeline Result ===")
            print(f"Success: {result.successful_entries}/{result.total_entries}")
            print(f"Failed: {result.failed_entries}")

            # Check output
            output_files = list(Path(config.cache.cache_dir).glob("output/*.yaml"))
            if output_files:
                latest_file = sorted(output_files)[-1]
                print(f"Reading from: {latest_file}")

                with open(latest_file, "r") as f:
                    results = yaml.safe_load(f)

                for name in test_names:
                    if name in results:
                        region_code = results[name].get("RegionCode", "MISSING")
                        print(f"{name}: {region_code}")
                        if region_code == "Z0":
                            print(f"  Entry keys: {list(results[name].keys())}")
                    else:
                        print(f"{name}: NOT FOUND")

        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    print("=== Testing D1 Region Directly ===")
    test_d1_validation()

    print("\n\n=== Testing D1 in Pipeline ===")
    test_d1_pipeline()
