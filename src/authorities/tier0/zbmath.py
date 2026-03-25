"""
zbMATH Open fetcher for GMNAP.

zbMATH Open is the world's most comprehensive mathematical database.
API Documentation: https://oai.zbmath.org/
"""

import asyncio
import urllib.parse
from typing import Any, Dict, List, Optional

from src.authorities.base import (
    AuthorityData,
    AuthorityFetcher,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)


class ZbMATHFetcher(AuthorityFetcher):
    """
    Fetcher for zbMATH Open API.

    Features:
    - Mathematical focus (perfect for GMNAP)
    - CC-BY license
    - Rich mathematical metadata including MSC codes
    - Author profiles with research areas
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = "zbMATH"
        self.tier = AuthorityTier.TIER_0
        self.daily_quota = 200  # Conservative due to low limit
        self.base_url = "https://oai.zbmath.org/v1"
        self.requires_auth = False

        # Rate limiting: Very conservative due to low quota
        self._min_request_interval = 0.5  # 500ms between requests (2/sec)

    async def fetch(self, query: str) -> FetchResult:
        """
        Fetch mathematician data from zbMATH.

        Args:
            query: Mathematician name or zbMATH author ID

        Returns:
            FetchResult with parsed data
        """
        try:
            # Rate limiting
            await self.ensure_rate_limit()

            # Check if query is a zbMATH author ID
            if query.startswith("au:") or query.isdigit():
                # Direct author lookup
                return await self._fetch_by_author_id(query)
            else:
                # Name search
                return await self._search_by_name(query)

        except asyncio.TimeoutError:
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message="Request timeout")

        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(e))

    async def _fetch_by_author_id(self, author_id: str) -> FetchResult:
        """Fetch data using zbMATH author ID."""
        # Clean author ID
        if author_id.startswith("au:"):
            author_id = author_id[3:]

        url = f"{self.base_url}/authors/{author_id}"
        headers = {"Accept": "application/json"}

        session = await self.get_session()

        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                parsed = self.parse_response(data)

                return FetchResult(
                    status=FetchStatus.SUCCESS,
                    data=parsed,
                    raw_response=self.scrub_personal_data(data),
                )

            elif response.status == 404:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND, error_message="zbMATH author ID not found"
                )

            elif response.status == 429:
                retry_after = response.headers.get("Retry-After", 60)
                return FetchResult(
                    status=FetchStatus.RATE_LIMITED,
                    error_message="Rate limit exceeded",
                    retry_after=int(retry_after),
                )

            else:
                return FetchResult(
                    status=FetchStatus.NETWORK_ERROR,
                    error_message=f"HTTP {response.status}: {await response.text()}",
                )

    async def _search_by_name(self, name: str) -> FetchResult:
        """Search zbMATH by mathematician name."""
        # Search for documents by author, then extract author info
        params = {"q": f"au:{name}", "results_per_page": 10, "format": "json"}

        url = f"{self.base_url}/document/_search"
        headers = {"Accept": "application/json"}

        session = await self.get_session()

        # Build URL with params
        full_url = url + "?" + urllib.parse.urlencode(params)

        async with session.get(full_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()

                # Parse search results to extract author data
                if "result" not in data or not data["result"]:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND, error_message="No zbMATH entries found"
                    )

                # Extract author data from documents
                parsed = self.parse_search_results(data["result"], name)

                return FetchResult(
                    status=FetchStatus.SUCCESS,
                    data=parsed,
                    raw_response=self.scrub_personal_data(data),
                )

            elif response.status == 429:
                retry_after = response.headers.get("Retry-After", 60)
                return FetchResult(
                    status=FetchStatus.RATE_LIMITED,
                    error_message="Rate limit exceeded",
                    retry_after=int(retry_after),
                )

            else:
                return FetchResult(
                    status=FetchStatus.NETWORK_ERROR,
                    error_message=f"HTTP {response.status}: {await response.text()}",
                )

    def parse_search_results(self, documents: List[Dict[str, Any]], query: str) -> AuthorityData:
        """Parse zbMATH search results to extract author data."""
        # Collect author statistics from documents
        author_stats = {
            "documents_count": len(documents),
            "msc_codes": {},
            "name_variants": set(),
            "years": [],
            "affiliations": set(),
            "zbmath_id": None,
        }

        for doc in documents:
            # Extract publication year
            if "year" in doc:
                author_stats["years"].append(doc["year"])

            # Extract MSC codes
            if "msc" in doc:
                for msc in doc["msc"]:
                    code = msc.get("code", "")
                    if code:
                        author_stats["msc_codes"][code] = author_stats["msc_codes"].get(code, 0) + 1

            # Extract author variants and affiliations from this document
            if "authors" in doc:
                for author in doc["authors"]:
                    # Check if this is likely our target author
                    author_name = author.get("name", "")
                    if self._name_matches(author_name, query):
                        author_stats["name_variants"].add(author_name)

                        # Extract zbMATH author ID
                        if "id" in author and not author_stats["zbmath_id"]:
                            author_stats["zbmath_id"] = author["id"]

                        # Extract affiliations
                        if "affiliations" in author:
                            for aff in author["affiliations"]:
                                if "name" in aff:
                                    author_stats["affiliations"].add(aff["name"])

        # Build AuthorityData
        canonical_name = query
        if author_stats["name_variants"]:
            # Use most common variant or longest name
            canonical_name = max(
                author_stats["name_variants"],
                key=lambda x: (author_stats["name_variants"].count(x), len(x)),
            )

        zbmath_id = author_stats["zbmath_id"] or f"zbmath_{hash(canonical_name)}"

        data = AuthorityData(
            source=self.service, source_id=zbmath_id, canonical_name=canonical_name
        )

        # Add name variants
        data.name_variants = list(author_stats["name_variants"])

        # Add MSC codes (top 5)
        msc_codes = []
        for code, count in sorted(
            author_stats["msc_codes"].items(), key=lambda x: x[1], reverse=True
        )[:5]:
            msc_codes.append({"code": code, "source": "zbMATH", "frequency": count})
        data.msc_codes = msc_codes

        # Add affiliations
        affiliations = []
        for aff_name in list(author_stats["affiliations"])[:5]:
            affiliations.append({"name": aff_name, "type": "institution"})
        data.affiliations = affiliations

        # Metadata
        data.metadata = {
            "documents_count": author_stats["documents_count"],
            "year_range": (
                f"{min(author_stats['years'])}-{max(author_stats['years'])}"
                if author_stats["years"]
                else ""
            ),
            "msc_codes_count": len(author_stats["msc_codes"]),
            "zbmath_source": "document_search",
        }

        # Calculate confidence
        data.confidence_score = self.calculate_confidence(data, author_stats)

        return data

    def _name_matches(self, author_name: str, query: str) -> bool:
        """Check if author name matches query."""
        author_words = set(author_name.lower().split())
        query_words = set(query.lower().split())

        # Check for significant overlap
        intersection = len(author_words.intersection(query_words))
        min_words = min(len(author_words), len(query_words))

        return intersection >= min_words * 0.5  # At least 50% overlap

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse zbMATH author response into AuthorityData.

        Args:
            response: Raw zbMATH API response

        Returns:
            Parsed AuthorityData
        """
        # Validate response
        if response is None or not isinstance(response, dict):
            return AuthorityData(source=self.service, source_id="", canonical_name="")

        # Extract basic info
        zbmath_id = response.get("id", "")
        name = response.get("name", "")

        data = AuthorityData(source=self.service, source_id=zbmath_id, canonical_name=name)

        # Add name variants if available
        if "variants" in response:
            data.name_variants = response["variants"]

        # Add affiliations
        if "affiliations" in response:
            affiliations = []
            for aff in response["affiliations"][:5]:
                affiliations.append({"name": aff.get("name", ""), "type": "institution"})
            data.affiliations = affiliations

        # Add research areas as MSC codes
        if "research_areas" in response:
            msc_codes = []
            for area in response["research_areas"][:5]:
                msc_codes.append(
                    {
                        "code": area.get("msc", ""),
                        "source": "zbMATH",
                        "description": area.get("description", ""),
                    }
                )
            data.msc_codes = msc_codes

        # Metadata
        data.metadata = {
            "zbmath_id": zbmath_id,
            "documents_count": response.get("documents_count", 0),
            "research_areas_count": len(response.get("research_areas", [])),
            "profile_type": "author_profile",
        }

        # Calculate confidence
        data.confidence_score = self.calculate_confidence(data)

        return data

    def calculate_confidence(
        self, data: AuthorityData, stats: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate confidence score for zbMATH data.

        Higher confidence for:
        - Multiple documents
        - MSC codes present
        - Name variants
        - Recent activity
        """
        score = 0.1  # Base score

        # Documents count
        docs_count = data.metadata.get("documents_count", 0)
        if stats:
            docs_count = stats.get("documents_count", docs_count)

        if docs_count > 0:
            score += 0.2
        if docs_count > 5:
            score += 0.1
        if docs_count > 20:
            score += 0.1

        # MSC codes (very valuable for mathematicians)
        if len(data.msc_codes) > 0:
            score += 0.2
        if len(data.msc_codes) > 2:
            score += 0.1

        # Name variants
        if len(data.name_variants) > 1:
            score += 0.1

        # Affiliations
        if len(data.affiliations) > 0:
            score += 0.1

        # zbMATH is math-specific, so boost confidence
        score += 0.1  # Mathematical source bonus

        return min(score, 1.0)
