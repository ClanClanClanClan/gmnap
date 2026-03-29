"""
Springer Nature Authority Fetcher - Tier 1.

Springer Nature publishes scientific journals, books, and educational materials.
Strong coverage in mathematics, physics, computer science, and life sciences.

APIs:
- Open Access API: 460,000+ open access documents
- Meta API v2: 12 million documents metadata

Documentation: https://dev.springernature.com/
License: Requires API keys
Daily Quota: 5,000 calls/day (free tier), 100 hits/min
"""

import aiohttp
import logging
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from src.authorities.base import (
    AuthorityFetcher,
    FetchStatus,
    AuthorityData,
    FetchResult,
    AuthorityTier,
)

logger = logging.getLogger(__name__)


class SpringerFetcher(AuthorityFetcher):
    """
    Springer Nature authority source fetcher.

    Uses both Open Access API and Meta API for comprehensive coverage.
    Particularly strong for mathematics, physics, and sciences.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Springer fetcher."""
        super().__init__(config or {})
        self.service = "Springer"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 5000  # Free tier
        self.base_url = "https://api.springernature.com"
        self.requires_auth = True
        self._min_request_interval = 0.6  # 100 hits/min = 0.6s interval

        # Load API keys from config
        self.open_access_key, self.meta_api_key = self._load_api_keys(config)

    def _load_api_keys(self, config: Optional[Dict[str, Any]]) -> tuple[str, str]:
        """Load Springer API keys from config or file."""
        open_access = ""
        meta_api = ""

        # Try config first
        if config:
            open_access = config.get("open_access_key", "")
            meta_api = config.get("meta_api_key", "")

        # Try loading from YAML file
        if not (open_access and meta_api):
            try:
                keys_file = Path("config/authority_api_keys.yaml")
                if keys_file.exists():
                    with open(keys_file) as f:
                        keys_config = yaml.safe_load(f)
                        springer_config = keys_config.get("springer", {})
                        open_access = open_access or springer_config.get(
                            "open_access_key", ""
                        )
                        meta_api = meta_api or springer_config.get("meta_api_key", "")
            except Exception as e:
                logger.warning(f"Could not load Springer API keys from file: {e}")

        return open_access, meta_api

    async def fetch(self, identifier: str) -> FetchResult:
        """
        Fetch authority data from Springer Nature.

        Args:
            identifier: Author name to search

        Returns:
            FetchResult with authority data
        """
        if not (self.open_access_key or self.meta_api_key):
            return FetchResult(
                status=FetchStatus.AUTH_FAILED,
                source=self.service,
                query=identifier,
                error="Springer API keys not configured",
            )

        try:
            # Try Open Access API first (faster, more complete data)
            results = []
            if self.open_access_key:
                results = await self._search_open_access(identifier)

            # Fall back to Meta API if no results
            if not results and self.meta_api_key:
                results = await self._search_meta_api(identifier)

            if not results or len(results) == 0:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND, source=self.service, query=identifier
                )

            # Parse results to extract author information
            author_data = self._parse_author_data(identifier, results)

            if not author_data:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND, source=self.service, query=identifier
                )

            return FetchResult(
                status=FetchStatus.SUCCESS,
                source=self.service,
                query=identifier,
                data=author_data,
            )

        except Exception as e:
            logger.error(f"Springer fetch error: {e}")
            return FetchResult(
                status=FetchStatus.ERROR,
                source=self.service,
                query=identifier,
                error=str(e),
            )

    async def _search_open_access(
        self, author_name: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Springer Open Access API.

        Args:
            author_name: Author name to search
            max_results: Maximum number of results

        Returns:
            List of document records
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        params = {
            "q": f"name:{author_name}",
            "api_key": self.open_access_key,
            "s": 1,  # Start
            "p": max_results,  # Page size
        }

        try:
            url = f"{self.base_url}/openaccess/json"
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    logger.info(
                        f"Springer OA: Found {len(records)} documents for '{author_name}'"
                    )
                    return records
                elif response.status == 401:
                    logger.error("Springer OA: Authentication failed")
                    return []
                elif response.status == 429:
                    logger.warning("Springer OA: Rate limit exceeded")
                    return []
                else:
                    logger.warning(
                        f"Springer OA search failed with status {response.status}"
                    )
                    return []
        except Exception as e:
            logger.error(f"Springer OA search error: {e}")
            return []

    async def _search_meta_api(
        self, author_name: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Springer Meta API.

        Args:
            author_name: Author name to search
            max_results: Maximum number of results

        Returns:
            List of document records
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        params = {
            "q": f"name:{author_name}",
            "api_key": self.meta_api_key,
            "s": 1,
            "p": max_results,
        }

        try:
            url = f"{self.base_url}/meta/v2/json"
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    logger.info(
                        f"Springer Meta: Found {len(records)} documents for '{author_name}'"
                    )
                    return records
                elif response.status == 401:
                    logger.error("Springer Meta: Authentication failed")
                    return []
                elif response.status == 429:
                    logger.warning("Springer Meta: Rate limit exceeded")
                    return []
                else:
                    logger.warning(
                        f"Springer Meta search failed with status {response.status}"
                    )
                    return []
        except Exception as e:
            logger.error(f"Springer Meta search error: {e}")
            return []

    def _parse_author_data(
        self, query_name: str, records: List[Dict[str, Any]]
    ) -> Optional[AuthorityData]:
        """
        Parse Springer records to extract author information.

        Args:
            query_name: Original query name
            records: List of Springer records

        Returns:
            AuthorityData object or None
        """
        if not records:
            return None

        # Extract information from records
        affiliations = set()
        publications = []
        subjects = set()
        dois = set()

        # Process each record
        for record in records:
            # Extract creators (authors) and affiliations
            creators = record.get("creators", [])
            for creator in creators:
                if "affiliation" in creator:
                    affiliations.add(creator["affiliation"])

            # Extract subjects/disciplines
            if "subjects" in record:
                for subject in record["subjects"]:
                    subjects.add(subject)

            # Extract DOI
            if "doi" in record:
                dois.add(record["doi"])

            # Extract publication info
            pub = {
                "title": record.get("title", ""),
                "doi": record.get("doi", ""),
                "publication_date": record.get("publicationDate", ""),
                "publication_name": record.get("publicationName", ""),
                "type": record.get("contentType", ""),
                "url": record.get("url", ""),
            }
            publications.append(pub)

        # Build AuthorityData
        authority_data = AuthorityData(
            source=self.service,
            source_id=(
                list(dois)[0] if dois else f"springer_{query_name.replace(' ', '_')}"
            ),
            canonical_name=query_name,
            name_variants=[],
            affiliations=[
                {"institution": aff}
                for aff in list(affiliations)[:5]  # Top 5 affiliations
            ],
            identifiers={"DOI": list(dois)[0] if dois else None},
            msc_codes=[],  # Springer doesn't use MSC codes directly
            metadata={
                "publications": publications[:10],  # Top 10 publications
                "subjects": list(subjects)[:20],  # Top 20 subjects
                "document_count": len(records),
            },
            confidence_score=self._calculate_confidence(records, affiliations, dois),
            fetch_timestamp=datetime.now(),
            personal_data_scrubbed=True,
        )

        return authority_data

    def _calculate_confidence(
        self, records: List[Dict], affiliations: set, dois: set
    ) -> float:
        """
        Calculate confidence score for Springer data.

        Args:
            records: List of records found
            affiliations: Set of affiliations found
            dois: Set of DOIs found

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.5  # Base confidence

        # More records = higher confidence
        if len(records) >= 10:
            confidence += 0.2
        elif len(records) >= 5:
            confidence += 0.1
        elif len(records) >= 2:
            confidence += 0.05

        # Affiliations increase confidence
        if len(affiliations) > 0:
            confidence += 0.1

        # DOIs indicate verified publications
        if len(dois) > 0:
            confidence += 0.1

        # Springer is authoritative for sciences
        confidence += 0.05

        return min(confidence, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse Springer response into AuthorityData.

        Args:
            response: Raw Springer API response

        Returns:
            AuthorityData object
        """
        records = response.get("records", [])

        if not records:
            return None

        # Use query name or first creator
        canonical_name = "Unknown"
        if records and "creators" in records[0]:
            creators = records[0]["creators"]
            if creators:
                canonical_name = creators[0].get("creator", "Unknown")

        return self._parse_author_data(canonical_name, records)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for parsed data.

        Args:
            data: AuthorityData object

        Returns:
            Confidence score (0.0-1.0)
        """
        return data.confidence_score if data else 0.0
