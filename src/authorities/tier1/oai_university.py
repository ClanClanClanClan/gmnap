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
    FetchStatus,
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
        """NOT IMPLEMENTED — there is no endpoint to call.

        R66: this was documented as "✅ WORKING" but could never return data,
        for three stacked reasons:
          1. it delegated to ``UniversalFetcher("OAI_University")``, and that
             name is absent from ``AUTHORITY_CONFIGS`` — so the call returned
             ``PARSE_ERROR: Unsupported authority`` before any socket opened;
          2. ``base_url`` above is the OAI-PMH XML *namespace URI*, not an
             endpoint — it serves no records;
          3. the only configured endpoint (``config/authorities.yaml``) is the
             placeholder ``https://example.edu/oai/request``.

        OAI-PMH is a PER-REPOSITORY protocol: there is no global endpoint, so
        making this work is a project (curate per-university base URLs, build
        verb construction, parse XML, add per-repo rate limits), not a fix.

        Returning NOT_FOUND explicitly makes the deadness HONEST rather than
        accidental, and stops the orchestrator's ``retry_with_backoff`` from
        burning two retries plus 0.5 s of sleep, per entry, on a pure-logic
        failure that can never succeed.
        """
        return FetchResult(
            status=FetchStatus.NOT_FOUND,
            error_message=(
                "OAI_University: not implemented — no repository endpoint "
                "registry exists (OAI-PMH is per-repository)"
            ),
        )

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """Parse OAI-PMH response."""
        return self._template_fetcher.parse_response(response)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """Calculate confidence score for OAI University data."""
        return self._template_fetcher.calculate_confidence(data)
