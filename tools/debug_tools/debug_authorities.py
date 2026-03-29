#!/usr/bin/env python3
"""Debug authority loading issue"""
import sys
import tempfile
import yaml
import json
import logging
from pathlib import Path

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.core.config import GMNAPConfig


def debug_authority_loading():
    """Debug why authorities are not loading"""
    print("=== Debugging Authority Loading ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        input_dir.mkdir()

        # Create test data
        test_data = {
            "Smith, John": {
                "GlobalID": "TEST001",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": 1980,
                "CountryCodes": ["US"],
                "Confidence": 85,
            }
        }

        with open(input_dir / "test.yaml", "w") as f:
            yaml.dump(test_data, f)

        # Setup config
        config = GMNAPConfig()
        config.cache.cache_dir = str(temp_path / "cache")
        config.database.db_path = str(temp_path / "test.db")
        config.database.path = str(temp_path / "test.db")

        # Create source manifest
        manifest_dir = temp_path / "cache" / "config"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "source_manifest.json"

        manifest_data = {
            "OpenAlex": {"enabled": True, "tier": 0, "daily_quota": 864000},
            "Crossref": {"enabled": True, "tier": 0, "daily_quota": 4300000},
            "ORCID": {"enabled": True, "tier": 0, "daily_quota": 500},
            "zbMATH": {"enabled": True, "tier": 0, "daily_quota": 200},
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        print(f"Created manifest at: {manifest_path}")
        print(f"Manifest exists: {manifest_path.exists()}")
        print(f"Manifest contents:")
        with open(manifest_path) as f:
            print(f.read())

        # Create pipeline and run
        print("\nCreating pipeline...")
        pipeline = GMNAPPipeline(config, PipelineMode.QUICK)

        print("\nChecking loaded authorities before stage 0...")
        print(f"Number of authorities loaded: {len(pipeline._authorities)}")

        print("\nCalling _stage_0_config...")
        pipeline._stage_0_config()

        print("\nChecking loaded authorities after stage 0...")
        print(f"Number of authorities loaded: {len(pipeline._authorities)}")
        for name, fetcher in pipeline._authorities.items():
            print(f"  - {name}: tier={fetcher.tier} (value={fetcher.tier.value})")

        print("\nRunning full pipeline...")
        result = pipeline.run(input_dir)

        print(f"\nPipeline completed: {result}")


if __name__ == "__main__":
    debug_authority_loading()
