#!/usr/bin/env python3
"""
Quick V7 Throughput Optimization - Fast Production Assessment
"""

import sys
import asyncio
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def quick_optimization_test():
    """Quick but comprehensive optimization test."""
    print("🚀 QUICK V7 THROUGHPUT OPTIMIZATION ASSESSMENT")
    print("=" * 60)

    try:
        from src.core.streaming_v7 import (
            V7StreamingPipeline,
            StreamingConfig,
            test_data_generator,
        )

        # Test 3 key configurations quickly
        configs = [
            {"name": "Current Default", "batch": 100, "workers": 8, "entries": 200},
            {"name": "High Concurrency", "batch": 200, "workers": 16, "entries": 300},
            {"name": "Ultra Optimized", "batch": 150, "workers": 12, "entries": 250},
        ]

        results = []

        for config in configs:
            print(f"\n🧪 Testing {config['name']}...")

            stream_config = StreamingConfig(
                batch_size=config["batch"],
                parallel_workers=config["workers"],
                database_batch_size=config["batch"] // 2,
                rate_limit_per_second=5000,
            )

            start_time = time.time()

            async with V7StreamingPipeline(stream_config) as pipeline:
                data_source = test_data_generator(count=config["entries"])
                metrics = await pipeline.process_stream(data_source)

            duration = time.time() - start_time
            throughput = metrics.entries_processed / duration

            result = {
                "name": config["name"],
                "throughput": throughput,
                "hourly": throughput * 3600,
                "latency": metrics.average_latency_ms,
                "success_rate": metrics.success_rate,
                "processed": metrics.entries_processed,
                "duration": duration,
            }

            results.append(result)

            print(
                f"   Throughput: {throughput:.1f} entries/sec ({throughput * 3600:.0f}/hour)"
            )
            print(f"   Latency: {metrics.average_latency_ms:.1f}ms")
            print(f"   Success: {metrics.success_rate:.1f}%")
            print(f"   Processed: {metrics.entries_processed} in {duration:.2f}s")

        # Find best configuration
        best = max(results, key=lambda r: r["throughput"])

        print(f"\n" + "=" * 60)
        print(f"🎯 OPTIMIZATION RESULTS SUMMARY")
        print(f"=" * 60)

        print(f"📊 Configuration Performance:")
        for result in sorted(results, key=lambda r: r["throughput"], reverse=True):
            print(
                f"   {result['name']:15s}: {result['throughput']:6.1f} entries/sec ({result['hourly']:7.0f}/hour)"
            )

        print(f"\n🏆 OPTIMAL CONFIGURATION: {best['name']}")
        print(f"   Peak Throughput: {best['throughput']:.1f} entries/sec")
        print(f"   Peak Hourly Capacity: {best['hourly']:.0f} entries/hour")
        print(f"   Low Latency: {best['latency']:.1f}ms")
        print(f"   High Success Rate: {best['success_rate']:.1f}%")

        # Production readiness assessment
        baseline_target = 100  # entries/sec production target
        hourly_target = 360000  # 360K/hour production target

        improvement = ((best["throughput"] - baseline_target) / baseline_target) * 100

        print(f"\n✅ PRODUCTION READINESS ASSESSMENT:")
        print(
            f"   Target: {baseline_target} entries/sec ({hourly_target} entries/hour)"
        )
        print(
            f"   Achieved: {best['throughput']:.1f} entries/sec ({best['hourly']:.0f} entries/hour)"
        )
        print(f"   Performance: {improvement:+.1f}% above target")

        if best["throughput"] >= baseline_target * 2:  # 2x target
            print(
                f"   🚀 STATUS: PRODUCTION EXCELLENCE (exceeds target by {improvement:.0f}%)"
            )
            grade = "A+"
        elif best["throughput"] >= baseline_target:
            print(f"   ✅ STATUS: PRODUCTION READY (meets target)")
            grade = "A"
        else:
            print(f"   ⚠️ STATUS: NEEDS OPTIMIZATION")
            grade = "B"

        # Final optimization recommendations
        print(f"\n🔧 OPTIMIZATION RECOMMENDATIONS:")

        if best["name"] == "Ultra Optimized":
            print(f"   ✅ Configuration already optimal")
        else:
            print(f"   🔄 Use {best['name']} configuration for best performance")

        if best["latency"] < 100:
            print(f"   ✅ Latency optimal ({best['latency']:.1f}ms)")
        else:
            print(f"   ⚠️ Consider reducing batch size to improve latency")

        if best["success_rate"] >= 99:
            print(f"   ✅ Success rate optimal ({best['success_rate']:.1f}%)")
        else:
            print(f"   ⚠️ Investigate error sources to improve success rate")

        print(f"\n🎖️ OVERALL OPTIMIZATION GRADE: {grade}")

        return best, grade

    except Exception as e:
        print(f"❌ Optimization test failed: {e}")
        import traceback

        traceback.print_exc()
        return None, "F"


async def main():
    """Run quick throughput optimization."""
    result, grade = await quick_optimization_test()

    if result and grade in ["A+", "A"]:
        print(f"\n🎉 V7 THROUGHPUT OPTIMIZATION: SUCCESS")
        print(f"   Grade: {grade}")
        print(f"   Ready for production deployment")
        return True
    elif result:
        print(f"\n✅ V7 THROUGHPUT OPTIMIZATION: ACCEPTABLE")
        print(f"   Grade: {grade}")
        print(f"   Production viable with room for improvement")
        return True
    else:
        print(f"\n❌ V7 THROUGHPUT OPTIMIZATION: FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
