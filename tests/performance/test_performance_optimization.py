import pytest

#!/usr/bin/env python3
"""
Test performance improvements with optimized RegionManager.
"""

import time
import tempfile
from pathlib import Path
import yaml

import sys

sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


def generate_test_data(n_entries: int) -> dict:
    """Generate test mathematician data."""
    test_data = {}

    # Mix of different regions to test detection
    test_patterns = [
        ("Smith, John", "A1"),
        ("Müller, Hans", "A2"),
        ("Ivanov, Ivan", "B1"),
        ("Kowalski, Piotr", "B2"),
        ("Hassan, Ahmad", "C3"),
        ("Sharma, Raj", "D1"),
        ("Wang, Xiaoming", "E1"),
        ("Tanaka, Satoshi", "E3"),
        ("García, María", "G1"),
    ]

    for i in range(n_entries):
        pattern = test_patterns[i % len(test_patterns)]
        name = f"{pattern[0].split(',')[0]}{i}, {pattern[0].split(',')[1].strip()}"
        test_data[name] = {
            "GlobalID": f"TEST{i:010d}",
            "CanonicalLatin": name,
            "UpdatedAt": "2025-01-01T00:00:00Z",
        }

    return test_data


@pytest.mark.timeout(15)
def test_with_manager(manager_type: str, n_entries: int):
    """Test pipeline with specified manager type."""

    # Temporarily modify the import
    if manager_type == "optimized":
        # Monkey patch to use optimized manager
        import src.regions
        from src.regions.manager_optimized import RegionManager

        src.regions.manager.RegionManager = RegionManager

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test data
        test_data = generate_test_data(n_entries)
        test_file = tmpdir_path / "test_data.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_data, f)

        # Setup config
        config = GMNAPConfig()
        config.cache.cache_dir = str(tmpdir_path / "cache")

        # Time the pipeline
        start_time = time.time()

        pipeline = GMNAPPipeline(config, mode=PipelineMode.QUICK)
        result = pipeline.run(tmpdir_path)

        end_time = time.time()
        duration = end_time - start_time

        return {
            "duration": duration,
            "entries_per_sec": n_entries / duration,
            "success_rate": result.successful_entries / result.total_entries,
            "total_entries": result.total_entries,
        }


def main():
    """Compare performance between standard and optimized managers."""
    print("🔬 GMNAP Performance Optimization Test")
    print("=" * 60)

    test_sizes = [100, 500, 1000]

    for size in test_sizes:
        print(f"\n📊 Testing with {size} entries...")

        # Test with standard manager
        print("  Standard RegionManager:", end=" ", flush=True)
        standard_result = test_with_manager("standard", size)
        print(
            f"{standard_result['duration']:.2f}s ({standard_result['entries_per_sec']:.1f} entries/sec)"
        )

        # Reset import
        import importlib
        import src.regions.manager

        importlib.reload(src.regions.manager)

        # Test with optimized manager
        print("  Optimized RegionManager:", end=" ", flush=True)
        optimized_result = test_with_manager("optimized", size)
        print(
            f"{optimized_result['duration']:.2f}s ({optimized_result['entries_per_sec']:.1f} entries/sec)"
        )

        # Calculate improvement
        improvement = (
            (standard_result["duration"] - optimized_result["duration"])
            / standard_result["duration"]
            * 100
        )
        speedup = standard_result["duration"] / optimized_result["duration"]

        print(f"  ⚡ Improvement: {improvement:.1f}% faster ({speedup:.2f}x speedup)")

    print("\n" + "=" * 60)
    print("💡 Recommendation: Use the optimized RegionManager for production")
    print("   Update src/core/pipeline_v6.py to import from manager_optimized")


if __name__ == "__main__":
    main()
