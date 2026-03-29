#!/usr/bin/env python3
"""
REAL 1M BATCH TEST - Production Validation (Async Version)
Tests pipeline with 1 million realistic entries
"""

import asyncio
import json
import time
import random
import traceback
import psutil
import os
from datetime import datetime
from typing import List, Dict, Any

# Test data generation
FIRST_NAMES = [
    "John",
    "Jane",
    "Michael",
    "Sarah",
    "David",
    "Emily",
    "Robert",
    "Lisa",
    "James",
    "Mary",
    "William",
    "Patricia",
    "Richard",
    "Jennifer",
    "Thomas",
    "Linda",
    "김정은",
    "박근혜",
    "문재인",
    "이명박",
    "김대중",
    "노무현",
    "전두환",
    "김영삼",
    "王",
    "李",
    "张",
    "刘",
    "陈",
    "杨",
    "黄",
    "赵",
    "田中",
    "山田",
    "鈴木",
    "高橋",
    "渡辺",
    "伊藤",
    "山本",
    "中村",
    "Владимир",
    "Сергей",
    "Александр",
    "Михаил",
    "Иван",
    "Дмитрий",
    "محمد",
    "أحمد",
    "علي",
    "حسن",
    "إبراهيم",
    "خالد",
    "José",
    "María",
    "Juan",
    "Pedro",
    "Carlos",
    "Luis",
    "François",
    "Pierre",
    "Jacques",
    "Michel",
    "Jean",
    "Philippe",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "김",
    "이",
    "박",
    "최",
    "정",
    "강",
    "조",
    "윤",
    "장",
    "임",
    "王",
    "李",
    "张",
    "刘",
    "陈",
    "杨",
    "黄",
    "赵",
    "吴",
    "周",
    "佐藤",
    "鈴木",
    "高橋",
    "田中",
    "渡辺",
    "伊藤",
    "山本",
    "中村",
    "Путин",
    "Медведев",
    "Иванов",
    "Петров",
    "Сидоров",
    "Смирнов",
    "الأحمد",
    "الحسن",
    "العلي",
    "الخالد",
    "المحمد",
    "García",
    "Rodríguez",
    "González",
    "Fernández",
    "López",
    "Martínez",
    "Dupont",
    "Martin",
    "Bernard",
    "Dubois",
    "Thomas",
    "Robert",
]


def generate_test_entry(index: int) -> Dict[str, Any]:
    """Generate a realistic test entry with international names"""

    # Mix of scripts and languages
    if index % 7 == 0:  # Korean names
        given = random.choice(
            [
                n
                for n in FIRST_NAMES
                if any(
                    "\u1100" <= c <= "\u11ff" or "\uac00" <= c <= "\ud7af" for c in n
                )
            ]
        )
        family = random.choice(
            [
                n
                for n in LAST_NAMES
                if any(
                    "\u1100" <= c <= "\u11ff" or "\uac00" <= c <= "\ud7af" for c in n
                )
            ]
        )
    elif index % 7 == 1:  # Chinese names
        given = random.choice(
            [n for n in FIRST_NAMES if any("\u4e00" <= c <= "\u9fff" for c in n)]
        )
        family = random.choice(
            [n for n in LAST_NAMES if any("\u4e00" <= c <= "\u9fff" for c in n)]
        )
    elif index % 7 == 2:  # Japanese names
        given = random.choice(
            [
                n
                for n in FIRST_NAMES
                if any(
                    "\u3040" <= c <= "\u309f"
                    or "\u30a0" <= c <= "\u30ff"
                    or "\u4e00" <= c <= "\u9fff"
                    for c in n
                )
            ]
        )
        family = random.choice(
            [
                n
                for n in LAST_NAMES
                if any(
                    "\u3040" <= c <= "\u309f"
                    or "\u30a0" <= c <= "\u30ff"
                    or "\u4e00" <= c <= "\u9fff"
                    for c in n
                )
            ]
        )
    elif index % 7 == 3:  # Russian names
        given = random.choice(
            [n for n in FIRST_NAMES if any("\u0400" <= c <= "\u04ff" for c in n)]
        )
        family = random.choice(
            [n for n in LAST_NAMES if any("\u0400" <= c <= "\u04ff" for c in n)]
        )
    elif index % 7 == 4:  # Arabic names
        given = random.choice(
            [n for n in FIRST_NAMES if any("\u0600" <= c <= "\u06ff" for c in n)]
        )
        family = random.choice(
            [n for n in LAST_NAMES if any("\u0600" <= c <= "\u06ff" for c in n)]
        )
    else:  # Latin script names
        given = random.choice(
            [
                n
                for n in FIRST_NAMES
                if all(c < "\u0080" or c in "áéíóúàèìòùâêîôûäëïöüñç" for c in n)
            ]
        )
        family = random.choice(
            [
                n
                for n in LAST_NAMES
                if all(c < "\u0080" or c in "áéíóúàèìòùâêîôûäëïöüñç" for c in n)
            ]
        )

    # Create simpler entry format
    return {
        "GivenName": given,
        "FamilyName": family,
        "CanonicalNative": f"{family} {given}",
        "Email": f"author{index}@example.com",
        "TestIndex": index,
    }


