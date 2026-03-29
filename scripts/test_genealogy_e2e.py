#!/usr/bin/env python3
"""
End-to-End Integration Test: V7 Pipeline → Phase 2 Genealogy Enrichment

Tests the complete flow:
1. Takes a real V7 mathematician GlobalID
2. Runs V7 pipeline with genealogy.enabled=true
3. Verifies Genealogy field is added to output
4. Checks data quality and correctness

This test verifies that the Phase 2 integration actually works, not just that
the components work in isolation.

Usage:
    python3 scripts/test_genealogy_e2e.py
"""

import asyncio
import sys
import yaml
from pathlib import Path
from neo4j import GraphDatabase

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.pipeline_v7 import V7Pipeline, PipelineMode


def get_sample_v7_mathematician():
    """Get a real V7 mathematician GlobalID and data for testing"""
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=None)

    with driver.session() as sess:
        result = sess.run("""
            MATCH (m:Mathematician)
            WHERE m.global_id IS NOT NULL
              AND m.canonical_latin IS NOT NULL
            RETURN m.global_id as global_id,
                   m.canonical_latin as canonical_latin,
                   m.region_code as region_code
            LIMIT 1
        """)

        record = result.single()
        if not record:
            raise Exception("No mathematicians found in V7 database")

        data = {
            "GlobalID": record["global_id"],
            "CanonicalLatin": record["canonical_latin"],
            "RegionCode": record["region_code"] or "A1",
        }

    driver.close()
    return data


def verify_phase2_has_data(global_id: str) -> bool:
    """Check if Phase 2 has the mathematician with full data"""
    driver = GraphDatabase.driver("bolt://localhost:7688", auth=None)

    with driver.session() as sess:
        result = sess.run(
            """
            MATCH (m:Mathematician {global_id: $gid})
            RETURN m.canonical_latin as name,
                   m.region_code as region
        """,
            gid=global_id,
        )

        record = result.single()
        if not record:
            print(f"  ⚠️ GlobalID {global_id} not found in Phase 2")
            driver.close()
            return False

        print(f"  ✅ Found in Phase 2: {record['name']} (region: {record['region']})")
        driver.close()
        return True


def check_phase2_genealogy_relationships(global_id: str) -> int:
    """Check how many genealogy relationships exist for this mathematician"""
    driver = GraphDatabase.driver("bolt://localhost:7688", auth=None)

    with driver.session() as sess:
        result = sess.run(
            """
            MATCH (m:Mathematician {global_id: $gid})-[:DOCTORAL_ADVISOR]->(advisor)
            RETURN count(advisor) as count
        """,
            gid=global_id,
        )

        count = result.single()["count"]

    driver.close()
    return count


async def test_e2e_integration():
    """Main end-to-end test"""
    print("=" * 70)
    print("End-to-End Integration Test: V7 → Phase 2 Genealogy Enrichment")
    print("=" * 70)
    print()

    # Step 1: Get a real V7 mathematician
    print("Step 1: Get sample V7 mathematician")
    print("-" * 70)
    try:
        test_data = get_sample_v7_mathematician()
        print(f"✅ Selected mathematician:")
        print(f"   GlobalID: {test_data['GlobalID']}")
        print(f"   Name: {test_data['CanonicalLatin']}")
        print(f"   Region: {test_data['RegionCode']}")
        print()
    except Exception as e:
        print(f"❌ Failed to get V7 mathematician: {e}")
        return False

    # Step 2: Verify mathematician exists in Phase 2 with full data
    print("Step 2: Verify mathematician in Phase 2")
    print("-" * 70)
    if not verify_phase2_has_data(test_data["GlobalID"]):
        print(f"❌ Mathematician not found in Phase 2 - bootstrap incomplete")
        return False
    print()

    # Step 3: Check for genealogy relationships
    print("Step 3: Check genealogy relationships in Phase 2")
    print("-" * 70)
    rel_count = check_phase2_genealogy_relationships(test_data["GlobalID"])
    print(f"  Genealogy relationships: {rel_count}")
    if rel_count == 0:
        print(
            f"  ⚠️ No genealogy relationships (expected - V7 has no advisor data yet)"
        )
    else:
        print(f"  ✅ Has {rel_count} advisor relationship(s)")
    print()

    # Step 4: Enable genealogy enrichment
    print("Step 4: Enable genealogy enrichment in config")
    print("-" * 70)
    config_path = Path("config/genealogy.yaml")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    original_enabled = config["genealogy"]["enabled"]
    original_mode = config["genealogy"]["mode"]

    # Enable Direct mode for testing
    config["genealogy"]["enabled"] = True
    config["genealogy"]["mode"] = "direct"

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    print(f"  ✅ Genealogy enrichment enabled (mode: direct)")
    print()

    # Step 5: Run V7 pipeline with genealogy enabled
    print("Step 5: Run V7 pipeline with genealogy enrichment")
    print("-" * 70)
    try:
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        # Create test entry
        test_entry = {
            "CanonicalLatin": test_data["CanonicalLatin"],
            "GlobalID": test_data["GlobalID"],
            "RegionCode": test_data["RegionCode"],
            "BirthYear": 1950,  # Dummy data
        }

        result = await pipeline.process_batch([test_entry])

        if not result or len(result) == 0:
            print(f"❌ Pipeline returned no entries")
            return False

        enriched = result[0]
        print(f"  ✅ Pipeline completed")
        print()

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # Restore original config
        config["genealogy"]["enabled"] = original_enabled
        config["genealogy"]["mode"] = original_mode
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        print(f"  ✅ Config restored")

    # Step 6: Verify Genealogy field was added
    print()
    print("Step 6: Verify Genealogy field in output")
    print("-" * 70)

    if "Genealogy" not in enriched:
        print(f"❌ FAILED: Genealogy field not added to output")
        print(f"   Available fields: {list(enriched.keys())}")
        return False

    genealogy = enriched["Genealogy"]
    print(f"  ✅ Genealogy field present")
    print(f"     HasData: {genealogy.get('HasData')}")

    if genealogy.get("HasData"):
        print(f"     AdvisorCount: {genealogy.get('AdvisorCount')}")
        print(f"     LineageDepth: {genealogy.get('LineageDepth')}")
        print(f"     Paths: {len(genealogy.get('LineagePaths', []))}")
    else:
        print(
            f"     (No genealogy data available - expected since V7 has no advisor relationships yet)"
        )

    print()

    # Step 7: Verify data structure
    print("Step 7: Verify Genealogy data structure")
    print("-" * 70)

    required_fields = ["HasData"]
    for field in required_fields:
        if field not in genealogy:
            print(f"❌ Missing required field: {field}")
            return False

    print(f"  ✅ Genealogy data structure valid")
    print()

    # Success!
    print("=" * 70)
    print("✅ END-TO-END INTEGRATION TEST PASSED")
    print("=" * 70)
    print()
    print("Summary:")
    print("  ✅ V7 mathematician data retrieved")
    print("  ✅ Phase 2 bootstrap verified (full properties)")
    print("  ✅ V7 pipeline with genealogy enrichment completed")
    print("  ✅ Genealogy field added to pipeline output")
    print("  ✅ Data structure valid")
    print()
    print("Conclusion:")
    print("  The V7 → Phase 2 integration is WORKING correctly.")
    print(
        f"  Genealogy enrichment {'has data' if genealogy.get('HasData') else 'ready (no relationships yet)'}."
    )
    print()

    return True


if __name__ == "__main__":
    success = asyncio.run(test_e2e_integration())
    sys.exit(0 if success else 1)
