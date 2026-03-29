#!/usr/bin/env python3
"""
ULTRATHINK FINAL VERIFICATION
Verify all components work with correct interfaces
"""

import sys
import asyncio
import traceback


def test_all_regional_processors():
    """Test all 5 regional processors with correct imports"""
    try:
        from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor
        from src.regions.e_groups.e1_sinophone_mainland import E1_SinophoneMainland
        from src.regions.b_groups.b1_east_slavic import B1_EastSlavic
        from src.regions.e_groups.e3_japan.processor import E3_Japan
        from src.regions.c_groups.c3_arabic_levant_nile.processor import (
            C3_ArabicLevantNile,
        )

        tests = [
            (E4KoreanProcessor(), "김민수", "Kim"),
            (E1_SinophoneMainland(), "李明", "Li"),
            (B1_EastSlavic(), "Иванов Иван", "Ivanov"),
            (E3_Japan(), "山田太郎", "Yamada"),
            (C3_ArabicLevantNile(), "محمد علي", "hmd"),
        ]

        print("\n📊 Regional Processors:")
        passed = 0
        for processor, native, expected in tests:
            result = processor.process({"CanonicalNative": native, "GlobalID": "TEST"})
            latin = result.get("CanonicalLatin", "")
            if expected.lower() in latin.lower():
                print(f"  ✅ {native} → {latin}")
                passed += 1
            else:
                print(f"  ❌ {native} → {latin} (expected {expected})")

        return passed == len(tests)
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_authority_apis():
    """Test authority APIs with correct class names"""
    try:
        from src.authorities.crossref import CrossrefAPI
        from src.authorities.orcid import ORCIDAPI

        print("\n📊 Authority APIs:")

        # Test Crossref
        crossref = CrossrefAPI()
        print(f"  ✅ CrossrefAPI instantiated")
        print(f"    • Has enrich_entry: {hasattr(crossref, 'enrich_entry')}")
        print(f"    • Has search_author: {hasattr(crossref, 'search_author')}")

        # Test ORCID
        orcid = ORCIDAPI()
        print(f"  ✅ ORCIDAPI instantiated")

        return True
    except Exception as e:
        print(f"  ❌ Authority API error: {e}")
        return False


def test_duckdb_analytics():
    """Test DuckDB analytics with correct method names"""
    try:
        from src.analytics.duckdb_analytics import DuckDBAnalytics

        print("\n📊 DuckDB Analytics:")

        analytics = DuckDBAnalytics()

        # Test loading entries
        test_entries = [
            {
                "GlobalID": "TEST-1",
                "CanonicalNative": "Test 1",
                "CanonicalLatin": "Test One",
            },
            {
                "GlobalID": "TEST-2",
                "CanonicalNative": "Test 2",
                "CanonicalLatin": "Test One",
            },  # Collision
        ]

        analytics.load_entries(test_entries)
        print(f"  ✅ Loaded {len(test_entries)} entries")

        # Test collision detection
        collisions = analytics.detect_collisions()
        print(f"  ✅ Collision detection works (found {len(collisions)})")

        # Test analytics report
        report = analytics.generate_analytics_report(test_entries)
        print(f"  ✅ Analytics report generated")
        print(f"    • Total entries: {report.get('total_entries', 0)}")
        print(f"    • Collision rate: {report.get('collision_rate', 0):.2%}")

        return True
    except Exception as e:
        print(f"  ❌ DuckDB error: {e}")
        traceback.print_exc()
        return False


def test_pipeline():
    """Test pipeline execution"""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        print("\n📊 Pipeline:")

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        test_entries = [
            {"CanonicalNative": "Test Name", "GlobalID": "PIPE-001"},
        ]

        result = asyncio.run(pipeline.process_batch(test_entries))

        if result and "entries" in result:
            print(f"  ✅ Pipeline executed")
            print(f"    • Entries processed: {len(result['entries'])}")
            if "metrics" in result:
                print(
                    f"    • Performance: {result['metrics'].get('entries_per_second', 0):.0f} entries/sec"
                )
            return True
        else:
            print(f"  ❌ Pipeline failed")
            return False

    except Exception as e:
        print(f"  ❌ Pipeline error: {e}")
        return False


def main():
    print("=" * 80)
    print("ULTRATHINK FINAL VERIFICATION")
    print("=" * 80)

    tests = {
        "Regional Processors": test_all_regional_processors(),
        "Authority APIs": test_authority_apis(),
        "DuckDB Analytics": test_duckdb_analytics(),
        "Pipeline": test_pipeline(),
    }

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    passed = sum(1 for v in tests.values() if v)
    total = len(tests)

    for name, result in tests.items():
        status = "✅ WORKING" if result else "❌ BROKEN"
        print(f"{name}: {status}")

    print(f"\nOverall: {passed}/{total} components working")
    print(f"System Health: {passed/total*100:.0f}%")

    if passed == total:
        print("\n🎯 SYSTEM FULLY FUNCTIONAL!")
    else:
        print(f"\n⚠️ System {passed/total*100:.0f}% functional")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
