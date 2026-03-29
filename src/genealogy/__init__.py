"""
GMNAP Phase 2 Genealogy Integration

Provides academic genealogy enrichment for the main GMNAP V7 pipeline.
"""

from src.genealogy.enrichment import GenealogyEnricher, get_lineage

__all__ = ["GenealogyEnricher", "get_lineage"]
__version__ = "1.5.0"
