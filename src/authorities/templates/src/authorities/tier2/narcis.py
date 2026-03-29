"""
NARCIS fetcher for GMNAP.
Generated from universal authority template engine.

API: https://www.narcis.nl/api/search/person
Type: REST
"""

from typing import Dict, Any
from src.authorities.templates.authority_engine import create_authority_fetcher


class NARCISFetcher:
    """
    NARCIS authority fetcher generated from template.

    Based on successful authority patterns:
    - Standard fetch/parse/validate workflow
    - Rate limiting and session management
    - Confidence scoring algorithms
    """

    def __new__(cls, config: Dict[str, Any]):
        """Create fetcher using universal template"""
        return create_authority_fetcher("NARCIS", config)
