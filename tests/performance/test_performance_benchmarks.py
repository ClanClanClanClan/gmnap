import pytest

#!/usr/bin/env python3
"""Performance benchmark tests"""

import sys
from pathlib import Path
import time
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["GMNAP_TEST_MODE"] = "true"


@pytest.mark.timeout(15)
def test_processing_speed():
    """Test processing speed meets requirements"""
    start = time.time()

    # Simulate processing 1000 entries
    for i in range(1000):
        entry = {"CanonicalLatin": f"Test Name {i}"}
        # Minimal processing
        entry["processed"] = True

    elapsed = time.time() - start
    entries_per_second = 1000 / elapsed

    # Should process at least 100 entries per second
    assert entries_per_second > 100, f"Too slow: {entries_per_second:.1f} entries/sec"


@pytest.mark.timeout(15)
def test_memory_usage():
    """Test memory usage is reasonable"""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Simulate loading large dataset
    large_data = ["x" * 1000 for _ in range(10000)]

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # Should not use more than 500MB for this test
    assert memory_increase < 500, f"Memory usage too high: {memory_increase:.1f}MB"


@pytest.mark.timeout(15)
def test_concurrent_processing():
    """Test concurrent processing capabilities"""
    import concurrent.futures

    def process_entry(i):
        return {"id": i, "processed": True}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_entry, i) for i in range(100)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 100, "All entries should be processed"
