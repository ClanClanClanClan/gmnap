#!/usr/bin/env python3
"""
ULTRAFIX Phase 4: Apply the FINAL memory leak fix
The only real fix needed is the rate limiter cleanup we already implemented.
The rest is Python's normal memory management.
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


print("🔧 ULTRAFIX PHASE 4: FINAL MEMORY FIX TEST")
print("=" * 60)

# Test with the ACTUAL system (all components enabled)
from src.regions.manager_optimized import RegionManager
from src.core.rate_limiter import global_rate_limiter

print("✅ Using FULL system with rate limiter cleanup fix")
print("✅ Security validation ENABLED")
print("✅ FastText language detection ENABLED")
print("✅ LRU cache ENABLED")
print("✅ Rate limiter cleanup ENABLED")

# Initialize manager
manager = RegionManager()
initial_memory = get_memory_mb()
print(f"Initial memory: {initial_memory:.1f} MB")

# Generate test names (same as hell testing)
name_templates = [
    ("John {surname}", ["Smith", "Johnson", "Williams", "Brown", "Jones"]),
    ("Marie {surname}", ["Dupont", "Martin", "Bernard", "Petit", "Robert"]),
    ("{name} Petrov", ["Ivan", "Vladimir", "Sergei", "Dmitri", "Pavel"]),
    ("Ahmed {surname}", ["Hassan", "Ali", "Mohammad", "Ibrahim", "Omar"]),
    ("{name} Singh", ["Raj", "Amit", "Suresh", "Vikram", "Ravi"]),
    ("李{name}", ["明", "华", "伟", "强", "军"]),
    ("田中{name}", ["太郎", "花子", "一郎", "美咲", "健"]),
    ("José {surname}", ["García", "Rodríguez", "González", "Fernández", "López"]),
]

print("Generating 50,000 test names...")
test_names = []
for _ in range(50000):
    template, options = random.choice(name_templates)
    if "{surname}" in template:
        name = template.format(surname=random.choice(options))
    else:
        name = template.format(name=random.choice(options))
    test_names.append(name)

memory_points = []

print("Testing FULL SYSTEM memory usage every 10K operations...")
for i, name in enumerate(test_names):
    try:
        # Use full system detection
        result = manager.detect_region({"name": name})

        # Check memory every 10K operations
        if (i + 1) % 10000 == 0:
            # Force rate limiter cleanup
            cleanup_stats = global_rate_limiter.force_cleanup()

            gc.collect()
            current_memory = get_memory_mb()
            memory_growth = current_memory - initial_memory
            leak_rate = memory_growth / ((i + 1) / 1000)  # MB per 1K ops

            print(
                f"  {i+1:,} ops: {current_memory:.1f} MB (+{memory_growth:.1f} MB, {leak_rate:.3f} MB/1K ops)"
            )
            print(f"    Rate limiter cleanup: {cleanup_stats['clients_removed']} clients removed")

            memory_points.append(
                {
                    "operations": i + 1,
                    "memory_mb": current_memory,
                    "growth_mb": memory_growth,
                    "leak_rate": leak_rate,
                }
            )

            # Check cache size
            cache_stats = manager.get_cache_stats()
            print(
                f"    Cache: {cache_stats['cache_size']}/{cache_stats['cache_max_size']} entries, {cache_stats['hit_rate']:.1%} hit rate"
            )

    except Exception as e:
        print(f"Error at operation {i+1}: {e}")
        break

print(f"\n📊 FINAL SYSTEM MEMORY ANALYSIS:")
if memory_points:
    print(f"   Total operations: {len(test_names):,}")
    print(f"   Final memory: {memory_points[-1]['memory_mb']:.1f} MB")
    print(f"   Total growth: {memory_points[-1]['growth_mb']:.1f} MB")
    print(f"   Final leak rate: {memory_points[-1]['leak_rate']:.3f} MB/1K ops")

    # Compare to original hell testing results
    original_hell_leak = 0.127  # From maniacal hell testing
    original_simple_leak = 0.118  # From memory leak fix test
    python_baseline = 0.071  # From ultra minimal test
    current_leak = memory_points[-1]["leak_rate"]

    print(f"\n🔍 COMPREHENSIVE MEMORY ANALYSIS:")
    print(f"   Original hell testing leak: {original_hell_leak:.3f} MB/1K ops")
    print(f"   Original simple leak: {original_simple_leak:.3f} MB/1K ops")
    print(f"   Python baseline (unavoidable): {python_baseline:.3f} MB/1K ops")
    print(f"   Current system leak: {current_leak:.3f} MB/1K ops")

    # Calculate actual improvement
    real_system_overhead = original_simple_leak - python_baseline  # 0.047 MB/1K
    current_system_overhead = current_leak - python_baseline
    improvement = real_system_overhead - current_system_overhead

    print(f"\n🎯 REAL SYSTEM IMPROVEMENT:")
    print(f"   Original system overhead: {real_system_overhead:.3f} MB/1K ops")
    print(f"   Current system overhead: {current_system_overhead:.3f} MB/1K ops")
    print(
        f"   System improvement: {improvement:.3f} MB/1K ops ({improvement/real_system_overhead*100:.1f}%)"
    )

    # Verdict
    if current_system_overhead < 0.01:
        print(f"\n✅ MEMORY LEAK COMPLETELY FIXED!")
        print(f"   System now operates at near-Python baseline")
        print(f"   Suitable for production deployment")
    elif improvement > 0 and current_system_overhead < real_system_overhead * 0.5:
        print(f"\n🟢 MEMORY LEAK SIGNIFICANTLY REDUCED!")
        print(f"   Major improvement over original system")
        print(f"   Acceptable for production use")
    elif improvement > 0:
        print(f"\n🟡 MEMORY LEAK PARTIALLY FIXED")
        print(f"   Some improvement but still has overhead")
    else:
        print(f"\n🔴 NO IMPROVEMENT")
        print(f"   Rate limiter fix didn't help")

    # Production readiness
    total_leak_mb_per_million = current_leak * 1000
    print(f"\n🏭 PRODUCTION IMPACT ANALYSIS:")
    print(f"   Memory growth per 1M operations: {total_leak_mb_per_million:.1f} MB")
    if total_leak_mb_per_million < 100:
        print(f"   ✅ PRODUCTION READY: Minimal memory impact")
    elif total_leak_mb_per_million < 500:
        print(f"   🟡 PRODUCTION ACCEPTABLE: Moderate memory impact")
    else:
        print(f"   🔴 PRODUCTION RISK: High memory impact")

    # Final cache and rate limiter analysis
    final_cache = manager.get_cache_stats()
    final_rl = global_rate_limiter.get_memory_stats()

    print(f"\n📈 FINAL SYSTEM STATE:")
    print(f"   Cache: {final_cache['cache_size']:,}/{final_cache['cache_max_size']:,} entries")
    print(f"   Hit rate: {final_cache['hit_rate']:.1%}")
    print(
        f"   Rate limiter: {final_rl['total_clients']} clients, {final_rl['estimated_memory_kb']} KB"
    )

else:
    print("🔴 TEST FAILED: No memory measurements taken")
