#!/usr/bin/env python3
"""
ULTRAFIX Phase 4: Test memory leak with FastText DISABLED
This isolates whether FastText language detection is causing memory accumulation
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


print("🔥 ULTRAFIX PHASE 4: TESTING WITHOUT FASTTEXT")
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

# Also disable security validation like before
original_detect_region = RegionManager.detect_region


def detect_region_no_security_no_fasttext(self, entry, internal=False):
    """Bypass security validation AND FastText to isolate leak source"""
    # Basic input validation only
    if entry is None or not isinstance(entry, dict):
        from src.regions.manager_optimized import RegionDetectionResult

        return RegionDetectionResult(
            region_code="Z0",
            confidence=0.0,
            detection_method="invalid-input",
            metadata={
                "error": "Invalid input",
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

    # Create cache key
    cache_key = entry.get("name", "")

    # Check cache
    if cache_key in self._detection_cache:
        self._cache_hits += 1
        self._detection_cache.move_to_end(cache_key)
        return self._detection_cache[cache_key]

    self._cache_misses += 1

    # Detect region - NO SECURITY, NO FASTTEXT
    result = self._detect_region_uncached(entry)

    # Cache result
    if cache_key and len(self._detection_cache) >= self._detection_cache_size:
        self._detection_cache.popitem(last=False)  # Remove oldest
    if cache_key:
        self._detection_cache[cache_key] = result

    return result


# Apply the patch
RegionManager.detect_region = detect_region_no_security_no_fasttext

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

print("Testing memory usage every 10K operations (NO SECURITY, NO FASTTEXT)...")
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

print("\n📊 MEMORY ANALYSIS (NO SECURITY, NO FASTTEXT):")
if memory_points:
    print(f"   Total operations: {len(test_names):,}")
    print(f"   Final memory: {memory_points[-1]['memory_mb']:.1f} MB")
    print(f"   Total growth: {memory_points[-1]['growth_mb']:.1f} MB")
    print(f"   Final leak rate: {memory_points[-1]['leak_rate']:.3f} MB/1K ops")

    # Compare to previous results
    original_leak = 0.118  # With security
    no_security_leak = 0.090  # Without security
    current_leak = memory_points[-1]["leak_rate"]

    print("\n🔍 FASTTEXT OVERHEAD ANALYSIS:")
    print(f"   Original leak (with security): {original_leak:.3f} MB/1K ops")
    print(f"   No security leak: {no_security_leak:.3f} MB/1K ops")
    print(f"   No security + no FastText: {current_leak:.3f} MB/1K ops")
    print(
        f"   Security overhead: {(original_leak - no_security_leak):.3f} MB/1K ops ({(original_leak - no_security_leak)/original_leak*100:.1f}%)"
    )
    print(
        f"   FastText overhead: {(no_security_leak - current_leak):.3f} MB/1K ops ({(no_security_leak - current_leak)/original_leak*100:.1f}%)"
    )

    # Verdict
    if current_leak < 0.01:
        print("\nPASS LEAK ELIMINATED: FastText was the remaining leak source!")
        print(f"   Core detection leak: {current_leak:.3f} MB/1K ops (negligible)")
    elif current_leak < no_security_leak * 0.5:
        print("\n🟡 LEAK SIGNIFICANTLY REDUCED: FastText was major contributor")
        print(f"   But core detection still has leak: {current_leak:.3f} MB/1K ops")
    else:
        print("\n🔴 LEAK PERSISTS: FastText not the main source")
        print(
            "   Need to investigate caching, RegionDetectionResult retention, or other components"
        )

    # Final cache analysis
    final_cache = manager.get_cache_stats()
    print("\n📈 FINAL CACHE STATE:")
    print(
        f"   Cache size: {final_cache['cache_size']:,}/{final_cache['cache_max_size']:,}"
    )
    print(f"   Cache hits: {final_cache['cache_hits']:,}")
    print(f"   Cache misses: {final_cache['cache_misses']:,}")
    print(f"   Hit rate: {final_cache['hit_rate']:.1%}")
else:
    print("🔴 TEST FAILED: No memory measurements taken")
