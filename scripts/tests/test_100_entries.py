#!/usr/bin/env python3
"""
Test V7 pipeline with 100 entries to verify Week 1 goal.
"""

import asyncio
import json
import time
from datetime import datetime
from src.core.pipeline_v7_complete_final import create_v7_pipeline


def generate_test_entries(count: int = 100):
    """Generate test entries with diverse characteristics."""
    entries = []

    # Common names from different regions
    names = [
        ("John Smith", "A1"),
        ("Jean Dupont", "A2"),
        ("Hans Müller", "A2"),
        ("Giovanni Rossi", "A2"),
        ("Anders Nilsson", "A3"),
        ("Piotr Kowalski", "B1"),
        ("Ivan Petrov", "B1"),
        ("Dimitris Papadopoulos", "B3"),
        ("Mehmet Yılmaz", "C1"),
        ("Ali Hassan", "C3"),
        ("Zhang Wei", "E1"),
        ("Tanaka Hiroshi", "E3"),
        ("Kim Min-jun", "E4"),
        ("Nguyen Van A", "E5"),
        ("José Silva", "G1"),
        ("Mary Johnson", "A1"),
        ("Emma Wilson", "A1"),
        ("Sophie Martin", "A2"),
        ("Elena Popova", "B1"),
        ("Fatima Al-Rashid", "C4"),
    ]

    fields = ["Mathematics", "Physics", "Computer Science", "Chemistry", "Biology"]
    sources = ["Test", "Manual", "Import", "API"]
    statuses = ["pending", "verified", "disputed"]

    for i in range(count):
        name, region = names[i % len(names)]

        # Add some variety
        if i % 10 == 0:
            # Add native script for some entries
            native = "김민준" if region == "E4" else ""
        else:
            native = ""

        entry = {
            "GlobalID": f"TEST-{i:04d}",
            "CanonicalLatin": f"{name} {i//len(names)}",  # Add number to make unique
            "CanonicalNative": native,
            "DetectedRegion": region,
            "Field": fields[i % len(fields)],
            "Source": sources[i % len(sources)],
            "Sources": [sources[i % len(sources)], "test"],
            "LastUpdated": datetime.now().isoformat(),
            "ValidationStatus": statuses[i % len(statuses)],
            "TestIndex": i,  # Track original position
        }

        # Add some entries with deliberate issues to test error handling
        if i % 20 == 0 and i > 0:
            # Missing required field
            del entry["Field"]
        elif i % 30 == 0 and i > 0:
            # Invalid data type
            entry["BirthYear"] = "invalid"

        entries.append(entry)

    return entries


async def test_100_entries():
    """Test pipeline with 100 entries."""
    print("=" * 70)
    print("V7 PIPELINE - 100 ENTRY TEST")
    print("=" * 70)
    print(f"Start time: {datetime.now().isoformat()}")
    print()

    # Generate test data
    print("Generating 100 test entries...")
    entries = generate_test_entries(100)
    print(f"  ✓ Created {len(entries)} entries")
    print(
        f"  ✓ Regions: {len(set(e['DetectedRegion'] for e in entries if 'DetectedRegion' in e))} unique"
    )
    print(f"  ✓ Fields: {len(set(e.get('Field', 'Unknown') for e in entries))} unique")
    print()

    # Create pipeline
    print("Initializing V7 pipeline...")
    pipeline = create_v7_pipeline(mode="quick")
    print("  ✓ Pipeline created")
    print()

    # Process entries
    print("Processing entries...")
    start_time = time.time()

    try:
        results = await pipeline.process(entries)
        elapsed = time.time() - start_time

        print()
        print("✅ PROCESSING COMPLETE!")
        print("=" * 70)
        print(f"Results:")
        print(f"  • Input entries: {len(entries)}")
        print(f"  • Output entries: {len(results)}")
        print(f"  • Processing time: {elapsed:.2f} seconds")
        print(f"  • Rate: {len(entries)/elapsed:.1f} entries/sec")
        print()

        # Analyze results
        successful = [r for r in results if "PipelineErrors" not in r]
        with_errors = [r for r in results if "PipelineErrors" in r]

        print("Quality Analysis:")
        print(
            f"  • Successful: {len(successful)}/{len(results)} ({100*len(successful)/len(results):.1f}%)"
        )
        print(f"  • With errors: {len(with_errors)}")

        if with_errors:
            print(f"\nError Summary:")
            error_types = {}
            for entry in with_errors:
                for error in entry.get("PipelineErrors", []):
                    stage = error.split(":")[0]
                    error_types[stage] = error_types.get(stage, 0) + 1
            for stage, count in sorted(error_types.items()):
                print(f"    • {stage}: {count} errors")

        # Check key fields
        print("\nField Coverage:")
        fields_present = {
            "GlobalID": sum(1 for r in results if "GlobalID" in r),
            "DetectedRegion": sum(1 for r in results if "DetectedRegion" in r),
            "GraphCoherence": sum(1 for r in results if "GraphCoherence" in r),
            "BayesianConfidence": sum(1 for r in results if "BayesianConfidence" in r),
        }
        for field, count in fields_present.items():
            print(
                f"  • {field}: {count}/{len(results)} ({100*count/len(results):.1f}%)"
            )

        # Save results
        output_file = "test_100_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_file}")

        # Success criteria
        print("\n" + "=" * 70)
        if len(successful) >= 90:  # 90% success rate
            print("🎉 SUCCESS! Week 1 Goal Achieved!")
            print("Pipeline successfully processed 100 entries with >90% success rate")
        elif len(successful) >= 70:
            print("⚠️ PARTIAL SUCCESS")
            print(f"Pipeline processed {len(successful)}/100 entries successfully")
        else:
            print("❌ NEEDS IMPROVEMENT")
            print(f"Only {len(successful)}/100 entries processed successfully")

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback

        traceback.print_exc()

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_100_entries())
