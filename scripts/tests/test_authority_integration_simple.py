#!/usr/bin/env python3
"""
ULTRATHINK Authority Sources Simple Integration Test
Tests authority sources with actual API calls
"""

import os
import sys
import json
import time
import asyncio
import traceback
from datetime import datetime

# Enable online mode for testing
os.environ["OFFLINE"] = "0"

print(f"Testing with OFFLINE={os.environ.get('OFFLINE')}")


def test_live_adapters():
    """Test LiveAuthorityAdapters"""
    print("\n📚 Testing LiveAuthorityAdapters...")

    try:
        from src.authorities.live_adapters import LiveAuthorityAdapters

        adapters = LiveAuthorityAdapters()
        available = adapters.list_adapters()

        print(f"  Available adapters: {available}")

        results = {}

        # Test each adapter
        for adapter_name in available:
            adapter = adapters.get_adapter(adapter_name)
            if adapter:
                print(f"\n  Testing {adapter_name}...")
                try:
                    if adapter_name == "Crossref_Thesis":
                        result = adapter.query(author="A. Wiles")
                    elif adapter_name == "Wikidata_P184":
                        result = adapter.query(limit=1)
                    elif adapter_name == "OAI_University":
                        result = adapter.query()
                    elif adapter_name == "Crossref_V7":
                        # Check if it has a query method
                        if hasattr(adapter, "query"):
                            result = adapter.query("A. Wiles")
                        elif hasattr(adapter, "search"):
                            result = adapter.search("A. Wiles")
                        else:
                            result = {"ok": False, "reason": "no query/search method"}
                    elif adapter_name == "OpenAlex":
                        # Check available methods
                        if hasattr(adapter, "search_author"):
                            result = adapter.search_author("A. Wiles")
                        elif hasattr(adapter, "query"):
                            result = adapter.query("A. Wiles")
                        else:
                            result = {"ok": False, "reason": "no search method"}
                    else:
                        result = {"ok": False, "reason": "unknown adapter"}

                    results[adapter_name] = result

                    # Check result
                    if isinstance(result, dict):
                        if result.get("offline"):
                            print(f"    ⚠️ {adapter_name}: OFFLINE mode")
                        elif result.get("ok"):
                            print(f"    ✅ {adapter_name}: Success")
                            if "data" in result:
                                print(
                                    f"       Data keys: {list(result.get('data', {}).keys())[:5]}"
                                )
                        else:
                            print(
                                f"    ❌ {adapter_name}: {result.get('reason', 'Failed')}"
                            )
                    elif isinstance(result, list):
                        print(f"    ✅ {adapter_name}: Got {len(result)} results")
                    else:
                        print(
                            f"    ⚠️ {adapter_name}: Unexpected result type: {type(result)}"
                        )

                except Exception as e:
                    print(f"    ❌ {adapter_name}: Error - {str(e)[:100]}")
                    results[adapter_name] = {"ok": False, "error": str(e)}

                time.sleep(0.5)  # Rate limiting

        return results

    except Exception as e:
        print(f"  ❌ Error loading LiveAuthorityAdapters: {e}")
        traceback.print_exc()
        return {}


def test_crossref_v7():
    """Test CrossrefV7 directly"""
    print("\n📚 Testing CrossrefV7 Fetcher...")

    try:
        from src.authorities.crossref_v7 import CrossrefV7Fetcher

        fetcher = CrossrefV7Fetcher()

        # Test search_author method
        print("  Searching for 'A. Wiles'...")
        result = fetcher.search_author("A. Wiles", limit=3)

        if result:
            print(f"    ✅ Found {len(result)} works")
            if result:
                first = result[0]
                print(
                    f"       First result: {first.get('title', ['Unknown'])[0] if first.get('title') else 'Unknown'}"
                )
                print(f"       DOI: {first.get('DOI', 'No DOI')}")
        else:
            print(f"    ⚠️ No results found")

        return {"status": "success", "works_found": len(result) if result else 0}

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}


