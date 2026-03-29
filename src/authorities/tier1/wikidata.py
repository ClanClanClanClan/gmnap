"""
Wikidata authority source (Tier 1).

Implements GMNAP v7 authority fetching for Wikidata.
Licence: CC0
Daily Quota: Unlimited (reasonable use)
"""

from typing import Dict, Any, Optional
from src.authorities.base import AuthorityFetcher, AuthorityData, FetchResult, AuthorityTier
from src.authorities.templates.authority_engine import UniversalFetcher
import logging

logger = logging.getLogger(__name__)


class WikidataFetcher(AuthorityFetcher):
    """
    Wikidata authority source fetcher.

    Properly implements async methods by extending UniversalFetcher.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})
        self.service = "Wikidata"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 50000
        self.base_url = "https://query.wikidata.org/sparql"
        self.requires_auth = False
        self._min_request_interval = 1.0  # 1 second between requests

        # Create internal fetcher for template functionality
        self._template_fetcher = UniversalFetcher("Wikidata", config or {})

    async def fetch(self, query: str) -> FetchResult:
        """Fetch authority data from Wikidata."""
        # Delegate to template fetcher's async method
        return await self._template_fetcher.fetch(query)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """Parse Wikidata response."""
        return self._template_fetcher.parse_response(response)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """Calculate confidence score for Wikidata data."""
        return self._template_fetcher.calculate_confidence(data)
