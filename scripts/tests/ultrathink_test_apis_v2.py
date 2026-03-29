#!/usr/bin/env python3
"""
ULTRATHINK API Source Verification V2
Tests all authority sources to ensure APIs are working
"""

import os
import sys
import json
import time
import requests
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
        from src.authorities.crossref import CrossrefAPI

        api = CrossrefAPI()

        # Test a simple query
        name = "Albert Einstein"
        print(f"   Searching for: {name}")
        results = api.query_author(name)

        if results and len(results) > 0:
            print(f"✅ Crossref API working - Found {len(results)} results")
            first = results[0]
            if hasattr(first, "display_name"):
                print(f"   Sample: {first.display_name}")
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
        from src.authorities.orcid import ORCIDAPI

        api = ORCIDAPI()

        # Check if we have credentials
        if not api.client_id or not api.client_secret:
            print("❌ ORCID credentials not configured")
            return False

        # Test OAuth token generation
        if api.get_oauth_token():
            print("✅ ORCID OAuth token obtained")
        else:
            print("❌ Failed to get ORCID OAuth token")
            return False

        # Test search
        name = "Albert Einstein"
        print(f"   Searching for: {name}")
        results = api.search_person(name)

        if results and len(results) > 0:
            print(f"✅ ORCID API working - Found {len(results)} results")
            first = results[0]
            if hasattr(first, "orcid"):
                print(f"   Sample ORCID: {first.orcid}")
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
        from src.authorities.openalex import OpenAlexAPI

        api = OpenAlexAPI()

        # Test search
        name = "T. Tao"
        print(f"   Searching for: {name}")
        results = api.query_author(name)

        if results and len(results) > 0:
            print(f"✅ OpenAlex API working - Found {len(results)} results")
            first = results[0]
            if hasattr(first, "display_name"):
                print(f"   Sample: {first.display_name}")
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
        from src.authorities.arxiv import ArXivAPI

        api = ArXivAPI()

        # Test search
        name = "T. Tao"
        print(f"   Searching for: {name}")
        results = api.query_author(name)

        if results and len(results) > 0:
            print(f"✅ arXiv API working - Found {len(results)} results")
            first = results[0]
            if hasattr(first, "name"):
                print(f"   Sample author: {first.name}")
            return True
        else:
            print("⚠️ arXiv API returned no results")
            return False
    except Exception as e:
        print(f"❌ arXiv API failed: {e}")
        return False


def test_crossref_direct():
    """Test Crossref API directly with requests"""
    print("\n=== Testing Crossref API (Direct) ===")
    try:
        # Test direct API call
        url = "https://api.crossref.org/works"
        params = {"query.author": "Albert Einstein", "rows": 1}

        # Add polite header
        headers = {"User-Agent": "GMNAP/1.0 (mailto:admin@example.com)"}

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("message", {}).get("items"):
                print(
                    f"✅ Crossref API (direct) working - Found {len(data['message']['items'])} results"
                )
                return True
            else:
                print("⚠️ Crossref API (direct) returned no results")
                return False
        else:
            print(f"❌ Crossref API (direct) returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Crossref API (direct) failed: {e}")
        return False


def test_orcid_direct():
    """Test ORCID API directly with requests"""
    print("\n=== Testing ORCID API (Direct) ===")
    try:
        client_id = os.environ.get("ORCID_CLIENT_ID")
        client_secret = os.environ.get("ORCID_CLIENT_SECRET")

        if not client_id or not client_secret:
            print("❌ ORCID credentials not found in environment")
            return False

        # Get OAuth token
        token_url = "https://orcid.org/oauth/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "/read-public",
        }

        token_response = requests.post(token_url, data=token_data, timeout=10)

        if token_response.status_code == 200:
            token = token_response.json().get("access_token")
            print("✅ ORCID OAuth token obtained")

            # Test search API
            search_url = "https://pub.orcid.org/v3.0/search"
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            params = {"q": "family-name:Einstein AND given-names:Albert", "rows": 1}

            search_response = requests.get(
                search_url, params=params, headers=headers, timeout=10
            )

            if search_response.status_code == 200:
                data = search_response.json()
                num_found = data.get("num-found", 0)
                print(f"✅ ORCID API (direct) working - Found {num_found} results")
                return True
            else:
                print(f"❌ ORCID search returned status {search_response.status_code}")
                return False
        else:
            print(
                f"❌ ORCID token request failed with status {token_response.status_code}"
            )
            return False

    except Exception as e:
        print(f"❌ ORCID API (direct) failed: {e}")
        return False


