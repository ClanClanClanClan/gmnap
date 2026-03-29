#!/usr/bin/env python3
"""
Resource monitoring for production safety bounds.
Tests memory and runtime limits during FST builds.
"""

import psutil
import subprocess
import time
import sys


def monitor_fst_build():
    """Monitor resource usage during FST build"""

    print("📊 Testing FST build resource usage...")

    # Start FST build process
    process = subprocess.Popen(
        ["python3", "scripts/build_fsts_multi.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    max_memory = 0
    start_time = time.time()

    # Monitor while process runs
    while process.poll() is None:
        try:
            p = psutil.Process(process.pid)
            memory_mb = p.memory_info().rss / 1024 / 1024
            max_memory = max(max_memory, memory_mb)
            time.sleep(0.1)
        except psutil.NoSuchProcess:
            break

    process.wait()
    runtime = time.time() - start_time

    # Report results
    print(f"  📈 Peak memory: {max_memory:.1f} MB")
    print(f"  ⏱️  Runtime: {runtime:.1f} seconds")

    # Check limits (production bounds)
    memory_ok = max_memory < 6144  # 6GB limit
    runtime_ok = runtime < 4200  # 70 minute limit

    if memory_ok:
        print(f"  ✅ Memory OK: {max_memory:.1f} MB < 6144 MB")
    else:
        print(f"  ❌ Memory limit exceeded: {max_memory:.1f} MB >= 6144 MB")

    if runtime_ok:
        print(f"  ✅ Runtime OK: {runtime:.1f}s < 4200s")
    else:
        print(f"  ❌ Runtime limit exceeded: {runtime:.1f}s >= 4200s")

    return memory_ok and runtime_ok


def monitor_validation():
    """Monitor resource usage during validation"""

    print("📊 Testing validation resource usage...")

    # Test validation script
    start_time = time.time()

    try:
        result = subprocess.run(
            ["python3", "scripts/validate.py"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        runtime = time.time() - start_time

        print(f"  ⏱️  Validation runtime: {runtime:.1f} seconds")

        if runtime < 120:  # 2 minute limit for validation
            print(f"  ✅ Validation runtime OK: {runtime:.1f}s < 120s")
            return True
        else:
            print(f"  ❌ Validation runtime exceeded: {runtime:.1f}s >= 120s")
            return False

    except subprocess.TimeoutExpired:
        print("  ❌ Validation timeout (>300s)")
        return False
    except Exception as e:
        print(f"  ❌ Validation error: {e}")
        return False


def main():
    """Run complete resource monitoring suite"""

    print("🔍 Production Resource Monitoring Suite")
    print("=" * 50)

    # Check if psutil is available
    try:
        import psutil
    except ImportError:
        print("❌ psutil not available - install with: pip install psutil")
        sys.exit(1)

    # Test FST build resources
    fst_ok = monitor_fst_build()
    print()

    # Test validation resources
    val_ok = monitor_validation()
    print()

    # Overall result
    if fst_ok and val_ok:
        print("✅ All resource limits within production bounds")
        print("🚀 System ready for production deployment")
        return 0
    else:
        print("❌ Resource limits exceeded - optimization needed")
        print("🚨 System NOT ready for production deployment")
        return 1


if __name__ == "__main__":
    sys.exit(main())
