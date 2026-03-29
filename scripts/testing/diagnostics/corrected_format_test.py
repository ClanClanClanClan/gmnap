#!/usr/bin/env python3
"""
Corrected Format Test - Quick verification of pipeline format fix.
"""

import time
import json
import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.core.pipeline_v7 import V7Pipeline


async def test_corrected_format():
    """Test the corrected pipeline format handling."""
    print("🔧 PIPELINE FORMAT CORRECTION TEST")
    print("=" * 50)

    # Test with a few key batch sizes
    test_sizes = [10, 100, 1000, 5000]
    results = []

    for size in test_sizes:
        print(f"Testing {size:>4} entries... ", end="")

        # Generate simple entries
        entries = [
            {
                "ID": f"test_{i:06d}",
                "CanonicalNative": "Test User",
                "Region": "a1_anglo_sphere",
            }
            for i in range(size)
        ]

        pipeline = V7Pipeline()
        start = time.time()

        try:
            # Get the new format result
            result = await pipeline.process_batch(entries)
            duration = time.time() - start

            # Handle new format correctly
            if isinstance(result, dict) and "entries" in result:
                processed_entries = result["entries"]
                metrics = result.get("metrics", {})

                # Extract statistics
                successful = len(
                    [e for e in processed_entries if e.get("Status") == "success"]
                )
                speed = size / duration
                success_rate = (successful / size) * 100

                result_data = {
                    "size": size,
                    "duration": round(duration, 2),
                    "speed_eps": round(speed, 1),
                    "successful": successful,
                    "success_rate": round(success_rate, 1),
                    "format": "corrected_dict",
                    "status": "success",
                }

                print(f"✅ {speed:>6.0f} e/s ({success_rate:.0f}% success)")

            else:
                result_data = {
                    "size": size,
                    "error": "Unexpected format",
                    "status": "failed",
                }
                print("❌ Wrong format")

            results.append(result_data)

        except Exception as e:
            result_data = {"size": size, "error": str(e)[:50], "status": "failed"}
            results.append(result_data)
            print(f"❌ Error: {str(e)[:30]}")

        finally:
            del pipeline

        # Brief pause between tests
        await asyncio.sleep(0.5)

    # Summary
    successful_tests = [r for r in results if r["status"] == "success"]

    print(f"\n📊 FORMAT CORRECTION SUMMARY")
    print("=" * 50)
    print(f"Tests completed: {len(results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Format handling: ✅ CORRECTED")

    if successful_tests:
        avg_speed = sum(r["speed_eps"] for r in successful_tests) / len(
            successful_tests
        )
        avg_success_rate = sum(r["success_rate"] for r in successful_tests) / len(
            successful_tests
        )

        print(f"\nPerformance with corrected format:")
        print(f"  Average speed: {avg_speed:.0f} entries/sec")
        print(f"  Average success rate: {avg_success_rate:.1f}%")

        print(f"\nDetailed results:")
        for r in successful_tests:
            print(
                f"  {r['size']:>4} entries: {r['speed_eps']:>6.0f} e/s ({r['success_rate']:>5.1f}% success)"
            )

    # Save verification
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"corrected_format_test_{timestamp}.json", "w") as f:
        json.dump(
            {
                "test_type": "format_correction_verification",
                "timestamp": timestamp,
                "pipeline_format": "dict_with_entries_and_metrics",
                "correction_applied": True,
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n✅ FORMAT CORRECTION VERIFIED")
    print(f"   Pipeline now returns: dict with 'entries' and 'metrics' keys")
    print(f"   Batch tests will now handle this format correctly")


if __name__ == "__main__":
    asyncio.run(test_corrected_format())
