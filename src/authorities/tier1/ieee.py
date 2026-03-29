"""
IEEE Xplore Authority Fetcher - Tier 1.

IEEE Xplore is a research database providing access to IEEE and IET publications.
Strong coverage in engineering mathematics, computer science, and applied mathematics.

API: https://ieeexploreapi.ieee.org/api/v1/
Documentation: https://developer.ieee.org/docs
License: Requires API key
Daily Quota: 200 calls/day (free tier), 10,000/day (paid)
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


class IEEEFetcher(AuthorityFetcher):
    """
    IEEE Xplore authority source fetcher.

    Fetches author and publication data from IEEE Xplore database.
    Particularly strong for engineering mathematics and computer science.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize IEEE fetcher."""
        super().__init__(config or {})
        self.service = "IEEE"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 200  # Free tier
        self.base_url = "https://ieeexploreapi.ieee.org/api/v1"
        self.requires_auth = True
        self._min_request_interval = 5.0  # 5 seconds (200/day = ~720/hour max)

        # Load API key from config
        self.api_key = self._load_api_key(config)

    def _load_api_key(self, config: Optional[Dict[str, Any]]) -> str:
        """Load IEEE API key from config or file."""
        # Try config first
        if config and "api_key" in config:
            return config["api_key"]

        # Try loading from YAML file
        try:
            keys_file = Path("config/authority_api_keys.yaml")
            if keys_file.exists():
                with open(keys_file) as f:
                    keys_config = yaml.safe_load(f)
                    return keys_config.get("ieee", {}).get("api_key", "")
        except Exception as e:
            logger.warning(f"Could not load IEEE API key from file: {e}")

        return ""

    async def fetch(self, identifier: str) -> FetchResult:
        """
        Fetch authority data from IEEE Xplore.

        Args:
            identifier: Author name to search

        Returns:
            FetchResult with authority data
        """
        if not self.api_key:
            return FetchResult(
                status=FetchStatus.AUTH_FAILED,
                source=self.service,
                query=identifier,
                error="IEEE API key not configured",
            )

        try:
            # Search for author publications
            results = await self._search_author(identifier)

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
            logger.error(f"IEEE fetch error: {e}")
            return FetchResult(
                status=FetchStatus.ERROR,
                source=self.service,
                query=identifier,
                error=str(e),
            )

    async def _search_author(
        self, author_name: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search IEEE Xplore for articles by author.

        Args:
            author_name: Author name to search
            max_results: Maximum number of results to return

        Returns:
            List of article records
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        # IEEE Xplore API parameters
        params = {
            "apikey": self.api_key,
            "author": author_name,
            "max_records": max_results,
            "format": "json",
        }

        try:
            url = f"{self.base_url}/search/articles"
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("articles", [])
                    logger.info(
                        f"IEEE: Found {len(articles)} articles for '{author_name}'"
                    )
                    return articles
                elif response.status == 401:
                    logger.error("IEEE: Authentication failed - invalid API key")
                    return []
                elif response.status == 429:
                    logger.warning("IEEE: Rate limit exceeded")
                    return []
                else:
                    logger.warning(f"IEEE search failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"IEEE search error: {e}")
            return []

    def _parse_author_data(
        self, query_name: str, articles: List[Dict[str, Any]]
    ) -> Optional[AuthorityData]:
        """
        Parse IEEE articles to extract author information.

        Args:
            query_name: Original query name
            articles: List of IEEE articles

        Returns:
            AuthorityData object or None
        """
        if not articles:
            return None

        # Extract information from articles
        affiliations = set()
        publications = []
        author_ids = set()
        subjects = set()

        # Process each article
        for article in articles:
            # Extract authors and affiliations
            authors = article.get("authors", {}).get("authors", [])
            for author in authors:
                if "affiliation" in author and author["affiliation"]:
                    affiliations.add(author["affiliation"])
                if "id" in author:
                    author_ids.add(str(author["id"]))

            # Extract subjects/keywords
            if "index_terms" in article:
                terms = article["index_terms"]
                if "ieee_terms" in terms:
                    for term in terms["ieee_terms"].get("terms", []):
                        subjects.add(term)

            # Extract publication info
            pub = {
                "title": article.get("title", ""),
                "doi": article.get("doi", ""),
                "year": article.get("publication_year", ""),
                "type": article.get("content_type", ""),
                "citations": article.get("citing_paper_count", 0),
                "abstract": article.get("abstract", "")[:200],  # First 200 chars
            }
            publications.append(pub)

        # Build AuthorityData
        authority_data = AuthorityData(
            source=self.service,
            source_id=(
                list(author_ids)[0]
                if author_ids
                else f"ieee_{query_name.replace(' ', '_')}"
            ),
            canonical_name=query_name,
            name_variants=[],
            affiliations=[
                {"institution": aff}
                for aff in list(affiliations)[:5]  # Top 5 affiliations
            ],
            identifiers={"IEEE_Author_ID": list(author_ids)[0] if author_ids else None},
            msc_codes=[],  # IEEE doesn't use MSC codes
            metadata={
                "publications": publications[:10],  # Top 10 publications
                "subjects": list(subjects)[:20],  # Top 20 subjects
                "article_count": len(articles),
            },
            confidence_score=self._calculate_confidence(articles, affiliations),
            fetch_timestamp=datetime.now(),
            personal_data_scrubbed=True,
        )

        return authority_data

    def _calculate_confidence(self, articles: List[Dict], affiliations: set) -> float:
        """
        Calculate confidence score for IEEE data.

        Args:
            articles: List of articles found
            affiliations: Set of affiliations found

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.5  # Base confidence

        # More articles = higher confidence
        if len(articles) >= 10:
            confidence += 0.2
        elif len(articles) >= 5:
            confidence += 0.1
        elif len(articles) >= 2:
            confidence += 0.05

        # Affiliations increase confidence
        if len(affiliations) > 0:
            confidence += 0.1

        # IEEE publications are generally authoritative
        confidence += 0.1

        # Check for highly cited papers
        for article in articles:
            citations = article.get("citing_paper_count", 0)
            if citations > 50:
                confidence += 0.05
                break

        return min(confidence, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse IEEE response into AuthorityData.

        Args:
            response: Raw IEEE API response

        Returns:
            AuthorityData object
        """
        articles = response.get("articles", [])

        if not articles:
            return None

        # Use query name or first author
        canonical_name = "Unknown"
        if articles and "authors" in articles[0]:
            authors = articles[0]["authors"].get("authors", [])
            if authors:
                canonical_name = authors[0].get("full_name", "Unknown")

        return self._parse_author_data(canonical_name, articles)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for parsed data.

        Args:
            data: AuthorityData object

        Returns:
            Confidence score (0.0-1.0)
        """
        return data.confidence_score if data else 0.0
