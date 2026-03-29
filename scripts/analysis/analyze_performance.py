#!/usr/bin/env python3
"""
Performance Analysis for GMNAP V7
Week 4: Finding the real bottlenecks

This script profiles the pipeline to identify where time is being spent.
"""

import time
import cProfile
import pstats
import io
import sys
from pathlib import Path
from datetime import datetime
import psutil
import gc

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def profile_pipeline_stages():
    """Profile each pipeline stage individually."""

    print("🔍 GMNAP V7 PERFORMANCE ANALYSIS")
    print("=" * 60)

    # Import pipeline components
    try:
        from src.core.pipeline_v7 import V7Pipeline
        from src.core.config import get_config
        from src.regions.manager_optimized import RegionManager

        print("✅ Imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return

    # Get memory baseline
    process = psutil.Process()
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

    print(f"\nBaseline memory: {baseline_memory:.1f} MB")

    # Test data
    test_entries = [
        {"name": "John Smith", "year": 2024},
        {"name": "김철수", "year": 2024},
        {"name": "José García", "year": 2024},
        {"name": "李明", "year": 2024},
        {"name": "محمد الأحمد", "year": 2024},
    ]

    # Profile region manager initialization
    print("\n1. PROFILING REGION MANAGER INITIALIZATION:")
    print("-" * 40)

    start = time.time()
    manager = RegionManager()
    init_time = time.time() - start

    current_memory = process.memory_info().rss / 1024 / 1024
    memory_used = current_memory - baseline_memory

    print(f"  Initialization time: {init_time:.3f}s")
    print(f"  Memory after init: {current_memory:.1f} MB (+{memory_used:.1f} MB)")
    print(f"  FastText model loaded: {'Yes' if hasattr(manager, 'model') else 'No'}")

    # Check if singleton pattern is working
    print("\n  Testing singleton pattern:")
    start = time.time()
    manager2 = RegionManager()
    second_init_time = time.time() - start
    print(f"  Second initialization: {second_init_time:.3f}s")
    print(f"  Same instance: {manager is manager2}")

    # Profile region detection
    print("\n2. PROFILING REGION DETECTION:")
    print("-" * 40)

    detection_times = []
    for entry in test_entries:
        start = time.time()
        result = manager.detect_region(entry)  # Pass the full entry dict
        duration = time.time() - start
        detection_times.append(duration)
        print(f"  {entry['name']:20} -> {result.region_code:10} ({duration*1000:.1f}ms)")

    avg_detection = sum(detection_times) / len(detection_times)
    print(f"\n  Average detection time: {avg_detection*1000:.1f}ms")
    print(f"  Projected for 1M entries: {avg_detection * 1_000_000 / 60:.1f} minutes")

    # Show cache statistics
    if hasattr(manager, "get_cache_stats"):
        stats = manager.get_cache_stats()
        print(f"\n  Cache Statistics:")
        print(f"    Hits: {stats['cache_hits']}")
        print(f"    Misses: {stats['cache_misses']}")
        print(f"    Hit Rate: {stats['hit_rate']:.1%}")
        print(f"    Cache Size: {stats['cache_size']}/{stats['cache_max_size']}")

    # Test cache effectiveness
    print("\n  Testing cache with duplicate names:")
    duplicate_test = test_entries * 3  # 15 names, many duplicates
    start = time.time()
    for entry in duplicate_test:
        manager.detect_region(entry)
    cache_time = time.time() - start

    if hasattr(manager, "get_cache_stats"):
        stats = manager.get_cache_stats()
        print(f"    Processed {len(duplicate_test)} entries in {cache_time*1000:.1f}ms")
        print(f"    Final hit rate: {stats['hit_rate']:.1%}")
        print(f"    Average time per entry: {cache_time*1000/len(duplicate_test):.2f}ms")

    # Profile full pipeline
    print("\n3. PROFILING FULL PIPELINE:")
    print("-" * 40)

    try:
        config = get_config()
        pipeline = V7Pipeline(config)

        # Process test batch
        processing_times = []
        for entry in test_entries:
            start = time.time()
            try:
                result = pipeline.process_batch([entry], mode="quick")
                duration = time.time() - start
                processing_times.append(duration)
                print(f"  {entry['name']:20} processed in {duration*1000:.1f}ms")
            except Exception as e:
                print(f"  {entry['name']:20} failed: {e}")

        if processing_times:
            avg_processing = sum(processing_times) / len(processing_times)
            print(f"\n  Average processing time: {avg_processing*1000:.1f}ms per entry")
            print(f"  Projected for 1M entries: {avg_processing * 1_000_000 / 60:.1f} minutes")
    except Exception as e:
        print(f"  Pipeline initialization failed: {e}")

    # Memory analysis
    print("\n4. MEMORY ANALYSIS:")
    print("-" * 40)

    import gc as garbage_collector

    garbage_collector.collect()
    final_memory = process.memory_info().rss / 1024 / 1024

    print(f"  Final memory usage: {final_memory:.1f} MB")
    print(f"  Total memory growth: {final_memory - baseline_memory:.1f} MB")

    # Check for multiple model instances
    print("\n5. CHECKING FOR DUPLICATE MODELS:")
    print("-" * 40)

    import gc

    fasttext_objects = []
    for obj in gc.get_objects():
        if "fasttext" in str(type(obj)).lower():
            fasttext_objects.append(obj)

    print(f"  FastText objects in memory: {len(fasttext_objects)}")


def detailed_profiling():
    """Run detailed profiling with cProfile."""

    print("\n\n6. DETAILED PROFILING (top 20 functions):")
    print("-" * 40)

    from src.regions.manager_optimized import RegionManager

    # Profile region detection
    profiler = cProfile.Profile()

    manager = RegionManager()
    test_names = ["John Smith", "김철수", "José García", "李明", "محمد الأحمد"] * 20  # 100 names

    profiler.enable()

    for name in test_names:
        manager.detect_region({"name": name, "year": 2024})

    profiler.disable()

    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(20)

    print(s.getvalue())


def analyze_singleton_issue():
    """Specifically analyze the singleton pattern issue."""

    print("\n\n7. SINGLETON PATTERN ANALYSIS:")
    print("-" * 40)

    # Check the actual implementation
    region_manager_path = project_root / "src" / "regions" / "manager_optimized.py"

    if region_manager_path.exists():
        with open(region_manager_path, "r") as f:
            content = f.read()

        # Check for singleton pattern
        has_instances = "_instances" in content
        has_new = "__new__" in content
        has_class_var = "cls._instance" in content or "RegionManager._instance" in content

        print(f"  Has _instances dict: {has_instances}")
        print(f"  Has __new__ method: {has_new}")
        print(f"  Has class variable: {has_class_var}")

        if not (has_instances or has_new or has_class_var):
            print("  ❌ No singleton pattern detected!")
            print("  💡 This is likely why FastText loads multiple times")
    else:
        print("  ❌ manager_optimized.py not found")


def propose_fixes():
    """Propose specific performance fixes."""

    print("\n\n8. PROPOSED PERFORMANCE FIXES:")
    print("-" * 40)

    fixes = [
        {
            "issue": "FastText loading multiple times",
            "solution": "Implement proper singleton pattern in RegionManager",
            "impact": "Could save 30-50% of initialization time",
            "difficulty": "Easy (1 hour)",
        },
        {
            "issue": "No caching for region detection",
            "solution": "Add LRU cache for detect_regions method",
            "impact": "Significant speedup for duplicate names",
            "difficulty": "Easy (30 minutes)",
        },
        {
            "issue": "Synchronous processing",
            "solution": "Add async/parallel processing for batches",
            "impact": "Could improve throughput 2-4x",
            "difficulty": "Medium (1 day)",
        },
        {
            "issue": "Loading all regions on startup",
            "solution": "Lazy load regions on first use",
            "impact": "Faster startup time",
            "difficulty": "Medium (2 hours)",
        },
    ]

    for i, fix in enumerate(fixes, 1):
        print(f"\n  Fix #{i}: {fix['issue']}")
        print(f"    Solution: {fix['solution']}")
        print(f"    Impact: {fix['impact']}")
        print(f"    Difficulty: {fix['difficulty']}")

    print("\n  Recommended order: Start with #1 and #2 (quick wins)")


def main():
    """Run complete performance analysis."""

    start_time = time.time()

    profile_pipeline_stages()
    analyze_singleton_issue()
    detailed_profiling()
    propose_fixes()

    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"ANALYSIS COMPLETE in {total_time:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
