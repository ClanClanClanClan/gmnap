#!/usr/bin/env python3
"""
Quick test of V7 pipeline fixes.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.pipeline_v7_fixed import V7PipelineSimplified


async def test_fixes():
    """Test the fixed pipeline."""
    print("🔧 Testing V7 Pipeline Fixes")
    print("=" * 40)

    # Create pipeline
    pipeline = V7PipelineSimplified()

    # Test 1: None handling
    print("\n1️⃣ Testing None handling...")
    test_entries = [
        {"CanonicalLatin": None, "CanonicalNative": "김민준"},
        {"CanonicalLatin": "John Smith", "CanonicalNative": None},
        {"CanonicalLatin": "", "CanonicalNative": ""},
    ]

    try:
        result = await pipeline.process(test_entries)
        print(f"   ✅ Processed {len(result)} entries without NoneType errors")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Tab/newline normalization
    print("\n2️⃣ Testing tab/newline normalization...")
    test_entries = [
        {"CanonicalLatin": "Test\tName"},
        {"CanonicalLatin": "Test\nName"},
        {"CanonicalLatin": "Normal Name"},
    ]

    try:
        result = await pipeline.process(test_entries)
        print(f"   ✅ Processed {len(result)} entries with special characters")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Edge cases
    print("\n3️⃣ Testing edge cases...")
    test_entries = [
        {"CanonicalLatin": "X"},  # Single char
        {"CanonicalLatin": "A" * 200},  # Long name
        {"CanonicalLatin": "José María de la Cruz-Sánchez"},  # Complex
    ]

    try:
        result = await pipeline.process(test_entries)
        print(f"   ✅ Processed {len(result)} edge cases")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Performance
    print("\n4️⃣ Testing performance...")
    import time

    test_entries = [{"CanonicalLatin": f"Test Person {i}"} for i in range(100)]

    start = time.time()
    try:
        result = await pipeline.process(test_entries)
        elapsed = time.time() - start
        rate = len(test_entries) / elapsed if elapsed > 0 else 0
        print(f"   ✅ Processed {len(result)} entries at {rate:.1f} entries/sec")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 40)
    print("✅ V7 Pipeline Fixes Test Complete")


if __name__ == "__main__":
    asyncio.run(test_fixes())
