#!/usr/bin/env python3
"""
ULTRAFIX Phase 4: Test memory leak with CACHE DISABLED
This isolates whether the LRU cache is causing memory accumulation
"""

import gc
import random
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


print("🔥 ULTRAFIX PHASE 4: TESTING WITHOUT CACHE")
print("=" * 60)

# Disable FastText loading entirely
import src.regions.manager_optimized as manager_module


# Monkey patch get_fasttext_model to return None
def get_fasttext_model_disabled(config_dir=None):
    """Disabled FastText model loading for leak testing"""
    return None


manager_module.get_fasttext_model = get_fasttext_model_disabled

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

# Disable caching, security validation, and FastText
original_detect_region = RegionManager.detect_region


def detect_region_no_cache_no_security_no_fasttext(self, entry, internal=False):
    """Bypass caching, security validation AND FastText to isolate leak source"""
    # Basic input validation only
    if entry is None or not isinstance(entry, dict):
        from src.regions.manager_optimized import RegionDetectionResult

        return RegionDetectionResult(
            region_code="Z0",
            confidence=0.0,
            detection_method="invalid-input",
            metadata={
                "error": "Invalid input",
                "no_cache": True,
                "no_security": True,
                "no_fasttext": True,
            },
        )

    name = entry.get("name")
    if not name:
        from src.regions.manager_optimized import RegionDetectionResult

        return RegionDetectionResult(
            region_code="Z0",
            confidence=0.0,
            detection_method="missing-name",
            metadata={
                "error": "Missing name",
                "no_cache": True,
                "no_security": True,
                "no_fasttext": True,
            },
        )

    # Convert to string if needed
    if not isinstance(name, str):
        name = str(name)
        entry["name"] = name

    # Ensure regions are loaded
    self._ensure_regions_loaded()

    # NO CACHING - directly call detection
    result = self._detect_region_uncached(entry)

    # Count cache misses for stats
    self._cache_misses += 1

    return result


# Apply the patch
RegionManager.detect_region = detect_region_no_cache_no_security_no_fasttext

print("🚫 Caching DISABLED")
print("🚫 Security validation DISABLED")
print("🚫 FastText language detection DISABLED")

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

print(
    "Testing memory usage every 10K operations (NO CACHE, NO SECURITY, NO FASTTEXT)..."
)
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

            # Cache should be empty
            cache_stats = manager.get_cache_stats()
            print(
                f"    Cache: {cache_stats['cache_size']}/{cache_stats['cache_max_size']} entries (should be 0)"
            )

    except Exception as e:
        print(f"Error at operation {i+1}: {e}")
        break

print("\n📊 MEMORY ANALYSIS (NO CACHE, NO SECURITY, NO FASTTEXT):")
if memory_points:
    print(f"   Total operations: {len(test_names):,}")
    print(f"   Final memory: {memory_points[-1]['memory_mb']:.1f} MB")
    print(f"   Total growth: {memory_points[-1]['growth_mb']:.1f} MB")
    print(f"   Final leak rate: {memory_points[-1]['leak_rate']:.3f} MB/1K ops")

    # Compare to all previous results
    original_leak = 0.118  # With security
    no_security_leak = 0.090  # Without security
    no_security_no_fasttext = 0.098  # Without security and FastText
    current_leak = memory_points[-1]["leak_rate"]

    print("\n🔍 CACHE OVERHEAD ANALYSIS:")
    print(f"   Original leak (full system): {original_leak:.3f} MB/1K ops")
    print(f"   No security: {no_security_leak:.3f} MB/1K ops")
    print(f"   No security + no FastText: {no_security_no_fasttext:.3f} MB/1K ops")
    print(f"   No cache + no security + no FastText: {current_leak:.3f} MB/1K ops")

    cache_overhead = no_security_no_fasttext - current_leak
    print(
        f"   Cache overhead: {cache_overhead:.3f} MB/1K ops ({cache_overhead/original_leak*100:.1f}%)"
    )

    # Verdict
    if current_leak < 0.01:
        print("\nPASS LEAK ELIMINATED: Cache was the remaining leak source!")
        print(f"   Core processing leak: {current_leak:.3f} MB/1K ops (negligible)")
    elif current_leak < no_security_no_fasttext * 0.5:
        print("\n🟡 LEAK SIGNIFICANTLY REDUCED: Cache was major contributor")
        print(f"   But core processing still has leak: {current_leak:.3f} MB/1K ops")
    else:
        print("\n🔴 LEAK PERSISTS: Cache not the main source")
        print(
            "   Need to investigate RegionDetectionResult object retention or other components"
        )
        print(f"   Remaining leak in core processing: {current_leak:.3f} MB/1K ops")

    # Memory leak breakdown
    print("\n📈 MEMORY LEAK BREAKDOWN:")
    print(
        f"   Security validation: {(original_leak - no_security_leak):.3f} MB/1K ops ({(original_leak - no_security_leak)/original_leak*100:.1f}%)"
    )
    print(
        f"   FastText model: {(no_security_leak - no_security_no_fasttext):.3f} MB/1K ops ({(no_security_leak - no_security_no_fasttext)/original_leak*100:.1f}%)"
    )
    print(
        f"   Cache mechanism: {cache_overhead:.3f} MB/1K ops ({cache_overhead/original_leak*100:.1f}%)"
    )
    print(
        f"   Core processing: {current_leak:.3f} MB/1K ops ({current_leak/original_leak*100:.1f}%)"
    )

    # Final cache analysis (should be 0)
    final_cache = manager.get_cache_stats()
    print("\n📈 FINAL CACHE STATE:")
    print(f"   Cache size: {final_cache['cache_size']:,} (should be 0)")
    print(f"   Cache misses: {final_cache['cache_misses']:,}")
else:
    print("🔴 TEST FAILED: No memory measurements taken")