async def run_batch_test(batch_size: int, total_entries: int):
    """Run the async batch test with monitoring"""

    print(f"\n{'='*80}")
    print(f"RUNNING 1M BATCH TEST (ASYNC)")
    print(f"{'='*80}")
    print(f"Total Entries: {total_entries:,}")
    print(f"Batch Size: {batch_size:,}")
    print(f"Expected Batches: {total_entries // batch_size}")
    print(f"Starting Time: {datetime.now()}")
    print(f"{'='*80}\n")

    # Import pipeline
    try:
        from src.core.pipeline_v7 import V7Pipeline

        # Initialize pipeline
        pipeline = V7Pipeline()

        # Performance tracking
        start_time = time.time()
        processed = 0
        failed = 0
        duplicates_detected = 0
        batch_times = []
        memory_usage = []

        # Process in batches
        for batch_num in range(0, total_entries, batch_size):
            batch_start = time.time()

            # Generate batch
            batch = []
            for i in range(batch_num, min(batch_num + batch_size, total_entries)):
                batch.append(generate_test_entry(i))

            # Check memory before processing
            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / 1024 / 1024  # MB

            try:
                # Process batch asynchronously
                results = await pipeline.process_batch(batch)

                # Count results based on what's returned
                if isinstance(results, dict):
                    # Handle dict response
                    if "entries" in results:
                        for entry in results["entries"]:
                            processed += 1
                            if entry.get("Status") == "failed":
                                failed += 1
                            if "duplicate" in str(entry.get("GlobalID", "")).lower():
                                duplicates_detected += 1
                    elif "metrics" in results:
                        # Use metrics if available
                        processed += results["metrics"].get("processed", len(batch))
                        failed += results["metrics"].get("failed", 0)
                        duplicates_detected += results["metrics"].get(
                            "duplicate_global_ids", 0
                        )
                    else:
                        # Assume all processed if no clear indication
                        processed += len(batch)
                elif isinstance(results, list):
                    # Handle list response
                    for result in results:
                        processed += 1
                        if result.get("Status") == "failed":
                            failed += 1
                        if "duplicate" in str(result.get("GlobalID", "")).lower():
                            duplicates_detected += 1
                else:
                    # Unknown response type
                    print(f"  ⚠️ Unknown response type: {type(results)}")
                    processed += len(batch)

            except Exception as e:
                print(f"  ❌ Batch {batch_num // batch_size} failed: {str(e)}")
                failed += len(batch)
                processed += len(batch)

            # Check memory after processing
            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_usage.append(mem_after)

            # Track batch time
            batch_time = time.time() - batch_start
            batch_times.append(batch_time)

            # Progress report every 10 batches
            if (batch_num // batch_size + 1) % 10 == 0 or batch_num == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (total_entries - processed) / rate if rate > 0 else 0

                print(
                    f"  Progress: {processed:,}/{total_entries:,} ({processed*100/total_entries:.1f}%)"
                )
                print(f"  Speed: {rate:.1f} entries/sec | ETA: {eta/60:.1f} min")
                print(
                    f"  Memory: {mem_after:.1f} MB | Failed: {failed} | Duplicates: {duplicates_detected}"
                )
                print(f"  Batch time: {batch_time:.2f}s")
                print()

        # Final statistics
        total_time = time.time() - start_time
        avg_speed = processed / total_time if total_time > 0 else 0
        success_count = processed - failed

        print(f"\n{'='*80}")
        print(f"BATCH TEST COMPLETE")
        print(f"{'='*80}")
        print(f"Total Processed: {processed:,} / {total_entries:,}")
        print(f"Total Time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        print(f"Average Speed: {avg_speed:.1f} entries/sec")
        print(f"Time for 1M: {1_000_000 / avg_speed / 60:.1f} minutes (projected)")
        print(
            f"Failed Entries: {failed:,} ({failed*100/processed:.2f}%)"
            if processed > 0
            else "Failed Entries: 0"
        )
        print(
            f"Success Rate: {success_count*100/processed:.2f}%"
            if processed > 0
            else "Success Rate: 0%"
        )
        print(f"Duplicates Detected: {duplicates_detected:,}")
        print(
            f"Peak Memory: {max(memory_usage):.1f} MB"
            if memory_usage
            else "Peak Memory: N/A"
        )
        print(
            f"Avg Batch Time: {sum(batch_times)/len(batch_times):.2f}s"
            if batch_times
            else "Avg Batch Time: N/A"
        )
        print(f"{'='*80}\n")

        # Save results
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_entries": total_entries,
            "batch_size": batch_size,
            "processed": processed,
            "failed": failed,
            "duplicates_detected": duplicates_detected,
            "total_time_seconds": total_time,
            "average_speed_per_sec": avg_speed,
            "projected_1m_minutes": (
                1_000_000 / avg_speed / 60 if avg_speed > 0 else None
            ),
            "success_rate": success_count * 100 / processed if processed > 0 else 0,
            "peak_memory_mb": max(memory_usage) if memory_usage else 0,
            "batch_times": batch_times[:10],  # First 10 for reference
            "status": (
                "SUCCESS"
                if failed < processed * 0.05
                else "WARNING" if failed < processed * 0.5 else "FAILED"
            ),
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"1m_batch_results_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to: {filename}")
        return results

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        traceback.print_exc()
        return None


async def main():
    # Run with recommended batch size
    BATCH_SIZE = 1000  # Optimal based on CLAUDE.md
    TOTAL_ENTRIES = 1_000_000  # 1 million

    results = await run_batch_test(BATCH_SIZE, TOTAL_ENTRIES)

    if results:
        if results["status"] == "SUCCESS":
            print("✅ 1M BATCH TEST PASSED")
        elif results["status"] == "WARNING":
            print("⚠️ 1M BATCH TEST COMPLETED WITH WARNINGS")
        else:
            print("❌ 1M BATCH TEST FAILED")


if __name__ == "__main__":
    asyncio.run(main())