def test_openalex_direct():
    """Test OpenAlex API directly with requests"""
    print("\n=== Testing OpenAlex API (Direct) ===")
    try:
        # OpenAlex doesn't require authentication
        url = "https://api.openalex.org/authors"
        params = {"search": "T. Tao", "per_page": 1}

        # Add polite header with email
        headers = {"User-Agent": "GMNAP/1.0 (mailto:admin@example.com)"}

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                print(
                    f"✅ OpenAlex API (direct) working - Found {len(data['results'])} results"
                )
                first = data["results"][0]
                print(f"   Sample: {first.get('display_name', 'Unknown')}")
                return True
            else:
                print("⚠️ OpenAlex API (direct) returned no results")
                return False
        else:
            print(f"❌ OpenAlex API (direct) returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ OpenAlex API (direct) failed: {e}")
        return False


def test_arxiv_direct():
    """Test arXiv API directly with requests"""
    print("\n=== Testing arXiv API (Direct) ===")
    try:
        import urllib.parse

        # arXiv uses a different API format
        url = "http://export.arxiv.org/api/query"
        params = {"search_query": "au:Tao_T", "start": 0, "max_results": 1}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            # arXiv returns XML, just check if we got data
            if "<entry>" in response.text:
                print("✅ arXiv API (direct) working - Got results")
                return True
            else:
                print("⚠️ arXiv API (direct) returned no results")
                return False
        else:
            print(f"❌ arXiv API (direct) returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ arXiv API (direct) failed: {e}")
        return False


