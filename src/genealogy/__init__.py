"""
GMNAP Phase 2 Genealogy Integration

Provides academic genealogy enrichment for the main GMNAP V7 pipeline.

The eager ``from src.genealogy.enrichment import GenealogyEnricher``
at package import would pull the ``requests`` dependency even when a
caller only wants ``src.genealogy.query`` (Memgraph lineage, pure-JSON
fallback) — and the Docker image deliberately omits ``requests`` to
keep the container small. We fall back to a warning-only import path
and expose the two symbols lazily via ``__getattr__`` (PEP 562).
"""

from __future__ import annotations

import logging

__all__ = ["GenealogyEnricher", "get_lineage"]
__version__ = "1.5.0"

_logger = logging.getLogger(__name__)


def __getattr__(name: str):
    # Lazy-load the enrichment module so callers that only use
    # `src.genealogy.query` (e.g. the lineage API path) don't
    # pay for heavy HTTP deps.
    if name in __all__:
        try:
            from src.genealogy.enrichment import GenealogyEnricher, get_lineage
        except ImportError as exc:
            _logger.info("genealogy.enrichment unavailable: %s", exc)
            raise AttributeError(
                f"module 'src.genealogy' has attribute {name!r} only "
                f"when optional deps are installed ({exc})"
            ) from exc
        globals()["GenealogyEnricher"] = GenealogyEnricher
        globals()["get_lineage"] = get_lineage
        return globals()[name]
    raise AttributeError(f"module 'src.genealogy' has no attribute {name!r}")
