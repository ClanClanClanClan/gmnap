#!/usr/bin/env python3
"""
OpenAlex Authority API Implementation for GMNAP V7
Tier-0 authority source: CC0 license, 864k daily quota
Provides comprehensive author profiles with institution data
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OpenAlexAuthor:
    """OpenAlex author data structure"""

    id: str
    orcid: Optional[str] = None
    display_name: str = ""
    display_name_alternatives: List[str] = field(default_factory=list)
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    i10_index: int = 0
    last_known_institution: Optional[Dict] = None
    x_concepts: List[Dict] = field(default_factory=list)
    works_api_url: Optional[str] = None
    created_date: Optional[str] = None
    updated_date: Optional[str] = None

    @property
    def canonical_name(self) -> str:
        """Return name in canonical format"""
        # OpenAlex provides display_name in various formats
        # Try to convert to "Family, Given" if possible
        name = self.display_name
        if "," not in name and " " in name:
            # Assume Western order: Given Family
            parts = name.rsplit(" ", 1)
            if len(parts) == 2:
                return f"{parts[1]}, {parts[0]}"
        return name

    @property
    def institution_name(self) -> Optional[str]:
        """Get primary institution name"""
        if self.last_known_institution:
            return self.last_known_institution.get("display_name")
        return None

    @property
    def institution_country(self) -> Optional[str]:
        """Get institution country code"""
        if self.last_known_institution:
            return self.last_known_institution.get("country_code")
        return None

    @property
    def primary_concepts(self) -> List[str]:
        """Get top research concepts"""
        # x_concepts are sorted by score
        return [c["display_name"] for c in self.x_concepts[:5] if "display_name" in c]


class OpenAlexAPI:
    """
    OpenAlex REST API client for V7 authority enrichment

    OpenAlex provides:
    - 260M+ authors
    - 250M+ works
    - Institution affiliations
    - Citation metrics (h-index, i10-index)
    - Research concepts/topics
    - Co-authorship networks
    """

    BASE_URL = "https://api.openalex.org"
    POLITE_POOL_DELAY = 0.1  # 10 requests/second for polite pool
    USER_AGENT = "GMNAP/7.0 (https://github.com/gmnap; mailto:gmnap@eth.ch)"

    def __init__(self, mailto: str = None):
        """
        Initialize OpenAlex API client

        Args:
            mailto: Email for polite pool access (required for faster rates)
        """
        self.mailto = mailto or "gmnap@eth.ch"
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.last_request_time = 0

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"}
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

    async def search_authors(self, name: str, limit: int = 10) -> List[OpenAlexAuthor]:
        """
        Search for authors in OpenAlex

        Args:
            name: Author name to search
            limit: Maximum results to return

        Returns:
            List of OpenAlexAuthor objects
        """
        await self._rate_limit()

        # Build query with mailto for polite pool
        params = {"search": name, "per-page": limit, "mailto": self.mailto}

        url = f"{self.BASE_URL}/authors"

        try:
            async with self.session.get(url, params=params) as response:
                self.request_count += 1

                if response.status != 200:
                    logger.warning(f"OpenAlex API returned {response.status} for {name}")
                    return []

                data = await response.json()

                authors = []
                for item in data.get("results", []):
                    author = OpenAlexAuthor(
                        id=item.get("id", ""),
                        orcid=item.get("orcid"),
                        display_name=item.get("display_name", ""),
                        display_name_alternatives=item.get("display_name_alternatives", []),
                        works_count=item.get("works_count", 0),
                        cited_by_count=item.get("cited_by_count", 0),
                        h_index=item.get("summary_stats", {}).get("h_index", 0),
                        i10_index=item.get("summary_stats", {}).get("i10_index", 0),
                        last_known_institution=item.get("last_known_institution"),
                        x_concepts=item.get("x_concepts", []),
                        works_api_url=item.get("works_api_url"),
                        created_date=item.get("created_date"),
                        updated_date=item.get("updated_date"),
                    )
                    authors.append(author)

                return authors

        except Exception as e:
            logger.error(f"Error searching OpenAlex for {name}: {e}")
            return []

    async def get_author_by_orcid(self, orcid: str) -> Optional[OpenAlexAuthor]:
        """
        Get author by ORCID identifier

        Args:
            orcid: ORCID identifier (with or without URL prefix)

        Returns:
            OpenAlexAuthor object or None
        """
        await self._rate_limit()

        # Clean ORCID
        if "/" in orcid:
            orcid = orcid.split("/")[-1]

        url = f"{self.BASE_URL}/authors/orcid:{orcid}"
        params = {"mailto": self.mailto}

        try:
            async with self.session.get(url, params=params) as response:
                self.request_count += 1

                if response.status == 404:
                    return None
                elif response.status != 200:
                    logger.warning(f"OpenAlex API returned {response.status} for ORCID {orcid}")
                    return None

                item = await response.json()

                return OpenAlexAuthor(
                    id=item.get("id", ""),
                    orcid=item.get("orcid"),
                    display_name=item.get("display_name", ""),
                    display_name_alternatives=item.get("display_name_alternatives", []),
                    works_count=item.get("works_count", 0),
                    cited_by_count=item.get("cited_by_count", 0),
                    h_index=item.get("summary_stats", {}).get("h_index", 0),
                    i10_index=item.get("summary_stats", {}).get("i10_index", 0),
                    last_known_institution=item.get("last_known_institution"),
                    x_concepts=item.get("x_concepts", []),
                    works_api_url=item.get("works_api_url"),
                    created_date=item.get("created_date"),
                    updated_date=item.get("updated_date"),
                )

        except Exception as e:
            logger.error(f"Error fetching ORCID {orcid} from OpenAlex: {e}")
            return None

    async def get_coauthors(self, author_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get coauthors for an author

        Args:
            author_id: OpenAlex author ID
            limit: Maximum coauthors to return

        Returns:
            List of coauthor information
        """
        await self._rate_limit()

        # Get works by this author
        url = f"{self.BASE_URL}/works"
        params = {
            "filter": f"author.id:{author_id}",
            "per-page": 50,  # Get recent works
            "mailto": self.mailto,
        }

        try:
            async with self.session.get(url, params=params) as response:
                self.request_count += 1

                if response.status != 200:
                    return []

                data = await response.json()

                # Extract unique coauthors
                coauthors = {}
                for work in data.get("results", []):
                    for authorship in work.get("authorships", []):
                        author = authorship.get("author", {})
                        if author.get("id") != author_id:
                            aid = author.get("id")
                            if aid and aid not in coauthors:
                                coauthors[aid] = {
                                    "id": aid,
                                    "display_name": author.get("display_name"),
                                    "orcid": author.get("orcid"),
                                    "collaboration_count": 1,
                                }
                            elif aid:
                                coauthors[aid]["collaboration_count"] += 1

                # Sort by collaboration count
                sorted_coauthors = sorted(
                    coauthors.values(), key=lambda x: x["collaboration_count"], reverse=True
                )

                return sorted_coauthors[:limit]

        except Exception as e:
            logger.error(f"Error fetching coauthors for {author_id}: {e}")
            return []

    def _calculate_confidence(self, query_name: str, author: OpenAlexAuthor) -> float:
        """
        Calculate confidence score for name match

        Enhanced algorithm using:
        - Name similarity
        - Alternative names
        - Citation metrics
        - ORCID presence
        """
        query_lower = query_name.lower().strip()
        confidence = 0.0

        # Check primary name
        if author.display_name.lower() == query_lower:
            confidence = 95.0
        elif query_lower in author.display_name.lower():
            confidence = 70.0

        # Check alternative names
        for alt_name in author.display_name_alternatives:
            if alt_name.lower() == query_lower:
                confidence = max(confidence, 90.0)
            elif query_lower in alt_name.lower():
                confidence = max(confidence, 65.0)

        # Boost for ORCID
        if author.orcid:
            confidence = min(100.0, confidence + 5.0)

        # Boost for high citation count (likely the right person)
        if author.cited_by_count > 1000:
            confidence = min(100.0, confidence + 5.0)
        elif author.cited_by_count > 100:
            confidence = min(100.0, confidence + 3.0)

        # Boost for high h-index
        if author.h_index > 20:
            confidence = min(100.0, confidence + 3.0)

        return confidence

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a GMNAP entry with OpenAlex data

        Args:
            entry: GMNAP entry dictionary

        Returns:
            Enriched entry with OpenAlex metadata
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        if not name:
            return entry

        # First check if we have an ORCID
        orcid = None
        for ext_id in entry.get("ExternalIDs", []):
            if ext_id.get("type") == "ORCID":
                orcid = ext_id.get("value")
                break

        author = None

        # If we have ORCID, use it for precise lookup
        if orcid:
            author = await self.get_author_by_orcid(orcid)

        # Otherwise search by name
        if not author:
            authors = await self.search_authors(name, limit=5)
            if authors:
                # Take highest confidence match
                best_match = max(authors, key=lambda a: self._calculate_confidence(name, a))
                if self._calculate_confidence(name, best_match) >= 50:
                    author = best_match

        if not author:
            return entry

        # Enrich entry with OpenAlex data
        if "ExternalIDs" not in entry:
            entry["ExternalIDs"] = []

        # Add OpenAlex ID
        entry["ExternalIDs"].append({"type": "OpenAlex", "value": author.id, "source": "OpenAlex"})

        # Add/update ORCID if found
        if author.orcid and not orcid:
            entry["ExternalIDs"].append(
                {
                    "type": "ORCID",
                    "value": author.orcid,
                    "source": "OpenAlex",
                    "confidence": 100.0,  # OpenAlex ORCIDs are verified
                }
            )

        # Add institution
        if author.institution_name:
            if "Affiliations" not in entry:
                entry["Affiliations"] = []
            entry["Affiliations"].append(
                {
                    "institution": author.institution_name,
                    "country": author.institution_country,
                    "source": "OpenAlex",
                    "type": "last_known",
                }
            )

        # Add metrics
        entry["Metrics"] = entry.get("Metrics", {})
        entry["Metrics"]["openalex"] = {
            "works_count": author.works_count,
            "cited_by_count": author.cited_by_count,
            "h_index": author.h_index,
            "i10_index": author.i10_index,
        }

        # Add research topics
        if author.primary_concepts:
            entry["ResearchTopics"] = entry.get("ResearchTopics", [])
            for concept in author.primary_concepts:
                if concept not in entry["ResearchTopics"]:
                    entry["ResearchTopics"].append(concept)

        # Add alternative names
        if author.display_name_alternatives:
            if "VariantNames" not in entry:
                entry["VariantNames"] = []
            for alt_name in author.display_name_alternatives:
                entry["VariantNames"].append(
                    {"name": alt_name, "source": "OpenAlex", "type": "alternative"}
                )

        # Add authority source metadata
        entry["AuthoritySources"] = entry.get("AuthoritySources", [])
        entry["AuthoritySources"].append(
            {
                "source": "OpenAlex",
                "id": author.id,
                "last_updated": datetime.now(datetime.UTC).isoformat(),
                "confidence": self._calculate_confidence(name, author),
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
            "daily_quota": 864_000,
            "remaining_quota": 864_000 - self.request_count,
            "features": [
                "260M+ authors",
                "250M+ works",
                "Institution data",
                "Citation metrics",
                "Research concepts",
                "Coauthorship networks",
            ],
        }


# Example usage for testing
async def test_openalex_api():
    """Test the OpenAlex API implementation"""
    async with OpenAlexAPI() as api:
        # Test author search
        print("Testing OpenAlex API...")
        authors = await api.search_authors("T. Tao", limit=3)
        print(f"Found {len(authors)} results for T. Tao")

        if authors:
            author = authors[0]
            print(f"\nBest match: {author.display_name}")
            print(f"  OpenAlex ID: {author.id}")
            print(f"  ORCID: {author.orcid}")
            print(f"  Institution: {author.institution_name}")
            print(f"  Works: {author.works_count}")
            print(f"  Citations: {author.cited_by_count}")
            print(f"  h-index: {author.h_index}")
            print(f"  Topics: {', '.join(author.primary_concepts[:3])}")

            # Test coauthors
            coauthors = await api.get_coauthors(author.id, limit=5)
            if coauthors:
                print(f"\nTop coauthors:")
                for coauthor in coauthors[:3]:
                    print(
                        f"  - {coauthor['display_name']} ({coauthor['collaboration_count']} papers)"
                    )

        # Test entry enrichment
        test_entry = {"GlobalID": "test-002", "CanonicalLatin": "Maryam Mirzakhani"}
        enriched = await api.enrich_entry(test_entry)
        print(f"\nEnriched entry for {test_entry['CanonicalLatin']}:")
        print(f"  Metrics: {enriched.get('Metrics', {}).get('openalex', {})}")
        print(f"  Topics: {enriched.get('ResearchTopics', [])[:3]}")

        # Show stats
        print(f"\nAPI stats: {api.get_stats()}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_openalex_api())
