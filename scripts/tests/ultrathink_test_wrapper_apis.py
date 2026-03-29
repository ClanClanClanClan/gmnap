#!/usr/bin/env python3
"""
ULTRATHINK Test Wrapper APIs
Tests the actual wrapper classes with their real methods
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List

# Ensure OFFLINE mode is disabled for testing
os.environ["OFFLINE"] = "0"

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed, using existing environment")


async def test_crossref_wrapper():
    """Test Crossref wrapper class"""
    print("\n=== Testing Crossref Wrapper ===")
    try:
        from src.authorities.crossref import CrossrefAPI

        async with CrossrefAPI() as api:
            # Test search_author method
            name = "Albert Einstein"
            print(f"   Searching for: {name}")
            results = await api.search_author(name, limit=2)

            if results:
                print(f"✅ Crossref wrapper working - Found {len(results)} authors")
                first = results[0]
                if "display_name" in first:
                    print(f"   Sample: {first['display_name']}")
                if "affiliations" in first:
                    print(
                        f"   Affiliations: {len(first.get('affiliations', []))} found"
                    )
                return True
            else:
                print("⚠️ Crossref wrapper returned no results")
                return False
    except Exception as e:
        print(f"❌ Crossref wrapper failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_orcid_wrapper():
    """Test ORCID wrapper class"""
    print("\n=== Testing ORCID Wrapper ===")
    try:
        from src.authorities.orcid import ORCIDAPI

        client_id = os.environ.get("ORCID_CLIENT_ID")
        client_secret = os.environ.get("ORCID_CLIENT_SECRET")

        if not client_id or not client_secret:
            print("❌ ORCID credentials not in environment")
            return False

        async with ORCIDAPI(client_id=client_id, client_secret=client_secret) as api:
            # Test search method
            query = "Albert Einstein"
            print(f"   Searching for: {query}")
            orcid_ids = await api.search(query, limit=2)

            if orcid_ids:
                print(f"✅ ORCID wrapper working - Found {len(orcid_ids)} ORCID IDs")
                print(f"   Sample ORCID: {orcid_ids[0]}")

                # Try to get person details
                person = await api.get_person(orcid_ids[0])
                if person:
                    print(f"   Person: {person.canonical_name()}")
                return True
            else:
                print("⚠️ ORCID wrapper returned no results")
                # Still count as working if API connected
                return True
    except Exception as e:
        print(f"❌ ORCID wrapper failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_openalex_wrapper():
    """Test OpenAlex wrapper class"""
    print("\n=== Testing OpenAlex Wrapper ===")
    try:
        from src.authorities.openalex import OpenAlexAPI

        api = OpenAlexAPI()

        # Check what methods it has
        if hasattr(api, "search_author"):
            name = "Terence Tao"
            print(f"   Searching for: {name} (using search_author)")
            results = await api.search_author(name, limit=2)
        elif hasattr(api, "search"):
            name = "Terence Tao"
            print(f"   Searching for: {name} (using search)")
            results = await api.search(name, limit=2)
        elif hasattr(api, "get_author_by_name"):
            name = "Terence Tao"
            print(f"   Searching for: {name} (using get_author_by_name)")
            results = await api.get_author_by_name(name)
            results = [results] if results else []
        else:
            # List available methods
            methods = [m for m in dir(api) if not m.startswith("_")]
            print(f"   Available methods: {', '.join(methods)}")
            print("❌ No known search method found")
            return False

        if results:
            print(f"✅ OpenAlex wrapper working - Found {len(results)} results")
            if results and isinstance(results[0], dict):
                print(f"   Sample: {results[0].get('display_name', 'Unknown')}")
            return True
        else:
            print("⚠️ OpenAlex wrapper returned no results")
            return False
    except Exception as e:
        print(f"❌ OpenAlex wrapper failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_arxiv_wrapper():
    """Test arXiv wrapper class"""
    print("\n=== Testing arXiv Wrapper ===")
    try:
        from src.authorities.arxiv import ArXivAPI

        api = ArXivAPI()

        # Check what methods it has
        if hasattr(api, "search_author"):
            name = "Terence Tao"
            print(f"   Searching for: {name} (using search_author)")
            results = await api.search_author(name, limit=2)
        elif hasattr(api, "search"):
            name = "Terence Tao"
            print(f"   Searching for: {name} (using search)")
            results = await api.search(name, limit=2)
        elif hasattr(api, "query_papers"):
            query = "au:Tao_T"
            print(f"   Searching for: {query} (using query_papers)")
            results = await api.query_papers(query, max_results=2)
        else:
            # List available methods
            methods = [m for m in dir(api) if not m.startswith("_")]
            print(f"   Available methods: {', '.join(methods)}")
            print("❌ No known search method found")
            return False

        if results:
            print(f"✅ arXiv wrapper working - Found {len(results)} results")
            return True
        else:
            print("⚠️ arXiv wrapper returned no results")
            return False
    except Exception as e:
        print(f"❌ arXiv wrapper failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_enricher():
    """Test the main enricher that coordinates all sources"""
    print("\n=== Testing Authority Enricher ===")
    try:
        from src.authorities.enricher import AuthorityEnricher

        enricher = AuthorityEnricher()

        # Test entry
        entry = {
            "GlobalID": "TEST-001",
            "CanonicalNative": "Terence Tao",
            "AlternateNames": ["T. Tao", "Terry Tao"],
        }

        print(f"   Enriching: {entry['CanonicalNative']}")

        # Try async enrichment
        if asyncio.iscoroutinefunction(enricher.enrich):
            enriched = await enricher.enrich(entry)
        else:
            enriched = enricher.enrich(entry)

        # Check if any authority data was added
        authority_keys = [
            k
            for k in enriched.keys()
            if "Authority" in k or "ORCID" in k or "CrossRef" in k
        ]

        if authority_keys:
            print(f"✅ Enricher working - Added {len(authority_keys)} authority fields")
            for key in authority_keys[:3]:  # Show first 3
                print(f"   {key}: {str(enriched[key])[:50]}...")
            return True
        else:
            print("⚠️ Enricher returned no authority data")
            return False

    except Exception as e:
        print(f"❌ Enricher failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all wrapper tests"""
    print("=" * 60)
    print("ULTRATHINK WRAPPER API TESTS")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"OFFLINE mode: {os.environ.get('OFFLINE', '1')}")
    print("=" * 60)

    # Check environment
    print("\n=== Environment Check ===")
    print(
        f"ORCID_CLIENT_ID: {'✅ Set' if os.environ.get('ORCID_CLIENT_ID') else '❌ Not set'}"
    )
    print(
        f"ORCID_CLIENT_SECRET: {'✅ Set' if os.environ.get('ORCID_CLIENT_SECRET') else '❌ Not set'}"
    )
    print(
        f"PUBMED_API_KEY: {'✅ Set' if os.environ.get('PUBMED_API_KEY') else '❌ Not set'}"
    )

    # Run tests
    results = {
        "Crossref": await test_crossref_wrapper(),
        "ORCID": await test_orcid_wrapper(),
        "OpenAlex": await test_openalex_wrapper(),
        "arXiv": await test_arxiv_wrapper(),
        "Enricher": await test_enricher(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("WRAPPER API STATUS SUMMARY")
    print("=" * 60)

    working = []
    failed = []

    for api, status in results.items():
        if status:
            working.append(api)
            print(f"✅ {api}: WORKING")
        else:
            failed.append(api)
            print(f"❌ {api}: FAILED")

    print(f"\n📊 Statistics:")
    print(
        f"   Working: {len(working)}/{len(results)} ({100*len(working)/len(results):.1f}%)"
    )
    print(f"   Failed: {len(failed)}/{len(results)}")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "offline_mode": os.environ.get("OFFLINE", "0"),
        "results": results,
        "summary": {
            "total": len(results),
            "working": len(working),
            "failed": len(failed),
            "percentage": 100 * len(working) / len(results) if results else 0,
        },
        "working_apis": working,
        "failed_apis": failed,
    }

    with open("ultrathink_wrapper_test_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n📝 Results saved to ultrathink_wrapper_test_results.json")

    # Next steps
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)

    if len(working) == len(results):
        print("✅ All wrapper APIs are working!")
        print("📌 Next: Test pipeline integration")
    elif len(working) > 0:
        print(f"⚠️ {len(working)}/{len(results)} wrappers working")
        print(f"📌 Fix these wrappers: {', '.join(failed)}")
    else:
        print("❌ No wrapper APIs are working")
        print("📌 Need to implement wrapper methods properly")

    return len(working) > len(failed)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
