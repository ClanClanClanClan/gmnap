#!/usr/bin/env python3
"""
Robust Multi-Source Data Collector
Collects mathematician data from multiple sources with retry logic and error handling.
"""

import requests
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class RobustCollector:
    """Robust data collector with retry logic and error handling."""

    def __init__(self, output_dir: str = "data/real_world_collection"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    def retry_request(
        self,
        url: str,
        params: dict = None,
        headers: dict = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> Optional[requests.Response]:
        """Make HTTP request with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url, params=params, headers=headers, timeout=30
                )
                if response.status_code == 200:
                    return response
                elif response.status_code == 403 and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    print(f"  ⚠️  403 Forbidden, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"  ❌ Request failed: {response.status_code}")
                    return None
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    print(f"  ⚠️  Request error: {e}, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"  ❌ Request failed after {max_retries} attempts: {e}")
                    return None
        return None

    def collect_openalex(self, target: int = 1000) -> List[Dict]:
        """Collect OpenAlex mathematician profiles with robust error handling."""
        print("\n" + "=" * 80)
        print("COLLECTING FROM OPENALEX")
        print("=" * 80)
        print(f"Target: {target} authors\n")

        authors = []
        page = 1
        per_page = 200

        headers = {
            "User-Agent": "GMNAP-DataCollector/1.0 (mailto:research@gmnap.org)",
            "Accept": "application/json",
        }

        while len(authors) < target:
            print(f"  Page {page} ({len(authors)}/{target})...")

            response = self.retry_request(
                "https://api.openalex.org/authors",
                params={
                    "filter": "topics.id:T10528",  # Mathematics topic
                    "per-page": per_page,
                    "page": page,
                    "select": "id,display_name,last_known_institutions,works_count",
                },
                headers=headers,
            )

            if not response:
                print("  ⚠️  Stopping OpenAlex collection due to errors")
                break

            data = response.json()
            results = data.get("results", [])

            if not results:
                print("  No more results available")
                break

            for author in results:
                name = author.get("display_name")
                if name:
                    # Extract institution info
                    institutions = author.get("last_known_institutions", [])
                    country = (
                        institutions[0].get("country_code") if institutions else None
                    )

                    authors.append(
                        {
                            "name": name,
                            "country_code": country,
                            "works_count": author.get("works_count", 0),
                            "source": "openalex",
                        }
                    )

            page += 1
            time.sleep(0.1)  # Rate limiting

            if len(authors) >= target:
                break

        print(f"✅ Collected {len(authors)} OpenAlex profiles\n")
        return authors[:target]

    def collect_arxiv(self, target: int = 500) -> List[Dict]:
        """Collect arXiv author names from recent math papers."""
        print("=" * 80)
        print("COLLECTING FROM ARXIV")
        print("=" * 80)
        print(f"Target: {target} papers\n")

        authors = {}  # Use dict to deduplicate by name
        batch_size = 100

        for start in range(0, target, batch_size):
            print(f"  Papers {start} to {start + batch_size}...")

            response = self.retry_request(
                "http://export.arxiv.org/api/query",
                params={
                    "search_query": "cat:math.*",
                    "start": start,
                    "max_results": batch_size,
                    "sortBy": "lastUpdatedDate",
                    "sortOrder": "descending",
                },
            )

            if not response:
                print("  ⚠️  Stopping arXiv collection due to errors")
                break

            # Parse XML response
            from xml.etree import ElementTree as ET

            root = ET.fromstring(response.content)

            # Extract authors from entries
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                for author in entry.findall("atom:author", ns):
                    name_elem = author.find("atom:name", ns)
                    if name_elem is not None:
                        name = name_elem.text.strip()
                        if name and name not in authors:
                            authors[name] = {"name": name, "source": "arxiv"}

            time.sleep(3)  # arXiv rate limiting (required)

        author_list = list(authors.values())
        print(f"✅ Collected {len(author_list)} unique arXiv authors\n")
        return author_list

    def collect_all(self, openalex_target: int = 1000, arxiv_target: int = 500) -> Dict:
        """Collect from all sources and save results."""
        print("\n" + "=" * 80)
        print("ROBUST MULTI-SOURCE DATA COLLECTION")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"OpenAlex target: {openalex_target}")
        print(f"arXiv target: {arxiv_target}")
        print("=" * 80)

        results = {
            "timestamp": datetime.now().isoformat(),
            "sources": {},
            "all_profiles": [],
        }

        # Collect OpenAlex
        try:
            openalex_profiles = self.collect_openalex(openalex_target)
            results["sources"]["openalex"] = len(openalex_profiles)
            results["all_profiles"].extend(openalex_profiles)
            print(f"✅ OpenAlex: {len(openalex_profiles)} profiles")
        except Exception as e:
            print(f"❌ OpenAlex collection failed: {e}")
            results["sources"]["openalex"] = 0

        # Collect arXiv
        try:
            arxiv_profiles = self.collect_arxiv(arxiv_target)
            results["sources"]["arxiv"] = len(arxiv_profiles)
            results["all_profiles"].extend(arxiv_profiles)
            print(f"✅ arXiv: {len(arxiv_profiles)} profiles")
        except Exception as e:
            print(f"❌ arXiv collection failed: {e}")
            results["sources"]["arxiv"] = 0

        # Save results
        output_file = (
            self.output_dir
            / f"robust_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 80)
        print("COLLECTION COMPLETE")
        print("=" * 80)
        print(f"Total profiles: {len(results['all_profiles'])}")
        print(f"By source:")
        for source, count in results["sources"].items():
            print(f"  {source}: {count}")
        print(f"\nSaved to: {output_file}")
        print("=" * 80)

        return results


def main():
    """Run robust data collection."""
    collector = RobustCollector()

    # Collect with reasonable targets
    results = collector.collect_all(
        openalex_target=1000,  # 1K OpenAlex profiles
        arxiv_target=500,  # 500 arXiv papers (~1500 unique authors)
    )

    print(f"\n✅ Collection successful!")
    print(f"Total collected: {len(results['all_profiles'])} profiles")


if __name__ == "__main__":
    main()
