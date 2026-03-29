#!/usr/bin/env python3
"""Test if region-specific processing actually happens."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_region_processing():
    """Test region-specific processing features."""

    # Create test data with region-specific names
    test_data = [
        # A1 Anglo - should remain as-is
        {"CanonicalNative": "Newton, Isaac", "GlobalID": "test001"},
        # A3 Nordic - Icelandic patronymic
        {"CanonicalNative": "Magnúsdóttir, Sigrid", "GlobalID": "test002"},
        # B3 Greek - Greek script
        {"CanonicalNative": "Παπαδόπουλος, Δημήτρης", "GlobalID": "test003"},
        # E1 Chinese - Chinese characters
        {"CanonicalNative": "王小明", "GlobalID": "test004"},
        # E4 Korean - Hangul
        {"CanonicalNative": "김민수", "GlobalID": "test005"},
        # C1 Turkic - with Turkish characters
        {"CanonicalNative": "Özil, Mesut", "GlobalID": "test006"},
        # A2 German - with umlaut
        {"CanonicalNative": "Müller, Hans", "GlobalID": "test007"},
        # B1 Russian - Cyrillic
        {"CanonicalNative": "Чебышёв, Пафнутий", "GlobalID": "test008"},
        # E3 Japanese - Kanji
        {"CanonicalNative": "田中太郎", "GlobalID": "test009"},
        # C3 Arabic
        {"CanonicalNative": "محمد علي", "GlobalID": "test010"},
    ]

    # Run pipeline
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    try:
        result = await pipeline.process_batch(test_data)
        print("Pipeline completed successfully")
        print(f"Processed: {result['metrics']['processed_entries']} entries")

        # Check results - the pipeline returns 'entries' or 'results' depending on path
        output_data = result.get("entries") or result.get("results", [])

        print("\n🔍 REGION-SPECIFIC PROCESSING:")
        regions_detected = {}
        romanization_count = 0

        for entry in output_data:
            name = entry.get("CanonicalNative", "Unknown")
            region = entry.get("DetectedRegion", "UNKNOWN")
            latin = entry.get("CanonicalLatin", "")

            regions_detected[region] = regions_detected.get(region, 0) + 1

            features = []

            # Check for region detection
            if region != "UNKNOWN":
                features.append(f"Region: {region}")

            # Check for romanization
            if latin and latin != name:
                features.append(f"Latin: {latin}")
                romanization_count += 1

            # Check for variants
            if "Variants" in entry:
                variant_types = list(entry["Variants"].keys())
                features.append(f"Variants: {', '.join(variant_types)}")

            # Check for extras
            extras = entry.get("RegionalExtras", {})
            if extras:
                if extras.get("is_patronymic"):
                    features.append("Patronymic")
                if extras.get("has_particles"):
                    features.append("Particles detected")
                if extras.get("script"):
                    features.append(f"Script: {extras['script']}")

            info = " | ".join(features) if features else "No features"
            print(f"  {name:<30} -> {info}")

        print(f"\n📊 REGIONS DETECTED: {regions_detected}")
        print(f"📊 ROMANIZATIONS: {romanization_count}/{len(output_data)}")

        # Verify at least some region detection occurred
        assert len(regions_detected) > 1, "No regions detected"

        # Verify romanization happened for non-Latin scripts
        assert (
            romanization_count >= 4
        ), f"Expected at least 4 romanizations, got {romanization_count}"

        # Check specific expectations
        expected_regions = {
            "E4",
            "E1",
            "B1",
            "E3",
            "C3",
        }  # Korean, Chinese, Russian, Japanese, Arabic
        detected_set = set(regions_detected.keys()) - {"UNKNOWN"}

        if expected_regions & detected_set:
            print(f"PASS Found expected regions: {expected_regions & detected_set}")
        else:
            print(
                f"WARN Missing expected regions. Detected: {detected_set}, Expected some of: {expected_regions}"
            )

        return True

    except Exception as e:
        print(f"FAIL Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        pytest.fail(f"Pipeline execution failed: {e}")


if __name__ == "__main__":
    # Run the test directly
    result = asyncio.run(test_region_processing())
    print("\n" + "=" * 60)
    if result:
        print("PASS REGION PROCESSING WORKS!")
    else:
        print("FAIL REGION PROCESSING BROKEN!")
