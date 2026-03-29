import pytest

#!/usr/bin/env python3
"""
Simple test of V7 streaming pipeline
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


@pytest.mark.timeout(15)
def test_simple_streaming():
    """Test streaming with 10K entries"""
    print("🧪 V7 STREAMING PIPELINE SIMPLE TEST")
    print("=" * 60)

    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test dataset
        print("Creating test dataset with 10,000 entries...")
        input_file = tmpdir / "test_10k.jsonl"

        with open(input_file, "w") as f:
            for i in range(10000):
                entry = {
                    "CanonicalLatin": f"User{i}, Test",
                    "CanonicalNative": f"User{i}, Test",
                    "name": f"Test User{i}",  # Added for RegionManager compatibility
                    "id": f"ID{i:08d}",
                    "affiliation": "Test University",
                }
                f.write(json.dumps(entry) + "\n")

        print(f"Created {input_file} ({input_file.stat().st_size / (1024**2):.1f} MB)")

        # Configure pipeline
        output_dir = tmpdir / "output"
        config = V7StreamConfig(
            chunk_size=8000,
            output_dir=output_dir,
            enable_compression=False,  # Faster for testing
        )

        # Measure initial memory
        initial_memory = get_memory_mb()
        print(f"\nInitial memory: {initial_memory:.1f} MB")

        # Create and run pipeline
        pipeline = V7StreamingPipeline(config)

        print("\nProcessing chunks...")
        chunk_num = 0
        memory_samples = []

        for chunk in pipeline.read_chunks(input_file):
            chunk_start = time.time()

            # Process chunk
            results = pipeline.process_chunk(chunk)
            pipeline.write_chunk_results(results, chunk_num)

            # Sample memory
            current_memory = get_memory_mb()
            memory_growth = current_memory - initial_memory
            memory_samples.append(memory_growth)

            chunk_time = time.time() - chunk_start
            print(
                f"  Chunk {chunk_num}: {len(results)}/{len(chunk)} processed "
                f"in {chunk_time:.1f}s, Memory +{memory_growth:.1f} MB"
            )

            # Cleanup
            pipeline.cleanup_memory()

            chunk_num += 1

        # Final stats
        print(f"\nPASS Processed {chunk_num} chunks")
        print(f"   Max memory growth: {max(memory_samples):.1f} MB")
        print(f"   Avg memory growth: {sum(memory_samples)/len(memory_samples):.1f} MB")

        # Verify constant memory
        if max(memory_samples) - min(memory_samples) < 50:
            print("   PASS Memory usage is constant!")
        else:
            print("   FAIL Memory usage varies significantly")


if __name__ == "__main__":
    test_simple_streaming()
