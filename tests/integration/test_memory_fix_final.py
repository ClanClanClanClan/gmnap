#!/usr/bin/env python3
"""
Test final memory fix for ULTRAFIX Phase 6
"""

import gc
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import os

import psutil


def get_memory_mb():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


print("💾 TESTING FINAL MEMORY FIX")
print("=" * 60)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.regions.manager_optimized import RegionManager

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.rate_limiter import global_rate_limiter

manager = RegionManager()
start_memory = get_memory_mb()
print(f"Initial memory: {start_memory:.1f} MB")

# Test with 50K operations (same as brutal test)
test_names = [f"Test User {i}" for i in range(50000)]

memory_points = []

for i, name in enumerate(test_names):
    try:
        result = manager.detect_region({"name": name})

        # Check memory every 10K operations
        if (i + 1) % 10000 == 0:
            # Force cleanup
            global_rate_limiter.force_cleanup()
            gc.collect()

            current_memory = get_memory_mb()
            memory_growth = current_memory - start_memory
            leak_rate = memory_growth / ((i + 1) / 1000)  # MB per 1K ops

            print(
                f"  {i+1:,} ops: {current_memory:.1f} MB (+{memory_growth:.1f} MB, {leak_rate:.3f} MB/1K ops)"
            )

            memory_points.append(
                {
                    "ops": i + 1,
                    "memory_mb": current_memory,
                    "growth_mb": memory_growth,
                    "leak_rate": leak_rate,
                }
            )
    except Exception as e:
        print(f"Error at operation {i+1}: {e}")
        break

if memory_points:
    final_leak_rate = memory_points[-1]["leak_rate"]
    print("\n📊 MEMORY TEST RESULTS:")
    print(f"   Final memory growth: {memory_points[-1]['growth_mb']:.1f} MB")
    print(f"   Final leak rate: {final_leak_rate:.3f} MB/1K ops")

    if final_leak_rate < 0.10:
        print("   PASS PASS: Memory leak below 0.1 MB/1K threshold")
    else:
        print(
            f"   FAIL FAIL: Memory leak {final_leak_rate:.3f} exceeds 0.1 MB/1K threshold"
        )
