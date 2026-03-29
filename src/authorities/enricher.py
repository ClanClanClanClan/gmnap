"""
Authority Enricher - Integrates all authority sources for V7 pipeline.
Implements parallel fetching with tier-based prioritization.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from src.authorities.base import (
    AuthorityData,
    AuthorityFetcher,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)

# Import all available fetchers
from src.authorities.tier0.crossref import CrossrefFetcher
from src.authorities.tier0.orcid import ORCIDFetcher as OrcidFetcher

try:
    from src.authorities.tier0.openalex import OpenAlexFetcher
except ImportError:
    OpenAlexFetcher = None
try:
    from src.authorities.tier0.zbmath import ZbMathFetcher
except ImportError:
    ZbMathFetcher = None
try:
    from src.authorities.tier0.orcid_etd import ORCIDETDFetcher
except ImportError:
    ORCIDETDFetcher = None
try:
    from src.authorities.tier0.crossref_thesis import CrossrefThesisFetcher
except ImportError:
    CrossrefThesisFetcher = None

# Import tier1 fetchers
try:
    from src.authorities.tier1.arxiv import ArXivFetcher as ArxivFetcher
except ImportError:
    ArxivFetcher = None
try:
    from src.authorities.tier1.dblp import DBLPFetcher
except ImportError:
    DBLPFetcher = None
try:
    from src.authorities.tier1.mathscinet import MathSciNetFetcher
except ImportError:
    MathSciNetFetcher = None
try:
    from src.authorities.tier1.wikidata import WikidataFetcher
except ImportError:
    WikidataFetcher = None
try:
    from src.authorities.tier1.hal import HALFetcher
except ImportError:
    HALFetcher = None
try:
    from src.authorities.tier1.gnd import GNDFetcher
except ImportError:
    GNDFetcher = None
try:
    from src.authorities.tier1.viaf import VIAFFetcher
except ImportError:
    VIAFFetcher = None
try:
    from src.authorities.tier1.pubmed import PubMedFetcher
except ImportError:
    PubMedFetcher = None

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Result of enrichment across multiple sources."""

    query: str
    sources_attempted: List[str] = field(default_factory=list)
    sources_succeeded: List[str] = field(default_factory=list)
    sources_failed: Dict[str, str] = field(default_factory=dict)
    data: Dict[str, AuthorityData] = field(default_factory=dict)
    canonical_name: Optional[str] = None
    merged_variants: Set[str] = field(default_factory=set)
    merged_identifiers: Dict[str, str] = field(default_factory=dict)
    merged_affiliations: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    enrichment_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class AuthorityEnricher:
    """
    Coordinates fetching from multiple authority sources.
    Implements V7 specification for authority enrichment.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the enricher with configuration.

        Args:
            config: Configuration dictionary with API keys, tier settings, etc.
        """
        self.config = config or {}
        self.logger = logger

        # Initialize fetchers by tier
        self.fetchers_by_tier = {
            AuthorityTier.TIER_0: [],
            AuthorityTier.TIER_1: [],
            AuthorityTier.TIER_2: [],
        }

        # Initialize available fetchers
        self._initialize_fetchers()

        # Cache for results (simple in-memory cache)
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour TTL

        # Statistics
        self.stats = defaultdict(int)

    def _initialize_fetchers(self):
        """Initialize all available fetchers based on configuration."""

        # Tier 0 - Free APIs (V7 spec compliant)
        tier0_fetchers = [
            (CrossrefFetcher, "crossref"),
            (OrcidFetcher, "orcid"),
            (OpenAlexFetcher, "openalex"),
            (ZbMathFetcher, "zbmath"),
            (ORCIDETDFetcher, "orcid_etd"),
            (CrossrefThesisFetcher, "crossref_thesis"),
        ]

        for fetcher_class, name in tier0_fetchers:
            if fetcher_class is None:
                logger.debug(f"Fetcher {name} not available (not implemented)")
                continue
            try:
                fetcher_config = self.config.get(name, {})
                fetcher = fetcher_class(fetcher_config)
                self.fetchers_by_tier[AuthorityTier.TIER_0].append(fetcher)
                logger.info(f"Initialized {name} fetcher (Tier 0)")
            except Exception as e:
                logger.warning(f"Failed to initialize {name}: {e}")

        # Tier 1 - Premium/Limited APIs
        tier1_fetchers = [
            (ArxivFetcher, "arxiv"),
            (DBLPFetcher, "dblp"),
            (MathSciNetFetcher, "mathscinet"),
            (WikidataFetcher, "wikidata"),
            (HALFetcher, "hal"),
            (GNDFetcher, "gnd"),
            (VIAFFetcher, "viaf"),
            (PubMedFetcher, "pubmed"),
        ]

        for fetcher_class, config_name in tier1_fetchers:
            if fetcher_class is None:
                logger.debug(f"Fetcher {config_name} not available (not implemented)")
                continue
            try:
                fetcher_config = self.config.get(config_name, {})
                fetcher = fetcher_class(fetcher_config)
                self.fetchers_by_tier[AuthorityTier.TIER_1].append(fetcher)
                logger.info(f"Initialized {config_name} fetcher (Tier 1)")
            except Exception as e:
                logger.debug(f"Tier 1 fetcher {config_name} not available: {e}")

        # Log summary
        total_fetchers = sum(len(f) for f in self.fetchers_by_tier.values())
        logger.info(f"Initialized {total_fetchers} authority fetchers")
        logger.info(f"  Tier 0: {len(self.fetchers_by_tier[AuthorityTier.TIER_0])}")
        logger.info(f"  Tier 1: {len(self.fetchers_by_tier[AuthorityTier.TIER_1])}")
        logger.info(f"  Tier 2: {len(self.fetchers_by_tier[AuthorityTier.TIER_2])}")

    async def enrich(
        self,
        query: str,
        tiers: Optional[List[AuthorityTier]] = None,
        timeout: float = 10.0,
    ) -> EnrichmentResult:
        """
        Enrich a query by fetching from multiple authority sources.

        Args:
            query: The search query (name, DOI, ORCID, etc.)
            tiers: Which tiers to use (default: TIER_0 only)
            timeout: Maximum time to wait for all sources

        Returns:
            EnrichmentResult with merged data from all sources
        """
        start_time = datetime.now()

        # Check cache first
        cache_key = f"{query}:{tiers}"
        if cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                self.stats["cache_hits"] += 1
                return cached_result

        # Default to tier 0 if not specified
        if tiers is None:
            tiers = [AuthorityTier.TIER_0]

        # Collect fetchers to use
        fetchers_to_use = []
        for tier in tiers:
            fetchers_to_use.extend(self.fetchers_by_tier.get(tier, []))

        if not fetchers_to_use:
            logger.warning(f"No fetchers available for tiers {tiers}")
            return EnrichmentResult(
                query=query, sources_attempted=[], enrichment_time_ms=0
            )

        # Create result object
        result = EnrichmentResult(query=query)

        # Fetch from all sources in parallel
        tasks = []
        for fetcher in fetchers_to_use:
            result.sources_attempted.append(fetcher.service)
            task = asyncio.create_task(
                self._fetch_with_timeout(fetcher, query, timeout)
            )
            tasks.append((fetcher.service, task))

        # Wait for all tasks to complete
        for service_name, task in tasks:
            try:
                fetch_result = await task

                if fetch_result.status == FetchStatus.SUCCESS:
                    result.sources_succeeded.append(service_name)
                    if fetch_result.data:
                        result.data[service_name] = fetch_result.data
                        # Merge data
                        self._merge_data(result, fetch_result.data)
                else:
                    result.sources_failed[service_name] = (
                        fetch_result.error_message or str(fetch_result.status)
                    )

            except asyncio.TimeoutError:
                result.sources_failed[service_name] = "Timeout"
            except Exception as e:
                result.sources_failed[service_name] = str(e)
                logger.error(f"Error fetching from {service_name}: {e}")

        # Calculate confidence score based on number of successful sources
        if result.sources_succeeded:
            result.confidence_score = len(result.sources_succeeded) / len(
                result.sources_attempted
            )

        # Record timing
        result.enrichment_time_ms = int(
            (datetime.now() - start_time).total_seconds() * 1000
        )

        # Cache the result
        self.cache[cache_key] = (result, datetime.now())
        self.stats["total_enrichments"] += 1

        # Log summary
        logger.info(
            f"Enrichment for '{query}': {len(result.sources_succeeded)}/{len(result.sources_attempted)} sources succeeded in {result.enrichment_time_ms}ms"
        )

        return result

    async def _fetch_with_timeout(
        self, fetcher: AuthorityFetcher, query: str, timeout: float
    ) -> FetchResult:
        """
        Fetch from a single source with timeout.

        Args:
            fetcher: The fetcher to use
            query: The search query
            timeout: Maximum time to wait

        Returns:
            FetchResult from the fetcher
        """
        try:
            return await asyncio.wait_for(fetcher.fetch(query), timeout=timeout)
        except asyncio.TimeoutError:
            return FetchResult(
                status=FetchStatus.NETWORK_ERROR,
                error_message=f"Timeout after {timeout}s",
            )

    def _merge_data(self, result: EnrichmentResult, data: AuthorityData):
        """
        Merge data from a single source into the combined result.

        Args:
            result: The result to merge into
            data: The data to merge
        """
        # Merge name variants
        if data.canonical_name:
            if not result.canonical_name:
                result.canonical_name = data.canonical_name
            result.merged_variants.add(data.canonical_name)

        result.merged_variants.update(data.name_variants)

        # Merge identifiers
        result.merged_identifiers.update(data.identifiers)

        # Merge affiliations (avoid duplicates)
        existing_affiliations = {
            aff.get("name", ""): aff for aff in result.merged_affiliations
        }

        for affiliation in data.affiliations:
            aff_name = affiliation.get("name", "")
            if aff_name and aff_name not in existing_affiliations:
                result.merged_affiliations.append(affiliation)

    async def enrich_batch(
        self,
        queries: List[str],
        tiers: Optional[List[AuthorityTier]] = None,
        max_concurrent: int = 10,
    ) -> List[EnrichmentResult]:
        """
        Enrich multiple queries in parallel.

        Args:
            queries: List of search queries
            tiers: Which tiers to use
            max_concurrent: Maximum concurrent enrichments

        Returns:
            List of EnrichmentResults
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_with_semaphore(query: str) -> EnrichmentResult:
            async with semaphore:
                return await self.enrich(query, tiers)

        tasks = [enrich_with_semaphore(q) for q in queries]
        return await asyncio.gather(*tasks)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get enricher statistics.

        Returns:
            Dictionary with statistics
        """
        total_fetchers = sum(len(f) for f in self.fetchers_by_tier.values())

        return {
            "total_fetchers": total_fetchers,
            "fetchers_by_tier": {
                tier.name: len(fetchers)
                for tier, fetchers in self.fetchers_by_tier.items()
            },
            "cache_size": len(self.cache),
            "stats": dict(self.stats),
            "available_sources": [
                f.service
                for fetchers in self.fetchers_by_tier.values()
                for f in fetchers
            ],
        }

    async def close(self):
        """Clean up resources."""
        # Close all fetcher sessions
        for fetchers in self.fetchers_by_tier.values():
            for fetcher in fetchers:
                if hasattr(fetcher, "close"):
                    await fetcher.close()
