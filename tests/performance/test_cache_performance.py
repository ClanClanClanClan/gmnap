import pytest

#!/usr/bin/env python3
"""Test cache performance by running pipeline twice"""
import sys
import tempfile
import yaml
import json
from pathlib import Path
from datetime import datetime

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
def test_cache_performance():
    """Test cache performance with multiple runs"""
    print("=== TESTING CACHE PERFORMANCE ===")

    # Use persistent temp dir for cache
    cache_base = Path("/tmp/gmnap_cache_test")
    cache_base.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        input_dir.mkdir()

        # Create test data
        test_data = {}
        names = [
            "Smith, John Michael",
            "Johnson, Robert",
            "Williams, David",
            "Brown, Michael",
            "Jones, William",
        ]

        for i, name in enumerate(names):
            test_data[name] = {
                "GlobalID": f"TEST{i:03d}",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": name,
                "CanonicalNative": name,
                "BirthYear": 1980 + i,
                "CountryCodes": ["US"],
                "Confidence": 85,
            }

        with open(input_dir / "test.yaml", "w") as f:
            yaml.dump(test_data, f)

        # Setup config with persistent cache
        config = GMNAPConfig()
        config.cache.cache_dir = str(cache_base)
        config.database.db_path = str(temp_path / "test.db")
        config.database.path = str(temp_path / "test.db")

        # Create source manifest
        manifest_dir = cache_base / "config"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "source_manifest.json"

        manifest_data = {
            "OpenAlex": {"enabled": True, "tier": 0, "daily_quota": 864000},
            "Crossref": {"enabled": True, "tier": 0, "daily_quota": 4300000},
            "ORCID": {"enabled": True, "tier": 0, "daily_quota": 500},
            "zbMATH": {"enabled": True, "tier": 0, "daily_quota": 200},
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

        # Run 1: Cold cache
        print("\n🥶 RUN 1: COLD CACHE")
        print("-" * 50)
        pipeline1 = GMNAPPipeline(config, PipelineMode.QUICK)
        start1 = datetime.now()
        result1 = pipeline1.run(input_dir)
        duration1 = (datetime.now() - start1).total_seconds()

        stage4_time1 = (
            result1.stage_metrics["stage_4"].end_time - result1.stage_metrics["stage_4"].start_time
        )
        print(f"Total time: {duration1:.3f}s")
        print(f"Stage 4 (Authority): {stage4_time1.total_seconds():.3f}s")

        # Get cache stats
        if pipeline1._authority_cache:
            stats = pipeline1._authority_cache.get_stats()
            print(f"Cache stats: {stats['hits']} hits, {stats['misses']} misses")

        # Run 2: Warm cache
        print("\n🔥 RUN 2: WARM CACHE")
        print("-" * 50)
        pipeline2 = GMNAPPipeline(config, PipelineMode.QUICK)
        start2 = datetime.now()
        result2 = pipeline2.run(input_dir)
        duration2 = (datetime.now() - start2).total_seconds()

        stage4_time2 = (
            result2.stage_metrics["stage_4"].end_time - result2.stage_metrics["stage_4"].start_time
        )
        print(f"Total time: {duration2:.3f}s")
        print(f"Stage 4 (Authority): {stage4_time2.total_seconds():.3f}s")

        # Get cache stats
        if pipeline2._authority_cache:
            stats = pipeline2._authority_cache.get_stats()
            print(f"Cache stats: {stats['hits']} hits, {stats['misses']} misses")
            print(f"Cache hit rate: {stats['hit_rate']:.1%}")

        # Compare
        print("\n📊 PERFORMANCE IMPROVEMENT")
        print("-" * 50)
        improvement = (
            stage4_time1.total_seconds() - stage4_time2.total_seconds()
        ) / stage4_time1.total_seconds()
        print(f"Stage 4 speedup: {improvement:.1%}")
        print(f"Total speedup: {(duration1 - duration2) / duration1:.1%}")


if __name__ == "__main__":
    test_cache_performance()
