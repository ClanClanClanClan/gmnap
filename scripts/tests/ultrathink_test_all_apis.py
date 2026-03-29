#!/usr/bin/env python3
"""
ULTRATHINK API Source Verification
Tests all authority sources to ensure APIs are working
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


def test_crossref():
    """Test Crossref API"""
    print("\n=== Testing Crossref API ===")
    try:
        from src.authorities.crossref import CrossrefSource

        source = CrossrefSource()

        # Test search
        results = source.search("Einstein relativity", limit=1)
        if results:
            print(f"✅ Crossref API working - Found {len(results)} results")
            print(f"   Sample: {results[0].get('title', 'No title')[:50]}...")
            return True
        else:
            print("⚠️ Crossref API returned no results")
            return False
    except Exception as e:
        print(f"❌ Crossref API failed: {e}")
        return False


def test_orcid():
    """Test ORCID API"""
    print("\n=== Testing ORCID API ===")
    try:
        from src.authorities.orcid import ORCIDSource

        source = ORCIDSource()

        # Test search for a known researcher
        results = source.search("Albert Einstein", limit=1)
        if results:
            print(f"✅ ORCID API working - Found {len(results)} results")
            if results[0].get("orcid_id"):
                print(f"   Sample ORCID: {results[0]['orcid_id']}")
            return True
        else:
            print("⚠️ ORCID API returned no results")
            return False
    except Exception as e:
        print(f"❌ ORCID API failed: {e}")
        return False


def test_openalex():
    """Test OpenAlex API"""
    print("\n=== Testing OpenAlex API ===")
    try:
        from src.authorities.openalex import OpenAlexSource

        source = OpenAlexSource()

        # Test search
        results = source.search("machine learning", limit=1)
        if results:
            print(f"✅ OpenAlex API working - Found {len(results)} results")
            print(f"   Sample: {results[0].get('display_name', 'No name')[:50]}...")
            return True
        else:
            print("⚠️ OpenAlex API returned no results")
            return False
    except Exception as e:
        print(f"❌ OpenAlex API failed: {e}")
        return False


def test_arxiv():
    """Test arXiv API"""
    print("\n=== Testing arXiv API ===")
    try:
        from src.authorities.arxiv import ArxivSource

        source = ArxivSource()

        # Test search
        results = source.search("quantum computing", limit=1)
        if results:
            print(f"✅ arXiv API working - Found {len(results)} results")
            print(f"   Sample: {results[0].get('title', 'No title')[:50]}...")
            return True
        else:
            print("⚠️ arXiv API returned no results")
            return False
    except Exception as e:
        print(f"❌ arXiv API failed: {e}")
        return False


def test_pubmed():
    """Test PubMed API"""
    print("\n=== Testing PubMed API ===")
    try:
        # Check for tier1 PubMed implementation
        from src.authorities.tier1.pubmed import PubMedSource

        source = PubMedSource()

        # Test search
        results = source.search("COVID-19 vaccine", limit=1)
        if results:
            print(f"✅ PubMed API working - Found {len(results)} results")
            print(f"   Sample: {results[0].get('title', 'No title')[:50]}...")
            return True
        else:
            print("⚠️ PubMed API returned no results")
            return False
    except ImportError:
        print("⚠️ PubMed source not found in tier1, checking main authorities...")
        try:
            from src.authorities.pubmed import PubMedSource

            source = PubMedSource()
            results = source.search("COVID-19 vaccine", limit=1)
            if results:
                print(f"✅ PubMed API working - Found {len(results)} results")
                return True
        except:
            pass
        print("❌ PubMed API source not implemented")
        return False
    except Exception as e:
        print(f"❌ PubMed API failed: {e}")
        return False


def test_viaf():
    """Test VIAF API"""
    print("\n=== Testing VIAF API ===")
    try:
        from src.authorities.tier1.viaf import VIAFSource

        source = VIAFSource()

        # Test search
        results = source.search("Albert Einstein", limit=1)
        if results:
            print(f"✅ VIAF API working - Found {len(results)} results")
            print(f"   Sample: {results[0].get('viaf_id', 'No ID')}")
            return True
        else:
            print("⚠️ VIAF API returned no results")
            return False
    except Exception as e:
        print(f"❌ VIAF API failed: {e}")
        return False


def test_wikidata():
    """Test Wikidata API"""
    print("\n=== Testing Wikidata API ===")
    try:
        from src.authorities.tier1.wikidata import WikidataSource

        source = WikidataSource()

        # Test search
        results = source.search("Tim Berners-Lee", limit=1)
        if results:
            print(f"✅ Wikidata API working - Found {len(results)} results")
            print(f"   Sample: {results[0].get('label', 'No label')}")
            return True
        else:
            print("⚠️ Wikidata API returned no results")
            return False
    except Exception as e:
        print(f"❌ Wikidata API failed: {e}")
        return False


def test_zbmath():
    """Test zbMATH API"""
    print("\n=== Testing zbMATH API ===")
    try:
        from src.authorities.tier1.zbmath import ZbMathSource

        source = ZbMathSource()

        # Test search
        results = source.search("Terence Tao", limit=1)
        if results:
            print(f"✅ zbMATH API working - Found {len(results)} results")
            return True
        else:
            print("⚠️ zbMATH API returned no results")
            return False
    except Exception as e:
        print(f"❌ zbMATH API failed: {e}")
        return False


def test_mathgenealogy():
    """Test Mathematics Genealogy Project API"""
    print("\n=== Testing Math Genealogy API ===")
    try:
        from src.authorities.mathgenealogy import MathGenealogySource

        source = MathGenealogySource()

        # Test search - this might not have a search method
        if hasattr(source, "search"):
            results = source.search("John Nash", limit=1)
            if results:
                print(f"✅ Math Genealogy API working - Found {len(results)} results")
                return True
        else:
            print("⚠️ Math Genealogy source exists but no search method")
            return False
    except Exception as e:
        print(f"❌ Math Genealogy API failed: {e}")
        return False


def test_hal():
    """Test HAL API"""
    print("\n=== Testing HAL API ===")
    try:
        from src.authorities.tier1.hal import HALSource

        source = HALSource()

        # Test search
        results = source.search("machine learning", limit=1)
        if results:
            print(f"✅ HAL API working - Found {len(results)} results")
            return True
        else:
            print("⚠️ HAL API returned no results")
            return False
    except Exception as e:
        print(f"❌ HAL API failed: {e}")
        return False


def test_gnd():
    """Test GND (German National Library) API"""
    print("\n=== Testing GND API ===")
    try:
        from src.authorities.tier1.gnd import GNDSource

        source = GNDSource()

        # Test search
        results = source.search("Max Planck", limit=1)
        if results:
            print(f"✅ GND API working - Found {len(results)} results")
            return True
        else:
            print("⚠️ GND API returned no results")
            return False
    except Exception as e:
        print(f"❌ GND API failed: {e}")
        return False


def test_dblp():
    """Test DBLP API"""
    print("\n=== Testing DBLP API ===")
    try:
        from src.authorities.tier1.dblp import DBLPSource

        source = DBLPSource()

        # Test search
        results = source.search("Donald Knuth", limit=1)
        if results:
            print(f"✅ DBLP API working - Found {len(results)} results")
            return True
        else:
            print("⚠️ DBLP API returned no results")
            return False
    except Exception as e:
        print(f"❌ DBLP API failed: {e}")
        return False


def main():
    """Run all API tests"""
    print("=" * 60)
    print("ULTRATHINK API SOURCE VERIFICATION")
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
    print(
        f"CROSSREF_API_KEY: {'✅ Set' if os.environ.get('CROSSREF_API_KEY') else '⚠️ Not set (optional)'}"
    )
    print(
        f"OPENALEX_API_KEY: {'✅ Set' if os.environ.get('OPENALEX_API_KEY') else '⚠️ Not set (optional)'}"
    )

    # Test all APIs
    results = {
        "Crossref": test_crossref(),
        "ORCID": test_orcid(),
        "OpenAlex": test_openalex(),
        "arXiv": test_arxiv(),
        "PubMed": test_pubmed(),
        "VIAF": test_viaf(),
        "Wikidata": test_wikidata(),
        "zbMATH": test_zbmath(),
        "Math Genealogy": test_mathgenealogy(),
        "HAL": test_hal(),
        "GND": test_gnd(),
        "DBLP": test_dblp(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("API STATUS SUMMARY")
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
    print(
        f"   Failed: {len(failed)}/{len(results)} ({100*len(failed)/len(results):.1f}%)"
    )

    print(f"\n✅ Working APIs: {', '.join(working) if working else 'None'}")
    print(f"❌ Failed APIs: {', '.join(failed) if failed else 'None'}")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "offline_mode": os.environ.get("OFFLINE", "1"),
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

    with open("ultrathink_api_test_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n📝 Results saved to ultrathink_api_test_results.json")

    return len(working) > len(failed)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
