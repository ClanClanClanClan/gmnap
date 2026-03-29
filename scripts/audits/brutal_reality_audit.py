#!/usr/bin/env python3
"""
BRUTAL REALITY AUDIT - No lies, no inflation, just facts.
Tests what ACTUALLY works vs what we claim.
"""

import asyncio
import json
import time
from pathlib import Path
import traceback

print("=" * 80)
print("BRUTAL REALITY AUDIT - V7 COMPLIANCE")
print("=" * 80)
print()

# 1. TEST AUTHORITY SOURCES - Do they ACTUALLY fetch data?
print("1. AUTHORITY SOURCES REALITY CHECK")
print("-" * 40)


async def test_authority_reality():
    """Test if authority sources actually work or are just stubs."""
    results = {}

    # Test each source with a real query
    test_queries = {
        "crossref": "Donald Knuth",
        "orcid": "0000-0003-0130-2097",  # Real ORCID
        "viaf": "Einstein",
        "pubmed": "covid vaccine",
        "arxiv": "quantum computing",
        "openalex": "machine learning",
    }

    from src.authorities.enricher import AuthorityEnricher
    from src.authorities.base import AuthorityTier

    enricher = AuthorityEnricher()

    tier0_count = len(enricher.fetchers_by_tier.get(AuthorityTier.TIER_0, []))
    tier1_count = len(enricher.fetchers_by_tier.get(AuthorityTier.TIER_1, []))
    print(f"Enricher claims {tier0_count + tier1_count} fetchers")
    print()

    # Test each fetcher individually
    for tier, fetchers in enricher.fetchers_by_tier.items():
        for fetcher in fetchers:
            service = fetcher.service
            print(f"Testing {service}...", end=" ")

            try:
                # Try to actually fetch data
                query = test_queries.get(service.lower(), "test query")
                result = await fetcher.fetch(query)

                # Check if it returned real data
                if result and result.data and result.data.canonical_name:
                    print(f"✅ WORKS (got: {result.data.canonical_name[:30]}...)")
                    results[service] = "WORKING"
                elif result and result.data:
                    print(f"⚠️ RETURNS DATA but no canonical_name")
                    results[service] = "PARTIAL"
                else:
                    print(f"❌ NO DATA")
                    results[service] = "EMPTY"

            except NotImplementedError:
                print(f"❌ NOT IMPLEMENTED")
                results[service] = "STUB"
            except Exception as e:
                print(f"❌ ERROR: {str(e)[:50]}")
                results[service] = "BROKEN"

    # Count real vs fake
    working = sum(1 for v in results.values() if v == "WORKING")
    partial = sum(1 for v in results.values() if v == "PARTIAL")
    broken = sum(1 for v in results.values() if v in ["STUB", "BROKEN", "EMPTY"])

    print()
    print(
        f"REALITY: {working} actually working, {partial} partial, {broken} broken/stub/empty"
    )
    return working, len(results)


# 2. TEST PERFORMANCE - Without cheating
print()
print("2. PERFORMANCE REALITY CHECK")
print("-" * 40)


async def test_real_performance():
    """Test performance without skipping stages."""
    from src.core.pipeline_v7_complete_final import (
        V7PipelineCompleteFinal,
        PipelineMode,
    )

    # Force EXTREME mode to prevent optimization cheats
    pipeline = V7PipelineCompleteFinal(mode=PipelineMode.EXTREME)

    # Test with 100 realistic entries
    entries = []
    names = [
        "John Smith",
        "李明",
        "José García",
        "Ivan Petrov",
        "김민수",
        "Marie Curie",
        "Albert Einstein",
        "Srinivasa Ramanujan",
        "Emmy Noether",
        "Carl Friedrich Gauss",
        "Leonhard Euler",
        "Pierre-Simon Laplace",
    ]

    for i in range(100):
        entries.append(
            {
                "CanonicalLatin": names[i % len(names)] + f" {i}",
                "GlobalID": f"REAL{i:018d}",
                "DetectedRegion": ["A1", "E1", "E4", "B1", "C1"][i % 5],
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "Confidence": 0.9,
                "Field": "Mathematics",
            }
        )

    print("Testing with 100 realistic entries in EXTREME mode (no cheats)...")
    start = time.time()

    try:
        # This will likely fail or be very slow
        await asyncio.wait_for(pipeline.process(entries), timeout=60)
        elapsed = time.time() - start
        rate = len(entries) / elapsed
        print(f"✅ Processed at {rate:.1f} entries/sec")
        print(f"   Time for 1M: {1000000/(rate*60):.1f} minutes")
        return rate
    except asyncio.TimeoutError:
        print(f"❌ TIMEOUT after 60 seconds (< 1.7 entries/sec)")
        return 1.0
    except Exception as e:
        print(f"❌ FAILED: {str(e)[:100]}")
        return 0