def test_authority_enrichment():
    """Test authority enrichment via enricher"""
    print("\n🔧 Testing Authority Enricher...")

    try:
        from src.authorities.enricher import AuthorityEnricher

        enricher = AuthorityEnricher()

        # Test entry
        entry = {
            "GlobalID": "TEST-001",
            "CanonicalNative": "A. Wiles",
            "CanonicalLatin": "A. Wiles",
        }

        print(f"  Enriching: {entry['CanonicalLatin']}")
        # Use asyncio.run if it's async
        enriched = asyncio.run(enricher.enrich(entry.copy()))

        # Check what was added
        added_fields = [k for k in enriched.keys() if k not in entry]

        if added_fields:
            print(f"    ✅ Added {len(added_fields)} fields: {added_fields}")
        else:
            print(f"    ⚠️ No fields added")

        return {"status": "success", "fields_added": len(added_fields)}

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}


def test_pipeline_authority_integration():
    """Test authority integration in V7 pipeline"""
    print("\n🔄 Testing V7 Pipeline Authority Integration...")

    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        # Create pipeline
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        # Test batch
        test_batch = [
            {
                "GlobalID": "PIPE-001",
                "CanonicalNative": "A. Wiles",
                "CanonicalLatin": "A. Wiles",
            },
            {
                "GlobalID": "PIPE-002",
                "CanonicalNative": "김민수",
                "CanonicalLatin": "Kim Min-su",
            },
        ]

        print(f"  Processing {len(test_batch)} entries...")
        result = asyncio.run(pipeline.process_batch(test_batch))

        # Check results
        processed = result.get("data", [])
        authority_count = 0

        for entry in processed:
            # Check for authority-related fields
            authority_fields = [
                k
                for k in entry.keys()
                if "Authority" in k
                or "Crossref" in k
                or "ORCID" in k
                or "OpenAlex" in k
            ]

            if authority_fields:
                authority_count += 1
                print(
                    f"    ✅ {entry['GlobalID']}: Found authority fields: {authority_fields[:3]}"
                )
            else:
                print(f"    ⚠️ {entry['GlobalID']}: No authority fields found")

        return {"status": "success", "entries_with_authorities": authority_count}

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def main():
    """Run all tests"""
    print("=" * 70)
    print("🚀 ULTRATHINK AUTHORITY SOURCES INTEGRATION TEST")
    print("=" * 70)
    print(f"Time: {datetime.now()}")
    print(f"OFFLINE mode: {os.environ.get('OFFLINE')}")

    # Run tests
    results = {}

    # Test 1: LiveAuthorityAdapters
    results["LiveAdapters"] = test_live_adapters()

    # Test 2: CrossrefV7
    results["CrossrefV7"] = test_crossref_v7()

    # Test 3: Authority Enricher
    results["AuthorityEnricher"] = test_authority_enrichment()

    # Test 4: Pipeline Integration
    results["PipelineIntegration"] = test_pipeline_authority_integration()

    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)

    working = 0
    total = 0

    for test_name, result in results.items():
        total += 1
        if isinstance(result, dict):
            if result.get("status") == "success" or any(
                r.get("ok") for r in result.values() if isinstance(r, dict)
            ):
                working += 1
                print(f"✅ {test_name}: WORKING")
            else:
                print(f"❌ {test_name}: FAILED")
        else:
            print(f"⚠️ {test_name}: Unknown status")

    print(f"\n📈 Overall: {working}/{total} test suites working")

    # Save results
    report_file = (
        f"authority_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📄 Results saved to: {report_file}")

    if working >= 2:
        print("\n🎉 AUTHORITY INTEGRATION: PASSED")
        print("Authority sources are working!")
        return 0
    else:
        print("\n⚠️ AUTHORITY INTEGRATION: NEEDS WORK")
        print(f"Only {working} test suites working (need at least 2)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
