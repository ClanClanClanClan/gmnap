import pytest

#!/usr/bin/env python3
"""
ULTRAFIX Phase 4: Test memory leak with security validation DISABLED
This isolates the core detection logic to find the real memory leak source
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


print("🔥 ULTRAFIX PHASE 4: TESTING WITHOUT SECURITY VALIDATION")
print("=" * 60)

# Temporary patch to disable security validation
import src.regions.manager_optimized as manager_module
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

# Monkey patch the detect_region method to bypass security validation
original_detect_region = RegionManager.detect_region


def detect_region_no_security(self, entry, internal=False):
    """Bypass security validation to isolate core memory leak"""
    # Skip ALL security validation - direct to core detection

    # Basic input validation only
    if entry is None or not isinstance(entry, dict):
        from src.regions.manager_optimized import RegionDetectionResult

        return RegionDetectionResult(
            region_code="Z0",
            confidence=0.0,
            detection_method="invalid-input",
            metadata={"error": "Invalid input", "no_security": True},
        )

    name = entry.get("name")
    if not name:
        from src.regions.manager_optimized import RegionDetectionResult

        return RegionDetectionResult(
            region_code="Z0",
            confidence=0.0,
            detection_method="missing-name",
            metadata={"error": "Missing name", "no_security": True},
        )

    # Convert to string if needed
    if not isinstance(name, str):
        name = str(name)
        entry["name"] = name

    # Skip numeric check too - just process everything

    # Ensure regions are loaded
    self._ensure_regions_loaded()

    # Create cache key
    cache_key = entry.get("name", "")

    # Check cache
    if cache_key in self._detection_cache:
        self._cache_hits += 1
        self._detection_cache.move_to_end(cache_key)
        return self._detection_cache[cache_key]

    self._cache_misses += 1

    # Detect region - NO SECURITY VALIDATION
    result = self._detect_region_uncached(entry)

    # Cache result
    if cache_key and len(self._detection_cache) >= self._detection_cache_size:
        self._detection_cache.popitem(last=False)  # Remove oldest
    if cache_key:
        self._detection_cache[cache_key] = result

    return result


# Apply the patch
RegionManager.detect_region = detect_region_no_security

print("🚫 Security validation DISABLED - testing core detection only")

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

print("Testing memory usage every 10K operations (NO SECURITY)...")
for i, name in enumerate(test_names):
    try:
        result = manager.detect_region({"name": name})

        # Check memory every 10K operations
        if (i + 1) % 10000 == 0:
            gc.collect()
            current_memory = get_memory_mb()
            memory_growth = current_memory - initial_memory
            leak_rate = memory_growth / ((i + 1) / 1000)  # MB per 1K ops

            print(
                f"  {i+1:,} ops: {current_memory:.1f} MB (+{memory_growth:.1f} MB, {leak_rate:.3f} MB/1K ops)"
            )
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

print(f"\n📊 MEMORY ANALYSIS (NO SECURITY VALIDATION):")
if memory_points:
    print(f"   Total operations: {len(test_names):,}")
    print(f"   Final memory: {memory_points[-1]['memory_mb']:.1f} MB")
    print(f"   Total growth: {memory_points[-1]['growth_mb']:.1f} MB")
    print(f"   Final leak rate: {memory_points[-1]['leak_rate']:.3f} MB/1K ops")

    # Compare to original security-enabled results
    original_leak = 0.118  # From test_memory_leak_fix.py
    current_leak = memory_points[-1]["leak_rate"]
    security_overhead = original_leak - current_leak

    print(f"\n🔍 SECURITY OVERHEAD ANALYSIS:")
    print(f"   Original leak (with security): {original_leak:.3f} MB/1K ops")
    print(f"   Current leak (no security): {current_leak:.3f} MB/1K ops")
    print(
        f"   Security overhead: {security_overhead:.3f} MB/1K ops ({security_overhead/original_leak*100:.1f}%)"
    )

    # Verdict
    if current_leak < 0.01:
        print(f"\nPASS LEAK ISOLATED: Security validation was the primary source!")
        print(f"   Core detection leak: {current_leak:.3f} MB/1K ops (negligible)")
    elif security_overhead > current_leak:
        print(f"\n🟡 LEAK PARTIALLY ISOLATED: Security validation was major contributor")
        print(f"   But core detection still has leak: {current_leak:.3f} MB/1K ops")
    else:
        print(f"\n🔴 LEAK NOT ISOLATED: Core detection is the main source")
        print(f"   Need to investigate FastText model, caching, or RegionDetectionResult retention")

    # Final cache analysis
    final_cache = manager.get_cache_stats()
    print(f"\n📈 FINAL CACHE STATE:")
    print(f"   Cache size: {final_cache['cache_size']:,}/{final_cache['cache_max_size']:,}")
    print(f"   Cache hits: {final_cache['cache_hits']:,}")
    print(f"   Cache misses: {final_cache['cache_misses']:,}")
    print(f"   Hit rate: {final_cache['hit_rate']:.1%}")
else:
    print("🔴 TEST FAILED: No memory measurements taken")
