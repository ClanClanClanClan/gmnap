"""
Base classes for authority source integration.
Implements the AuthorityFetcher interface from specs v6.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp

logger = logging.getLogger(__name__)


class AuthorityTier(Enum):
    """Authority source tiers."""

    TIER_0 = 0  # Free APIs
    TIER_1 = 1  # Premium APIs
    TIER_2 = 2  # Experimental/Scraping


class FetchStatus(Enum):
    """Status of a fetch operation."""

    SUCCESS = "success"
    RATE_LIMITED = "rate_limited"
    AUTH_FAILED = "auth_failed"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    NOT_FOUND = "not_found"
    QUOTA_EXCEEDED = "quota_exceeded"


@dataclass
class AuthorityData:
    """Parsed data from an authority source."""

    source: str
    source_id: str
    canonical_name: Optional[str] = None
    name_variants: List[str] = field(default_factory=list)
    affiliations: List[Dict[str, Any]] = field(default_factory=list)
    identifiers: Dict[str, str] = field(default_factory=dict)
    msc_codes: List[Dict[str, str]] = field(default_factory=list)
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    countries: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    fetch_timestamp: datetime = field(default_factory=datetime.now)
    personal_data_scrubbed: bool = True


@dataclass
class FetchResult:
    """Result of a fetch operation."""

    status: FetchStatus
    data: Optional[AuthorityData] = None
    error_message: Optional[str] = None
    retry_after: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None


class AuthorityFetcher(ABC):
    """
    Abstract base class for authority source fetchers.

    All authority fetchers must implement this interface.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service = self.__class__.__name__.replace("Fetcher", "")
        self.tier = AuthorityTier.TIER_0  # Override in subclasses
        self.daily_quota = 0  # Override in subclasses
        self.base_url = ""  # Override in subclasses
        self.requires_auth = False  # Override in subclasses

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.0  # seconds

        # Session management
        self._session: Optional[aiohttp.ClientSession] = None

        # Logging
        self.logger = logging.getLogger(f"authorities.{self.service}")

    @abstractmethod
    async def fetch(self, query: str) -> FetchResult:
        """
        Fetch data for a query.

        Args:
            query: Search query (name, ID, etc.)

        Returns:
            FetchResult with status and data
        """
        pass

    @abstractmethod
    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse API response into AuthorityData.

        Args:
            response: Raw API response

        Returns:
            Parsed AuthorityData
        """
        pass

    async def ensure_rate_limit(self) -> None:
        """Ensure we don't exceed rate limits."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._min_request_interval:
            wait_time = self._min_request_interval - time_since_last
            await asyncio.sleep(wait_time)

        self._last_request_time = asyncio.get_event_loop().time()

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"User-Agent": self.config.get("user_agent", "GMNAP/1.0")}

            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)

        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def scrub_personal_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove personal data before caching.

        Args:
            data: Raw data

        Returns:
            Scrubbed data
        """
        # Default implementation - override as needed
        sensitive_fields = ["email", "phone", "address", "ssn", "tax_id"]

        scrubbed = data.copy()
        for field_name in sensitive_fields:
            if field_name in scrubbed:
                scrubbed[field_name] = "[REDACTED]"

        return scrubbed

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for the data.

        Args:
            data: Authority data

        Returns:
            Confidence score (0.0 - 1.0)
        """
        score = 0.0

        # Base score for having data
        score += 0.1

        # Name data
        if data.canonical_name:
            score += 0.2
        if len(data.name_variants) > 0:
            score += 0.1

        # Identifiers
        if len(data.identifiers) > 0:
            score += 0.1 * min(len(data.identifiers), 3)

        # Affiliations
        if len(data.affiliations) > 0:
            score += 0.1

        # MSC codes
        if len(data.msc_codes) > 0:
            score += 0.1

        # Biographical data
        if data.birth_year:
            score += 0.05
        if data.countries:
            score += 0.05

        return min(score, 1.0)


