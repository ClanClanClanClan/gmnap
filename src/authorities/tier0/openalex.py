"""
OpenAlex fetcher for GMNAP.

OpenAlex is a free, open-source catalog of scholarly works.
API Documentation: https://docs.openalex.org/
"""

import asyncio
import urllib.parse
from typing import Any, Dict

from src.authorities.base import (
    AuthorityData,
    AuthorityFetcher,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)


class OpenAlexFetcher(AuthorityFetcher):
    """
    Fetcher for OpenAlex API.

    Features:
    - Free tier with 10 requests/second
    - No authentication required
    - Rich metadata including affiliations, works, and concepts
    - ORCID integration
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = "OpenAlex"
        self.tier = AuthorityTier.TIER_0
        self.daily_quota = 864_000  # 10/sec * 86400 sec/day
        self.base_url = "https://api.openalex.org"
        self.requires_auth = False

        # Rate limiting: 10 requests per second
        self._min_request_interval = 0.1  # 100ms between requests

        # Search configuration
        self.email = config.get("email", "gmnap@example.com")

    async def fetch(self, query: str) -> FetchResult:
        """
        Fetch author data from OpenAlex.

        Args:
            query: Author name or OpenAlex ID

        Returns:
            FetchResult with parsed data
        """
        try:
            # Rate limiting
            await self.ensure_rate_limit()

            # Check if query is an OpenAlex ID
            if isinstance(query, str) and query.startswith("A") and len(query) == 11:
                # Direct ID lookup
                endpoint = f"/authors/{query}"
                params = {"mailto": self.email}
            else:
                # Name search
                endpoint = "/authors"
                params = {
                    "filter": f"display_name.search:{query}",
                    "mailto": self.email,
                    "per_page": 10,
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
                    if "results" in data:
                        # Search results
                        if not data["results"]:
                            return FetchResult(
                                status=FetchStatus.NOT_FOUND,
                                error_message="No results found",
                            )

                        # Take best match
                        author_data = data["results"][0]
                    else:
                        # Direct lookup
                        author_data = data

                    # Parse response
                    parsed = self.parse_response(author_data)

                    return FetchResult(
                        status=FetchStatus.SUCCESS,
                        data=parsed,
                        raw_response=self.scrub_personal_data(author_data),
                    )

                elif response.status == 404:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND, error_message="Author not found"
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

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse OpenAlex response into AuthorityData.

        Args:
            response: Raw API response

        Returns:
            Parsed AuthorityData
        """
        # Validate response
        if not response or not isinstance(response, dict):
            return AuthorityData(source=self.service, source_id="", canonical_name="")

        # Extract basic info
        openalex_id = (
            response.get("id", "").split("/")[-1] if response.get("id") else ""
        )
        display_name = response.get("display_name", "")

        # Initialize data
        data = AuthorityData(
            source=self.service, source_id=openalex_id, canonical_name=display_name
        )

        # Name variants
        if "display_name_alternatives" in response:
            data.name_variants = response["display_name_alternatives"]

        # ORCID
        if response.get("orcid"):
            orcid = response["orcid"].split("/")[-1]
            data.identifiers["ORCID"] = orcid

        # Extract affiliations
        affiliations = []
        if "affiliations" in response:
            for affiliation in response["affiliations"]:
                institution = affiliation.get("institution")
                if institution:
                    aff_data = {
                        "name": institution.get("display_name", ""),
                        "country": institution.get("country_code", ""),
                        "type": institution.get("type", ""),
                        "years": affiliation.get("years", []),
                    }

                    # Try to determine timeline
                    if aff_data["years"]:
                        aff_data["from"] = min(aff_data["years"])
                        aff_data["to"] = max(aff_data["years"])

                    affiliations.append(aff_data)

        data.affiliations = affiliations

        # Extract countries from affiliations
        countries = set()
        for aff in affiliations:
            if aff.get("country"):
                countries.add(aff["country"])
        data.countries = list(countries)

        # Research areas (concepts)
        if "x_concepts" in response:
            # Extract MSC-like codes from concepts
            msc_codes = []
            for concept in response["x_concepts"][:5]:  # Top 5
                if concept.get("level") == 2:  # Field level
                    msc_codes.append(
                        {
                            "code": str(concept.get("id", ""))[-5:],  # Fake MSC
                            "source": "OpenAlex",
                            "name": concept.get("display_name", ""),
                        }
                    )
            data.msc_codes = msc_codes

        # Metadata
        data.metadata = {
            "works_count": response.get("works_count", 0),
            "cited_by_count": response.get("cited_by_count", 0),
            "h_index": response.get("summary_stats", {}).get("h_index", 0),
            "last_known_affiliation": response.get("last_known_affiliation"),
            "created_date": response.get("created_date"),
            "updated_date": response.get("updated_date"),
        }

        # Calculate confidence
        data.confidence_score = self.calculate_confidence(data)

        return data

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for OpenAlex data.

        Higher confidence for:
        - ORCID present
        - Multiple affiliations
        - High citation count
        - Recent activity
        """
        score = 0.0

        # Base score
        score += 0.1

        # ORCID is strong signal
        if "ORCID" in data.identifiers:
            score += 0.3

        # Name data
        if data.canonical_name:
            score += 0.1
        if len(data.name_variants) > 0:
            score += 0.1

        # Affiliations
        if len(data.affiliations) > 0:
            score += 0.1
        if len(data.affiliations) > 2:
            score += 0.1

        # Research activity
        works_count = data.metadata.get("works_count", 0)
        if works_count > 0:
            score += 0.05
        if works_count > 10:
            score += 0.05

        # Citations
        citations = data.metadata.get("cited_by_count", 0)
        if citations > 0:
            score += 0.05
        if citations > 100:
            score += 0.05

        return min(score, 1.0)
