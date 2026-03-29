import pytest

#!/usr/bin/env python3
"""
ULTRAFIX Phase 4: Test memory leak with MINIMAL processing
This creates RegionDetectionResult objects without any region logic to isolate object retention
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


print("🔥 ULTRAFIX PHASE 4: TESTING MINIMAL OBJECT CREATION")
print("=" * 60)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionDetectionResult


def minimal_detect_region(entry):
    """Create RegionDetectionResult without any processing"""
    name = entry.get("name", "")

    # Just create a simple result object and return it immediately
    result = RegionDetectionResult(
        region_code="A1",
        confidence=0.5,
        detection_method="minimal-test",
        metadata={"name": name, "test": True},
    )

    # Don't store it anywhere - let it go out of scope immediately
    return result


print("🚫 All processing DISABLED - testing pure object creation/destruction")

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

print("Testing memory usage every 10K operations (MINIMAL OBJECT CREATION)...")
for i, name in enumerate(test_names):
    try:
        # Create and immediately discard result
        result = minimal_detect_region({"name": name})
        # Let result go out of scope (should be garbage collected)

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

print(f"\n📊 MEMORY ANALYSIS (MINIMAL OBJECT CREATION):")
if memory_points:
    print(f"   Total operations: {len(test_names):,}")
    print(f"   Final memory: {memory_points[-1]['memory_mb']:.1f} MB")
    print(f"   Total growth: {memory_points[-1]['growth_mb']:.1f} MB")
    print(f"   Final leak rate: {memory_points[-1]['leak_rate']:.3f} MB/1K ops")

    # Compare to core processing
    core_processing_leak = 0.094  # From previous test
    current_leak = memory_points[-1]["leak_rate"]

    print(f"\n🔍 OBJECT CREATION ANALYSIS:")
    print(f"   Core processing leak: {core_processing_leak:.3f} MB/1K ops")
    print(f"   Minimal object creation: {current_leak:.3f} MB/1K ops")
    print(
        f"   Complex processing overhead: {(core_processing_leak - current_leak):.3f} MB/1K ops"
    )

    # Verdict
    if current_leak < 0.01:
        print(
            f"\nPASS NO OBJECT LEAK: RegionDetectionResult objects are properly collected"
        )
        print(f"   The leak must be in complex region processing logic")
    elif current_leak >= core_processing_leak * 0.8:
        print(
            f"\n🔴 OBJECT RETENTION ISSUE: RegionDetectionResult objects not being collected"
        )
        print(
            f"   This suggests a reference retention problem in the dataclass or metadata"
        )
    else:
        print(f"\n🟡 PARTIAL OBJECT LEAK: Some object retention + processing overhead")

    # Final analysis
    print(f"\n📈 LEAK SOURCE ANALYSIS:")
    if current_leak < 0.01:
        print(
            f"   -> The leak is in region processing logic (script analysis, pattern matching, etc.)"
        )
        print(
            f"   -> Check _analyze_scripts, _enhance_detection_with_patterns, or region loading"
        )
    elif current_leak >= 0.05:
        print(f"   -> The leak is in RegionDetectionResult object retention")
        print(f"   -> Check for circular references or metadata dictionary growth")
    else:
        print(
            f"   -> Mixed: Both object retention and processing logic contributing to leak"
        )
else:
    print("🔴 TEST FAILED: No memory measurements taken")
