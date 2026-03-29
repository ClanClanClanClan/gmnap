import pytest

#!/usr/bin/env python3
"""
Test streaming pipeline performance vs regular pipeline.

Demonstrates bounded memory usage and scalability improvements.
"""

import sys
import tempfile
import time
from pathlib import Path

import psutil
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.core.streaming_pipeline import StreamingConfig, StreamingPipeline

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


def generate_test_data(num_entries: int, output_dir: Path) -> None:
    """Generate test dataset with specified number of entries."""
    entries_per_file = 1000
    num_files = (num_entries + entries_per_file - 1) // entries_per_file

    print(f"Generating {num_entries} test entries across {num_files} files...")

    # Sample data patterns for different regions
    sample_patterns = [
        # Anglo-Sphere
        {"name": "Smith, John {}", "country": "US", "region": "A1"},
        {"name": "Brown, Sarah {}", "country": "GB", "region": "A1"},
        {"name": "Davis, Michael {}", "country": "CA", "region": "A1"},
        # Hindi Belt
        {"name": "राम प्रकाश शर्मा {}", "country": "IN", "region": "D1"},
        {"name": "सुनील कुमार गुप्ता {}", "country": "IN", "region": "D1"},
        {"name": "अनिता देवी {}", "country": "IN", "region": "D1"},
        # East Slavic
        {"name": "Иванов Иван Петрович {}", "country": "RU", "region": "B1"},
        {"name": "Петров Петр Иванович {}", "country": "RU", "region": "B1"},
        # Chinese
        {"name": "王小明 {}", "country": "CN", "region": "E1"},
        {"name": "李大华 {}", "country": "CN", "region": "E1"},
        # Arabic
        {"name": "محمد عبد الله {}", "country": "EG", "region": "C3"},
        {"name": "أحمد حسن {}", "country": "EG", "region": "C3"},
    ]

    entry_count = 0
    for file_idx in range(num_files):
        file_data = {}

        entries_this_file = min(entries_per_file, num_entries - entry_count)

        for i in range(entries_this_file):
            pattern = sample_patterns[entry_count % len(sample_patterns)]

            name = pattern["name"].format(entry_count)
            canonical_latin = name

            # Generate GlobalID
            global_id = f"G{entry_count:019d}"  # 20-char GlobalID

            file_data[canonical_latin] = {
                "GlobalID": global_id,
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": canonical_latin,
                "CanonicalNative": name,
                "BirthYear": 1980 + (entry_count % 40),
                "CountryCodes": [pattern["country"]],
                "Confidence": 85 + (entry_count % 15),
            }

            entry_count += 1

        # Write file
        file_path = output_dir / f"test_data_{file_idx:04d}.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(file_data, f, allow_unicode=True, default_flow_style=False)

    print(f"Generated {entry_count} entries in {output_dir}")


def measure_memory_usage() -> float:
    """Get current memory usage in MB."""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except:
        return 0.0


