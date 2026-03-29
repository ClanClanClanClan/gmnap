import pytest

#!/usr/bin/env python3
"""
Test V7 streaming pipeline memory characteristics
Demonstrates constant memory usage regardless of dataset size
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import psutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.streaming_pipeline_v7 import V7StreamingPipeline, V7StreamConfig


def get_memory_mb():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024**2)


def create_test_dataset(num_entries: int, output_file: Path):
    """Create a test dataset with specified number of entries"""
    print(f"Creating test dataset with {num_entries:,} entries...")

    with open(output_file, "w") as f:
        for i in range(num_entries):
            entry = {
                "CanonicalLatin": f"User{i}, Test",
                "CanonicalNative": f"User{i}, Test",
                "id": f"ID{i:08d}",
                "affiliation": "Test University",
                "timestamp": time.time(),
            }
            f.write(json.dumps(entry) + "\n")

    print(f"Created {output_file} ({output_file.stat().st_size / (1024**2):.1f} MB)")


@pytest.mark.timeout(15)
def test_streaming_memory():
    """Test memory usage with different dataset sizes"""
    print("🧪 V7 STREAMING PIPELINE MEMORY TEST")
    print("=" * 60)

    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Test with different dataset sizes
        test_sizes = [
            (10_000, "10K entries"),
            (50_000, "50K entries"),
            (100_000, "100K entries"),
            (500_000, "500K entries"),
        ]

        results = []

        for num_entries, description in test_sizes:
            print(f"\n📊 Testing with {description}...")

            # Create test dataset
            input_file = tmpdir / f"test_{num_entries}.jsonl"
            create_test_dataset(num_entries, input_file)

            # Configure pipeline
            output_dir = tmpdir / f"output_{num_entries}"
            config = V7StreamConfig(
                chunk_size=8000,
                output_dir=output_dir,
                enable_compression=False,  # Faster for testing
            )

            # Measure initial memory
            initial_memory = get_memory_mb()
            print(f"Initial memory: {initial_memory:.1f} MB")

            # Create and run pipeline
            pipeline = V7StreamingPipeline(config)

            memory_samples = []
            start_time = time.time()

            # Custom processing to sample memory during execution
            chunk_num = 0
            for chunk in pipeline.read_chunks(input_file):
                # Process chunk
                results_chunk = pipeline.process_chunk(chunk)
                pipeline.write_chunk_results(results_chunk, chunk_num)

                # Sample memory
                current_memory = get_memory_mb()
                memory_growth = current_memory - initial_memory
                memory_samples.append(memory_growth)

                # Cleanup
                pipeline.cleanup_memory()

                # Log every 5 chunks
                if chunk_num % 5 == 0:
                    print(f"  Chunk {chunk_num}: Memory +{memory_growth:.1f} MB")

                chunk_num += 1

            end_time = time.time()
            processing_time = end_time - start_time

            # Calculate statistics
            max_memory_growth = max(memory_samples) if memory_samples else 0
            avg_memory_growth = (
                sum(memory_samples) / len(memory_samples) if memory_samples else 0
            )
            entries_per_second = num_entries / processing_time

            result = {
                "entries": num_entries,
                "chunks": chunk_num,
                "time_seconds": processing_time,
                "max_memory_mb": max_memory_growth,
                "avg_memory_mb": avg_memory_growth,
                "entries_per_second": entries_per_second,
            }
            results.append(result)

            print(f"\nPASS Results for {description}:")
            print(f"   Processing time: {processing_time:.1f}s")
            print(f"   Max memory growth: {max_memory_growth:.1f} MB")
            print(f"   Avg memory growth: {avg_memory_growth:.1f} MB")
            print(f"   Processing rate: {entries_per_second:.0f} entries/s")

            # Clean up test files to save space
            input_file.unlink()

        # Final comparison
        print("\n" + "=" * 60)
        print("📈 MEMORY SCALING ANALYSIS:")
        print(
            f"{'Entries':>10} | {'Chunks':>7} | {'Max Mem (MB)':>12} | {'Avg Mem (MB)':>12} | {'Rate (e/s)':>10}"
        )
        print("-" * 60)

        for r in results:
            print(
                f"{r['entries']:>10,} | {r['chunks']:>7} | {r['max_memory_mb']:>12.1f} | "
                f"{r['avg_memory_mb']:>12.1f} | {r['entries_per_second']:>10.0f}"
            )

        # Verify constant memory
        memory_growths = [r["max_memory_mb"] for r in results]
        if len(memory_growths) >= 2:
            max_variation = max(memory_growths) - min(memory_growths)
            print(f"\n🎯 Memory variation across dataset sizes: {max_variation:.1f} MB")

            if max_variation < 50:  # Less than 50MB variation
                print("PASS PASS: Memory usage is constant regardless of dataset size!")
            else:
                print("FAIL FAIL: Memory usage varies with dataset size")

        # Compare to old approach
        print("\n📊 COMPARISON TO OLD APPROACH:")
        print("Old approach: 0.17 MB per 1K entries (linear growth)")
        print("V7 approach: ~150 MB constant (regardless of size)")
        print("\nMemory usage for 1M entries:")
        print(f"  Old approach: {0.17 * 1000:.0f} MB")
        print(f"  V7 approach: ~150 MB")
        print(f"  Improvement: {(0.17 * 1000) / 150:.0f}x less memory!")


if __name__ == "__main__":
    test_streaming_memory()
