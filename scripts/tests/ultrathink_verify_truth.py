#!/usr/bin/env python3
"""
ULTRATHINK Truth Verification Script
Demonstrates the actual state vs claimed state
"""

import asyncio
import sys
import time
from pathlib import Path


def print_section(title):
    print(f"\n{'='*60}")
    print(f"📊 {title}")
    print("=" * 60)


async def verify_pipeline_integration():
    """Test if pipeline actually integrates with regions properly"""
    print_section("PIPELINE-REGION INTEGRATION TEST")

    from src.core.pipeline_v7 import V7Pipeline, PipelineMode

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    test_cases = [
        ("Korean", "김민수", "Kim Min-su"),
        ("Chinese", "李明", "Li Ming"),
        ("Russian", "Иванов Иван", "Ivanov Ivan"),
        ("Japanese", "山田太郎", "Yamada Taro"),
        ("Arabic", "محمد علي", "Muhammad Ali"),
    ]

    test_data = [
        {"CanonicalNative": name, "GlobalID": f"{lang}-TEST"} for lang, name, _ in test_cases
    ]

    print("Testing 5 regional names through pipeline...")
    result = await pipeline.process_batch(test_data)

    success_count = 0
    for i, (lang, native, expected) in enumerate(test_cases):
        entry = result["entries"][i]
        latin = entry.get("CanonicalLatin", "NO LATIN!")
        is_correct = latin != "NO LATIN!" and len(latin) > 0

        status = "✅" if is_correct else "❌"
        print(f"  {status} {lang}: {native} → {latin}")
        if latin != expected and latin != "NO LATIN!":
            print(f"     Expected: {expected}")

        if is_correct:
            success_count += 1

    rate = success_count / len(test_cases) * 100
    print(f"\nSuccess rate: {success_count}/{len(test_cases)} = {rate:.0f}%")
    return rate


def verify_regional_processors():
    """Test if regional processors work directly"""
    print_section("REGIONAL PROCESSORS DIRECT TEST")

    from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor
    from src.regions.e_groups.e1_sinophone_mainland import E1_SinophoneMainland
    from src.regions.b_groups.b1_east_slavic import B1_EastSlavic
    from src.regions.e_groups.e3_japan.processor import E3_Japan
    from src.regions.c_groups.c3_arabic_levant_nile import C3_ArabicLevantNile

    test_cases = [
        ("Korean", E4KoreanProcessor(), "김민수", "Kim Min-su"),
        ("Chinese", E1_SinophoneMainland(), "李明", "Li Ming"),
        ("Russian", B1_EastSlavic(), "Иванов Иван", "Ivanov Ivan"),
        ("Japanese", E3_Japan(), "山田太郎", "Yamada Taro"),
        ("Arabic", C3_ArabicLevantNile(), "محمد علي", "Mhmd Ly"),
    ]

    print("Testing same names directly with processors...")
    success_count = 0

    for lang, processor, native, expected in test_cases:
        try:
            result = processor.process({"CanonicalNative": native, "GlobalID": "TEST"})
            latin = result.get("CanonicalLatin", "NO LATIN!")
            is_correct = latin != "NO LATIN!"

            status = "✅" if is_correct else "❌"
            print(f"  {status} {lang}: {native} → {latin}")

            if is_correct:
                success_count += 1
        except Exception as e:
            print(f"  ❌ {lang}: ERROR - {e}")

    rate = success_count / len(test_cases) * 100
    print(f"\nSuccess rate: {success_count}/{len(test_cases)} = {rate:.0f}%")
    return rate


async def verify_performance():
    """Test actual performance vs claims"""
    print_section("PERFORMANCE TEST")

    from src.core.pipeline_v7 import V7Pipeline, PipelineMode

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    # Test with 100 entries
    test_data = [
        {"CanonicalNative": f"Test Name {i}", "GlobalID": f"PERF-{i:04d}"} for i in range(100)
    ]

    print("Processing 100 entries...")
    start = time.time()
    result = await pipeline.process_batch(test_data)
    duration = time.time() - start

    entries_per_sec = 100 / duration
    projected_1m_time = 1_000_000 / entries_per_sec / 60  # minutes

    print(f"  Processed: 100 entries")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Speed: {entries_per_sec:.0f} entries/sec")
    print(f"  Projected 1M time: {projected_1m_time:.0f} minutes")

    target = 35  # minutes
    if projected_1m_time <= target:
        print(f"  ✅ PASS: {projected_1m_time:.0f} min <= {target} min target")
        return 100
    else:
        print(f"  ❌ FAIL: {projected_1m_time:.0f} min > {target} min target")
        print(f"  Performance is {projected_1m_time/target:.1f}x slower than required!")
        return 0


def test_suite_health():
    """Quick test of test suite health"""
    print_section("TEST SUITE HEALTH CHECK")

    import subprocess

    test_files = [
        "tests/unit/test_minimal.py",
        "tests/unit/test_pipeline.py",
        "tests/unit/test_regions.py",
        "tests/integration/test_pipeline_integration.py",
    ]

    print("Running sample of 4 tests...")
    results = {"pass": 0, "fail": 0, "timeout": 0}

    for test_file in test_files:
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", test_file, "-v", "--tb=no", "-q"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print(f"  ✅ {Path(test_file).name}: PASS")
                results["pass"] += 1
            else:
                print(f"  ❌ {Path(test_file).name}: FAIL")
                results["fail"] += 1
        except subprocess.TimeoutExpired:
            print(f"  ⏱️ {Path(test_file).name}: TIMEOUT")
            results["timeout"] += 1

    pass_rate = results["pass"] / len(test_files) * 100
    print(f"\nPass rate: {results['pass']}/{len(test_files)} = {pass_rate:.0f}%")
    return pass_rate


async def main():
    print("\n" + "=" * 60)
    print("🔍 ULTRATHINK TRUTH VERIFICATION")
    print("=" * 60)
    print("Verifying actual system state vs claims...")

    scores = {}

    # Test 1: Pipeline integration
    scores["pipeline_integration"] = await verify_pipeline_integration()

    # Test 2: Regional processors
    scores["regional_direct"] = verify_regional_processors()

    # Test 3: Performance
    scores["performance"] = await verify_performance()

    # Test 4: Test suite
    scores["test_suite"] = test_suite_health()

    # Summary
    print_section("FINAL VERDICT")

    print("Component scores:")
    for component, score in scores.items():
        status = "✅" if score >= 80 else "⚠️" if score >= 50 else "❌"
        print(f"  {status} {component}: {score:.0f}%")

    avg_score = sum(scores.values()) / len(scores)
    print(f"\nOverall compliance: {avg_score:.0f}%")

    if avg_score >= 95:
        print("✅ System is ready for production")
    elif avg_score >= 80:
        print("⚠️ System needs minor fixes")
    elif avg_score >= 60:
        print("⚠️ System needs significant work")
    else:
        print("❌ System is NOT ready - major issues found")

    print("\n" + "=" * 60)
    print("Note: The audit script claims 100% but this is the reality!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
