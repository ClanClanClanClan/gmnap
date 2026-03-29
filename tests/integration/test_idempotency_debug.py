import pytest

#!/usr/bin/env python3
"""
Quick idempotency test to debug non-deterministic behavior.
"""

import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os

os.environ["GMNAP_OFFLINE"] = "1"
from src.core.pipeline_v7 import V7Pipeline


async def test_idempotency():
    # Create a simple test entry
    test_entry = {
        "CanonicalLatin": "Smith, John",
        "CanonicalNative": "Smith, John",
        "BirthYear": 1975,
        "Region": "A1",
        "CountryCodes": ["US"],
        "UpdatedAt": "2025-01-01T00:00:00Z",
        "LanguageOfPublication": ["en"],
        "FamilyNameType": "surname",
        "Gender": "unspecified",
        "Confidence": 95,
        "Historic": False,
        "GDPR_DATA": False,
    }

    pipeline = V7Pipeline()

    # Process through stages 1-3, 5-8 (skip Stage 4 authority enrichment)
    result1 = await pipeline._stage_1_ingest([test_entry])
    result1 = await pipeline._stage_2_detect_region(result1)
    result1 = await pipeline._stage_3_region_hooks(result1)
    result1 = await pipeline._stage_5_collision_analytics(result1)
    result1 = await pipeline._stage_6_graph_consistency(result1)
    result1 = await pipeline._stage_7_tag_short_forms(result1)
    result1 = await pipeline._stage_8_global_validate(result1)
    result1_clean = pipeline._clean_entry_for_comparison(result1[0])

    # Process again with same data
    result2 = await pipeline._stage_1_ingest([test_entry])
    result2 = await pipeline._stage_2_detect_region(result2)
    result2 = await pipeline._stage_3_region_hooks(result2)
    result2 = await pipeline._stage_5_collision_analytics(result2)
    result2 = await pipeline._stage_6_graph_consistency(result2)
    result2 = await pipeline._stage_7_tag_short_forms(result2)
    result2 = await pipeline._stage_8_global_validate(result2)
    result2_clean = pipeline._clean_entry_for_comparison(result2[0])

    # Compare cleaned results
    if result1_clean == result2_clean:
        print("PASS Cleaned results are identical")
    else:
        print("FAIL Even cleaned results differ")
        print("Keys in result1:", sorted(result1_clean.keys()))
        print("Keys in result2:", sorted(result2_clean.keys()))

        # Find different keys
        for key in result1_clean:
            if key not in result2_clean:
                print(f"Missing in result2: {key}")
            elif result1_clean[key] != result2_clean[key]:
                print(f"Different values for {key}:")
                print(f"  Result1: {result1_clean[key]}")
                print(f"  Result2: {result2_clean[key]}")


if __name__ == "__main__":
    asyncio.run(test_idempotency())
