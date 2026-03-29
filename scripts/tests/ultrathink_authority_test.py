#!/usr/bin/env python3
"""
ULTRATHINK Authority Sources Test
Test each authority source to verify they actually fetch data
"""

import os
import sys
import asyncio
import traceback
from typing import Dict, Any, List


def test_crossref():
    """Test Crossref fetcher"""
    try:
        from src.authorities.crossref import CrossrefFetcher

        fetcher = CrossrefFetcher()

        # Test with a known DOI
        doi = "10.1038/nature12373"
        result = fetcher.fetch(doi)

        if result and "title" in str(result):
            print("  ✅ Crossref works - fetched data for DOI")
            return True
        else:
            print(f"  ❌ Crossref returned no/invalid data: {result}")
            return False
    except Exception as e:
        print(f"  ❌ Crossref error: {e}")
        return False


def test_orcid():
    """Test ORCID fetcher"""
    try:
        from src.authorities.orcid import ORCIDFetcher

        fetcher = ORCIDFetcher()

        # Test with a known ORCID
        orcid_id = "0000-0002-1825-0097"
        result = fetcher.fetch(orcid_id)

        if result:
            print(f"  ✅ ORCID works - fetched data")
            return True
        else:
            print(f"  ❌ ORCID returned no data")
            return False
    except Exception as e:
        print(f"  ❌ ORCID error: {e}")
        return False


def test_arxiv():
    """Test arXiv fetcher"""
    try:
        from src.authorities.arxiv import ArxivFetcher

        fetcher = ArxivFetcher()

        # Test with a known arXiv ID
        arxiv_id = "2103.15348"
        result = fetcher.fetch(arxiv_id)

        if result:
            print("  ✅ arXiv works - fetched data")
            return True
        else:
            print(f"  ❌ arXiv returned no data")
            return False
    except Exception as e:
        print(f"  ❌ arXiv error: {e}")
        return False


def test_openalex():
    """Test OpenAlex fetcher"""
    try:
        from src.authorities.openalex import OpenAlexFetcher

        fetcher = OpenAlexFetcher()

        # Test with a known work ID
        work_id = "W2741809807"
        result = fetcher.fetch(work_id)

        if result:
            print("  ✅ OpenAlex works - fetched data")
            return True
        else:
            print(f"  ❌ OpenAlex returned no data")
            return False
    except Exception as e:
        print(f"  ❌ OpenAlex error: {e}")
        return False


def test_wikidata():
    """Test Wikidata fetcher"""
    try:
        from src.authorities.wikidata_p184 import WikidataP184Fetcher

        fetcher = WikidataP184Fetcher()

        # Test with Einstein's Wikidata ID
        wikidata_id = "Q937"
        result = fetcher.fetch(wikidata_id)

        if result:
            print("  ✅ Wikidata works - fetched data")
            return True
        else:
            print(f"  ❌ Wikidata returned no data")
            return False
    except Exception as e:
        print(f"  ❌ Wikidata error: {e}")
        return False


def test_enricher():
    """Test the authority enricher"""
    try:
        from src.authorities.enricher import AuthorityEnricher

        # Set to online mode
        os.environ["OFFLINE"] = "0"
        enricher = AuthorityEnricher()

        entry = {"GlobalID": "TEST-001", "CanonicalNative": "Albert Einstein"}

        # Try to enrich
        result = asyncio.run(enricher.enrich(entry))

        if "AuthoritySources" in result and result["AuthoritySources"]:
            print(
                f"  ✅ Enricher works - added {len(result['AuthoritySources'])} sources"
            )
            return True
        else:
            print(f"  ❌ Enricher added no authority sources")
            return False
    except Exception as e:
        print(f"  ❌ Enricher error: {e}")
        traceback.print_exc()
        return False


def main():
    print("=" * 80)
    print("ULTRATHINK AUTHORITY SOURCES TEST")
    print("=" * 80)

    # Check if we're in offline mode
    offline_mode = os.environ.get("OFFLINE", "1") == "1"
    if offline_mode:
        print("\n⚠️ WARNING: OFFLINE mode detected. Setting OFFLINE=0 for testing...")
        os.environ["OFFLINE"] = "0"

    print("\n📊 Testing Individual Authority Sources:")

    results = {
        "Crossref": test_crossref(),
        "ORCID": test_orcid(),
        "arXiv": test_arxiv(),
        "OpenAlex": test_openalex(),
        "Wikidata": test_wikidata(),
        "Enricher": test_enricher(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} authority sources working")
    print(f"Success Rate: {passed/total*100:.1f}%")

    if passed == total:
        print("\n🎯 ALL AUTHORITY SOURCES WORKING!")
    elif passed == 0:
        print("\n🔴 NO AUTHORITY SOURCES WORKING!")
    else:
        print(f"\n⚠️ Only {passed}/{total} authority sources working")

    return 0 if passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
