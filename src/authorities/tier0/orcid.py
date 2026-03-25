"""
ORCID fetcher for GMNAP.

ORCID provides a persistent digital identifier for researchers.
API Documentation: https://info.orcid.org/documentation/features/public-api/
"""

import asyncio
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.authorities.base import (
    AuthorityData,
    AuthorityFetcher,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)


class ORCIDFetcher(AuthorityFetcher):
    """
    Fetcher for ORCID API.

    Features:
    - Free public API access
    - Persistent researcher identifiers
    - Rich profile data including employment, education
    - High-quality, curated data
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = "ORCID"
        self.tier = AuthorityTier.TIER_0
        self.daily_quota = 500  # Conservative limit
        self.base_url = "https://pub.orcid.org/v3.0"
        self.requires_auth = False

        # Rate limiting: Be conservative
        self._min_request_interval = 0.2  # 200ms between requests (5/sec)

        # Search endpoint for names
        self.search_url = "https://pub.orcid.org/v3.0/search"

    async def fetch(self, query: str) -> FetchResult:
        """
        Fetch researcher data from ORCID.

        Args:
            query: Researcher name or ORCID ID

        Returns:
            FetchResult with parsed data
        """
        try:
            # Rate limiting
            await self.ensure_rate_limit()

            # Check if query is an ORCID ID
            if self._is_orcid_id(query):
                # Direct ORCID lookup
                return await self._fetch_by_orcid(query)
            else:
                # Name search
                return await self._search_by_name(query)

        except asyncio.TimeoutError:
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message="Request timeout")

        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(e))

    def _is_orcid_id(self, query: str) -> bool:
        """Check if query looks like an ORCID ID."""
        # ORCID format: 0000-0000-0000-0000
        return (
            len(query) == 19
            and query.count("-") == 3
            and all(c.isdigit() or c == "-" for c in query)
        )

    async def _fetch_by_orcid(self, orcid_id: str) -> FetchResult:
        """Fetch data using ORCID ID."""
        # Clean ORCID ID
        orcid_id = orcid_id.replace("https://orcid.org/", "")

        # Get profile data
        url = f"{self.base_url}/{orcid_id}/record"
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
                return FetchResult(status=FetchStatus.NOT_FOUND, error_message="ORCID ID not found")

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
        """Search ORCID by researcher name."""
        # Build search query
        params = {
            "q": f'family-name:"{name.split()[-1]}" OR given-names:"{name.split()[0]}"',
            "rows": 10,
        }

        url = self.search_url + "?" + urllib.parse.urlencode(params)
        headers = {"Accept": "application/json"}

        session = await self.get_session()

        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()

                # Parse search results
                if "result" not in data or not data["result"]:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND, error_message="No ORCID profiles found"
                    )

                # Get best match
                best_result = self._find_best_match(data["result"], name)

                if not best_result:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND, error_message="No suitable matches found"
                    )

                # Fetch full profile for best match
                orcid_id = best_result["orcid-identifier"]["path"]
                return await self._fetch_by_orcid(orcid_id)

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

    def _find_best_match(
        self, results: List[Dict[str, Any]], query: str
    ) -> Optional[Dict[str, Any]]:
        """Find best matching ORCID profile."""
        if not results:
            return None

        query_words = set(query.lower().split())
        best_score = 0
        best_result = None

        for result in results:
            score = 0

            # Check person details
            if "person" in result:
                person = result["person"]

                # Check given names
                if "given-names" in person and person["given-names"]:
                    given_words = set(person["given-names"]["value"].lower().split())
                    score += len(query_words.intersection(given_words)) * 2

                # Check family name
                if "family-name" in person and person["family-name"]:
                    family_words = set(person["family-name"]["value"].lower().split())
                    score += len(query_words.intersection(family_words)) * 3

                # Check credit name
                if "credit-name" in person and person["credit-name"]:
                    credit_words = set(person["credit-name"]["value"].lower().split())
                    score += len(query_words.intersection(credit_words))

            if score > best_score:
                best_score = score
                best_result = result

        return best_result if best_score > 0 else results[0]  # Fallback to first

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse ORCID response into AuthorityData.

        Args:
            response: Raw ORCID API response

        Returns:
            Parsed AuthorityData
        """
        # Validate response
        if response is None or not isinstance(response, dict):
            return AuthorityData(source=self.service, source_id="", canonical_name="")

        # Extract ORCID ID
        orcid_id = ""
        if "orcid-identifier" in response:
            orcid_id = response["orcid-identifier"]["path"]

        # Extract person data
        person = response.get("person", {})

        # Get canonical name
        canonical_name = ""
        name_variants = []

        if "name" in person:
            name_data = person["name"]

            # Primary name
            family = name_data.get("family-name", {}).get("value", "")
            given = name_data.get("given-names", {}).get("value", "")

            if family and given:
                canonical_name = f"{family}, {given}"
            elif family:
                canonical_name = family

            # Credit name as variant
            if "credit-name" in name_data and name_data["credit-name"]:
                credit_name = name_data["credit-name"]["value"]
                if credit_name != canonical_name:
                    name_variants.append(credit_name)

        # Initialize data
        data = AuthorityData(
            source=self.service,
            source_id=orcid_id,
            canonical_name=canonical_name or f"ORCID_{orcid_id}",
        )

        data.name_variants = name_variants
        data.identifiers["ORCID"] = orcid_id

        # Extract affiliations from employment and education
        affiliations = []

        # Employment
        if "activities-summary" in response:
            activities = response["activities-summary"]

            # Current/past employment
            if "employments" in activities:
                for emp_group in activities["employments"]["affiliation-group"]:
                    for emp in emp_group["summaries"]:
                        emp_detail = emp["employment-summary"]
                        org = emp_detail.get("organization", {})

                        aff_data = {
                            "name": org.get("name", ""),
                            "type": "employment",
                            "country": org.get("address", {}).get("country", ""),
                        }

                        # Extract years
                        if "start-date" in emp_detail and emp_detail["start-date"]:
                            aff_data["from"] = emp_detail["start-date"].get("year", {}).get("value")
                        if "end-date" in emp_detail and emp_detail["end-date"]:
                            aff_data["to"] = emp_detail["end-date"].get("year", {}).get("value")

                        affiliations.append(aff_data)

            # Education
            if "educations" in activities:
                for edu_group in activities["educations"]["affiliation-group"]:
                    for edu in edu_group["summaries"]:
                        edu_detail = edu["education-summary"]
                        org = edu_detail.get("organization", {})

                        aff_data = {
                            "name": org.get("name", ""),
                            "type": "education",
                            "country": org.get("address", {}).get("country", ""),
                        }

                        # Extract years
                        if "start-date" in edu_detail and edu_detail["start-date"]:
                            aff_data["from"] = edu_detail["start-date"].get("year", {}).get("value")
                        if "end-date" in edu_detail and edu_detail["end-date"]:
                            aff_data["to"] = edu_detail["end-date"].get("year", {}).get("value")

                        affiliations.append(aff_data)

        data.affiliations = affiliations[:5]  # Limit to 5 most recent

        # Extract countries from affiliations
        countries = set()
        for aff in affiliations:
            if aff.get("country"):
                countries.add(aff["country"])
        data.countries = list(countries)

        # Metadata
        data.metadata = {
            "orcid_id": orcid_id,
            "profile_created": response.get("history", {}).get("creation-method"),
            "last_modified": response.get("history", {}).get("last-modified-date"),
            "affiliations_count": len(affiliations),
        }

        # Calculate confidence
        data.confidence_score = self.calculate_confidence(data)

        return data

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for ORCID data.

        ORCID data is generally high quality since it's curated.
        """
        score = 0.5  # High base score for ORCID

        # Has canonical name
        if data.canonical_name:
            score += 0.1

        # Has name variants
        if len(data.name_variants) > 0:
            score += 0.1

        # Has affiliations
        if len(data.affiliations) > 0:
            score += 0.1
        if len(data.affiliations) > 2:
            score += 0.1

        # Has countries
        if len(data.countries) > 0:
            score += 0.1

        return min(score, 1.0)