class QuotaManager:
    """
    Manages API quotas across multiple services.

    Tracks usage, enforces limits, and handles quota resets.
    """

    def __init__(
        self, source_manifest: Dict[str, Any], cache_dir: Optional[Union[str, Path]] = None
    ):
        self.source_manifest = source_manifest
        # Ensure cache_dir is always a Path object
        if cache_dir is None:
            self.cache_dir = Path("./cache")
        else:
            self.cache_dir = Path(cache_dir) if not isinstance(cache_dir, Path) else cache_dir
        self.usage: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._load_usage_state()

    def _load_usage_state(self) -> None:
        """Load previous usage state if available."""
        usage_file = self.cache_dir / "quota_usage.json"
        if usage_file.exists():
            try:
                with open(usage_file) as f:
                    self.usage = json.load(f)

                # Check for date rollover
                today = datetime.now().date().isoformat()
                for service in list(self.usage.keys()):
                    if self.usage[service].get("date") != today:
                        # Reset daily quota
                        self.usage[service] = {
                            "date": today,
                            "used": 0,
                            "quota": self._get_quota(service),
                        }
            except Exception as e:
                logger.error(f"Failed to load quota usage: {e}")
                self.usage = {}

    def _save_usage_state(self) -> None:
        """Save current usage state."""
        usage_file = self.cache_dir / "quota_usage.json"
        usage_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(usage_file, "w") as f:
                json.dump(self.usage, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save quota usage: {e}")

    def _get_quota(self, service: str) -> int:
        """Get daily quota for a service."""
        service_config = self.source_manifest.get(service, {})
        quota = service_config.get("daily_quota", 0)

        # Fallback to default quotas if not configured
        if quota == 0:
            default_quotas = {
                "OpenAlex": 864000,
                "Crossref": 4300000,
                "ORCID": 500,
                "zbMATH": 200,
                "DBLP": 86400,
                "MathSciNet": 20000,
                "Scopus": 20000,
                "Dimensions": 10000,
            }
            quota = default_quotas.get(service, 1000)  # Default 1K/day

        return quota

    async def acquire_quota(self, service: str, count: int = 1) -> bool:
        """
        Try to acquire quota for a service.

        Args:
            service: Service name
            count: Number of requests

        Returns:
            True if quota acquired, False if exceeded
        """
        async with self._lock:
            today = datetime.now().date().isoformat()

            # Initialize if needed
            if service not in self.usage:
                self.usage[service] = {"date": today, "used": 0, "quota": self._get_quota(service)}

            # Check date rollover
            if self.usage[service]["date"] != today:
                self.usage[service] = {"date": today, "used": 0, "quota": self._get_quota(service)}

            # Check quota
            quota = self.usage[service]["quota"]
            used = self.usage[service]["used"]

            if used + count > quota:
                logger.warning(f"Quota exceeded for {service}: {used + count}/{quota}")
                return False

            # Update usage
            self.usage[service]["used"] += count
            self._save_usage_state()

            return True

    def get_remaining_quota(self, service: str) -> int:
        """Get remaining quota for today."""
        if service not in self.usage:
            return self._get_quota(service)

        quota = self.usage[service]["quota"]
        used = self.usage[service]["used"]
        return max(0, quota - used)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        stats = {}

        for service, data in self.usage.items():
            stats[service] = {
                "used": data["used"],
                "quota": data["quota"],
                "remaining": max(0, data["quota"] - data["used"]),
                "percentage": (data["used"] / data["quota"] * 100) if data["quota"] > 0 else 0,
            }

        return stats

    def reset(self) -> None:
        """Reset all usage state (primarily for testing)."""
        self.usage.clear()
        # Also remove the persistent state file
        usage_file = self.cache_dir / "quota_usage.json"
        if usage_file.exists():
            try:
                usage_file.unlink()
                logger.info(f"Removed quota usage file: {usage_file}")
            except Exception as e:
                logger.error(f"Failed to remove quota usage file: {e}")

    async def batch_fetch(
        self,
        queries: List[Tuple[str, str]],  # [(service, query), ...]
        fetchers: Dict[str, AuthorityFetcher],
    ) -> List[FetchResult]:
        """
        Batch fetch from multiple services with quota management.

        Args:
            queries: List of (service, query) tuples
            fetchers: Dictionary of service -> fetcher

        Returns:
            List of FetchResults
        """
        # Group by service and respect tier priorities
        tier_groups = {AuthorityTier.TIER_0: [], AuthorityTier.TIER_1: [], AuthorityTier.TIER_2: []}

        for service, query in queries:
            if service in fetchers:
                fetcher = fetchers[service]
                tier_groups[fetcher.tier].append((service, query, fetcher))

        results = []

        # Process by tier priority
        for tier in [AuthorityTier.TIER_0, AuthorityTier.TIER_1, AuthorityTier.TIER_2]:
            if not tier_groups[tier]:
                continue

            # Check quotas and fetch
            tasks = []
            for service, query, fetcher in tier_groups[tier]:
                if await self.acquire_quota(service):
                    task = fetcher.fetch(query)
                    tasks.append(task)
                else:
                    # Quota exceeded
                    results.append(
                        FetchResult(
                            status=FetchStatus.QUOTA_EXCEEDED,
                            error_message=f"Daily quota exceeded for {service}",
                        )
                    )

            # Wait for all fetches in this tier
            if tasks:
                tier_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in tier_results:
                    if isinstance(result, Exception):
                        results.append(
                            FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(result))
                        )
                    else:
                        results.append(result)

        return results
