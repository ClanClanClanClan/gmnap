"""
Wiley Online Library Authority Fetcher - Tier 1.

Wiley is a major publisher of scientific journals and educational materials.
Strong coverage in mathematics, statistics, sciences, and engineering.

API: https://api.wiley.com/onlinelibrary/tdm/v1/
Documentation: https://onlinelibrary.wiley.com/library-info/resources/text-and-datamining
License: Requires TDM token
Daily Quota: 3 requests/second (rate limit)
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


class WileyFetcher(AuthorityFetcher):
    """
    Wiley authority source fetcher.

    Fetches author and publication data from Wiley Online Library.
    Uses Crossref API with Wiley member filter for author search.
    Particularly strong for mathematics and statistics.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Wiley fetcher."""
        super().__init__(config or {})
        self.service = "Wiley"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 86400 // 3  # 3 per second = ~28,800/day
        self.base_url = "https://api.wiley.com"
        self.crossref_url = "https://api.crossref.org"
        self.requires_auth = True
        self._min_request_interval = 0.34  # 3 requests/second

        # Load API key from config
        self.api_key = self._load_api_key(config)

        # Wiley publisher ID in Crossref: 311
        self.wiley_member_id = "311"

    def _load_api_key(self, config: Optional[Dict[str, Any]]) -> str:
        """Load Wiley API key from config or file."""
        # Try config first
        if config and "api_key" in config:
            return config["api_key"]

        # Try loading from YAML file
        try:
            keys_file = Path("config/authority_api_keys.yaml")
            if keys_file.exists():
                with open(keys_file) as f:
                    keys_config = yaml.safe_load(f)
                    return keys_config.get("wiley", {}).get("api_key", "")
        except Exception as e:
            logger.warning(f"Could not load Wiley API key from file: {e}")

        return ""

    async def fetch(self, identifier: str) -> FetchResult:
        """
        Fetch authority data from Wiley via Crossref.

        Args:
            identifier: Author name to search

        Returns:
            FetchResult with authority data
        """
        try:
            # Search for author publications via Crossref (Wiley member filter)
            results = await self._search_author_crossref(identifier)

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
            logger.error(f"Wiley fetch error: {e}")
            return FetchResult(
                status=FetchStatus.ERROR,
                source=self.service,
                query=identifier,
                error=str(e),
            )

    async def _search_author_crossref(
        self, author_name: str, max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for Wiley publications by author via Crossref API.

        Args:
            author_name: Author name to search
            max_results: Maximum number of results

        Returns:
            List of work records
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        # Crossref query: filter by Wiley member and author
        params = {
            "query.author": author_name,
            "filter": f"member:{self.wiley_member_id}",  # Wiley
            "rows": max_results,
            "select": "DOI,title,author,published,container-title,type,subject",
        }

        headers = {"User-Agent": "GMNAP/1.0 (mailto:research@example.com)"}

        try:
            url = f"{self.crossref_url}/works"
            async with self._session.get(
                url, params=params, headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("message", {}).get("items", [])
                    logger.info(
                        f"Wiley (via Crossref): Found {len(items)} works for '{author_name}'"
                    )
                    return items
                else:
                    logger.warning(
                        f"Wiley/Crossref search failed with status {response.status}"
                    )
                    return []
        except Exception as e:
            logger.error(f"Wiley/Crossref search error: {e}")
            return []

    def _parse_author_data(
        self, query_name: str, works: List[Dict[str, Any]]
    ) -> Optional[AuthorityData]:
        """
        Parse Wiley/Crossref works to extract author information.

        Args:
            query_name: Original query name
            works: List of work records

        Returns:
            AuthorityData object or None
        """
        if not works:
            return None

        # Extract information from works
        affiliations = set()
        publications = []
        subjects = set()
        dois = set()

        # Process each work
        for work in works:
            # Extract authors and affiliations
            authors = work.get("author", [])
            for author in authors:
                if "affiliation" in author:
                    for aff in author["affiliation"]:
                        if "name" in aff:
                            affiliations.add(aff["name"])

            # Extract subjects
            if "subject" in work:
                for subject in work["subject"]:
                    subjects.add(subject)

            # Extract DOI
            if "DOI" in work:
                dois.add(work["DOI"])

            # Extract publication info
            pub_date = work.get("published", {})
            pub_year = None
            if "date-parts" in pub_date and pub_date["date-parts"]:
                pub_year = (
                    pub_date["date-parts"][0][0] if pub_date["date-parts"][0] else None
                )

            pub = {
                "title": (
                    work.get("title", [""])[0]
                    if isinstance(work.get("title"), list)
                    else work.get("title", "")
                ),
                "doi": work.get("DOI", ""),
                "year": pub_year,
                "journal": (
                    work.get("container-title", [""])[0]
                    if isinstance(work.get("container-title"), list)
                    else work.get("container-title", "")
                ),
                "type": work.get("type", ""),
            }
            publications.append(pub)

        # Build AuthorityData
        authority_data = AuthorityData(
            source=self.service,
            source_id=(
                list(dois)[0] if dois else f"wiley_{query_name.replace(' ', '_')}"
            ),
            canonical_name=query_name,
            name_variants=[],
            affiliations=[
                {"institution": aff}
                for aff in list(affiliations)[:5]  # Top 5 affiliations
            ],
            identifiers={"DOI": list(dois)[0] if dois else None},
            msc_codes=[],  # Wiley doesn't provide MSC codes directly
            metadata={
                "publications": publications[:10],  # Top 10 publications
                "subjects": list(subjects)[:20],  # Top 20 subjects
                "work_count": len(works),
            },
            confidence_score=self._calculate_confidence(works, affiliations, dois),
            fetch_timestamp=datetime.now(),
            personal_data_scrubbed=True,
        )

        return authority_data

    def _calculate_confidence(
        self, works: List[Dict], affiliations: set, dois: set
    ) -> float:
        """
        Calculate confidence score for Wiley data.

        Args:
            works: List of works found
            affiliations: Set of affiliations found
            dois: Set of DOIs found

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.5  # Base confidence

        # More works = higher confidence
        if len(works) >= 10:
            confidence += 0.2
        elif len(works) >= 5:
            confidence += 0.1
        elif len(works) >= 2:
            confidence += 0.05

        # Affiliations increase confidence
        if len(affiliations) > 0:
            confidence += 0.1

        # DOIs indicate verified publications
        if len(dois) > 0:
            confidence += 0.1

        # Wiley is authoritative for mathematics/statistics
        confidence += 0.05

        return min(confidence, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse Wiley response into AuthorityData.

        Args:
            response: Raw API response

        Returns:
            AuthorityData object
        """
        items = response.get("message", {}).get("items", [])

        if not items:
            return None

        # Use query name or first author
        canonical_name = "Unknown"
        if items and "author" in items[0]:
            authors = items[0]["author"]
            if authors:
                author = authors[0]
                given = author.get("given", "")
                family = author.get("family", "")
                canonical_name = f"{given} {family}".strip()

        return self._parse_author_data(canonical_name, items)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for parsed data.

        Args:
            data: AuthorityData object

        Returns:
            Confidence score (0.0-1.0)
        """
        return data.confidence_score if data else 0.0