def test_pubmed_direct():
    """Test PubMed API directly with requests"""
    print("\n=== Testing PubMed API (Direct) ===")
    try:
        api_key = os.environ.get("PUBMED_API_KEY")

        # PubMed E-utilities search
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": "COVID-19 vaccine",
            "retmax": 1,
            "retmode": "json",
        }

        if api_key:
            params["api_key"] = api_key
            print("   Using API key")

        response = requests.get(search_url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("esearchresult", {}).get("idlist"):
                count = data["esearchresult"].get("count", "0")
                print(f"✅ PubMed API (direct) working - Found {count} total results")
                return True
            else:
                print("⚠️ PubMed API (direct) returned no results")
                return False
        else:
            print(f"❌ PubMed API (direct) returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ PubMed API (direct) failed: {e}")
        return False


def test_viaf_direct():
    """Test VIAF API directly with requests"""
    print("\n=== Testing VIAF API (Direct) ===")
    try:
        # VIAF search API
        url = "https://viaf.org/viaf/search"
        params = {
            "query": 'cql.any all "Albert Einstein"',
            "maximumRecords": 1,
            "httpAccept": "application/json",
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("searchRetrieveResponse", {}).get("records"):
                print("✅ VIAF API (direct) working - Got results")
                return True
            else:
                print("⚠️ VIAF API (direct) returned no results")
                return False
        else:
            print(f"❌ VIAF API (direct) returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ VIAF API (direct) failed: {e}")
        return False


def test_wikidata_direct():
    """Test Wikidata SPARQL API directly"""
    print("\n=== Testing Wikidata API (Direct) ===")
    try:
        # Wikidata SPARQL endpoint
        url = "https://query.wikidata.org/sparql"

        # Simple SPARQL query to find Tim Berners-Lee
        query = """
        SELECT ?person ?personLabel WHERE {
          ?person wdt:P31 wd:Q5.
          ?person ?label "Tim Berners-Lee"@en.
        } LIMIT 1
        """

        params = {"query": query, "format": "json"}

        headers = {"User-Agent": "GMNAP/1.0 (https://github.com/gmnap)"}

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("results", {}).get("bindings"):
                print("✅ Wikidata API (direct) working - Got results")
                return True
            else:
                # Try a simpler test
                test_url = "https://www.wikidata.org/w/api.php"
                test_params = {
                    "action": "wbsearchentities",
                    "search": "Tim Berners-Lee",
                    "language": "en",
                    "format": "json",
                    "limit": 1,
                }
                test_response = requests.get(
                    test_url, params=test_params, headers=headers, timeout=10
                )
                if test_response.status_code == 200:
                    test_data = test_response.json()
                    if test_data.get("search"):
                        print(
                            "✅ Wikidata API (direct) working - Got results via wbsearchentities"
                        )
                        return True
                print("⚠️ Wikidata API (direct) returned no results")
                return False
        else:
            print(f"❌ Wikidata API (direct) returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Wikidata API (direct) failed: {e}")
        return False


def main():
    """Run all API tests"""
    print("=" * 60)
    print("ULTRATHINK API SOURCE VERIFICATION V2")
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

    # Test wrapper classes first
    print("\n" + "=" * 60)
    print("TESTING WRAPPER CLASSES")
    print("=" * 60)

    wrapper_results = {
        "Crossref (wrapper)": test_crossref(),
        "ORCID (wrapper)": test_orcid(),
        "OpenAlex (wrapper)": test_openalex(),
        "arXiv (wrapper)": test_arxiv(),
    }

    # Test direct API calls
    print("\n" + "=" * 60)
    print("TESTING DIRECT API CALLS")
    print("=" * 60)

    direct_results = {
        "Crossref": test_crossref_direct(),
        "ORCID": test_orcid_direct(),
        "OpenAlex": test_openalex_direct(),
        "arXiv": test_arxiv_direct(),
        "PubMed": test_pubmed_direct(),
        "VIAF": test_viaf_direct(),
        "Wikidata": test_wikidata_direct(),
    }

    # Combine results
    all_results = {**wrapper_results, **direct_results}

    # Summary
    print("\n" + "=" * 60)
    print("API STATUS SUMMARY")
    print("=" * 60)

    working = []
    failed = []

    print("\nWrapper Classes:")
    for api, status in wrapper_results.items():
        if status:
            working.append(api)
            print(f"✅ {api}: WORKING")
        else:
            failed.append(api)
            print(f"❌ {api}: FAILED")

    print("\nDirect API Calls:")
    for api, status in direct_results.items():
        if status:
            if api not in working:
                working.append(api)
            print(f"✅ {api}: WORKING")
        else:
            if api not in failed:
                failed.append(api)
            print(f"❌ {api}: FAILED")

    print(f"\n📊 Overall Statistics:")
    print(
        f"   Direct APIs Working: {sum(1 for v in direct_results.values() if v)}/{len(direct_results)}"
    )
    print(
        f"   Wrapper Classes Working: {sum(1 for v in wrapper_results.values() if v)}/{len(wrapper_results)}"
    )

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "offline_mode": os.environ.get("OFFLINE", "0"),
        "wrapper_results": wrapper_results,
        "direct_results": direct_results,
        "summary": {
            "direct_working": sum(1 for v in direct_results.values() if v),
            "direct_total": len(direct_results),
            "wrapper_working": sum(1 for v in wrapper_results.values() if v),
            "wrapper_total": len(wrapper_results),
        },
    }

    with open("ultrathink_api_test_results_v2.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n📝 Results saved to ultrathink_api_test_results_v2.json")

    # Key finding
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    if sum(1 for v in direct_results.values() if v) > sum(
        1 for v in wrapper_results.values() if v
    ):
        print("⚠️ APIs are accessible but wrapper classes are broken!")
        print("📌 Next step: Fix the wrapper class implementations")
    elif sum(1 for v in direct_results.values() if v) == 0:
        print("❌ No APIs are working - check network/credentials")
    else:
        print("✅ Both APIs and wrappers are working")

    return sum(1 for v in direct_results.values() if v) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
