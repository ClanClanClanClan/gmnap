"""
VIAF (Virtual International Authority File) fetcher for V7 compliance.
Provides access to global authority data from multiple national libraries.
"""

import aiohttp
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.authorities.base import (
    AuthorityFetcher,
    AuthorityData,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class VIAFData:
    """VIAF authority data structure."""

    viaf_id: Optional[str] = None
    preferred_name: Optional[str] = None
    name_variants: List[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    national_library_ids: Dict[str, str] = None
    sources: List[str] = None

    def __post_init__(self):
        if self.name_variants is None:
            self.name_variants = []
        if self.national_library_ids is None:
            self.national_library_ids = {}
        if self.sources is None:
            self.sources = []


class VIAFFetcher(AuthorityFetcher):
    """
    VIAF Authority Fetcher - Tier 1.
    Fetches authority data from the Virtual International Authority File.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize VIAF fetcher with configuration."""
        super().__init__(config)
        self.base_url = "https://viaf.org/viaf"
        self.search_url = "https://viaf.org/viaf/search"
        self.session = None
        self.tier = AuthorityTier.TIER_1

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search VIAF for authority records.

        Args:
            query: Name or identifier to search
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        params = {
            "query": f'local.personalNames all "{query}"',
            "maximumRecords": limit,
            "httpAccept": "application/json",
        }

        try:
            async with self.session.get(self.search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # Parse search results
                    results = []
                    if "searchRetrieveResponse" in data:
                        records = data.get("searchRetrieveResponse", {}).get("records", [])
                        for record in records:
                            if isinstance(record, dict):
                                record_data = record.get("record", {}).get("recordData", {})
                                if record_data:
                                    results.append(
                                        {
                                            "viaf_id": record_data.get("viafID"),
                                            "name": record_data.get("mainHeadings", {})
                                            .get("data", [{}])[0]
                                            .get("text"),
                                            "sources": record_data.get("sources", {}).get(
                                                "source", []
                                            ),
                                        }
                                    )
                    return results
                else:
                    logger.warning(f"VIAF search failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"VIAF search error: {e}")
            return []

    async def fetch(self, identifier: str) -> FetchResult:
        """
        Fetch authority data from VIAF.

        Args:
            identifier: VIAF ID or name to search

        Returns:
            FetchResult with authority data
        """
        try:
            # Search if not a VIAF ID
            if not identifier.isdigit():
                search_results = await self.search(identifier, limit=5)
                if not search_results:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND, source="VIAF", query=identifier
                    )
                # Use first result
                identifier = search_results[0].get("viaf_id")

            # Fetch full record
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = f"{self.base_url}/{identifier}/viaf.json"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Parse VIAF data
                    viaf_data = VIAFData(
                        viaf_id=identifier,
                        preferred_name=self._extract_preferred_name(data),
                        name_variants=self._extract_variants(data),
                        birth_year=self._extract_year(data, "birthDate"),
                        death_year=self._extract_year(data, "deathDate"),
                        national_library_ids=self._extract_library_ids(data),
                        sources=self._extract_sources(data),
                    )

                    # Convert to AuthorityData
                    authority_data = AuthorityData(
                        source="VIAF",
                        identifier=identifier,
                        name=viaf_data.preferred_name,
                        variants=viaf_data.name_variants,
                        birth_year=viaf_data.birth_year,
                        death_year=viaf_data.death_year,
                        external_ids=viaf_data.national_library_ids,
                        confidence=0.9,
                    )

                    return FetchResult(
                        status=FetchStatus.SUCCESS,
                        source="VIAF",
                        query=identifier,
                        data=authority_data,
                    )
                else:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND, source="VIAF", query=identifier
                    )

        except Exception as e:
            logger.error(f"VIAF fetch error: {e}")
            return FetchResult(
                status=FetchStatus.ERROR, source="VIAF", query=identifier, error=str(e)
            )

    def _extract_preferred_name(self, data: Dict) -> str:
        """Extract preferred name from VIAF data."""
        try:
            main_headings = data.get("mainHeadings", {}).get("data", [])
            if main_headings:
                return main_headings[0].get("text", "")
        except:
            pass
        return ""

    def _extract_variants(self, data: Dict) -> List[str]:
        """Extract name variants from VIAF data."""
        variants = []
        try:
            # Get x400s (alternate forms)
            x400s = data.get("x400s", {}).get("x400", [])
            if isinstance(x400s, dict):
                x400s = [x400s]
            for x400 in x400s:
                if "datafield" in x400:
                    subfields = x400["datafield"].get("subfield", [])
                    if isinstance(subfields, dict):
                        subfields = [subfields]
                    name_parts = []
                    for subfield in subfields:
                        if subfield.get("code") in ["a", "b", "c", "d"]:
                            name_parts.append(subfield.get("text", ""))
                    if name_parts:
                        variants.append(" ".join(name_parts))
        except:
            pass
        return list(set(variants))

    def _extract_year(self, data: Dict, field: str) -> Optional[int]:
        """Extract birth or death year from VIAF data."""
        try:
            date_str = data.get(field, "")
            if date_str and len(date_str) >= 4:
                return int(date_str[:4])
        except:
            pass
        return None

    def _extract_library_ids(self, data: Dict) -> Dict[str, str]:
        """Extract national library identifiers."""
        ids = {}
        try:
            sources = data.get("sources", {}).get("source", [])
            if isinstance(sources, dict):
                sources = [sources]
            for source in sources:
                if isinstance(source, dict):
                    code = source.get("code", "")
                    sid = source.get("sid", "")
                    if code and sid:
                        ids[code] = sid
        except:
            pass
        return ids

    def _extract_sources(self, data: Dict) -> List[str]:
        """Extract contributing sources."""
        sources = []
        try:
            source_list = data.get("sources", {}).get("source", [])
            if isinstance(source_list, dict):
                source_list = [source_list]
            for source in source_list:
                if isinstance(source, dict) and "code" in source:
                    sources.append(source["code"])
        except:
            pass
        return sources
