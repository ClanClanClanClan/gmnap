import pytest

#!/usr/bin/env python3
"""
ULTRAFIX Phase 4: Test memory leak with ULTRA MINIMAL processing
Test if the leak is from Python's internal string/object management
"""

import gc
import sys
import random

import psutil
import os


def get_memory_mb():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


print("🔥 ULTRAFIX PHASE 4: ULTRA MINIMAL TEST (NO OBJECTS)")
print("=" * 60)


def ultra_minimal_process(entry):
    """Process entry with absolutely minimal operations"""
    name = entry.get("name", "")

    # Just return a simple string - no objects at all
    if "john" in name.lower():
        return "A1_john"
    elif "ahmed" in name.lower():
        return "C3_ahmed"
    elif "li" in name.lower():
        return "E1_li"
    else:
        return "A1_default"


print("🚫 NO OBJECTS - testing pure string processing")

initial_memory = get_memory_mb()
print(f"Initial memory: {initial_memory:.1f} MB")

# Generate test names
name_templates = [
    ("John {surname}", ["Smith", "Johnson", "Williams", "Brown", "Jones"]),
    ("Marie {surname}", ["Dupont", "Martin", "Bernard", "Petit", "Robert"]),
    ("{name} Petrov", ["Ivan", "Vladimir", "Sergei", "Dmitri", "Pavel"]),
    ("Ahmed {surname}", ["Hassan", "Ali", "Mohammad", "Ibrahim", "Omar"]),
    ("{name} Singh", ["Raj", "Amit", "Suresh", "Vikram", "Ravi"]),
    ("李{name}", ["明", "华", "伟", "强", "军"]),
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

print("Testing memory usage every 10K operations (ULTRA MINIMAL)...")
for i, name in enumerate(test_names):
    try:
        # Process with absolutely minimal operations
        result = ultra_minimal_process({"name": name})
        # Don't even store the result

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

    except Exception as e:
        print(f"Error at operation {i+1}: {e}")
        break

print(f"\n📊 MEMORY ANALYSIS (ULTRA MINIMAL - NO OBJECTS):")
if memory_points:
    print(f"   Total operations: {len(test_names):,}")
    print(f"   Final memory: {memory_points[-1]['memory_mb']:.1f} MB")
    print(f"   Total growth: {memory_points[-1]['growth_mb']:.1f} MB")
    print(f"   Final leak rate: {memory_points[-1]['leak_rate']:.3f} MB/1K ops")

    # Compare to object creation
    object_creation_leak = 0.062  # From original test
    current_leak = memory_points[-1]["leak_rate"]

    print(f"\n🔍 PYTHON BASELINE ANALYSIS:")
    print(f"   Object creation leak: {object_creation_leak:.3f} MB/1K ops")
    print(f"   Ultra minimal processing: {current_leak:.3f} MB/1K ops")
    print(f"   Object overhead: {(object_creation_leak - current_leak):.3f} MB/1K ops")

    # Verdict
    if current_leak < 0.01:
        print(f"\nPASS BASELINE CONFIRMED: No leak in minimal processing")
        print(f"   The leak is definitely in the object creation/retention")
    elif current_leak >= object_creation_leak * 0.8:
        print(f"\n🔴 PYTHON BASELINE LEAK: Memory growth even with minimal processing")
        print(f"   This suggests Python internal memory management or test artifacts")
    else:
        print(f"\n🟡 MIXED BASELINE: Some Python overhead + object retention issues")

    # Analysis
    if current_leak < 0.01:
        print(f"\n📈 CONFIRMED LEAK SOURCE:")
        print(f"   -> RegionDetectionResult dataclass or its metadata dictionary")
        print(
            f"   -> Need to investigate dataclass field retention or circular references"
        )
        print(f"   -> Potential fix: Use slots, or avoid default_factory=dict")
    elif current_leak < 0.02:
        print(f"\n📈 LIKELY LEAK SOURCES:")
        print(f"   -> Python string interning or dictionary growth")
        print(f"   -> RegionDetectionResult object retention")
        print(f"   -> Need memory profiling with tracemalloc")
    else:
        print(f"\n📈 INVESTIGATION NEEDED:")
        print(f"   -> Memory leak may be in test setup or Python runtime")
        print(f"   -> Need proper memory profiling to identify source")
else:
    print("🔴 TEST FAILED: No memory measurements taken")
