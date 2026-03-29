"""
CNKI fetcher for GMNAP.
Generated from universal authority template engine.

API: http://search.cnki.net/api/search
Type: REST
"""

from typing import Any, Dict

from ..templates.authority_engine import create_authority_fetcher


class CNKIFetcher:
    """
    CNKI authority fetcher generated from template.

    Based on successful authority patterns:
    - Standard fetch/parse/validate workflow
    - Rate limiting and session management
    - Confidence scoring algorithms
    - Chinese academic database integration
    """

    def __new__(cls, config: Dict[str, Any]):
        """Create fetcher using universal template"""
        return create_authority_fetcher("CNKI", config)
