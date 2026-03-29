"""
OAI University authority source (Tier 1).

Implements GMNAP v7 authority fetching for OAI University repositories.
Licence: Mixed
Daily Quota: Varies by repository
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


class OAIUniversityFetcher(AuthorityFetcher):
    """
    OAI University authority source fetcher.

    Properly implements async methods by extending UniversalFetcher.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})
        self.service = "OAI_University"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 10000  # Conservative estimate for OAI-PMH
        self.base_url = "http://www.openarchives.org/OAI/2.0/"
        self.requires_auth = False
        self._min_request_interval = 0.5  # 500ms between requests

        # Create internal fetcher for template functionality
        self._template_fetcher = UniversalFetcher("OAI_University", config or {})

    async def fetch(self, query: str) -> FetchResult:
        """Fetch authority data from OAI University repositories."""
        # Delegate to template fetcher's async method
        return await self._template_fetcher.fetch(query)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """Parse OAI-PMH response."""
        return self._template_fetcher.parse_response(response)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """Calculate confidence score for OAI University data."""
        return self._template_fetcher.calculate_confidence(data)
