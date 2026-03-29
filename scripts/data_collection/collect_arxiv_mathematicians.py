#!/usr/bin/env python3
"""
arXiv Data Collector - Real Mathematician Names

Collect author names from arXiv mathematics papers.
arXiv has a free API with no authentication required.

API docs: https://info.arxiv.org/help/api/index.html
"""

import requests
import xml.etree.ElementTree as ET
import time
from typing import List, Dict, Set
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ArxivCollector:
    """Collect mathematician names from arXiv papers."""

    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

    def search_papers(self, category: str = "math", max_results: int = 10000) -> List[Dict]:
        """
        Search arXiv for mathematics papers.

        Args:
            category: arXiv category (default: "math" for all mathematics)
            max_results: Maximum papers to retrieve

        Returns:
            List of paper records with authors
        """
        print(f"Searching arXiv for category: {category}")
        print(f"Target: {max_results} papers")

        papers = []
        start = 0
        max_per_request = 1000  # arXiv API limit

        while len(papers) < max_results:
            batch_size = min(max_per_request, max_results - len(papers))

            print(f"  Fetching papers {start} to {start + batch_size}...")

            params = {
                "search_query": f"cat:{category}.*",  # All math subcategories
                "start": start,
                "max_results": batch_size,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }

            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"⚠️  Request failed: {e}")
                break

            # Parse XML response
            root = ET.fromstring(response.content)

            # Extract papers
            entries = root.findall("atom:entry", self.namespaces)

            if not entries:
                print("No more papers found")
                break

            for entry in entries:
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)

            start += batch_size

            # Rate limiting (arXiv requests no more than 1 request per 3 seconds)
            time.sleep(3)

            # Check if we got fewer results than requested (end of results)
            if len(entries) < batch_size:
                break

        print(f"✅ Found {len(papers)} papers")
        return papers

    def _parse_entry(self, entry: ET.Element) -> Optional[Dict]:
        """Parse a single arXiv entry."""
        # Extract authors
        authors = []
        author_elements = entry.findall("atom:author", self.namespaces)

        for author_elem in author_elements:
            name_elem = author_elem.find("atom:name", self.namespaces)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())

        if not authors:
            return None

        # Extract paper ID
        id_elem = entry.find("atom:id", self.namespaces)
        paper_id = id_elem.text if id_elem is not None else None

        # Extract title
        title_elem = entry.find("atom:title", self.namespaces)
        title = title_elem.text.strip() if title_elem is not None else None

        # Extract categories
        categories = []
        for category_elem in entry.findall("atom:category", self.namespaces):
            term = category_elem.get("term")
            if term:
                categories.append(term)

        # Extract published date
        published_elem = entry.find("atom:published", self.namespaces)
        published = published_elem.text if published_elem is not None else None

        return {
            "arxiv_id": paper_id,
            "title": title,
            "authors": authors,
            "categories": categories,
            "published": published,
        }

    def extract_unique_authors(self, papers: List[Dict]) -> List[Dict]:
        """
        Extract unique author names from papers.

        Returns:
            List of author profiles with paper counts
        """
        print(f"\nExtracting unique authors from {len(papers)} papers...")

        author_stats = defaultdict(lambda: {"count": 0, "categories": set()})

        for paper in papers:
            for author in paper["authors"]:
                author_stats[author]["count"] += 1
                author_stats[author]["categories"].update(paper.get("categories", []))

        # Convert to list of profiles
        profiles = []
        for author_name, stats in author_stats.items():
            profiles.append(
                {
                    "name": author_name,
                    "paper_count": stats["count"],
                    "categories": list(stats["categories"]),
                    "source": "arxiv",
                }
            )

        print(f"✅ Found {len(profiles)} unique authors")
        return profiles

    def save_profiles(self, profiles: List[Dict], papers: List[Dict], output_path: str):
        """Save profiles and paper data to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Category statistics
        category_counts = defaultdict(int)
        for paper in papers:
            for cat in paper.get("categories", []):
                category_counts[cat] += 1

        data = {
            "metadata": {
                "source": "arxiv",
                "total_papers": len(papers),
                "total_authors": len(profiles),
                "collection_date": time.strftime("%Y-%m-%d"),
                "top_categories": dict(
                    sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:20]
                ),
            },
            "profiles": profiles,
            "papers_sample": papers[:100],  # Save first 100 papers as examples
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved to {output_path}")


def main():
    """Collect mathematician names from arXiv."""
    print("=" * 80)
    print("ARXIV MATHEMATICIAN DATA COLLECTION")
    print("=" * 80)
    print()

    # Initialize collector
    collector = ArxivCollector()

    # Search for mathematics papers
    print("Phase 1: Collecting mathematics papers from arXiv...")
    papers = collector.search_papers(category="math", max_results=5000)

    # Extract unique authors
    print("\nPhase 2: Extracting unique author names...")
    profiles = collector.extract_unique_authors(papers)

    # Save results
    output_path = "data/real_world_collection/arxiv_mathematicians.json"
    collector.save_profiles(profiles, papers, output_path)

    # Statistics
    print("\n" + "=" * 80)
    print("COLLECTION COMPLETE")
    print("=" * 80)
    print(f"Total papers: {len(papers)}")
    print(f"Total unique authors: {len(profiles)}")

    # Top prolific authors
    top_authors = sorted(profiles, key=lambda x: x["paper_count"], reverse=True)[:10]
    print("\nTop 10 Most Prolific Authors:")
    for i, profile in enumerate(top_authors, 1):
        print(f"  {i}. {profile['name']} ({profile['paper_count']} papers)")

    # Top categories
    category_counts = defaultdict(int)
    for profile in profiles:
        for cat in profile.get("categories", []):
            category_counts[cat] += 1

    print("\nTop 10 Math Categories:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cat}: {count} authors")

    print()
    print(f"Data saved to: {output_path}")


if __name__ == "__main__":
    import json

    main()
