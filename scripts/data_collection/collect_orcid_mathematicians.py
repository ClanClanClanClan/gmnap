import os

#!/usr/bin/env python3
"""
ORCID Data Collector - Real Mathematician Names

Uses ORCID API to collect real mathematician profiles with:
- Full names
- Affiliations (university, country)
- Research areas (to filter for mathematics)

Authentication provided by user:
- Client ID: (env ORCID_CLIENT_ID)
- Client Secret: (env ORCID_CLIENT_SECRET)
"""

import requests
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
import sys

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ORCIDCollector:
    """Collect mathematician profiles from ORCID API."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.base_url = "https://pub.orcid.org/v3.0"
        self.auth_url = "https://orcid.org/oauth/token"

    def authenticate(self) -> str:
        """Get OAuth2 access token."""
        print("Authenticating with ORCID API...")

        response = requests.post(
            self.auth_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
                "scope": "/read-public",
            },
            headers={"Accept": "application/json"},
        )

        if response.status_code == 200:
            self.access_token = response.json()["access_token"]
            print(f"✅ Authenticated successfully")
            return self.access_token
        else:
            raise Exception(
                f"ORCID authentication failed: {response.status_code} {response.text}"
            )

    def search_mathematicians(
        self, query: str = "mathematics", max_results: int = 10000
    ) -> List[str]:
        """
        Search for mathematician ORCID IDs.

        Args:
            query: Search term (default: "mathematics")
            max_results: Maximum ORCIDs to retrieve

        Returns:
            List of ORCID IDs
        """
        if not self.access_token:
            self.authenticate()

        print(f"Searching ORCID for: {query}")
        print(f"Target: {max_results} profiles")

        orcid_ids = []
        start = 0
        rows = 200  # Max per request

        while len(orcid_ids) < max_results:
            print(f"  Fetching results {start} to {start + rows}...")

            response = requests.get(
                f"{self.base_url}/search/",
                params={
                    "q": f"keyword:{query} OR affiliation-org-name:mathematics OR affiliation-org-name:math",
                    "start": start,
                    "rows": rows,
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                print(f"⚠️  Search failed: {response.status_code}")
                break

            data = response.json()
            results = data.get("result", [])

            if not results:
                print("No more results")
                break

            for result in results:
                orcid_id = result.get("orcid-identifier", {}).get("path")
                if orcid_id:
                    orcid_ids.append(orcid_id)

            start += rows
            time.sleep(0.5)  # Rate limiting

            if len(results) < rows:
                break  # No more pages

        print(f"✅ Found {len(orcid_ids)} ORCID IDs")
        return orcid_ids[:max_results]

    def get_profile(self, orcid_id: str) -> Optional[Dict]:
        """
        Fetch full profile for an ORCID ID.

        Returns:
            dict with name, affiliations, country
        """
        if not self.access_token:
            self.authenticate()

        response = requests.get(
            f"{self.base_url}/{orcid_id}/person",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
        )

        if response.status_code != 200:
            return None

        data = response.json()

        # Extract name
        name_data = data.get("name", {})
        given_names = name_data.get("given-names", {}).get("value", "")
        family_name = name_data.get("family-name", {}).get("value", "")

        if not family_name:
            return None  # Skip if no family name

        full_name = f"{given_names} {family_name}".strip()

        # Extract affiliations
        affiliations = []
        addresses = data.get("addresses", {}).get("address", [])

        for addr in addresses:
            country = addr.get("country", {}).get("value")
            if country:
                affiliations.append({"country": country})

        return {
            "orcid_id": orcid_id,
            "name": full_name,
            "given_names": given_names,
            "family_name": family_name,
            "affiliations": affiliations,
            "source": "orcid",
        }

    def collect_batch(self, orcid_ids: List[str], batch_size: int = 100) -> List[Dict]:
        """
        Collect profiles in batches with progress tracking.

        Args:
            orcid_ids: List of ORCID IDs to fetch
            batch_size: Progress update frequency

        Returns:
            List of profiles
        """
        profiles = []
        total = len(orcid_ids)

        print(f"\nFetching {total} ORCID profiles...")

        for i, orcid_id in enumerate(orcid_ids):
            profile = self.get_profile(orcid_id)

            if profile:
                profiles.append(profile)

            # Progress update
            if (i + 1) % batch_size == 0 or (i + 1) == total:
                print(f"  Progress: {i+1}/{total} ({len(profiles)} valid profiles)")

            # Rate limiting (ORCID allows ~24 requests/second)
            time.sleep(0.05)

        print(f"✅ Collected {len(profiles)} profiles")
        return profiles

    def save_profiles(self, profiles: List[Dict], output_path: str):
        """Save profiles to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "source": "orcid",
                "total_profiles": len(profiles),
                "collection_date": time.strftime("%Y-%m-%d"),
                "api_version": "v3.0",
            },
            "profiles": profiles,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved to {output_path}")


def main():
    """Collect mathematician profiles from ORCID."""
    print("=" * 80)
    print("ORCID MATHEMATICIAN DATA COLLECTION")
    print("=" * 80)
    print()

    # ORCID credentials — read from env (ORCID_CLIENT_ID/_SECRET).
    # The previously-committed literals are in git history: REVOKE that app.
    CLIENT_ID = os.environ[
        "ORCID_CLIENT_ID"
    ]  # R54: was a committed literal (rotate the old app!)
    CLIENT_SECRET = os.environ[
        "ORCID_CLIENT_SECRET"
    ]  # R54: was a committed literal — REVOKE it in the ORCID dev dashboard

    # Initialize collector
    collector = ORCIDCollector(CLIENT_ID, CLIENT_SECRET)

    # Search for mathematicians
    print("Phase 1: Searching for mathematician ORCID IDs...")
    orcid_ids = collector.search_mathematicians(
        query="mathematics", max_results=10000  # Target 10K profiles
    )

    # Collect profiles
    print("\nPhase 2: Fetching full profiles...")
    profiles = collector.collect_batch(orcid_ids)

    # Save results
    output_path = "data/real_world_collection/orcid_mathematicians.json"
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
            country = affiliation.get("country", "Unknown")
            country_counts[country] = country_counts.get(country, 0) + 1

    print("\nTop 10 Countries:")
    for country, count in sorted(
        country_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        print(f"  {country}: {count}")

    print()
    print(f"Data saved to: {output_path}")


if __name__ == "__main__":
    main()
