#!/usr/bin/env python3
"""
OpenAlex Data Collector - Real Mathematician Names

OpenAlex is a free, open catalog of scholarly papers and authors.
No API key required. Massive database of mathematician names with affiliations.

API docs: https://docs.openalex.org/
"""

import requests
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class OpenAlexCollector:
    """Collect mathematician profiles from OpenAlex API."""

    def __init__(self, email: str = "research@example.com"):
        """
        Initialize OpenAlex collector.

        Args:
            email: Your email (polite pool gets better rate limits)
        """
        self.base_url = "https://api.openalex.org"
        self.email = email
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": f"GMNAP-DataCollector (mailto:{email})", "Accept": "application/json"}
        )

    def search_authors(self, query: str = "mathematics", max_results: int = 10000) -> List[Dict]:
        """
        Search for mathematician authors.

        Args:
            query: Search term (default: "mathematics")
            max_results: Maximum authors to retrieve

        Returns:
            List of author records
        """
        print(f"Searching OpenAlex for: {query}")
        print(f"Target: {max_results} authors")

        authors = []
        page = 1
        per_page = 200  # Max per request

        while len(authors) < max_results:
            print(f"  Fetching page {page} ({len(authors)} authors so far)...")

            # Search for authors with mathematics in their works
            # OpenAlex polite pool requires email in query params
            # Using broader search strategy to avoid 403 errors
            params = {
                "filter": "display_name.search:mathematics",  # Broader search
                "per-page": per_page,
                "page": page,
                "select": "id,display_name,last_known_institutions,works_count,cited_by_count,topics",
                "mailto": self.email,  # Polite pool access
            }

            response = self.session.get(f"{self.base_url}/authors", params=params)

            if response.status_code == 403:
                print(f"⚠️  Access forbidden (403). Trying alternative search method...")
                # Fallback: simple search without topic filter
                params_fallback = {
                    "search": query,
                    "per-page": per_page,
                    "page": page,
                    "mailto": self.email,
                }
                response = self.session.get(f"{self.base_url}/authors", params=params_fallback)

            if response.status_code != 200:
                print(f"⚠️  Request failed: {response.status_code}")
                if response.status_code == 429:
                    print(f"    Rate limited. Waiting 60s...")
                    time.sleep(60)
                    continue
                break

            data = response.json()
            results = data.get("results", [])

            if not results:
                print("No more results")
                break

            authors.extend(results)
            page += 1

            # Rate limiting (polite: 10 requests/second, with email: 100 req/s)
            time.sleep(0.1)

            # Check if we have more pages
            meta = data.get("meta", {})
            if page > meta.get("per_page", 0):
                break

        authors = authors[:max_results]
        print(f"✅ Found {len(authors)} authors")
        return authors

    def enrich_author(self, author: Dict) -> Optional[Dict]:
        """
        Extract name and affiliation info from OpenAlex author record.

        Returns:
            Standardized profile dict
        """
        display_name = author.get("display_name")
        if not display_name:
            return None

        # Extract last known institution
        institutions = author.get("last_known_institutions", [])
        affiliations = []

        for inst in institutions:
            country_code = inst.get("country_code")
            inst_name = inst.get("display_name")

            if country_code or inst_name:
                affiliations.append({"institution": inst_name, "country_code": country_code})

        # Extract topics (to verify mathematics)
        topics = [t.get("display_name") for t in author.get("topics", [])[:3]]

        return {
            "openalex_id": author.get("id"),
            "name": display_name,
            "affiliations": affiliations,
            "works_count": author.get("works_count", 0),
            "citations": author.get("cited_by_count", 0),
            "topics": topics,
            "source": "openalex",
        }

    def collect_batch(self, max_authors: int = 10000) -> List[Dict]:
        """
        Collect mathematician profiles in batch.

        Args:
            max_authors: Maximum authors to collect

        Returns:
            List of enriched profiles
        """
        # Search for authors
        raw_authors = self.search_authors("mathematics", max_authors)

        # Enrich profiles
        print(f"\nEnriching {len(raw_authors)} author profiles...")
        profiles = []

        for i, author in enumerate(raw_authors):
            profile = self.enrich_author(author)
            if profile and profile.get("affiliations"):
                profiles.append(profile)

            if (i + 1) % 500 == 0:
                print(f"  Progress: {i+1}/{len(raw_authors)} ({len(profiles)} with affiliations)")

        print(f"✅ Enriched {len(profiles)} profiles with affiliation data")
        return profiles

    def save_profiles(self, profiles: List[Dict], output_path: str):
        """Save profiles to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Country statistics
        country_counts = {}
        for profile in profiles:
            for affiliation in profile.get("affiliations", []):
                country = affiliation.get("country_code", "Unknown")
                country_counts[country] = country_counts.get(country, 0) + 1

        data = {
            "metadata": {
                "source": "openalex",
                "total_profiles": len(profiles),
                "collection_date": time.strftime("%Y-%m-%d"),
                "country_distribution": country_counts,
            },
            "profiles": profiles,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved to {output_path}")


def main():
    """Collect mathematician profiles from OpenAlex."""
    print("=" * 80)
    print("OPENALEX MATHEMATICIAN DATA COLLECTION")
    print("=" * 80)
    print()

    # Initialize collector
    collector = OpenAlexCollector(email="research@example.com")

    # Collect profiles
    print("Collecting mathematician profiles from OpenAlex...")
    profiles = collector.collect_batch(max_authors=10000)

    # Save results
    output_path = "data/real_world_collection/openalex_mathematicians.json"
    collector.save_profiles(profiles, output_path)

    # Statistics
    print("\n" + "=" * 80)
    print("COLLECTION COMPLETE")
    print("=" * 80)
    print(f"Total profiles: {len(profiles)}")

    # Country distribution
    country_counts = {}
    for profile in profiles:
        for affiliation in profile.get("affiliations", []):
            country = affiliation.get("country_code", "Unknown")
            country_counts[country] = country_counts.get(country, 0) + 1

    print("\nTop 10 Countries:")
    for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {country}: {count}")

    # Top cited
    top_cited = sorted(profiles, key=lambda x: x.get("citations", 0), reverse=True)[:10]
    print("\nTop 10 Most Cited:")
    for i, profile in enumerate(top_cited, 1):
        print(f"  {i}. {profile['name']} ({profile.get('citations', 0)} citations)")

    print()
    print(f"Data saved to: {output_path}")


if __name__ == "__main__":
    main()
