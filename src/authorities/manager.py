#!/usr/bin/env python3
"""
GMNAP V7 Authority Source Manager
Orchestrates multiple authority APIs based on runtime mode and tier
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AuthorityResult:
    """Unified result from authority source"""

    source: str
    confidence: float
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    cached: bool = False


@dataclass
class EnrichmentStats:
    """Statistics for enrichment operations"""

    total_entries: int = 0
    enriched_entries: int = 0
    api_calls: Dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        if self.total_entries == 0:
            return 0.0
        return (self.enriched_entries / self.total_entries) * 100

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    @property
    def elapsed_time(self) -> float:
        return (datetime.utcnow() - self.start_time).total_seconds()


class AuthoritySourceManager:
    """
    Manages and orchestrates multiple authority sources
    Implements caching, deduplication, and tier-based access
    """

    def __init__(self, config: Dict[str, Any] = None, cache_dir: Path = None):
        """
        Initialize authority source manager

        Args:
            config: Runtime configuration
            cache_dir: Directory for caching results
        """
        self.config = config or {}
        self.cache_dir = cache_dir or Path("cache/authorities")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.sources = {}
        self.cache = {}
        self.stats = EnrichmentStats()

        # Initialize based on mode
        self.mode = self.config.get("mode", "Quick")
        self._initialize_sources()

    def _initialize_sources(self):
        """Initialize authority sources based on configuration"""
        self.config.get("runtime", {})
        authorities = self.config.get("authorities", {})

        # Always initialize tier-0 sources
        if authorities.get("crossref", {}).get("enabled", True):
            self.sources["crossref"] = {
                "tier": 0,
                "api": None,  # Lazy load
                "quota": 4_300_000,
                "priority": 1,
            }

        if authorities.get("openalex", {}).get("enabled", True):
            self.sources["openalex"] = {
                "tier": 0,
                "api": None,  # Lazy load
                "quota": 864_000,
                "priority": 2,
            }

        # Tier-1 sources for Full/Extreme modes
        if self.mode in ["Full", "Extreme"]:
            if authorities.get("orcid", {}).get("enabled", False):
                self.sources["orcid"] = {
                    "tier": 1,
                    "api": None,
                    "quota": 100_000,
                    "priority": 0,  # Highest priority (authoritative)
                }

            if authorities.get("wikidata", {}).get("enabled", False):
                self.sources["wikidata"] = {
                    "tier": 1,
                    "api": None,
                    "quota": None,  # Dump-based
                    "priority": 3,
                }

        logger.info(
            f"Initialized {len(self.sources)} authority sources for {self.mode} mode"
        )

    async def _get_api(self, source: str):
        """Get or create API instance for a source"""
        if source not in self.sources:
            return None

        source_info = self.sources[source]
        if source_info["api"] is None:
            # Lazy load the API
            if source == "crossref":
                from .crossref import CrossrefAPI

                source_info["api"] = CrossrefAPI()
            elif source == "openalex":
                from .openalex import OpenAlexAPI

                source_info["api"] = OpenAlexAPI()
            elif source == "orcid":
                from .orcid import ORCIDAPI

                secrets = self.config.get("secrets", {})
                source_info["api"] = ORCIDAPI(
                    client_id=secrets.get("orcid_client_id"),
                    client_secret=secrets.get("orcid_client_secret"),
                )
            # Add more sources as implemented

        return source_info["api"]

    def _get_cache_key(self, name: str, source: str) -> str:
        """Generate cache key for a name/source combination"""
        key_str = f"{source}:{name.lower().strip()}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _load_cache(self, name: str, source: str) -> Optional[AuthorityResult]:
        """Load cached result if available and fresh"""
        cache_key = self._get_cache_key(name, source)

        # Memory cache first
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(hours=24):
                self.stats.cache_hits += 1
                result.cached = True
                return result

        # Disk cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    timestamp = datetime.fromisoformat(data["timestamp"])
                    if datetime.utcnow() - timestamp < timedelta(days=7):
                        result = AuthorityResult(
                            source=data["source"],
                            confidence=data["confidence"],
                            data=data["data"],
                            timestamp=timestamp,
                            cached=True,
                        )
                        # Add to memory cache
                        self.cache[cache_key] = (result, timestamp)
                        self.stats.cache_hits += 1
                        return result
            except Exception as e:
                logger.warning(f"Failed to load cache for {cache_key}: {e}")

        self.stats.cache_misses += 1
        return None

    def _save_cache(self, name: str, source: str, result: AuthorityResult):
        """Save result to cache"""
        cache_key = self._get_cache_key(name, source)

        # Memory cache
        self.cache[cache_key] = (result, datetime.utcnow())

        # Disk cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "source": result.source,
                        "confidence": result.confidence,
                        "data": result.data,
                        "timestamp": result.timestamp.isoformat(),
                    },
                    f,
                )
        except Exception as e:
            logger.warning(f"Failed to save cache for {cache_key}: {e}")

    async def search_single_source(
        self, name: str, source: str
    ) -> Optional[AuthorityResult]:
        """
        Search a single authority source

        Args:
            name: Name to search
            source: Authority source name

        Returns:
            AuthorityResult or None
        """
        # Check cache first
        cached = self._load_cache(name, source)
        if cached:
            return cached

        # Get API
        api = await self._get_api(source)
        if not api:
            return None

        try:
            # Search based on source type
            if source == "crossref":
                async with api as crossref:
                    authors = await crossref.search_author(name, limit=5)
                    if authors:
                        best = authors[0]
                        result = AuthorityResult(
                            source="Crossref", confidence=best["confidence"], data=best
                        )
                        self._save_cache(name, source, result)
                        self.stats.api_calls["crossref"] = (
                            self.stats.api_calls.get("crossref", 0) + 1
                        )
                        return result

            elif source == "openalex":
                async with api as openalex:
                    authors = await openalex.search_authors(name, limit=5)
                    if authors:
                        best = authors[0]
                        result = AuthorityResult(
                            source="OpenAlex",
                            confidence=openalex._calculate_confidence(name, best),
                            data={
                                "id": best.id,
                                "display_name": best.display_name,
                                "orcid": best.orcid,
                                "institution": best.institution_name,
                                "h_index": best.h_index,
                                "works_count": best.works_count,
                                "cited_by_count": best.cited_by_count,
                                "concepts": best.primary_concepts,
                            },
                        )
                        self._save_cache(name, source, result)
                        self.stats.api_calls["openalex"] = (
                            self.stats.api_calls.get("openalex", 0) + 1
                        )
                        return result

            elif source == "orcid":
                async with api as orcid:
                    # Parse name for structured search
                    family = None
                    given = None
                    if "," in name:
                        parts = name.split(",", 1)
                        family = parts[0].strip()
                        given = parts[1].strip() if len(parts) > 1 else None
                    else:
                        parts = name.rsplit(" ", 1)
                        if len(parts) == 2:
                            given = parts[0]
                            family = parts[1]

                    orcids = await orcid.search_by_name(given, family, limit=3)
                    if orcids:
                        person = await orcid.get_person(orcids[0])
                        if person:
                            result = AuthorityResult(
                                source="ORCID",
                                confidence=100.0,  # ORCID is authoritative
                                data={
                                    "orcid": person.orcid,
                                    "canonical_name": person.canonical_name,
                                    "credit_name": person.credit_name,
                                    "affiliations": person.current_affiliations,
                                    "keywords": person.keywords,
                                    "researcher_ids": person.researcher_ids,
                                },
                            )
                            self._save_cache(name, source, result)
                            self.stats.api_calls["orcid"] = (
                                self.stats.api_calls.get("orcid", 0) + 1
                            )
                            return result

        except Exception as e:
            logger.error(f"Error searching {source} for {name}: {e}")
            self.stats.errors.append(f"{source}: {str(e)[:100]}")

        return None

    async def search_all_sources(
        self, name: str, tier_limit: int = None
    ) -> List[AuthorityResult]:
        """
        Search all available sources up to tier limit

        Args:
            name: Name to search
            tier_limit: Maximum tier to search (None = all)

        Returns:
            List of AuthorityResults from all sources
        """
        results = []

        # Sort sources by priority
        sorted_sources = sorted(
            self.sources.items(), key=lambda x: (x[1]["tier"], x[1]["priority"])
        )

        # Search each source
        tasks = []
        for source_name, source_info in sorted_sources:
            if tier_limit is not None and source_info["tier"] > tier_limit:
                continue
            tasks.append(self.search_single_source(name, source_name))

        # Gather results
        source_results = await asyncio.gather(*tasks)

        # Filter out None results
        results = [r for r in source_results if r is not None]

        return results

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single entry with authority data

        Args:
            entry: GMNAP entry to enrich

        Returns:
            Enriched entry
        """
        self.stats.total_entries += 1

        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        if not name:
            return entry

        # Determine tier based on mode
        tier_limit = {"Quick": 0, "Full": 1, "Extreme": None}.get(self.mode, 0)

        # Search all sources
        results = await self.search_all_sources(name, tier_limit)

        if not results:
            return entry

        self.stats.enriched_entries += 1

        # Merge results into entry
        entry = self._merge_results(entry, results)

        return entry

    def _merge_results(
        self, entry: Dict[str, Any], results: List[AuthorityResult]
    ) -> Dict[str, Any]:
        """
        Merge authority results into entry

        Implements intelligent merging with conflict resolution
        """
        # Initialize collections
        if "ExternalIDs" not in entry:
            entry["ExternalIDs"] = []
        if "Affiliations" not in entry:
            entry["Affiliations"] = []
        if "AuthoritySources" not in entry:
            entry["AuthoritySources"] = []
        if "VariantNames" not in entry:
            entry["VariantNames"] = []
        if "ResearchTopics" not in entry:
            entry["ResearchTopics"] = []
        if "Metrics" not in entry:
            entry["Metrics"] = {}

        # Track what we've added to avoid duplicates
        added_ids = set()
        added_affiliations = set()
        added_topics = set()

        # Process results in priority order
        for result in sorted(results, key=lambda r: -r.confidence):
            data = result.data

            # Add authority source record
            entry["AuthoritySources"].append(
                {
                    "source": result.source,
                    "confidence": result.confidence,
                    "timestamp": result.timestamp.isoformat(),
                    "cached": result.cached,
                }
            )

            # Extract and add ORCID
            orcid = data.get("orcid")
            if orcid and orcid not in added_ids:
                entry["ExternalIDs"].append(
                    {
                        "type": "ORCID",
                        "value": orcid,
                        "source": result.source,
                        "confidence": result.confidence,
                    }
                )
                added_ids.add(orcid)

            # Extract and add OpenAlex ID
            openalex_id = data.get("id")
            if openalex_id and openalex_id not in added_ids:
                entry["ExternalIDs"].append(
                    {"type": "OpenAlex", "value": openalex_id, "source": result.source}
                )
                added_ids.add(openalex_id)

            # Add affiliations
            if result.source == "ORCID" and "affiliations" in data:
                for aff in data["affiliations"][:3]:  # Top 3
                    aff_key = (aff.get("organization"), aff.get("country"))
                    if aff_key not in added_affiliations:
                        entry["Affiliations"].append(
                            {
                                "institution": aff.get("organization"),
                                "department": aff.get("department"),
                                "role": aff.get("role"),
                                "country": aff.get("country"),
                                "source": result.source,
                            }
                        )
                        added_affiliations.add(aff_key)

            elif "institution" in data and data["institution"]:
                aff_key = (data["institution"], None)
                if aff_key not in added_affiliations:
                    entry["Affiliations"].append(
                        {"institution": data["institution"], "source": result.source}
                    )
                    added_affiliations.add(aff_key)

            # Add research topics/concepts
            concepts = data.get("concepts", []) or data.get("keywords", [])
            for concept in concepts[:10]:  # Top 10
                if concept and concept not in added_topics:
                    entry["ResearchTopics"].append(concept)
                    added_topics.add(concept)

            # Add metrics
            if result.source == "OpenAlex":
                entry["Metrics"]["openalex"] = {
                    "h_index": data.get("h_index", 0),
                    "works_count": data.get("works_count", 0),
                    "cited_by_count": data.get("cited_by_count", 0),
                }
            elif result.source == "ORCID":
                entry["Metrics"]["orcid"] = {
                    "verified": True,
                    "researcher_ids": len(data.get("researcher_ids", {})),
                }

        return entry

    async def batch_enrich(
        self,
        entries: List[Dict[str, Any]],
        max_concurrent: int = 10,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple entries concurrently

        Args:
            entries: List of entries to enrich
            max_concurrent: Maximum concurrent enrichments
            progress_callback: Optional callback for progress updates

        Returns:
            List of enriched entries
        """
        self.stats = EnrichmentStats()  # Reset stats
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_with_limit(entry, index):
            async with semaphore:
                enriched = await self.enrich_entry(entry)
                if progress_callback:
                    progress_callback(index, len(entries))
                return enriched

        tasks = [enrich_with_limit(entry, i) for i, entry in enumerate(entries)]
        enriched_entries = await asyncio.gather(*tasks)

        return enriched_entries

    def get_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics"""
        return {
            "total_entries": self.stats.total_entries,
            "enriched_entries": self.stats.enriched_entries,
            "success_rate": f"{self.stats.success_rate:.1f}%",
            "cache_hit_rate": f"{self.stats.cache_hit_rate:.1f}%",
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "api_calls": self.stats.api_calls,
            "elapsed_time": f"{self.stats.elapsed_time:.1f}s",
            "errors": len(self.stats.errors),
            "mode": self.mode,
            "sources_enabled": list(self.sources.keys()),
        }

    async def close(self):
        """Clean up resources"""
        # Close any open API connections
        for source_info in self.sources.values():
            if source_info["api"] and hasattr(source_info["api"], "close"):
                await source_info["api"].close()


# Example usage
async def test_authority_manager():
    """Test the authority source manager"""

    # Create config
    config = {
        "mode": "Full",
        "runtime": {},
        "authorities": {
            "crossref": {"enabled": True},
            "openalex": {"enabled": True},
            "orcid": {"enabled": True},
        },
    }

    # Create manager
    manager = AuthoritySourceManager(config)

    # Test entries
    test_entries = [
        {"GlobalID": "test-001", "CanonicalLatin": "T. Tao"},
        {"GlobalID": "test-002", "CanonicalLatin": "Maryam Mirzakhani"},
        {"GlobalID": "test-003", "CanonicalLatin": "Cédric Villani"},
    ]

    import logging

    logger = logging.getLogger(__name__)
    logger.info("Testing Authority Source Manager...")
    logger.info(f"Mode: {manager.mode}")
    logger.info(f"Sources: {list(manager.sources.keys())}")
    logger.info("-" * 40)

    # Enrich entries
    def progress(i, total):
        logger.info(f"  Progress: {i+1}/{total}")

    enriched = await manager.batch_enrich(test_entries, progress_callback=progress)

    # Show results
    logger.info("\nResults:")
    for entry in enriched:
        logger.info(f"\n{entry['CanonicalLatin']}:")
        logger.info(f"  Sources: {len(entry.get('AuthoritySources', []))}")
        logger.info(f"  External IDs: {len(entry.get('ExternalIDs', []))}")
        logger.info(f"  Affiliations: {len(entry.get('Affiliations', []))}")
        logger.info(f"  Topics: {len(entry.get('ResearchTopics', []))}")

        for source in entry.get("AuthoritySources", []):
            logger.info(
                f"    - {source['source']}: {source['confidence']:.1f}% confidence"
            )

    # Show stats
    logger.info("\nStatistics:")
    stats = manager.get_stats()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    await manager.close()


# Alias for compatibility
AuthorityManager = AuthoritySourceManager

# Import extreme adapters for test compatibility


# Add missing enrich_all function for test compatibility
async def enrich_all(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich an entry using all available authority sources."""
    manager = AuthoritySourceManager()
    try:
        result = await manager.enrich_entry(entry)
        return result
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(test_authority_manager())
