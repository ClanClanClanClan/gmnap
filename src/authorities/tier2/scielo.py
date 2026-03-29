"""
SciELO fetcher for GMNAP.
Generated from universal authority template engine.

API: https://search.scielo.org/
Type: REST
"""

from typing import Any, Dict

from src.authorities.templates.authority_engine import create_authority_fetcher


class SciELOFetcher:
    """
    SciELO authority fetcher generated from template.

    Based on successful authority patterns:
    - Standard fetch/parse/validate workflow
    - Rate limiting and session management
    - Confidence scoring algorithms
    """

    def __new__(cls, config: Dict[str, Any]):
        """Create fetcher using universal template"""
        return create_authority_fetcher("SciELO", config)
