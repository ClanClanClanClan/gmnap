#!/usr/bin/env python3
"""Debug idempotency issues in GMNAP pipeline."""

import json
import tempfile
from pathlib import Path

from src.core.config import GMNAPConfig
from src.core.pipeline_v6 import GMNAPPipeline


def debug_idempotency():
    # Create temp directory and config
    with tempfile.TemporaryDirectory() as temp_dir:
        config = GMNAPConfig()
        config.cache.cache_dir = temp_dir + "/cache"
        config.database.db_path = temp_dir + "/test.db"

        # Test same entry processed twice
        test_entry = {
            "Smith, John": {
                "GlobalID": "TESTABCDEFGHIJKLMNOPQR",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": 1980,
                "CountryCodes": ["US"],
            }
        }

        # Write test data
        input_dir = Path(temp_dir) / "input"
        input_dir.mkdir(parents=True)

        with open(input_dir / "test.yaml", "w") as f:
            import yaml

            yaml.dump(test_entry, f)

        # First run
        pipeline1 = GMNAPPipeline(config, idempotency_check=True)
        result1 = pipeline1.run(input_dir)
        hash1 = pipeline1._compute_pipeline_hash()

        # Second run with same data
        pipeline2 = GMNAPPipeline(config, idempotency_check=True)
        result2 = pipeline2.run(input_dir)
        hash2 = pipeline2._compute_pipeline_hash()

        print(f"Hash 1: {hash1[:16]}...")
        print(f"Hash 2: {hash2[:16]}...")
        print(f"Hashes match: {hash1 == hash2}")

        # Check if entries are identical
        if hasattr(pipeline1, "_entries") and hasattr(pipeline2, "_entries"):
            entry1 = pipeline1._entries.get("Smith, John", {})
            entry2 = pipeline2._entries.get("Smith, John", {})

            # Compare without non-deterministic fields
            clean1 = {k: v for k, v in entry1.items() if not k.startswith("_")}
            clean2 = {k: v for k, v in entry2.items() if not k.startswith("_")}

            print(f"Entries match: {clean1 == clean2}")

            # Show differences
            for k in set(clean1.keys()) | set(clean2.keys()):
                v1 = clean1.get(k)
                v2 = clean2.get(k)
                if v1 != v2:
                    print(f'Diff {k}: "{v1}" vs "{v2}"')

            # Show all fields to debug
            print("\nEntry 1 fields:")
            for k, v in sorted(clean1.items()):
                print(f"  {k}: {v}")

            print("\nEntry 2 fields:")
            for k, v in sorted(clean2.items()):
                print(f"  {k}: {v}")


if __name__ == "__main__":
    debug_idempotency()
