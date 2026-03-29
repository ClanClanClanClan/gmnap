"""
GND authority source (Tier 1).

Implements GMNAP v7 authority fetching for GND (Gemeinsame Normdatei).
Licence: CC0
Daily Quota: Unlimited
"""

import logging
from typing import Any, Dict, Optional

from src.authorities.base import (
    AuthorityData,
    AuthorityFetcher,
    AuthorityTier,
    FetchResult,
)
from src.authorities.templates.authority_engine import UniversalFetcher

logger = logging.getLogger(__name__)


class GNDFetcher(AuthorityFetcher):
    """
    GND authority source fetcher.

    Properly implements async methods by extending UniversalFetcher.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})
        self.service = "GND"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 100000  # Unlimited but set reasonable limit
        self.base_url = "https://lobid.org/gnd/"
        self.requires_auth = False
        self._min_request_interval = 0.2  # 200ms between requests

        # Create internal fetcher for template functionality
        self._template_fetcher = UniversalFetcher("GND", config or {})

    async def fetch(self, query: str) -> FetchResult:
        """Fetch authority data from GND."""
        # Delegate to template fetcher's async method
        return await self._template_fetcher.fetch(query)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """Parse GND response."""
        return self._template_fetcher.parse_response(response)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """Calculate confidence score for GND data."""
        return self._template_fetcher.calculate_confidence(data)
