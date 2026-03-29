#!/usr/bin/env python3
"""
Test script to verify Crossref free API works correctly
Uses only the free API with mailto parameter for polite pool access
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment for testing
os.environ["OFFLINE"] = "0"  # Enable API calls
os.environ["CROSSREF_MAILTO"] = "test@example.com"  # Use your email for polite pool


async def test_crossref_free_api():
    """Test the free Crossref API with just mailto parameter"""

    print("=" * 70)
    print("CROSSREF FREE API TEST")
    print("=" * 70)
    print()

    # Test both implementations
    implementations = []

    try:
        from src.authorities.crossref import CrossrefAPI

        implementations.append(("crossref.py", CrossrefAPI))
    except ImportError as e:
        print(f"Warning: Could not import CrossrefAPI: {e}")

    try:
        from src.authorities.crossref_v7 import CrossrefV7Fetcher

        implementations.append(("crossref_v7.py", CrossrefV7Fetcher))
    except ImportError as e:
        print(f"Warning: Could not import CrossrefV7Fetcher: {e}")

    if not implementations:
        print("ERROR: No Crossref implementations could be imported!")
        return False

    test_queries = ["Albert Einstein", "Marie Curie", "T. Tao"]

    all_tests_passed = True

    for impl_name, impl_class in implementations:
        print(f"\n{'='*50}")
        print(f"Testing: {impl_name}")
        print(f"{'='*50}")

        if impl_name == "crossref.py":
            # Test CrossrefAPI
            async with impl_class(mailto="test@example.com") as api:
                print(f"✓ Using mailto: {api.mailto}")
                print(f"✓ Rate limit: {api.POLITE_POOL_DELAY}s between requests (polite pool)")
                print()

                for query in test_queries:
                    print(f"Searching for: {query}")
                    try:
                        results = await api.search_author(query, limit=3)
                        if results:
                            print(f"  ✓ Found {len(results)} results")
                            first = results[0]
                            print(f"    - Name: {first.get('canonical_name', 'Unknown')}")
                            print(f"    - Confidence: {first.get('confidence', 0):.1f}%")
                            if first.get("orcid"):
                                print(f"    - ORCID: {first['orcid']}")
                        else:
                            print(f"  ⚠ No results found")
                    except Exception as e:
                        print(f"  ✗ Error: {e}")
                        all_tests_passed = False
                    print()

                # Show stats
                stats = api.get_stats()
                print(f"API Statistics:")
                print(f"  - Requests made: {stats['request_count']}")
                print(f"  - Daily quota: {stats['daily_quota']:,}")
                print(f"  - Remaining: {stats['remaining_quota']:,}")

        elif impl_name == "crossref_v7.py":
            # Test CrossrefV7Fetcher
            async with impl_class(email="test@example.com") as fetcher:
                print(f"✓ Using email: {fetcher.email}")
                print(f"✓ Rate limit: {fetcher.requests_per_second} req/sec")
                print(f"✓ Daily quota: {fetcher.daily_quota:,}")
                print()

                for query in test_queries:
                    print(f"Searching for: {query}")
                    try:
                        works = await fetcher.search_author(query, limit=3)
                        if works:
                            print(f"  ✓ Found {len(works)} works")
                            first_work = works[0]
                            # Extract first author
                            authors = first_work.get("author", [])
                            if authors:
                                author = authors[0]
                                name = (
                                    f"{author.get('given', '')} {author.get('family', '')}".strip()
                                )
                                print(f"    - First author: {name}")
                            title = (
                                first_work.get("title", [""])[0]
                                if first_work.get("title")
                                else "Unknown"
                            )
                            print(f"    - Title: {title[:60]}...")
                            if first_work.get("DOI"):
                                print(f"    - DOI: {first_work['DOI']}")
                        else:
                            print(f"  ⚠ No results found")
                    except Exception as e:
                        print(f"  ✗ Error: {e}")
                        all_tests_passed = False
                    print()

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    if all_tests_passed:
        print("✅ All tests PASSED!")
        print("\nThe Crossref FREE API is working correctly:")
        print("  - No API key required")
        print("  - Just use mailto parameter for polite pool access")
        print("  - Rate limit: 50 req/sec with mailto (vs 10 without)")
        print("\nTo use in production:")
        print("  export CROSSREF_MAILTO='your-email@example.com'")
    else:
        print("⚠️ Some tests failed")
        print("Please check the errors above")

    return all_tests_passed


def main():
    """Run the test"""
    print("\nCrossref Free API Test")
    print("This verifies the Crossref API works without any API keys")
    print("Using only the free REST API with mailto for polite pool")
    print()

    # Check environment
    print("Environment:")
    print(f"  OFFLINE: {os.getenv('OFFLINE', '1')}")
    print(f"  CROSSREF_MAILTO: {os.getenv('CROSSREF_MAILTO', 'Not set')}")
    print(f"  CROSSREF_API_KEY: {os.getenv('CROSSREF_API_KEY', 'Not set (good!)')}")
    print()

    # Run async test
    success = asyncio.run(test_crossref_free_api())

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
