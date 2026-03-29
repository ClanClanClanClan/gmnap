"""
TEL fetcher for GMNAP.
Generated from universal authority template engine.

API: https://tel.archives-ouvertes.fr/search/
Type: REST
"""

from typing import Dict, Any
from ..templates.authority_engine import create_authority_fetcher


class TELFetcher:
    """
    TEL authority fetcher generated from template.

    Based on successful authority patterns:
    - Standard fetch/parse/validate workflow
    - Rate limiting and session management
    - Confidence scoring algorithms
    - French thesis repository integration
    """

    def __new__(cls, config: Dict[str, Any]):
        """Create fetcher using universal template"""
        return create_authority_fetcher("TEL", config)