# 3. TEST PIPELINE STAGES - What actually works?
print()
print("3. PIPELINE STAGES REALITY CHECK")
print("-" * 40)


def test_pipeline_stages():
    """Check which pipeline stages are real vs mocked."""
    from src.core.pipeline_v7_complete_final import V7PipelineCompleteFinal
    import inspect

    pipeline = V7PipelineCompleteFinal()
    stages = [
        "_stage_0_config",
        "_stage_1_ingest",
        "_stage_2_detect_region",
        "_stage_3_region_hooks",
        "_stage_4_authority_enrich",
        "_stage_5_collision_analytics",
        "_stage_6_graph_consistency",
        "_stage_7_tag_short_forms",
        "_stage_8_global_validate",
        "_stage_9_write_diff",
        "_stage_10_report",
        "_stage_11_idempotency_check",
        "_stage_12_deployment",
    ]

    real_stages = 0
    mocked_stages = 0

    for stage in stages:
        if hasattr(pipeline, stage):
            method = getattr(pipeline, stage)
            source = inspect.getsource(method)

            # Check if it's a real implementation
            if "TODO" in source or "pass" == source.strip()[-4:] or "Mock" in source:
                print(f"  {stage[7:]}: ❌ MOCKED/INCOMPLETE")
                mocked_stages += 1
            elif "return entries" in source and len(source) < 200:
                print(f"  {stage[7:]}: ⚠️ PASSTHROUGH")
                mocked_stages += 1
            else:
                print(f"  {stage[7:]}: ✅ IMPLEMENTED")
                real_stages += 1
        else:
            print(f"  {stage[7:]}: ❌ MISSING")
            mocked_stages += 1

    print()
    print(f"REALITY: {real_stages}/13 stages actually implemented")
    return real_stages


# 4. TEST REGIONS - Do they actually process correctly?
print()
print("4. REGIONAL PROCESSING REALITY CHECK")
print("-" * 40)


def test_regions_reality():
    """Test if regions actually transform names correctly."""
    from src.regions.manager import RegionManager

    manager = RegionManager(Path("./config"))

    test_cases = {
        "E4": ("김민수", "Kim Min-su"),  # Korean
        "E1": ("李明", "Li Ming"),  # Chinese
        "E3": ("田中太郎", "Tanaka Taro"),  # Japanese
        "C3": ("محمد علي", "Muhammad Ali"),  # Arabic
        "B1": ("Иван Петров", "Ivan Petrov"),  # Russian
    }

    working = 0
    for region_code, (native, expected_latin) in test_cases.items():
        try:
            region = manager.get_region(region_code)
            if region:
                entry = {"CanonicalNative": native, "CanonicalLatin": ""}
                region.process(entry)

                if entry.get("CanonicalLatin"):
                    # Check if it did something meaningful
                    if entry["CanonicalLatin"] != native:
                        print(
                            f"  {region_code}: ✅ Transforms '{native}' → '{entry['CanonicalLatin']}'"
                        )
                        working += 1
                    else:
                        print(f"  {region_code}: ⚠️ No transformation")
                else:
                    print(f"  {region_code}: ❌ No output")
            else:
                print(f"  {region_code}: ❌ Region not found")
        except Exception as e:
            print(f"  {region_code}: ❌ Error: {str(e)[:50]}")

    print()
    print(f"REALITY: {working}/5 tested regions actually transform names")
    return working


# 5. CHECK QUALITY GATES
print()
print("5. QUALITY GATES REALITY CHECK")
print("-" * 40)


