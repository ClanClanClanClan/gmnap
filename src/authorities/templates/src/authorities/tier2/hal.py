"""
HAL fetcher for GMNAP.
Generated from universal authority template engine.

API: https://api.archives-ouvertes.fr/search/
Type: REST
"""

from typing import Any, Dict

from src.authorities.templates.authority_engine import create_authority_fetcher


class HALFetcher:
    """
    HAL authority fetcher generated from template.

    Based on successful authority patterns:
    - Standard fetch/parse/validate workflow
    - Rate limiting and session management
    - Confidence scoring algorithms
    """

    def __new__(cls, config: Dict[str, Any]):
        """Create fetcher using universal template"""
        return create_authority_fetcher("HAL", config)