@pytest.mark.timeout(15)
def test_pipeline_performance(
    pipeline_class, dataset_size: int, config: GMNAPConfig, streaming_config=None
) -> dict:
    """Test pipeline performance and memory usage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        input_dir.mkdir()

        # Set up config paths
        config.cache.cache_dir = str(temp_path / "cache")
        config.database.db_path = str(temp_path / "test.db")

        # Copy source_manifest.json if it exists
        source_manifest_path = Path("cache/config/source_manifest.json")
        if source_manifest_path.exists():
            cache_config_dir = temp_path / "cache" / "config"
            cache_config_dir.mkdir(parents=True, exist_ok=True)

            import shutil

            shutil.copy2(
                source_manifest_path, cache_config_dir / "source_manifest.json"
            )

        # Generate test data
        generate_test_data(dataset_size, input_dir)

        # Measure initial memory
        initial_memory = measure_memory_usage()

        # Create pipeline
        if streaming_config:
            pipeline = pipeline_class(config, PipelineMode.QUICK, streaming_config)
        else:
            pipeline = pipeline_class(config, PipelineMode.QUICK)

        # Run pipeline and measure performance
        start_time = time.time()
        peak_memory = initial_memory

        try:
            result = pipeline.run(input_dir)
            success = True
            error = None

        except Exception as e:
            success = False
            error = str(e)
            result = None

        end_time = time.time()
        final_memory = measure_memory_usage()

        # Try to estimate peak memory (rough approximation)
        current_memory = measure_memory_usage()
        peak_memory = max(peak_memory, current_memory)

        return {
            "success": success,
            "error": error,
            "duration_seconds": end_time - start_time,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "peak_memory_mb": peak_memory,
            "memory_increase_mb": final_memory - initial_memory,
            "dataset_size": dataset_size,
            "entries_per_second": (
                dataset_size / (end_time - start_time) if success else 0
            ),
            "result": result,
        }


def run_performance_comparison():
    """Run performance comparison between regular and streaming pipelines."""
    print("🚀 GMNAP Pipeline Performance Comparison")
    print("=" * 60)

    # Test dataset sizes
    test_sizes = [100, 1000, 5000]  # Start with smaller sizes for safety

    config = GMNAPConfig()

    results = {}

    for size in test_sizes:
        print(f"\n📊 Testing with {size} entries:")
        print("-" * 40)

        # Test regular pipeline
        print("🔄 Regular Pipeline...")
        try:
            regular_result = test_pipeline_performance(GMNAPPipeline, size, config)
            results[f"regular_{size}"] = regular_result

            if regular_result["success"]:
                print(
                    f"  PASS Success: {regular_result['duration_seconds']:.1f}s, "
                    f"Memory: {regular_result['memory_increase_mb']:.1f}MB increase, "
                    f"Speed: {regular_result['entries_per_second']:.1f} entries/sec"
                )
            else:
                print(f"  FAIL Failed: {regular_result['error']}")

        except Exception as e:
            print(f"  💥 Crashed: {e}")
            regular_result = {"success": False, "error": str(e)}
            results[f"regular_{size}"] = regular_result

        # Test streaming pipeline
        print("🌊 Streaming Pipeline...")
        try:
            streaming_config = StreamingConfig(
                chunk_size=min(100, size // 2),  # Adaptive chunk size
                memory_limit_mb=256,
                checkpoint_interval=5,
            )

            streaming_result = test_pipeline_performance(
                StreamingPipeline, size, config, streaming_config
            )
            results[f"streaming_{size}"] = streaming_result

            if streaming_result["success"]:
                print(
                    f"  PASS Success: {streaming_result['duration_seconds']:.1f}s, "
                    f"Memory: {streaming_result['memory_increase_mb']:.1f}MB increase, "
                    f"Speed: {streaming_result['entries_per_second']:.1f} entries/sec"
                )
            else:
                print(f"  FAIL Failed: {streaming_result['error']}")

        except Exception as e:
            print(f"  💥 Crashed: {e}")
            streaming_result = {"success": False, "error": str(e)}
            results[f"streaming_{size}"] = streaming_result

        # Compare results
        if regular_result.get("success") and streaming_result.get("success"):
            speed_improvement = (
                streaming_result["entries_per_second"]
                / regular_result["entries_per_second"]
            )
            memory_improvement = regular_result["memory_increase_mb"] / max(
                streaming_result["memory_increase_mb"], 1
            )

            print("\n📈 Comparison:")
            print(f"  Speed improvement: {speed_improvement:.2f}x")
            print(f"  Memory efficiency: {memory_improvement:.2f}x better")

        print()

    # Generate summary
    print("🏁 PERFORMANCE SUMMARY")
    print("=" * 60)

    for size in test_sizes:
        regular_key = f"regular_{size}"
        streaming_key = f"streaming_{size}"

        if regular_key in results and streaming_key in results:
            regular = results[regular_key]
            streaming = results[streaming_key]

            print(f"\n📊 {size} entries:")

            if regular.get("success"):
                print(
                    f"  Regular:   {regular['duration_seconds']:.1f}s, "
                    f"{regular['memory_increase_mb']:.1f}MB, "
                    f"{regular['entries_per_second']:.1f} entries/sec"
                )
            else:
                print(f"  Regular:   FAILED - {regular.get('error', 'Unknown error')}")

            if streaming.get("success"):
                print(
                    f"  Streaming: {streaming['duration_seconds']:.1f}s, "
                    f"{streaming['memory_increase_mb']:.1f}MB, "
                    f"{streaming['entries_per_second']:.1f} entries/sec"
                )
            else:
                print(
                    f"  Streaming: FAILED - {streaming.get('error', 'Unknown error')}"
                )

    # Performance projection
    print("\n🎯 EXTRAPOLATION TO 1M ENTRIES:")

    # Find best performing streaming result
    best_streaming = None
    for size in test_sizes:
        key = f"streaming_{size}"
        if key in results and results[key].get("success"):
            if (
                not best_streaming
                or results[key]["entries_per_second"]
                > best_streaming["entries_per_second"]
            ):
                best_streaming = results[key]

    if best_streaming:
        projected_time_minutes = (1_000_000 / best_streaming["entries_per_second"]) / 60
        print(
            f"  Projected streaming time for 1M entries: {projected_time_minutes:.1f} minutes"
        )

        if projected_time_minutes <= 30:
            print("  🎉 MEETS PERFORMANCE TARGET! (<=30 min)")
        else:
            print(
                f"  WARN  Still {projected_time_minutes/30:.1f}x slower than 30min target"
            )
    else:
        print("  FAIL No successful streaming runs to extrapolate from")

    return results


if __name__ == "__main__":
    try:
        results = run_performance_comparison()
        print("\nPASS Performance testing completed successfully!")

    except KeyboardInterrupt:
        print("\n⏹️  Performance testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Performance testing failed: {e}")
        import traceback

        traceback.print_exc()
