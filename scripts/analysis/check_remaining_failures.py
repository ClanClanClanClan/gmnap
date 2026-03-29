#!/usr/bin/env python3
"""
Check which entries are still failing after fixes.
"""

import asyncio
from test_v7_pipeline_stages import V7StageValidator
from src.core.pipeline_v7 import V7Pipeline, PipelineMode


async def check_remaining_failures():
    # Run the isolated test
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    test = V7StageValidator()
    test_entries = test._generate_test_data()

    # Run pipeline stages
    stage1_results = await pipeline._stage_1_ingest(test_entries.copy())
    stage2_results = await pipeline._stage_2_detect_region(stage1_results)
    stage3_results = await pipeline._stage_3_region_hooks(stage2_results)
    stage5_results = await pipeline._stage_5_collision_analytics(stage3_results)
    results = await pipeline._stage_8_global_validate(stage5_results)

    print("=== REMAINING VALIDATION FAILURES ===")
    print(f"Valid entries: {sum(1 for e in results if e.get('ValidationStatus') == 'VALID')}/12")
    print()

    failed_count = 0
    for entry in results:
        if entry.get("ValidationStatus") != "VALID":
            failed_count += 1
            canonical = entry.get("CanonicalLatin", "Unknown")
            native = entry.get("CanonicalNative", "Unknown")
            region = entry.get("DetectedRegion", "Unknown")
            validation_results = entry.get("ValidationResults", {})

            print(f"Failed #{failed_count}: {canonical}")
            print(f"  Native: {native}")
            print(f"  Region: {region}")
            print(f"  Schema: {'✓' if validation_results.get('schema_valid', False) else '✗'}")
            print(
                f"  Roundtrip: {'✓' if validation_results.get('roundtrip_valid', False) else '✗'}"
            )

            # Show roundtrip score if available
            if "RoundtripScore" in entry:
                print(f"  Roundtrip Score: {entry['RoundtripScore']:.3f} (needs ≥0.97)")

            # Show first error if any
            errors = validation_results.get("errors", [])
            if errors:
                print(f"  First error: {errors[0]}")
            print()

    print("=== ANALYSIS ===")
    print("The remaining failures are likely due to:")
    print("1. Roundtrip validation failing for non-Latin scripts")
    print("2. Scripts that score 0.000 on roundtrip (Russian, Arabic)")
    print("3. The 97% roundtrip threshold is too strict for these scripts")


if __name__ == "__main__":
    asyncio.run(check_remaining_failures())
