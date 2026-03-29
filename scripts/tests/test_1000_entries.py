#!/usr/bin/env python3
"""
Test V7 pipeline with 1000 entries for Week 2 goal.
Tests scale, performance, and authority enrichment.
"""

import asyncio
import json
import time
import random
from datetime import datetime
from src.core.pipeline_v7_complete_final import create_v7_pipeline


def generate_test_entries(count: int = 1000):
    """Generate test entries with diverse characteristics."""
    entries = []

    # Diverse names from different regions and fields
    names = [
        # Mathematicians
        ("Carl Friedrich Gauss", "A2", "Mathematics"),
        ("Leonhard Euler", "A2", "Mathematics"),
        ("Srinivasa Ramanujan", "D2", "Mathematics"),
        ("Emmy Noether", "A2", "Mathematics"),
        ("David Hilbert", "A2", "Mathematics"),
        ("Henri Poincaré", "A2", "Mathematics"),
        ("Terence Tao", "E1", "Mathematics"),
        ("Andrew Wiles", "A1", "Mathematics"),
        ("Maryam Mirzakhani", "C2", "Mathematics"),
        # Physicists
        ("Albert Einstein", "A2", "Physics"),
        ("Marie Curie", "B1", "Physics"),
        ("Niels Bohr", "A3", "Physics"),
        ("Richard Feynman", "A1", "Physics"),
        ("Chen Ning Yang", "E1", "Physics"),
        ("Hideki Yukawa", "E3", "Physics"),
        ("Abdus Salam", "D4", "Physics"),
        # Computer Scientists
        ("Alan Turing", "A1", "Computer Science"),
        ("Donald Knuth", "A1", "Computer Science"),
        ("Edsger Dijkstra", "A2", "Computer Science"),
        ("Grace Hopper", "A1", "Computer Science"),
        ("Yoshua Bengio", "G1", "Computer Science"),
        ("Andrew Ng", "E1", "Computer Science"),
        # Chemists
        ("Linus Pauling", "A1", "Chemistry"),
        ("Dorothy Hodgkin", "A1", "Chemistry"),
        ("Ahmed Zewail", "C3", "Chemistry"),
        ("Dmitri Mendeleev", "B1", "Chemistry"),
        # Biologists
        ("Charles Darwin", "A1", "Biology"),
        ("Rosalind Franklin", "A1", "Biology"),
        ("Barbara McClintock", "A1", "Biology"),
        ("Tu Youyou", "E1", "Biology"),
        # Generic names for padding
        ("John Smith", "A1", "Mathematics"),
        ("Jean Dupont", "A2", "Physics"),
        ("Hans Müller", "A2", "Chemistry"),
        ("Giovanni Rossi", "A2", "Biology"),
        ("Anders Nilsson", "A3", "Computer Science"),
        ("Piotr Kowalski", "B1", "Mathematics"),
        ("Ivan Petrov", "B1", "Physics"),
        ("Dimitris Papadopoulos", "B3", "Chemistry"),
        ("Mehmet Yılmaz", "C1", "Biology"),
        ("Ali Hassan", "C3", "Computer Science"),
        ("Zhang Wei", "E1", "Mathematics"),
        ("Tanaka Hiroshi", "E3", "Physics"),
        ("Kim Min-jun", "E4", "Chemistry"),
        ("Nguyen Van A", "E5", "Biology"),
        ("José Silva", "G1", "Computer Science"),
    ]

    sources = ["Test", "Manual", "Import", "API", "CrossRef", "ORCID"]
    statuses = ["pending", "verified", "disputed"]
    institutions = [
        "MIT",
        "Harvard",
        "Stanford",
        "Princeton",
        "Cambridge",
        "Oxford",
        "ETH Zurich",
        "Sorbonne",
        "Tokyo University",
        "Tsinghua University",
        "IIT",
        "Moscow State University",
    ]

    for i in range(count):
        name, region, field = names[i % len(names)]

        # Add variation to make names unique
        if i >= len(names):
            name = f"{name} {i//len(names)}"

        # Add native script for some entries
        native = ""
        if region == "E4" and random.random() < 0.3:
            native = "김민준"
        elif region == "E1" and random.random() < 0.3:
            native = "张伟"
        elif region == "E3" and random.random() < 0.3:
            native = "田中浩"
        elif region == "C3" and random.random() < 0.3:
            native = "علي حسن"
        elif region == "B1" and random.random() < 0.3:
            native = "Иван Петров"

        entry = {
            "GlobalID": f"TEST-{i:05d}",
            "CanonicalLatin": name,
            "CanonicalNative": native,
            "DetectedRegion": region,
            "Field": field,
            "Source": sources[i % len(sources)],
            "Sources": [sources[i % len(sources)], "test"],
            "LastUpdated": datetime.now().isoformat(),
            "ValidationStatus": statuses[i % len(statuses)],
            "TestIndex": i,
        }

        # Add optional fields for some entries
        if random.random() < 0.5:
            entry["Institution"] = [
                institutions[random.randint(0, len(institutions) - 1)]
            ]

        if random.random() < 0.3:
            entry["BirthYear"] = random.randint(1900, 2000)

        if random.random() < 0.2:
            entry["Gender"] = random.choice(["M", "F", "X"])

        # Add some entries with deliberate issues to test error handling
        if i % 100 == 99:
            # Missing required field
            del entry["Field"]
        elif i % 200 == 199:
            # Invalid data type
            entry["BirthYear"] = "invalid"
        elif i % 300 == 299:
            # Test tab/newline normalization
            entry["CanonicalLatin"] = f"Test\t{name}\nVariant"

        entries.append(entry)

    return entries


