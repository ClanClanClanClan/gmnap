"""
ACM Digital Library Authority Fetcher - Tier 1.

ACM (Association for Computing Machinery) is the world's largest computing society.
Strong coverage in computer science and computational mathematics.

API: Via Crossref (ACM member ID: 320)
Documentation: https://www.crossref.org/documentation/
License: Open access via Crossref
Daily Quota: Unlimited (Crossref open API, polite usage)
"""

import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.authorities.base import (
    AuthorityFetcher,
    FetchStatus,
    AuthorityData,
    FetchResult,
    AuthorityTier,
)

logger = logging.getLogger(__name__)


class ACMFetcher(AuthorityFetcher):
    """
    ACM Digital Library authority source fetcher.

    Fetches author and publication data via Crossref API with ACM member filter.
    Particularly strong for computer science and computational mathematics.

    Note: ACM does not provide a public API. We use Crossref API with ACM member
    filter (320) as an alternative for accessing ACM publication metadata.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ACM fetcher."""
        super().__init__(config or {})
        self.service = "ACM"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 999999  # Unlimited via Crossref (polite usage)
        self.base_url = "https://api.crossref.org"
        self.requires_auth = False
        self._min_request_interval = 1.0  # Polite: 1 request/second

        # ACM publisher ID in Crossref: 320
        self.acm_member_id = "320"

    async def fetch(self, identifier: str) -> FetchResult:
        """
        Fetch authority data from ACM via Crossref.

        Args:
            identifier: Author name to search

        Returns:
            FetchResult with authority data
        """
        try:
            # Search for author publications via Crossref (ACM member filter)
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
            logger.error(f"ACM fetch error: {e}")
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
        Search for ACM publications by author via Crossref API.

        Args:
            author_name: Author name to search
            max_results: Maximum number of results

        Returns:
            List of work records
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        # Crossref query: filter by ACM member and author
        params = {
            "query.author": author_name,
            "filter": f"member:{self.acm_member_id}",  # ACM
            "rows": max_results,
            "select": "DOI,title,author,published,container-title,type,subject,is-referenced-by-count",
        }

        headers = {"User-Agent": "GMNAP/1.0 (mailto:research@example.com)"}

        try:
            url = f"{self.base_url}/works"
            async with self._session.get(
                url, params=params, headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("message", {}).get("items", [])
                    logger.info(
                        f"ACM (via Crossref): Found {len(items)} works for '{author_name}'"
                    )
                    return items
                else:
                    logger.warning(
                        f"ACM/Crossref search failed with status {response.status}"
                    )
                    return []
        except Exception as e:
            logger.error(f"ACM/Crossref search error: {e}")
            return []

    def _parse_author_data(
        self, query_name: str, works: List[Dict[str, Any]]
    ) -> Optional[AuthorityData]:
        """
        Parse ACM/Crossref works to extract author information.

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
        total_citations = 0

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

            # Extract citations
            citations = work.get("is-referenced-by-count", 0)
            total_citations += citations

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
                "venue": (
                    work.get("container-title", [""])[0]
                    if isinstance(work.get("container-title"), list)
                    else work.get("container-title", "")
                ),
                "type": work.get("type", ""),
                "citations": citations,
            }
            publications.append(pub)

        # Build AuthorityData
        authority_data = AuthorityData(
            source=self.service,
            source_id=list(dois)[0] if dois else f"acm_{query_name.replace(' ', '_')}",
            canonical_name=query_name,
            name_variants=[],
            affiliations=[
                {"institution": aff}
                for aff in list(affiliations)[:5]  # Top 5 affiliations
            ],
            identifiers={"DOI": list(dois)[0] if dois else None},
            msc_codes=[],  # ACM uses Computing Classification System, not MSC
            metadata={
                "publications": sorted(
                    publications, key=lambda x: x.get("citations", 0), reverse=True
                )[
                    :10
                ],  # Top 10 by citations
                "subjects": list(subjects)[:20],  # Top 20 subjects
                "work_count": len(works),
                "total_citations": total_citations,
            },
            confidence_score=self._calculate_confidence(
                works, affiliations, dois, total_citations
            ),
            fetch_timestamp=datetime.now(),
            personal_data_scrubbed=True,
        )

        return authority_data

    def _calculate_confidence(
        self, works: List[Dict], affiliations: set, dois: set, total_citations: int
    ) -> float:
        """
        Calculate confidence score for ACM data.

        Args:
            works: List of works found
            affiliations: Set of affiliations found
            dois: Set of DOIs found
            total_citations: Total citation count

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

        # Citations increase confidence
        if total_citations >= 100:
            confidence += 0.1
        elif total_citations >= 10:
            confidence += 0.05

        return min(confidence, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse ACM response into AuthorityData.

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