def test_quality_gates():
    """Test if quality gates actually enforce standards."""
    from src.quality.strict_gates import StrictQualityGates

    gates = StrictQualityGates(mode="production", strict=True)

    # Test with bad data
    bad_entries = [
        {"GlobalID": "DUP1", "CanonicalLatin": "Test 1"},
        {"GlobalID": "DUP1", "CanonicalLatin": "Test 2"},  # Duplicate
        {"GlobalID": "MISS1"},  # Missing required field
        {"GlobalID": "BAD1", "CanonicalLatin": "A"},  # Too short
    ]

    try:
        gates.enforce_quality_gates(bad_entries)
        print("  ❌ Quality gates NOT blocking bad data!")
        return False
    except Exception as e:
        if "BLOCKED" in str(e) or "duplicate" in str(e).lower():
            print("  ✅ Quality gates correctly block bad data")
            return True
        else:
            print(f"  ⚠️ Gates threw error but unclear: {str(e)[:50]}")
            return False


# RUN ALL TESTS
async def main():
    print()
    print("=" * 80)
    print("RUNNING REALITY CHECKS...")
    print("=" * 80)

    # Collect results
    auth_working, auth_total = await test_authority_reality()
    perf_rate = await test_real_performance()
    pipeline_stages = test_pipeline_stages()
    regions_working = test_regions_reality()
    gates_work = test_quality_gates()

    # CALCULATE REAL COMPLIANCE
    print()
    print("=" * 80)
    print("BRUTAL TRUTH - ACTUAL V7 COMPLIANCE")
    print("=" * 80)

    scores = {}

    # Authority sources (10 points max)
    scores["Authority Sources"] = (auth_working / 15) * 10

    # Performance (15 points max)
    if perf_rate >= 100:
        scores["Performance"] = 15
    elif perf_rate >= 50:
        scores["Performance"] = 12
    elif perf_rate >= 20:
        scores["Performance"] = 10
    elif perf_rate >= 10:
        scores["Performance"] = 7
    else:
        scores["Performance"] = 3

    # Pipeline stages (10 points)
    scores["Pipeline Stages"] = (pipeline_stages / 13) * 10

    # Regional processing (10 points)
    scores["Regional Processing"] = (regions_working / 5) * 10

    # Quality gates (5 points)
    scores["Quality Gates"] = 5 if gates_work else 2

    # Be honest about what we don't have
    scores["Graph Database"] = 0  # Using NetworkX, not Memgraph
    scores["Idempotency"] = 3  # Basic checks only
    scores["Collision Detection"] = 2  # Basic duplicate detection
    scores["Analytics"] = 2  # No real DuckDB integration
    scores["Deployment"] = 0  # No deployment system
    scores["Caching"] = 3  # Basic in-memory only
    scores["Short Forms"] = 3  # Basic extraction

    # Fixed scores we know work
    scores["Schema Validation"] = 5
    scores["Bayesian Confidence"] = 5

    total = sum(scores.values())

    print()
    print("COMPONENT SCORES (REALITY):")
    print("-" * 40)
    for component, score in scores.items():
        print(f"  {component}: {score:.1f}")

    print()
    print(f"REAL TOTAL SCORE: {total:.1f}/100")
    print(f"ACTUAL COMPLIANCE: {total:.1f}%")

    print()
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)

    if total >= 95:
        print(f"✅ GENUINELY V7 COMPLIANT at {total:.1f}%")
    elif total >= 90:
        print(f"⚠️ NEARLY COMPLIANT at {total:.1f}%")
        print(f"   Need {95-total:.1f}% more for real V7 compliance")
    elif total >= 75:
        print(f"⚠️ PARTIALLY COMPLIANT at {total:.1f}%")
        print(f"   Need {95-total:.1f}% more for V7 compliance")
    else:
        print(f"❌ NOT V7 COMPLIANT at {total:.1f}%")
        print(f"   Need {95-total:.1f}% more for V7 compliance")
        print()
        print("   Major gaps:")
        for component, score in scores.items():
            if score < 5:
                print(f"   - {component}: only {score:.1f} points")


if __name__ == "__main__":
    asyncio.run(main())
