import pytest

#!/usr/bin/env python3
"""
Test ULTRAFIX Phase 4 - Memory leak fix validation
"""

import gc
import sys
import random
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import psutil
import os


def get_memory_mb():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


print("🔧 ULTRAFIX PHASE 4 MEMORY LEAK FIX VALIDATION")
print("=" * 60)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.rate_limiter import global_rate_limiter

# Initialize
manager = RegionManager()
initial_memory = get_memory_mb()
print(f"Initial memory: {initial_memory:.1f} MB")

# Generate test names
name_templates = [
    ("John {surname}", ["Smith", "Johnson", "Williams", "Brown", "Jones"]),
    ("Marie {surname}", ["Dupont", "Martin", "Bernard", "Petit", "Robert"]),
    ("{name} Petrov", ["Ivan", "Vladimir", "Sergei", "Dmitri", "Pavel"]),
    ("Ahmed {surname}", ["Hassan", "Ali", "Mohammad", "Ibrahim", "Omar"]),
    ("{name} Singh", ["Raj", "Amit", "Suresh", "Vikram", "Ravi"]),
]

print("Generating 25,000 test names...")
test_names = []
for _ in range(25000):
    template, options = random.choice(name_templates)
    if "{surname}" in template:
        name = template.format(surname=random.choice(options))
    else:
        name = template.format(name=random.choice(options))
    test_names.append(name)

print("Testing memory fix with periodic cleanup...")
memory_points = []

for i, name in enumerate(test_names):
    try:
        result = manager.detect_region({"name": name})

        # Check memory and cleanup every 5K operations
        if (i + 1) % 5000 == 0:
            # Get rate limiter stats BEFORE cleanup
            memory_stats_before = global_rate_limiter.get_memory_stats()

            # Force rate limiter cleanup
            cleanup_stats = global_rate_limiter.force_cleanup()

            # Get stats AFTER cleanup
            memory_stats_after = global_rate_limiter.get_memory_stats()

            # Force garbage collection
            gc.collect()
            current_memory = get_memory_mb()
            memory_growth = current_memory - initial_memory
            leak_rate = memory_growth / ((i + 1) / 1000)  # MB per 1K ops

            print(
                f"\n  {i+1:,} ops: {current_memory:.1f} MB (+{memory_growth:.1f} MB, {leak_rate:.4f} MB/1K ops)"
            )
            print(f"    Rate limiter cleanup: {cleanup_stats['clients_removed']} clients removed")
            print(f"    Rate limiter memory: {memory_stats_after['estimated_memory_kb']} KB")

            memory_points.append(
                {
                    "operations": i + 1,
                    "memory_mb": current_memory,
                    "growth_mb": memory_growth,
                    "leak_rate": leak_rate,
                    "rate_limiter_memory_kb": memory_stats_after["estimated_memory_kb"],
                }
            )

    except Exception as e:
        print(f"Error at operation {i+1}: {e}")
        break

print(f"\n📊 MEMORY LEAK FIX VALIDATION:")
print(f"   Total operations: {len(test_names):,}")
if memory_points:
    print(f"   Final memory: {memory_points[-1]['memory_mb']:.1f} MB")
    print(f"   Total growth: {memory_points[-1]['growth_mb']:.1f} MB")
    print(f"   Final leak rate: {memory_points[-1]['leak_rate']:.4f} MB/1K ops")

    # Check if leak rate improved
    if len(memory_points) >= 3:
        early_rate = memory_points[1]["leak_rate"]  # After 10K ops
        late_rate = memory_points[-1]["leak_rate"]  # Final rate
        rate_change = late_rate - early_rate

        print(f"\n🔍 LEAK IMPROVEMENT ANALYSIS:")
        print(f"   Early leak rate (10K ops): {early_rate:.4f} MB/1K ops")
        print(f"   Late leak rate (final): {late_rate:.4f} MB/1K ops")
        print(f"   Rate change: {rate_change:.4f} MB/1K ops")

        if abs(rate_change) < 0.001:
            print("   PASS STABLE: Memory usage completely stabilized")
        elif late_rate < 0.01:
            print("   PASS FIXED: Memory leak eliminated (< 0.01 MB/1K ops)")
        elif late_rate < early_rate:
            print("   🟡 IMPROVED: Memory leak reduced but not eliminated")
        else:
            print("   🔴 STILL LEAKING: Memory leak persists")

# Final rate limiter analysis
final_rl_stats = global_rate_limiter.get_memory_stats()
print(f"\n📈 FINAL RATE LIMITER STATE:")
print(f"   Total clients tracked: {final_rl_stats['total_clients']:,}")
print(f"   Total cooldowns: {final_rl_stats['total_cooldowns']:,}")
print(f"   Rate limiter memory: {final_rl_stats['estimated_memory_kb']} KB")

# Memory leak verdict
if memory_points:
    final_leak_rate = memory_points[-1]["leak_rate"]
    if final_leak_rate < 0.01:
        verdict = "PASS MEMORY LEAK ELIMINATED"
        status = "PRODUCTION READY"
    elif final_leak_rate < 0.05:
        verdict = "🟡 MEMORY LEAK REDUCED"
        status = "SIGNIFICANTLY IMPROVED"
    else:
        verdict = "🔴 MEMORY LEAK PERSISTS"
        status = "STILL BROKEN"

    print(f"\n🏁 ULTRAFIX VERDICT: {verdict}")
    print(f"   Status: {status}")
    print(f"   Final leak rate: {final_leak_rate:.4f} MB per 1,000 operations")

    # Compare to original leak (0.106 MB/1K ops)
    original_leak = 0.106
    improvement = ((original_leak - final_leak_rate) / original_leak) * 100
    print(f"   Improvement: {improvement:.1f}% reduction from original leak")
else:
    print("\n🔴 TEST FAILED: No memory measurements taken")
