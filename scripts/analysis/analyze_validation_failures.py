#!/usr/bin/env python3
"""
Analyze which entries fail validation and why.
"""

import asyncio
from test_v7_pipeline_stages import V7StageValidator
from src.core.pipeline_v7 import V7Pipeline, PipelineMode


async def analyze_validation_failures():
    print("=== ANALYZING VALIDATION FAILURES ===")

    # Run the isolated test to see which 4 entries are failing
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    test = V7StageValidator()
    test_entries = test._generate_test_data()

    # Run the exact sequence from the isolated test
    stage1_results = await pipeline._stage_1_ingest(test_entries.copy())
    stage2_results = await pipeline._stage_2_detect_region(stage1_results)
    stage3_results = await pipeline._stage_3_region_hooks(stage2_results)
    stage5_results = await pipeline._stage_5_collision_analytics(stage3_results)
    results = await pipeline._stage_8_global_validate(stage5_results)

    print(f"Total entries: {len(results)}")
    print(f"Valid entries: {sum(1 for e in results if e.get('ValidationStatus') == 'VALID')}")
    print()

    # Analyze failures
    print("=== FAILED ENTRIES ===")
    failed_count = 0

    for i, entry in enumerate(results):
        if entry.get("ValidationStatus") != "VALID":
            failed_count += 1
            canonical = entry.get("CanonicalLatin", "Unknown")
            native = entry.get("CanonicalNative", "Unknown")
            region = entry.get("DetectedRegion", "Unknown")
            validation_results = entry.get("ValidationResults", {})

            print(f"\nFailed Entry {failed_count}: {canonical}")
            print(f"  Native: {native}")
            print(f"  Region: {region}")
            print(f"  GlobalID: {entry.get('GlobalID', 'MISSING')}")

            # Check validation components
            schema_valid = validation_results.get("schema_valid", False)
            roundtrip_valid = validation_results.get("roundtrip_valid", False)
            coherence_valid = validation_results.get("coherence_valid", False)

            print(f"  Schema: {'✓' if schema_valid else '✗'}")
            print(f"  Roundtrip: {'✓' if roundtrip_valid else '✗'}")
            print(f"  Coherence: {'✓' if coherence_valid else '✗'}")

            # Show specific errors
            errors = validation_results.get("errors", [])
            if errors:
                print(f"  Errors ({len(errors)} total):")
                # Show first 3 errors
                for error in errors[:3]:
                    print(f"    - {error}")
                if len(errors) > 3:
                    print(f"    ... and {len(errors) - 3} more errors")

            # Check roundtrip score if available
            if "RoundtripScore" in entry:
                print(f"  Roundtrip Score: {entry['RoundtripScore']:.3f}")

    # Summary analysis
    print("\n=== FAILURE PATTERNS ===")

    # Count failure types
    schema_failures = 0
    roundtrip_failures = 0
    coherence_failures = 0

    for entry in results:
        if entry.get("ValidationStatus") != "VALID":
            validation_results = entry.get("ValidationResults", {})
            if not validation_results.get("schema_valid", False):
                schema_failures += 1
            if not validation_results.get("roundtrip_valid", False):
                roundtrip_failures += 1
            if not validation_results.get("coherence_valid", False):
                coherence_failures += 1

    print(f"Schema failures: {schema_failures}")
    print(f"Roundtrip failures: {roundtrip_failures} (threshold: ≥97%)")
    print(f"Coherence failures: {coherence_failures}")

    # Identify root causes
    print("\n=== ROOT CAUSES ===")
    if roundtrip_failures > 0:
        print(
            "1. ROUNDTRIP FAILURES: Non-Latin scripts (Russian, Arabic, Chinese) failing 97% threshold"
        )
        print("   - These need specialized transliteration tools")
        print("   - Current implementation uses simple heuristics")

    if schema_failures > 0:
        print("2. SCHEMA FAILURES: Missing or malformed GlobalIDs")
        print("   - Check if GlobalID generation is working for all entries")

    print("\n=== SOLUTION ===")
    print("To achieve 80%+ validation:")
    print("1. Fix roundtrip validation for CJK/Arabic/Cyrillic scripts")
    print("2. Ensure all entries have valid GlobalIDs")
    print("3. Consider relaxing roundtrip threshold for non-Latin scripts")


if __name__ == "__main__":
    asyncio.run(analyze_validation_failures())