async def test_1000_entries():
    """Test pipeline with 1000 entries."""
    print("=" * 70)
    print("V7 PIPELINE - 1000 ENTRY SCALE TEST (WEEK 2)")
    print("=" * 70)
    print(f"Start time: {datetime.now().isoformat()}")
    print()

    # Generate test data
    print("Generating 1000 test entries...")
    entries = generate_test_entries(1000)
    print(f"  ✓ Created {len(entries)} entries")
    print(
        f"  ✓ Regions: {len(set(e['DetectedRegion'] for e in entries if 'DetectedRegion' in e))} unique"
    )
    print(f"  ✓ Fields: {len(set(e.get('Field', 'Unknown') for e in entries))} unique")

    # Sample some notable entries
    notable = [
        e
        for e in entries[:50]
        if "Einstein" in e["CanonicalLatin"]
        or "Gauss" in e["CanonicalLatin"]
        or "Curie" in e["CanonicalLatin"]
        or "Turing" in e["CanonicalLatin"]
    ]
    if notable:
        print(
            f"  ✓ Notable entries include: {', '.join(e['CanonicalLatin'] for e in notable[:3])}"
        )
    print()

    # Create pipeline with authority enrichment enabled
    print("Initializing V7 pipeline...")
    pipeline = create_v7_pipeline(mode="quick", enable_live=True)
    print("  ✓ Pipeline created with authority enrichment enabled")
    print()

    # Process entries in batches
    print("Processing 1000 entries...")
    batch_size = 100
    all_results = []
    start_time = time.time()

    try:
        for batch_start in range(0, len(entries), batch_size):
            batch_end = min(batch_start + batch_size, len(entries))
            batch = entries[batch_start:batch_end]

            print(
                f"  Processing batch {batch_start//batch_size + 1}/{(len(entries)-1)//batch_size + 1} "
                f"(entries {batch_start+1}-{batch_end})...",
                end="",
            )

            batch_results = await pipeline.process(batch)
            all_results.extend(batch_results)

            print(f" ✓ ({len(batch_results)} processed)")

        elapsed = time.time() - start_time

        print()
        print("✅ PROCESSING COMPLETE!")
        print("=" * 70)
        print(f"Results:")
        print(f"  • Input entries: {len(entries)}")
        print(f"  • Output entries: {len(all_results)}")
        print(f"  • Processing time: {elapsed:.2f} seconds")
        print(f"  • Rate: {len(entries)/elapsed:.1f} entries/sec")
        print(f"  • Projected 1M time: {1000000/len(entries)*elapsed/60:.1f} minutes")
        print()

        # Analyze results
        successful = [r for r in all_results if "PipelineErrors" not in r]
        with_errors = [r for r in all_results if "PipelineErrors" in r]
        with_authority = [r for r in all_results if r.get("AuthoritySources")]
        with_coherence = [r for r in all_results if "GraphCoherence" in r]
        with_bayesian = [r for r in all_results if "BayesianConfidence" in r]

        print("Quality Analysis:")
        print(
            f"  • Successful: {len(successful)}/{len(all_results)} ({100*len(successful)/len(all_results):.1f}%)"
        )
        print(
            f"  • With errors: {len(with_errors)} ({100*len(with_errors)/len(all_results):.1f}%)"
        )
        print(
            f"  • Authority enriched: {len(with_authority)} ({100*len(with_authority)/len(all_results):.1f}%)"
        )
        print(
            f"  • Graph coherence: {len(with_coherence)} ({100*len(with_coherence)/len(all_results):.1f}%)"
        )
        print(
            f"  • Bayesian confidence: {len(with_bayesian)} ({100*len(with_bayesian)/len(all_results):.1f}%)"
        )

        if with_errors:
            print(f"\nError Summary:")
            error_types = {}
            for entry in with_errors:
                for error in entry.get("PipelineErrors", []):
                    stage = error.split(":")[0] if ":" in error else error
                    error_types[stage] = error_types.get(stage, 0) + 1
            for stage, count in sorted(error_types.items(), key=lambda x: -x[1])[:5]:
                print(f"    • {stage}: {count} errors")

        # Check for authority data
        if with_authority:
            print(f"\nAuthority Sources Used:")
            sources = {}
            for entry in with_authority:
                for source in entry.get("AuthoritySources", []):
                    sources[source] = sources.get(source, 0) + 1
            for source, count in sorted(sources.items(), key=lambda x: -x[1]):
                print(f"    • {source}: {count} entries")

            # Show sample enriched entry
            sample = with_authority[0]
            print(f"\nSample enriched entry:")
            print(f"  Name: {sample.get('CanonicalLatin')}")
            print(f"  Sources: {sample.get('AuthoritySources')}")
            if "CrossrefData" in sample:
                print(
                    f"  Crossref works: {sample['CrossrefData'].get('works_count', 0)}"
                )

        # Performance metrics by stage
        print("\nStage Performance:")
        stages = [
            "Stage 1",
            "Stage 2",
            "Stage 3",
            "Stage 4",
            "Stage 5",
            "Stage 6",
            "Stage 7",
            "Stage 8",
            "Stage 9",
            "Stage 10",
            "Stage 11",
        ]
        for stage in stages:
            stage_errors = sum(
                1
                for e in with_errors
                for err in e.get("PipelineErrors", [])
                if stage in err
            )
            success_rate = 100 * (1 - stage_errors / len(all_results))
            print(f"  • {stage}: {success_rate:.1f}% success rate")

        # Save results
        output_file = "test_1000_results.json"
        with open(output_file, "w") as f:
            # Save a subset to avoid huge file
            sample_results = (
                all_results[:100] if len(all_results) > 100 else all_results
            )
            json.dump(
                {
                    "summary": {
                        "total_entries": len(all_results),
                        "successful": len(successful),
                        "with_errors": len(with_errors),
                        "with_authority": len(with_authority),
                        "processing_time": elapsed,
                        "entries_per_second": len(entries) / elapsed,
                    },
                    "sample_results": sample_results,
                },
                f,
                indent=2,
                default=str,
            )
        print(f"\nResults saved to: {output_file}")

        # Success criteria for Week 2
        print("\n" + "=" * 70)
        print("WEEK 2 GOALS ASSESSMENT:")
        success_rate = len(successful) / len(all_results) * 100

        if success_rate >= 90:
            print(
                "✅ Goal 1: Process 1000 entries - ACHIEVED ({:.1f}% success)".format(
                    success_rate
                )
            )
        else:
            print(
                "⚠️ Goal 1: Process 1000 entries - PARTIAL ({:.1f}% success, target 90%)".format(
                    success_rate
                )
            )

        if len(with_authority) > 0:
            print(
                "✅ Goal 2: Authority enrichment - WORKING ({} entries enriched)".format(
                    len(with_authority)
                )
            )
        else:
            print("❌ Goal 2: Authority enrichment - NOT WORKING")

        if elapsed < 60:  # Less than 1 minute for 1000 entries
            print(
                "✅ Goal 3: Performance - EXCELLENT ({:.1f} entries/sec)".format(
                    len(entries) / elapsed
                )
            )
        elif elapsed < 120:
            print(
                "⚠️ Goal 3: Performance - ACCEPTABLE ({:.1f} entries/sec)".format(
                    len(entries) / elapsed
                )
            )
        else:
            print(
                "❌ Goal 3: Performance - NEEDS IMPROVEMENT ({:.1f} entries/sec)".format(
                    len(entries) / elapsed
                )
            )

        # Overall assessment
        print("\n" + "=" * 70)
        if success_rate >= 90 and len(with_authority) > 0:
            print("🎉 WEEK 2 MILESTONE ACHIEVED!")
            print(
                "Pipeline successfully processes 1000 entries with authority enrichment"
            )
            print("Estimated V7 compliance: ~45-50%")
        elif success_rate >= 80:
            print("⚠️ GOOD PROGRESS")
            print(f"Pipeline processes {success_rate:.1f}% of entries successfully")
            print("Some improvements needed for full Week 2 goals")
        else:
            print("❌ MORE WORK NEEDED")
            print(f"Only {success_rate:.1f}% success rate")

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback

        traceback.print_exc()

    print("=" * 70)


if __name__ == "__main__":
    # Set environment to allow testing (not offline)
    import os

    os.environ["OFFLINE"] = "0"  # Enable authority sources
    os.environ["GMNAP_OFFLINE"] = "0"

    asyncio.run(test_1000_entries())
