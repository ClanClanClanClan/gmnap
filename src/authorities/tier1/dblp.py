"""
DBLP fetcher for GMNAP.

DBLP (Database Systems and Logic Programming) is a major computer science bibliography.
API Documentation: https://dblp.org/faq/13501473.html
"""

import asyncio
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from src.authorities.base import (
    AuthorityData,
    AuthorityFetcher,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)


class DBLPFetcher(AuthorityFetcher):
    """
    Fetcher for DBLP API.

    Features:
    - Computer science focus (good for computational math)
    - CC-BY license
    - Free API access
    - Rich publication metadata
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = "DBLP"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 86400  # Local processing, generous limit
        self.base_url = "https://dblp.org"
        self.requires_auth = False

        # Rate limiting: Be polite
        self._min_request_interval = 0.1  # 100ms between requests

    async def fetch(self, query: str) -> FetchResult:
        """
        Fetch researcher data from DBLP.

        Args:
            query: Researcher name or DBLP person ID

        Returns:
            FetchResult with parsed data
        """
        try:
            # Rate limiting
            await self.ensure_rate_limit()

            # Check if query is a DBLP person ID
            if query.startswith("pid/") or "/" in query:
                # Direct person lookup
                return await self._fetch_by_person_id(query)
            else:
                # Name search
                return await self._search_by_name(query)

        except asyncio.TimeoutError:
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message="Request timeout")

        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(e))

    async def _fetch_by_person_id(self, person_id: str) -> FetchResult:
        """Fetch data using DBLP person ID."""
        # Clean person ID
        if person_id.startswith("pid/"):
            person_id = person_id[4:]

        url = f"{self.base_url}/pid/{person_id}.xml"

        session = await self.get_session()

        async with session.get(url) as response:
            if response.status == 200:
                xml_data = await response.text()
                parsed = self.parse_xml_response(xml_data, person_id)

                return FetchResult(
                    status=FetchStatus.SUCCESS,
                    data=parsed,
                    raw_response={"xml_length": len(xml_data), "person_id": person_id},
                )

            elif response.status == 404:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND, error_message="DBLP person ID not found"
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
        """Search DBLP by researcher name."""
        # Use DBLP search API
        params = {"q": name, "format": "xml", "h": 10}  # Limit results

        url = f"{self.base_url}/search/author/api"

        session = await self.get_session()

        # Build URL with params
        full_url = url + "?" + urllib.parse.urlencode(params)

        async with session.get(full_url) as response:
            if response.status == 200:
                xml_data = await response.text()

                # Parse search results
                search_results = self.parse_search_xml(xml_data)

                if not search_results:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND, error_message="No DBLP authors found"
                    )

                # Get best match and fetch full profile
                best_match = self._find_best_match(search_results, name)

                if best_match and "pid" in best_match:
                    return await self._fetch_by_person_id(best_match["pid"])
                else:
                    # Use search result data directly
                    parsed = self.parse_search_result(best_match or search_results[0])

                    return FetchResult(
                        status=FetchStatus.SUCCESS,
                        data=parsed,
                        raw_response={"search_results": len(search_results)},
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

    def parse_search_xml(self, xml_data: str) -> List[Dict[str, Any]]:
        """Parse DBLP search XML response."""
        try:
            root = ET.fromstring(xml_data)
            results = []

            # Find all author hits
            for hit in root.findall(".//hit"):
                author_data = {}

                # Extract basic info
                info = hit.find("info")
                if info is not None:
                    author_data["name"] = (
                        info.find("author").text if info.find("author") is not None else ""
                    )

                    # Extract DBLP URL/PID
                    url_elem = info.find("url")
                    if url_elem is not None:
                        dblp_url = url_elem.text
                        if "pid/" in dblp_url:
                            author_data["pid"] = dblp_url.split("pid/")[-1]

                # Extract publication count
                author_data["publications"] = len(hit.findall(".//hit"))

                results.append(author_data)

            return results

        except ET.ParseError as e:
            self.logger.error(f"Failed to parse DBLP search XML: {e}")
            return []

    def parse_xml_response(self, xml_data: str, person_id: str) -> AuthorityData:
        """Parse DBLP XML person response."""
        try:
            root = ET.fromstring(xml_data)

            # Extract person info
            person = root.find(".//person")
            if person is None:
                # Fallback to basic data
                return AuthorityData(
                    source=self.service, source_id=person_id, canonical_name=f"DBLP_{person_id}"
                )

            # Get primary name
            primary_name = person.get("name", "")

            data = AuthorityData(
                source=self.service, source_id=person_id, canonical_name=primary_name
            )

            # Collect name variants
            name_variants = []
            for name_elem in person.findall(".//name"):
                name_text = name_elem.text
                if name_text and name_text != primary_name:
                    name_variants.append(name_text)

            data.name_variants = name_variants

            # Count publications by type
            publications = {"total": 0, "by_type": {}}

            for pub in root.findall(".//r"):
                publications["total"] += 1

                # Count by publication type
                for child in pub:
                    pub_type = child.tag
                    publications["by_type"][pub_type] = publications["by_type"].get(pub_type, 0) + 1

            # Extract years for timeline
            years = []
            for year_elem in root.findall(".//year"):
                try:
                    year = int(year_elem.text)
                    years.append(year)
                except (ValueError, TypeError):
                    pass

            # Metadata
            data.metadata = {
                "dblp_person_id": person_id,
                "publications_total": publications["total"],
                "publications_by_type": publications["by_type"],
                "year_range": f"{min(years)}-{max(years)}" if years else "",
                "active_years": len(set(years)),
            }

            # Calculate confidence
            data.confidence_score = self.calculate_confidence(data)

            return data

        except ET.ParseError as e:
            self.logger.error(f"Failed to parse DBLP person XML: {e}")
            return AuthorityData(
                source=self.service, source_id=person_id, canonical_name=f"DBLP_{person_id}"
            )

    def parse_search_result(self, result: Dict[str, Any]) -> AuthorityData:
        """Parse DBLP search result into AuthorityData."""
        name = result.get("name", "")
        pid = result.get("pid", f"search_{hash(name)}")

        data = AuthorityData(source=self.service, source_id=pid, canonical_name=name)

        # Basic metadata from search
        data.metadata = {
            "publications_count": result.get("publications", 0),
            "source_type": "search_result",
        }

        # Calculate confidence
        data.confidence_score = self.calculate_confidence(data)

        return data

    def _find_best_match(
        self, results: List[Dict[str, Any]], query: str
    ) -> Optional[Dict[str, Any]]:
        """Find best matching DBLP author."""
        if not results:
            return None

        query_words = set(query.lower().split())
        best_score = 0
        best_result = None

        for result in results:
            name = result.get("name", "")
            name_words = set(name.lower().split())

            # Calculate similarity score
            intersection = len(query_words.intersection(name_words))
            union = len(query_words.union(name_words))
            similarity = intersection / union if union > 0 else 0

            # Boost score for publication count
            pub_count = result.get("publications", 0)
            score = similarity + (pub_count * 0.01)  # Small boost for more publications

            if score > best_score:
                best_score = score
                best_result = result

        return best_result if best_score > 0.3 else results[0]  # 30% similarity threshold

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for DBLP data.

        Higher confidence for:
        - Multiple publications
        - Name variants
        - Recent activity
        - Diverse publication types
        """
        score = 0.1  # Base score

        # Publications count
        pub_count = data.metadata.get("publications_total", 0)
        if pub_count > 0:
            score += 0.1
        if pub_count > 10:
            score += 0.1
        if pub_count > 50:
            score += 0.1

        # Name variants
        if len(data.name_variants) > 0:
            score += 0.1
        if len(data.name_variants) > 2:
            score += 0.1

        # Publication diversity
        pub_types = data.metadata.get("publications_by_type", {})
        if len(pub_types) > 1:
            score += 0.1
        if len(pub_types) > 3:
            score += 0.1

        # Activity span
        if data.metadata.get("active_years", 0) > 5:
            score += 0.1

        # DBLP is CS-focused, moderate boost for computational math
        score += 0.05

        return min(score, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """Parse API response - not used for DBLP XML."""
        # Validate response
        if response is None or not isinstance(response, dict):
            return AuthorityData(source=self.service, source_id="", canonical_name="")

        # Required by base class but not used since we parse XML directly
        return AuthorityData(source=self.service, source_id="", canonical_name="")
