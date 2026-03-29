#!/usr/bin/env python3
"""
Comprehensive scale testing for 200k, 500k, and 1M entries
Tests system performance, memory usage, and stability at scale
"""

import asyncio
import time
import json
import psutil
import gc
from datetime import datetime
from typing import Dict, List, Any
from src.core.pipeline_v7 import V7Pipeline, PipelineMode


class ScaleTester:
    def __init__(self):
        self.results = {}
        self.process = psutil.Process()

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024

    def generate_entries(self, count: int) -> List[Dict[str, Any]]:
        """Generate test entries with diverse characteristics"""
        entries = []

        # Mix of different name types for realistic testing
        templates = [
            ("김민수", "KOR-{:07d}"),  # Korean
            ("王小明", "CHN-{:07d}"),  # Chinese
            ("John Smith", "ENG-{:07d}"),  # English
            ("山田太郎", "JPN-{:07d}"),  # Japanese
            ("محمد علي", "ARB-{:07d}"),  # Arabic
            ("Иван Петров", "RUS-{:07d}"),  # Russian
            ("François Dupont", "FRA-{:07d}"),  # French
            ("José García", "SPA-{:07d}"),  # Spanish
        ]

        for i in range(count):
            template_idx = i % len(templates)
            name_template, id_template = templates[template_idx]

            entries.append(
                {
                    "CanonicalNative": f"{name_template} {i:07d}",
                    "GlobalID": id_template.format(i),
                    "Source": "scale_test",
                    "Confidence": 0.95,
                }
            )

            if (i + 1) % 50000 == 0:
                print(f"  Generated {i + 1:,}/{count:,} entries...")

        return entries

    async def test_scale(self, entry_count: int, batch_size: int = 1000) -> Dict[str, Any]:
        """Test pipeline at specific scale"""
        print(f"\n{'='*80}")
        print(f"TESTING {entry_count:,} ENTRIES")
        print(f"{'='*80}")

        # Clear memory before test
        gc.collect()
        initial_memory = self.get_memory_usage()
        print(f"Initial memory: {initial_memory:.2f} MB")

        # Generate entries
        print(f"\nGenerating {entry_count:,} entries...")
        entries = self.generate_entries(entry_count)

        memory_after_generation = self.get_memory_usage()
        print(f"Memory after generation: {memory_after_generation:.2f} MB")
        print(f"Memory used for entries: {memory_after_generation - initial_memory:.2f} MB")

        # Initialize pipeline
        print(f"\nInitializing pipeline (mode=QUICK, batch_size={batch_size})...")
        pipeline = V7Pipeline(mode=PipelineMode.QUICK, deterministic=False)

        # Process entries
        print(f"Starting processing...")
        total_processed = 0
        failed_batches = 0
        batch_results = []
        start_time = time.time()
        last_update_time = start_time

        for i in range(0, len(entries), batch_size):
            batch = entries[i : i + batch_size]
            batch_num = i // batch_size

            try:
                batch_start = time.time()
                result = await pipeline.process_batch(batch)
                batch_time = time.time() - batch_start

                total_processed += len(batch)

                # Track batch metrics
                batch_results.append(
                    {
                        "batch_num": batch_num,
                        "batch_size": len(batch),
                        "duration": batch_time,
                        "rate": len(batch) / batch_time if batch_time > 0 else 0,
                        "success": True,
                    }
                )

                # Progress update every 5 seconds
                current_time = time.time()
                if current_time - last_update_time >= 5:
                    elapsed = current_time - start_time
                    rate = total_processed / elapsed if elapsed > 0 else 0
                    eta = (len(entries) - total_processed) / rate if rate > 0 else 0
                    memory_current = self.get_memory_usage()

                    print(
                        f"  Progress: {total_processed:,}/{entry_count:,} "
                        f"({100 * total_processed / entry_count:.1f}%) | "
                        f"Rate: {rate:.0f} e/s | "
                        f"Memory: {memory_current:.0f} MB | "
                        f"ETA: {eta:.0f}s"
                    )
                    last_update_time = current_time

            except Exception as e:
                failed_batches += 1
                batch_results.append(
                    {
                        "batch_num": batch_num,
                        "batch_size": len(batch),
                        "duration": 0,
                        "rate": 0,
                        "success": False,
                        "error": str(e),
                    }
                )
                print(f"  ❌ Batch {batch_num} failed: {e}")

                # Stop if too many failures
                if failed_batches > 10:
                    print(f"  ⚠️ Too many failures, stopping test")
                    break

        total_time = time.time() - start_time
        final_memory = self.get_memory_usage()
        peak_memory = max(self.process.memory_info().peak_wset / 1024 / 1024, final_memory)

        # Calculate statistics
        successful_batches = [b for b in batch_results if b["success"]]
        if successful_batches:
            rates = [b["rate"] for b in successful_batches]
            avg_rate = sum(rates) / len(rates)
            min_rate = min(rates)
            max_rate = max(rates)
        else:
            avg_rate = min_rate = max_rate = 0

        result = {
            "entry_count": entry_count,
            "total_processed": total_processed,
            "total_time_seconds": total_time,
            "total_time_minutes": total_time / 60,
            "overall_rate": total_processed / total_time if total_time > 0 else 0,
            "avg_batch_rate": avg_rate,
            "min_batch_rate": min_rate,
            "max_batch_rate": max_rate,
            "batch_size": batch_size,
            "total_batches": len(batch_results),
            "failed_batches": failed_batches,
            "success_rate": (
                100 * (len(batch_results) - failed_batches) / len(batch_results)
                if batch_results
                else 0
            ),
            "memory": {
                "initial_mb": initial_memory,
                "final_mb": final_memory,
                "peak_mb": peak_memory,
                "used_mb": final_memory - initial_memory,
            },
            "sample_batches": (
                batch_results[:5] + batch_results[-5:] if len(batch_results) > 10 else batch_results
            ),
        }

        # Print summary
        print(f"\n{'='*80}")
        print(f"RESULTS FOR {entry_count:,} ENTRIES")
        print(f"{'='*80}")
        print(f"Total processed: {total_processed:,}/{entry_count:,}")
        print(f"Total time: {total_time:.2f}s ({total_time/60:.2f} min)")
        print(f"Overall rate: {result['overall_rate']:.2f} entries/sec")
        print(f"Average batch rate: {avg_rate:.2f} entries/sec")
        print(f"Failed batches: {failed_batches}/{len(batch_results)}")
        print(f"Memory usage: {final_memory - initial_memory:.2f} MB")
        print(f"Peak memory: {peak_memory:.2f} MB")

        # Check against targets
        target_rate = 35  # entries/sec for 1M in 35 min
        if result["overall_rate"] >= target_rate:
            print(
                f"✅ PASSED: Rate {result['overall_rate']:.0f} e/s exceeds target {target_rate} e/s"
            )
        else:
            print(
                f"❌ FAILED: Rate {result['overall_rate']:.0f} e/s below target {target_rate} e/s"
            )

        return result

    async def run_all_tests(self):
        """Run tests at all scales"""
        scales = [200_000, 500_000, 1_000_000]

        print(f"{'='*80}")
        print("COMPREHENSIVE SCALE TESTING")
        print(f"{'='*80}")
        print(f"Start time: {datetime.now()}")
        print(f"Testing scales: {[f'{s:,}' for s in scales]}")

        for scale in scales:
            try:
                result = await self.test_scale(scale)
                self.results[f"{scale}_entries"] = result

                # Save intermediate results
                self.save_results()

                # Pause between tests to let system recover
                if scale != scales[-1]:
                    print(f"\nPausing 10 seconds before next test...")
                    gc.collect()
                    await asyncio.sleep(10)

            except Exception as e:
                print(f"\n❌ Test for {scale:,} entries failed: {e}")
                self.results[f"{scale}_entries"] = {
                    "error": str(e),
                    "entry_count": scale,
                    "status": "failed",
                }

        return self.results

    def save_results(self):
        """Save results to file"""
        filename = f"scale_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {filename}")

    def print_summary(self):
        """Print final summary"""
        print(f"\n{'='*80}")
        print("FINAL SUMMARY")
        print(f"{'='*80}")

        for scale_name, result in self.results.items():
            if "error" in result:
                print(f"\n{scale_name}: ❌ FAILED - {result['error']}")
            else:
                print(f"\n{scale_name}:")
                print(f"  Rate: {result['overall_rate']:.2f} e/s")
                print(f"  Time: {result['total_time_minutes']:.2f} min")
                print(f"  Memory: {result['memory']['used_mb']:.2f} MB")
                print(f"  Success: {result['success_rate']:.1f}%")

                # Check if meets production target
                if result["overall_rate"] >= 476:  # 1M in 35 min = 476 e/s
                    print(f"  Status: ✅ PRODUCTION READY")
                elif result["overall_rate"] >= 35:  # Minimum viable
                    print(f"  Status: ⚠️ ACCEPTABLE")
                else:
                    print(f"  Status: ❌ TOO SLOW")


async def main():
    tester = ScaleTester()
    await tester.run_all_tests()
    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
