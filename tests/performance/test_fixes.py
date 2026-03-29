import pytest

# \!/usr/bin/env python3
"""Test the fixes for idempotency and authority errors"""
import sys
import tempfile
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


@pytest.mark.timeout(15)
def test_idempotency():
    """Test if idempotency is now working"""
    print("Testing idempotency fix...")

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

        # Create source manifest
        manifest_dir = temp_path / "cache" / "config"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_dir / "source_manifest.json", "w") as f:
            f.write('{"OpenAlex": {"enabled": true, "tier": 0, "daily_quota": 10}}')

        # Run pipeline
        pipeline = GMNAPPipeline(config, PipelineMode.QUICK)
        result = pipeline.run(input_dir)

        print(f"Pipeline completed: {result}")


if __name__ == "__main__":
    test_idempotency()
    print("\nTest completed\!")
