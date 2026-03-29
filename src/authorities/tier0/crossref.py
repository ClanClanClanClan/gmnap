"""
Crossref fetcher for GMNAP.

Crossref is a free, open-source DOI registration agency.
API Documentation: https://api.crossref.org/
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


class CrossrefFetcher(AuthorityFetcher):
    """
    Fetcher for Crossref API.

    Features:
    - Free tier with high quotas (4.3M/day)
    - No authentication required
    - Rich DOI metadata including authors, affiliations
    - ORCID integration via DOI metadata
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = "Crossref"
        self.tier = AuthorityTier.TIER_0
        self.daily_quota = 4_300_000
        self.base_url = "https://api.crossref.org"
        self.requires_auth = False

        # Rate limiting: Be polite with requests
        self._min_request_interval = 0.1  # 100ms between requests

        # Required polite email
        self.email = config.get("email", "gmnap@example.com")

    async def fetch(self, query: str) -> FetchResult:
        """
        Fetch author data from Crossref.

        Args:
            query: Author name or DOI

        Returns:
            FetchResult with parsed data
        """
        try:
            # Rate limiting
            await self.ensure_rate_limit()

            # Check if query is a DOI
            if isinstance(query, str) and (query.startswith("10.") or "/" in query):
                # Direct DOI lookup
                endpoint = f"/works/{urllib.parse.quote(query, safe='')}"
                params = {"mailto": self.email}
            else:
                # Author name search via works
                endpoint = "/works"
                params = {
                    "query.author": query,
                    "mailto": self.email,
                    "rows": 10,
                    "sort": "relevance",
                }

            # Build URL
            url = self.base_url + endpoint
            if params:
                url += "?" + urllib.parse.urlencode(params)

            # Make request
            session = await self.get_session()

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Handle search results vs direct lookup
                    if "message" in data and "items" in data["message"]:
                        # Search results
                        works = data["message"]["items"]
                        if not works:
                            return FetchResult(
                                status=FetchStatus.NOT_FOUND,
                                error_message="No works found",
                            )

                        # Parse author data from works
                        parsed = self.parse_works(works, query)

                    elif "message" in data:
                        # Direct DOI lookup
                        work = data["message"]
                        parsed = self.parse_works([work], query)

                    else:
                        return FetchResult(
                            status=FetchStatus.PARSE_ERROR,
                            error_message="Unexpected response format",
                        )

                    return FetchResult(
                        status=FetchStatus.SUCCESS,
                        data=parsed,
                        raw_response=self.scrub_personal_data(data),
                    )

                elif response.status == 404:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND,
                        error_message="Author/DOI not found",
                    )

                elif response.status == 429:
                    # Rate limited
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

        except asyncio.TimeoutError:
            return FetchResult(
                status=FetchStatus.NETWORK_ERROR, error_message="Request timeout"
            )

        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(e))

    def parse_works(self, works: List[Dict[str, Any]], query: str) -> AuthorityData:
        """
        Parse Crossref works into AuthorityData.

        Args:
            works: List of work objects from Crossref API
            query: Original query string

        Returns:
            Parsed AuthorityData
        """
        # Find best matching author across all works
        best_author = None
        author_stats = {}

        # Collect author statistics
        for work in works:
            if "author" not in work:
                continue

            for author in work["author"]:
                author_key = self._get_author_key(author)
                if not author_key:
                    continue

                if author_key not in author_stats:
                    author_stats[author_key] = {
                        "author": author,
                        "works_count": 0,
                        "affiliations": set(),
                        "orcids": set(),
                        "name_variants": set(),
                    }

                stats = author_stats[author_key]
                stats["works_count"] += 1

                # Collect name variants
                if "given" in author and "family" in author:
                    full_name = f"{author['family']}, {author['given']}"
                    stats["name_variants"].add(full_name)

                # Collect ORCID
                if "ORCID" in author:
                    orcid = author["ORCID"].split("/")[-1]
                    stats["orcids"].add(orcid)

                # Collect affiliations
                if "affiliation" in author:
                    for aff in author["affiliation"]:
                        if "name" in aff:
                            stats["affiliations"].add(aff["name"])

        # Find best match (most works, or closest name match)
        if author_stats:
            best_key = max(
                author_stats.keys(),
                key=lambda k: (
                    author_stats[k]["works_count"],
                    self._name_similarity(k, query),
                ),
            )
            best_author = author_stats[best_key]["author"]
            best_stats = author_stats[best_key]

        if not best_author:
            # Create minimal data
            return AuthorityData(
                source=self.service,
                source_id=f"crossref_{hash(query)}",
                canonical_name=query,
            )

        # Build AuthorityData
        author_key = self._get_author_key(best_author)

        data = AuthorityData(
            source=self.service,
            source_id=f"crossref_{hash(author_key)}",
            canonical_name=author_key,
        )

        # Add name variants
        data.name_variants = list(best_stats["name_variants"])

        # Add ORCID if available
        if best_stats["orcids"]:
            data.identifiers["ORCID"] = list(best_stats["orcids"])[0]

        # Add affiliations
        affiliations = []
        for aff_name in list(best_stats["affiliations"])[:5]:  # Top 5
            affiliations.append({"name": aff_name, "type": "institution"})
        data.affiliations = affiliations

        # Metadata
        data.metadata = {
            "works_count": best_stats["works_count"],
            "crossref_source": "works_search",
            "query_method": (
                "author_search"
                if not (isinstance(query, str) and query.startswith("10."))
                else "doi_lookup"
            ),
        }

        # Calculate confidence
        data.confidence_score = self.calculate_confidence(data, best_stats)

        return data

    def _get_author_key(self, author: Dict[str, Any]) -> Optional[str]:
        """Get normalized author key for matching."""
        if "family" in author:
            family = author["family"]
            given = author.get("given", "")
            return f"{family}, {given}".strip(", ")
        return None

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Simple name similarity score."""
        name1_words = set(name1.lower().split())
        name2_words = set(name2.lower().split())

        if not name1_words or not name2_words:
            return 0.0

        intersection = len(name1_words.intersection(name2_words))
        union = len(name1_words.union(name2_words))

        return intersection / union if union > 0 else 0.0

    def calculate_confidence(self, data: AuthorityData, stats: Dict[str, Any]) -> float:
        """
        Calculate confidence score for Crossref data.

        Higher confidence for:
        - ORCID present
        - Multiple works
        - Multiple affiliations
        - Name variants
        """
        score = 0.0

        # Base score
        score += 0.1

        # ORCID is strong signal
        if "ORCID" in data.identifiers:
            score += 0.3

        # Works count
        works_count = stats.get("works_count", 0)
        if works_count > 0:
            score += 0.1
        if works_count > 5:
            score += 0.1
        if works_count > 20:
            score += 0.1

        # Name variants
        if len(data.name_variants) > 1:
            score += 0.1

        # Affiliations
        if len(data.affiliations) > 0:
            score += 0.1
        if len(data.affiliations) > 2:
            score += 0.1

        return min(score, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """Parse API response - not used for Crossref."""
        # Validate response
        if response is None or not isinstance(response, dict):
            return AuthorityData(source=self.service, source_id="", canonical_name="")

        # This method is required by base class but not used
        # since we use parse_works instead
        return AuthorityData(source=self.service, source_id="", canonical_name="")
