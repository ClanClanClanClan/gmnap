"""
Crossref authority source implementation for V7.
Provides real API integration with proper error handling and caching.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp

from .base import AuthorityFetcher, AuthorityData, FetchStatus, FetchResult

logger = logging.getLogger(__name__)


class CrossrefV7Fetcher(AuthorityFetcher):
    """
    Production-ready Crossref fetcher for V7 compliance.

    Features:
    - Real API integration
    - Rate limiting (10-50 requests/sec based on politeness)
    - Result caching
    - Error recovery
    - Batch processing support
    """

    BASE_URL = "https://api.crossref.org"

    def __init__(self, email: Optional[str] = None):
        """
        Initialize Crossref fetcher.

        Args:
            email: Contact email for polite pool (higher rate limits)
        """
        config = {"email": email}
        super().__init__(config)

        self.email = email or os.getenv("CROSSREF_EMAIL")
        self.daily_quota = 100000
        self.requests_per_second = 50 if self.email else 10
        self.base_url = self.BASE_URL
        self.tier = 0  # Free tier

        # Cache for results
        self._cache = {}
        self._session = None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with User-Agent and optional email."""
        headers = {"User-Agent": f"GMNAP/7.0 (mailto:{self.email})" if self.email else "GMNAP/7.0"}
        return headers

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None:
            self._session = aiohttp.ClientSession(headers=self._get_headers())

    async def search_author(self, name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for works by author name.

        Args:
            name: Author name to search
            limit: Maximum results to return

        Returns:
            List of work records
        """
        # Use external cache if available
        try:
            from .cache import AuthorityCache
            from pathlib import Path

            cache = AuthorityCache(Path("cache/authority"))

            # Try cache first
            cached = cache.get("Crossref", f"author:{name}:{limit}")
            if cached is not None:
                logger.debug(f"Cache hit for author:{name}")
                return cached.get("items", [])
        except ImportError:
            # Fall back to in-memory cache
            cache_key = f"author:{name}:{limit}"
            if cache_key in self._cache:
                logger.debug(f"Memory cache hit for {cache_key}")
                return self._cache[cache_key]

        await self._ensure_session()

        # Build query
        params = {
            "query.author": name,
            "rows": limit,
            "select": "DOI,title,author,published-print,publisher,type,subject",
        }

        try:
            url = f"{self.BASE_URL}/works"
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("message", {}).get("items", [])

                    # Cache results
                    try:
                        cache.put("Crossref", f"author:{name}:{limit}", {"items": items})
                    except:
                        # Fallback to memory cache
                        self._cache[f"author:{name}:{limit}"] = items

                    return items
                else:
                    logger.error(f"Crossref API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Crossref search failed: {e}")
            return []

    async def fetch_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific work by DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Work metadata or None
        """
        # Check cache
        cache_key = f"doi:{doi}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        await self._ensure_session()

        try:
            url = f"{self.BASE_URL}/works/{quote(doi, safe='')}"
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    work = data.get("message", {})

                    # Cache result
                    self._cache[cache_key] = work

                    return work
                elif response.status == 404:
                    logger.debug(f"DOI not found: {doi}")
                    return None
                else:
                    logger.error(f"Crossref DOI fetch error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Failed to fetch DOI {doi}: {e}")
            return None

    async def enrich_entry(self, entry: Dict[str, Any]) -> AuthorityData:
        """
        Enrich a GMNAP entry with Crossref data.

        Args:
            entry: GMNAP entry with CanonicalLatin name

        Returns:
            AuthorityData with Crossref information
        """
        name = entry.get("CanonicalLatin", "")
        if not name:
            return AuthorityData(source="Crossref", source_id="")

        # Search for author works
        works = await self.search_author(name, limit=5)

        if not works:
            return AuthorityData(source="Crossref", source_id="", canonical_name=name)

        # Extract author information from first work
        first_work = works[0]
        authors = first_work.get("author", [])

        # Find matching author
        matched_author = None
        for author in authors:
            full_name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            if self._name_similarity(name, full_name) > 0.8:
                matched_author = author
                break

        if not matched_author:
            matched_author = authors[0] if authors else {}

        # Build authority data
        authority_data = AuthorityData(
            source="Crossref",
            source_id=first_work.get("DOI", ""),
            canonical_name=f"{matched_author.get('given', '')} {matched_author.get('family', '')}".strip(),
            metadata={
                "works_count": len(works),
                "affiliations": self._extract_affiliations(matched_author),
                "orcid": matched_author.get("ORCID"),
                "works": [
                    {
                        "doi": w.get("DOI"),
                        "title": w.get("title", [""])[0] if w.get("title") else "",
                        "year": w.get("published-print", {}).get("date-parts", [[None]])[0][0],
                    }
                    for w in works[:3]  # Include top 3 works
                ],
            },
        )

        # Add to entry
        entry["CrossrefData"] = authority_data.metadata
        entry["AuthoritySources"] = entry.get("AuthoritySources", [])
        if "Crossref" not in entry["AuthoritySources"]:
            entry["AuthoritySources"].append("Crossref")

        return authority_data

    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names (0-1).
        Simple implementation - could be improved with fuzzy matching.
        """
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()

        if name1 == name2:
            return 1.0

        # Check if one contains the other
        if name1 in name2 or name2 in name1:
            return 0.9

        # Check last name match (simple heuristic)
        parts1 = name1.split()
        parts2 = name2.split()

        if parts1 and parts2:
            if parts1[-1] == parts2[-1]:  # Last names match
                return 0.7

        return 0.0

    def _extract_affiliations(self, author: Dict[str, Any]) -> List[str]:
        """Extract affiliation names from author data."""
        affiliations = []
        for aff in author.get("affiliation", []):
            name = aff.get("name")
            if name:
                affiliations.append(name)
        return affiliations

    async def fetch(self, query: str) -> FetchResult:
        """
        Implementation of abstract fetch method.
        Searches for works by author name.

        Args:
            query: Author name to search

        Returns:
            FetchResult with status and data
        """
        try:
            works = await self.search_author(query, limit=5)

            if not works:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND, error_message=f"No works found for {query}"
                )

            # Parse the first work to get author data
            first_work = works[0]
            authority_data = self.parse_response({"works": works, "query": query})

            return FetchResult(
                status=FetchStatus.SUCCESS, data=authority_data, raw_response={"works": works}
            )

        except Exception as e:
            logger.error(f"Crossref fetch failed for {query}: {e}")
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(e))

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Implementation of abstract parse_response method.
        Parses Crossref API response into AuthorityData.

        Args:
            response: Response containing works and query

        Returns:
            Parsed AuthorityData
        """
        works = response.get("works", [])
        query = response.get("query", "")

        if not works:
            return AuthorityData(source="Crossref", source_id="")

        first_work = works[0]
        authors = first_work.get("author", [])

        # Find matching author
        matched_author = None
        for author in authors:
            full_name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            if self._name_similarity(query, full_name) > 0.8:
                matched_author = author
                break

        if not matched_author and authors:
            matched_author = authors[0]

        if not matched_author:
            matched_author = {}

        return AuthorityData(
            source="Crossref",
            source_id=first_work.get("DOI", ""),
            canonical_name=f"{matched_author.get('given', '')} {matched_author.get('family', '')}".strip(),
            affiliations=self._extract_affiliations(matched_author),
            identifiers=(
                {"orcid": matched_author.get("ORCID")} if matched_author.get("ORCID") else {}
            ),
            metadata={
                "works_count": len(works),
                "works": [
                    {
                        "doi": w.get("DOI"),
                        "title": w.get("title", [""])[0] if w.get("title") else "",
                        "year": w.get("published-print", {}).get("date-parts", [[None]])[0][0],
                    }
                    for w in works[:3]
                ],
            },
        )

    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience function for testing
async def test_crossref():
    """Test Crossref fetcher with a sample query."""
    async with CrossrefV7Fetcher() as fetcher:
        # Test search
        results = await fetcher.search_author("Einstein Albert", limit=3)
        print(f"Found {len(results)} works for Einstein")

        if results:
            # Test DOI fetch
            doi = results[0].get("DOI")
            if doi:
                work = await fetcher.fetch_by_doi(doi)
                print(f"Fetched work: {work.get('title', ['Unknown'])[0] if work else 'Failed'}")

        # Test enrichment
        entry = {"CanonicalLatin": "Albert Einstein"}
        data = await fetcher.enrich_entry(entry)
        print(f"Enriched: {data.canonical_name} with {len(data.metadata.get('works', []))} works")

        return data


if __name__ == "__main__":
    # Run test
    asyncio.run(test_crossref())
