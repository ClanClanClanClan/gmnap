#!/usr/bin/env python3
"""
Crossref Authority API Implementation for GMNAP V7
Tier-0 authority source: CC0 license, 4.3M daily quota
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CrossrefAuthor:
    """Crossref author data structure"""

    given: Optional[str] = None
    family: Optional[str] = None
    sequence: Optional[str] = None
    affiliation: List[Dict] = None
    orcid: Optional[str] = None
    authenticated_orcid: bool = False

    @property
    def canonical_name(self) -> str:
        """Return name in 'Family, Given' format"""
        if self.family and self.given:
            return f"{self.family}, {self.given}"
        elif self.family:
            return self.family
        elif self.given:
            return self.given
        return ""


class CrossrefAPI:
    """
    Crossref REST API client for V7 authority enrichment

    Implements:
    - Rate limiting (per Crossref etiquette)
    - Async batch processing
    - Author deduplication
    - Confidence scoring
    """

    BASE_URL = "https://api.crossref.org"
    POLITE_POOL_DELAY = 0.1  # 10 requests/second for polite pool
    USER_AGENT = "GMNAP/7.0 (https://github.com/gmnap; mailto:gmnap@eth.ch)"

    def __init__(self, mailto: str = None):
        """
        Initialize Crossref API client

        Args:
            mailto: Email for polite pool access (faster rate limits)
        """
        self.mailto = mailto or "gmnap@eth.ch"
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.last_request_time = 0

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.USER_AGENT, "mailto": self.mailto}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        """Enforce polite rate limiting"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.POLITE_POOL_DELAY:
            await asyncio.sleep(self.POLITE_POOL_DELAY - elapsed)
        self.last_request_time = time.time()

    async def search_author(self, name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for author in Crossref

        Args:
            name: Author name to search
            limit: Maximum results to return

        Returns:
            List of author records with metadata
        """
        await self._rate_limit()

        # Build query
        query_name = quote_plus(name)
        url = f"{self.BASE_URL}/works"
        params = {
            "query.author": name,
            "rows": limit,
            "select": "DOI,title,author,published-print,publisher,container-title,type,subject",
        }

        try:
            async with self.session.get(url, params=params) as response:
                self.request_count += 1

                if response.status != 200:
                    logger.warning(
                        f"Crossref API returned {response.status} for {name}"
                    )
                    return []

                data = await response.json()

                # Extract author information from works
                authors = []
                for item in data.get("message", {}).get("items", []):
                    for author_data in item.get("author", []):
                        author = CrossrefAuthor(
                            given=author_data.get("given"),
                            family=author_data.get("family"),
                            sequence=author_data.get("sequence"),
                            affiliation=author_data.get("affiliation", []),
                            orcid=author_data.get("ORCID"),
                        )

                        # Add metadata from the work
                        author_record = {
                            "source": "Crossref",
                            "canonical_name": author.canonical_name,
                            "given": author.given,
                            "family": author.family,
                            "orcid": author.orcid,
                            "affiliations": self._extract_affiliations(
                                author.affiliation
                            ),
                            "work_doi": item.get("DOI"),
                            "work_title": (
                                item.get("title", [""])[0] if item.get("title") else ""
                            ),
                            "work_year": self._extract_year(
                                item.get("published-print")
                            ),
                            "work_type": item.get("type"),
                            "subjects": item.get("subject", []),
                            "confidence": self._calculate_confidence(name, author),
                        }

                        authors.append(author_record)

                return self._deduplicate_authors(authors)

        except Exception as e:
            logger.error(f"Error searching Crossref for {name}: {e}")
            return []

    def _extract_affiliations(self, affiliations: List[Dict]) -> List[str]:
        """Extract affiliation names"""
        if not affiliations:
            return []
        return [aff.get("name", "") for aff in affiliations if aff.get("name")]

    def _extract_year(self, date_parts: Dict) -> Optional[int]:
        """Extract year from Crossref date format"""
        if not date_parts:
            return None
        parts = date_parts.get("date-parts", [[]])
        if parts and parts[0]:
            return parts[0][0] if len(parts[0]) > 0 else None
        return None

    def _calculate_confidence(self, query_name: str, author: CrossrefAuthor) -> float:
        """
        Calculate confidence score for name match

        Simple algorithm:
        - Exact match: 100
        - Family name match: 70
        - Given name match: 30
        - Has ORCID: +10
        """
        query_lower = query_name.lower().strip()
        confidence = 0.0

        if author.canonical_name.lower() == query_lower:
            confidence = 100.0
        elif author.family and author.family.lower() in query_lower:
            confidence = 70.0
        elif author.given and author.given.lower() in query_lower:
            confidence = 30.0

        if author.orcid:
            confidence = min(100.0, confidence + 10.0)

        return confidence

    def _deduplicate_authors(self, authors: List[Dict]) -> List[Dict]:
        """
        Deduplicate author records by canonical name + ORCID
        Keep the one with highest confidence
        """
        seen = {}
        for author in authors:
            key = (author["canonical_name"], author.get("orcid"))
            if key not in seen or author["confidence"] > seen[key]["confidence"]:
                seen[key] = author

        return list(seen.values())

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a GMNAP entry with Crossref data

        Args:
            entry: GMNAP entry dictionary

        Returns:
            Enriched entry with Crossref metadata
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        if not name:
            return entry

        # Search Crossref
        authors = await self.search_author(name)

        if not authors:
            return entry

        # Take highest confidence match
        best_match = max(authors, key=lambda x: x["confidence"])

        # Enrich entry
        if "ExternalIDs" not in entry:
            entry["ExternalIDs"] = []

        # Add ORCID if found
        if best_match.get("orcid"):
            entry["ExternalIDs"].append(
                {
                    "type": "ORCID",
                    "value": best_match["orcid"],
                    "source": "Crossref",
                    "confidence": best_match["confidence"],
                }
            )

        # Add affiliations
        if best_match.get("affiliations"):
            if "Affiliations" not in entry:
                entry["Affiliations"] = []
            for aff in best_match["affiliations"]:
                entry["Affiliations"].append({"institution": aff, "source": "Crossref"})

        # Add Crossref metadata
        entry["AuthoritySources"] = entry.get("AuthoritySources", [])
        entry["AuthoritySources"].append(
            {
                "source": "Crossref",
                "last_updated": datetime.utcnow().isoformat(),
                "confidence": best_match["confidence"],
                "work_count": len(
                    [
                        a
                        for a in authors
                        if a["canonical_name"] == best_match["canonical_name"]
                    ]
                ),
            }
        )

        return entry

    async def batch_enrich(
        self, entries: List[Dict[str, Any]], max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple entries concurrently

        Args:
            entries: List of GMNAP entries
            max_concurrent: Maximum concurrent requests

        Returns:
            List of enriched entries
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_with_limit(entry):
            async with semaphore:
                return await self.enrich_entry(entry)

        tasks = [enrich_with_limit(entry) for entry in entries]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            "request_count": self.request_count,
            "mailto": self.mailto,
            "daily_quota": 4_300_000,
            "remaining_quota": 4_300_000 - self.request_count,
        }


# Example usage for testing
async def test_crossref_api():
    """Test the Crossref API implementation"""
    async with CrossrefAPI() as api:
        # Test single author search
        results = await api.search_author("Terence Tao")
        print(f"Found {len(results)} results for Terence Tao")
        if results:
            print(
                f"Best match: {results[0]['canonical_name']} (confidence: {results[0]['confidence']})"
            )

        # Test entry enrichment
        test_entry = {"GlobalID": "test-001", "CanonicalLatin": "Terence Tao"}
        enriched = await api.enrich_entry(test_entry)
        print(f"Enriched entry: {json.dumps(enriched, indent=2)}")

        # Show stats
        print(f"API stats: {api.get_stats()}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_crossref_api())
