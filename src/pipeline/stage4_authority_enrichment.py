#!/usr/bin/env python3
"""
GMNAP V7 Stage 4: Authority Enrichment
Simplified implementation with real Crossref API integration
"""

import asyncio
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


async def enrich_from_authorities(
    batch: List[Dict[str, Any]], mode: str = "Quick"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Stage 4: Authority Enrichment
    Enrich entries with data from authority sources (currently Crossref only)

    Args:
        batch: List of entries to enrich
        mode: Runtime mode (Quick/Full/Extreme)

    Returns:
        Tuple of (enriched_batch, metrics)
    """
    from ..authorities.crossref import CrossrefAPI

    metrics = {
        "entries_processed": len(batch),
        "entries_enriched": 0,
        "crossref_requests": 0,
        "orcids_found": 0,
        "affiliations_found": 0,
    }

    # Initialize Crossref API
    try:
        async with CrossrefAPI() as api:
            # Process based on mode
            if mode == "Quick":
                # Quick mode: Only process first 100 entries
                entries_to_process = batch[:100]
            elif mode == "Full":
                # Full mode: Process all entries
                entries_to_process = batch
            else:  # Extreme
                # Extreme mode: Process all with higher concurrency
                entries_to_process = batch

            # Enrich entries
            enriched = await api.batch_enrich(entries_to_process, max_concurrent=10)

            # Update metrics
            for i, entry in enumerate(enriched):
                if "AuthoritySources" in entry:
                    metrics["entries_enriched"] += 1
                if "ExternalIDs" in entry:
                    orcids = [
                        e for e in entry["ExternalIDs"] if e.get("type") == "ORCID"
                    ]
                    metrics["orcids_found"] += len(orcids)
                if "Affiliations" in entry:
                    metrics["affiliations_found"] += len(entry["Affiliations"])

                # Update original batch entry
                if i < len(batch):
                    batch[i].update(entry)

            # Get API stats
            api_stats = api.get_stats()
            metrics["crossref_requests"] = api_stats["request_count"]

    except Exception as e:
        logger.error(f"Authority enrichment failed: {e}")
        # Return batch unchanged if enrichment fails

    return batch, metrics


def enrich_from_authorities_sync(
    batch: List[Dict[str, Any]], mode: str = "Quick"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Synchronous wrapper for authority enrichment
    """
    try:
        return asyncio.run(enrich_from_authorities(batch, mode))
    except RuntimeError:
        # If already in async context, create new loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(enrich_from_authorities(batch, mode))
        finally:
            loop.close()


class AuthorityManager:
    """
    Manages authority sources based on V7 specs
    Currently implements Crossref (tier-0)
    Future: OpenAlex, ORCID, Wikidata, etc.
    """

    def __init__(self, config_path: Path = None):
        """Initialize authority manager"""
        self.config_path = config_path or Path("config/authorities.yaml")
        self.sources = {}
        self.load_config()

    def load_config(self):
        """Load authority configuration"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            # Default config
            self.config = {
                "tier_0": {
                    "crossref": {
                        "enabled": True,
                        "daily_quota": 4300000,
                        "license": "CC0",
                    },
                    "openalex": {
                        "enabled": False,
                        "daily_quota": 864000,
                        "license": "CC0",
                    },
                },
                "tier_1": {
                    "wikidata": {
                        "enabled": False,
                        "daily_quota": None,
                        "license": "CC0",
                    }
                },
            }

    async def enrich_batch(
        self, batch: List[Dict[str, Any]], tier: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Enrich a batch of entries using configured authority sources

        Args:
            batch: Entries to enrich
            tier: Authority tier to use (0=free, 1=registered, 2=commercial)

        Returns:
            Enriched entries
        """
        # Currently only Crossref is implemented
        if tier == 0 and self.config.get("tier_0", {}).get("crossref", {}).get(
            "enabled"
        ):
            from ..authorities.crossref import CrossrefAPI

            async with CrossrefAPI() as api:
                return await api.batch_enrich(batch)

        return batch

    def get_enabled_sources(self, tier: int = None) -> List[str]:
        """Get list of enabled authority sources"""
        sources = []
        for tier_name, tier_sources in self.config.items():
            if tier is not None and not tier_name.endswith(str(tier)):
                continue
            for source, config in tier_sources.items():
                if config.get("enabled"):
                    sources.append(source)
        return sources


# For compatibility with existing pipeline
authority_enrichment = enrich_from_authorities_sync
