#!/usr/bin/env python3
"""
Math Genealogy Project Data Collector

Scrapes real mathematician names from https://www.mathgenealogy.org/
Respectful scraping with rate limiting and caching.

Note: MGP has no official API, so we scrape their public pages.
Be respectful: 1 request per 2 seconds, cache results.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
import sys
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MathGenealogyCollector:
    """Collect mathematician profiles from Math Genealogy Project."""

    def __init__(self, cache_dir: str = "data/cache/mgp"):
        self.base_url = "https://www.mathgenealogy.org"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Academic Research Bot; mailto:research@example.com)"
            }
        )

    def search_by_name(self, name: str) -> List[Dict]:
        """
        Search for a mathematician by name.

        Args:
            name: Name to search for

        Returns:
            List of matching mathematician records
        """
        # Check cache first
        cache_file = self.cache_dir / f"search_{name.replace(' ', '_')}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)

        print(f"  Searching for: {name}")

        # Search MGP
        response = self.session.get(
            f"{self.base_url}/id.php", params={"freetext": name, "submit": "Search"}
        )

        if response.status_code != 200:
            print(f"    ⚠️  Search failed: {response.status_code}")
            return []

        # Parse results
        soup = BeautifulSoup(response.content, "html.parser")
        results = []

        # Find result entries
        for result in soup.find_all("table"):
            name_elem = result.find("a", href=re.compile(r"id\.php\?id=\d+"))
            if not name_elem:
                continue

            # Extract mathematician ID
            href = name_elem.get("href")
            match = re.search(r"id=(\d+)", href)
            if not match:
                continue

            mgp_id = match.group(1)
            full_name = name_elem.text.strip()

            results.append({"mgp_id": mgp_id, "name": full_name})

        # Cache results
        with open(cache_file, "w") as f:
            json.dump(results, f)

        time.sleep(2)  # Respectful rate limiting
        return results

    def get_profile(self, mgp_id: str) -> Optional[Dict]:
        """
        Fetch full profile for a mathematician.

        Args:
            mgp_id: Math Genealogy Project ID

        Returns:
            Profile dict with name, university, country, advisor, year
        """
        # Check cache
        cache_file = self.cache_dir / f"profile_{mgp_id}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)

        print(f"  Fetching profile: ID {mgp_id}")

        response = self.session.get(f"{self.base_url}/id.php?id={mgp_id}")

        if response.status_code != 200:
            print(f"    ⚠️  Failed: {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        # Extract name
        name_elem = soup.find("h2")
        if not name_elem:
            return None

        name = name_elem.text.strip()

        # Extract university and year
        institution = None
        country = None
        year = None

        # Look for dissertation info
        spans = soup.find_all("span", style="margin-right: 0.5em")
        for span in spans:
            text = span.get_text()
            if "Ph.D." in text or "University" in text:
                # Extract institution
                inst_match = re.search(r"(University[^,]*|Institute[^,]*)", text)
                if inst_match:
                    institution = inst_match.group(1).strip()

                # Extract year
                year_match = re.search(r"\b(19|20)\d{2}\b", text)
                if year_match:
                    year = year_match.group(0)

        # Try to infer country from institution name
        if institution:
            country = self._infer_country_from_institution(institution)

        # Extract advisor
        advisor = None
        advisor_elem = soup.find("p", string=re.compile(r"Advisor"))
        if advisor_elem:
            advisor_link = advisor_elem.find_next("a")
            if advisor_link:
                advisor = advisor_link.text.strip()

        profile = {
            "mgp_id": mgp_id,
            "name": name,
            "institution": institution,
            "country": country,
            "year": year,
            "advisor": advisor,
            "source": "math_genealogy",
        }

        # Cache profile
        with open(cache_file, "w") as f:
            json.dump(profile, f)

        time.sleep(2)  # Respectful rate limiting
        return profile

    def _infer_country_from_institution(self, institution: str) -> Optional[str]:
        """Infer country from institution name."""
        institution_lower = institution.lower()

        country_keywords = {
            "harvard": "USA",
            "mit": "USA",
            "stanford": "USA",
            "berkeley": "USA",
            "princeton": "USA",
            "yale": "USA",
            "chicago": "USA",
            "columbia": "USA",
            "cambridge": "UK",
            "oxford": "UK",
            "london": "UK",
            "edinburgh": "UK",
            "paris": "France",
            "sorbonne": "France",
            "göttingen": "Germany",
            "berlin": "Germany",
            "munich": "Germany",
            "moscow": "Russia",
            "st. petersburg": "Russia",
            "tokyo": "Japan",
            "kyoto": "Japan",
            "beijing": "China",
            "tsinghua": "China",
            "peking": "China",
            "toronto": "Canada",
            "montreal": "Canada",
            "sydney": "Australia",
            "melbourne": "Australia",
        }

        for keyword, country in country_keywords.items():
            if keyword in institution_lower:
                return country

        return None

    def collect_by_id_range(
        self, start_id: int, end_id: int, sample_rate: int = 100
    ) -> List[Dict]:
        """
        Collect profiles by sampling ID range.

        Args:
            start_id: Starting MGP ID
            end_id: Ending MGP ID
            sample_rate: Sample every Nth ID

        Returns:
            List of profiles
        """
        print(
            f"Collecting MGP profiles from ID {start_id} to {end_id} (every {sample_rate}th)"
        )

        profiles = []
        ids_to_sample = list(range(start_id, end_id, sample_rate))

        for i, mgp_id in enumerate(ids_to_sample):
            profile = self.get_profile(str(mgp_id))

            if profile:
                profiles.append(profile)

            if (i + 1) % 10 == 0:
                print(
                    f"  Progress: {i+1}/{len(ids_to_sample)} ({len(profiles)} valid profiles)"
                )

        print(f"✅ Collected {len(profiles)} profiles")
        return profiles

    def save_profiles(self, profiles: List[Dict], output_path: str):
        """Save profiles to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Country statistics
        country_counts = {}
        for profile in profiles:
            country = profile.get("country", "Unknown")
            country_counts[country] = country_counts.get(country, 0) + 1

        data = {
            "metadata": {
                "source": "math_genealogy",
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
    """Collect mathematician profiles from Math Genealogy Project."""
    print("=" * 80)
    print("MATH GENEALOGY PROJECT DATA COLLECTION")
    print("=" * 80)
    print()
    print("⚠️  This scraper is RESPECTFUL:")
    print("   - 2 second delay between requests")
    print("   - Caches all results")
    print("   - Samples IDs (not exhaustive)")
    print()

    # Initialize collector
    collector = MathGenealogyCollector()

    # Collect profiles by sampling ID range
    # MGP has ~280,000 IDs, we'll sample every 100th
    print("Collecting sample of MGP profiles...")
    profiles = collector.collect_by_id_range(
        start_id=1,
        end_id=50000,  # Sample first 50K IDs
        sample_rate=100,  # Every 100th ID = ~500 profiles
    )

    # Save results
    output_path = "data/real_world_collection/mathgenealogy_mathematicians.json"
    collector.save_profiles(profiles, output_path)

    # Statistics
    print("\n" + "=" * 80)
    print("COLLECTION COMPLETE")
    print("=" * 80)
    print(f"Total profiles: {len(profiles)}")

    # Country distribution
    country_counts = {}
    for profile in profiles:
        country = profile.get("country", "Unknown")
        country_counts[country] = country_counts.get(country, 0) + 1

    print("\nCountry Distribution:")
    for country, count in sorted(
        country_counts.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {country}: {count}")

    # Year distribution
    year_counts = {}
    for profile in profiles:
        year = profile.get("year", "Unknown")
        if year and year != "Unknown":
            decade = (int(year) // 10) * 10
            year_counts[decade] = year_counts.get(decade, 0) + 1

    print("\nDecade Distribution:")
    for decade, count in sorted(year_counts.items()):
        print(f"  {decade}s: {count}")

    print()
    print(f"Data saved to: {output_path}")
    print()
    print(f"Cache directory: {collector.cache_dir}")
    print("(Rerun will be instant due to caching)")


if __name__ == "__main__":
    main()
