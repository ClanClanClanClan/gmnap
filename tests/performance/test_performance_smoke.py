import pytest

#!/usr/bin/env python3
"""
Performance smoke test - basic performance checks
"""

import sys
from pathlib import Path
import time
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set test mode
os.environ["GMNAP_TEST_MODE"] = "true"
os.environ["GMNAP_OFFLINE"] = "1"


@pytest.mark.timeout(15)
def test_basic_performance():
    """Basic performance smoke test"""
    start = time.time()

    # Simple computation to verify test runs
    result = sum(range(1000000))

    elapsed = time.time() - start

    assert elapsed < 1.0, f"Basic computation took too long: {elapsed:.2f}s"
    assert result == 499999500000
    print(f"PASS Basic performance test passed in {elapsed:.3f}s")


@pytest.mark.timeout(15)
def test_import_performance():
    """Test that imports don't take too long"""
    start = time.time()

    # Try importing a core module
    from src.regions.base import RegionSpec

    elapsed = time.time() - start

    assert elapsed < 2.0, f"Import took too long: {elapsed:.2f}s"
    assert RegionSpec is not None
    print(f"PASS Import performance test passed in {elapsed:.3f}s")


@pytest.mark.timeout(15)
def test_memory_allocation():
    """Test basic memory allocation performance"""
    start = time.time()

    # Allocate a moderately sized list
    data = [i for i in range(100000)]

    elapsed = time.time() - start

    assert elapsed < 0.5, f"Memory allocation took too long: {elapsed:.2f}s"
    assert len(data) == 100000
    print(f"PASS Memory allocation test passed in {elapsed:.3f}s")


if __name__ == "__main__":
    print("=" * 60)
    print("PERFORMANCE SMOKE TEST")
    print("=" * 60)

    test_basic_performance()
    test_import_performance()
    test_memory_allocation()

    print("=" * 60)
    print("PASS ALL PERFORMANCE SMOKE TESTS PASSED")
    print("=" * 60)
