"""
ORCID ETD (Electronic Theses and Dissertations) authority source for GMNAP V7.

Tier-0 authority source: CC0 license, 100k daily quota
Focuses on dissertation/thesis metadata from ORCID.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

from ..base import AuthorityFetcher, AuthorityData

logger = logging.getLogger(__name__)


@dataclass
class ORCIDETDRecord(AuthorityData):
    """ORCID ETD-specific record."""

    thesis_title: Optional[str] = None
    thesis_year: Optional[int] = None
    university: Optional[str] = None
    advisor_name: Optional[str] = None
    thesis_type: Optional[str] = None  # PhD, Masters, etc.
    thesis_doi: Optional[str] = None
    thesis_url: Optional[str] = None


class ORCIDETDFetcher(AuthorityFetcher):
    """
    ORCID ETD fetcher for V7 authority enrichment.

    Focuses on extracting Electronic Theses and Dissertations data
    from ORCID profiles, particularly education records and works
    marked as dissertations.
    """

    BASE_URL = "https://pub.orcid.org/v3.0"

    def __init__(self, config_or_client_id=None, client_secret: Optional[str] = None):
        """
        Initialize ORCID ETD fetcher.

        Args:
            config_or_client_id: Either a config dict or client_id string
            client_secret: ORCID API client secret (optional for public API)
        """
        # Handle both dict config and individual parameters for backward compatibility
        if isinstance(config_or_client_id, dict):
            config = config_or_client_id
            client_id = config.get("client_id")
            client_secret = config.get("client_secret")
        elif isinstance(config_or_client_id, str):
            client_id = config_or_client_id
            config = {"client_id": client_id, "client_secret": client_secret}
        else:
            client_id = None
            client_secret = None
            config = {}

        super().__init__(config)

        # Set ORCID-specific attributes
        self.daily_quota = 100000
        self.requests_per_second = 8
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = self.BASE_URL
        self._last_request_time = 0
        self._rate_limit_delay = 1.0 / self.requests_per_second

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    async def search(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for ORCID IDs with dissertation/thesis data.

        Args:
            query: Search query (name or keywords)
            limit: Maximum results

        Returns:
            List of ORCID identifiers
        """
        await self._rate_limit()

        # Build query focusing on dissertation keywords
        search_query = f"({query}) AND (dissertation OR thesis OR PhD OR doctoral)"

        params = {"q": search_query, "rows": limit}

        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/search"
            headers = {"Accept": "application/json"}

            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"ORCID ETD search returned {response.status}")
                    return []

                data = await response.json()

                # Extract ORCID IDs
                orcids = []
                for result in data.get("result", []):
                    orcid_id = result.get("orcid-identifier", {}).get("path")
                    if orcid_id:
                        orcids.append(orcid_id)

                return orcids

    async def fetch(self, identifier: str) -> Optional[ORCIDETDRecord]:
        """
        Fetch ETD data from ORCID profile.

        Args:
            identifier: ORCID ID

        Returns:
            ORCIDETDRecord with thesis/dissertation data
        """
        await self._rate_limit()

        # Handle both string and dict inputs
        if isinstance(identifier, dict):
            # If we get a dict, try to extract the actual identifier
            identifier = identifier.get("identifier", identifier.get("query", str(identifier)))

        # Clean ORCID ID
        if isinstance(identifier, str) and "/" in identifier:
            identifier = identifier.split("/")[-1]

        # Validate format
        if not isinstance(identifier, str) or not re.match(
            r"^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$", identifier
        ):
            logger.warning(f"Invalid ORCID format: {identifier}")
            return None

        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "application/json"}

            # Fetch education data (contains thesis info)
            education_data = await self._fetch_education(session, identifier, headers)

            # Fetch works to find dissertations
            thesis_works = await self._fetch_thesis_works(session, identifier, headers)

            # Fetch person data for names
            person_data = await self._fetch_person(session, identifier, headers)

            if not (education_data or thesis_works):
                return None

            # Build ETD record
            record = ORCIDETDRecord(
                source="ORCID_ETD",
                identifier=identifier,
                confidence=0.9,  # High confidence for ORCID data
            )

            # Extract person names
            if person_data:
                name_data = person_data.get("name", {})
                given_name = name_data.get("given-names", {}).get("value")
                family_name = name_data.get("family-name", {}).get("value")

                if given_name and family_name:
                    record.canonical_latin = f"{given_name} {family_name}"

            # Extract PhD/thesis from education
            if education_data:
                for edu in education_data.get("education-summary", []):
                    org_name = edu.get("organization", {}).get("name")
                    role = edu.get("role-title")

                    # Check if it's a PhD or thesis-granting degree
                    if role and any(
                        term in role.lower() for term in ["phd", "ph.d", "doctorate", "doctoral"]
                    ):
                        record.university = org_name

                        # Extract year from education
                        end_date = edu.get("end-date")
                        if end_date:
                            year = end_date.get("year", {}).get("value")
                            if year:
                                record.thesis_year = int(year)
                                record.birth_year = record.thesis_year - 28  # Estimate

                        # Department info might contain advisor
                        dept = edu.get("department-name")
                        if dept and "advisor" in dept.lower():
                            record.advisor_name = self._extract_advisor(dept)

                        record.thesis_type = "PhD"

            # Extract dissertation from works
            if thesis_works:
                for work in thesis_works:
                    title = work.get("title", {}).get("title", {}).get("value")
                    work_type = work.get("type")

                    if work_type == "DISSERTATION":
                        record.thesis_title = title

                        # Get DOI if available
                        for ext_id in work.get("external-ids", {}).get("external-id", []):
                            if ext_id.get("external-id-type") == "doi":
                                record.thesis_doi = ext_id.get("external-id-value")
                                record.thesis_url = f"https://doi.org/{record.thesis_doi}"

                        # Get publication year
                        pub_date = work.get("publication-date")
                        if pub_date:
                            year = pub_date.get("year", {}).get("value")
                            if year:
                                record.thesis_year = int(year)

            return record

    async def _fetch_education(
        self, session: aiohttp.ClientSession, orcid: str, headers: Dict
    ) -> Optional[Dict]:
        """Fetch education data from ORCID."""
        url = f"{self.BASE_URL}/{orcid}/educations"
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching education for {orcid}: {e}")
        return None

    async def _fetch_thesis_works(
        self, session: aiohttp.ClientSession, orcid: str, headers: Dict
    ) -> List[Dict]:
        """Fetch dissertation/thesis works from ORCID."""
        url = f"{self.BASE_URL}/{orcid}/works"
        thesis_works = []

        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # Get detailed info for works that might be dissertations
                    for work_summary in data.get("group", []):
                        work_id = work_summary.get("work-summary", [{}])[0].get("put-code")
                        if work_id:
                            work_detail = await self._fetch_work_detail(
                                session, orcid, work_id, headers
                            )
                            if work_detail:
                                work_type = work_detail.get("type")
                                title = (
                                    work_detail.get("title", {}).get("title", {}).get("value", "")
                                )

                                # Check if it's a dissertation
                                if work_type == "DISSERTATION" or any(
                                    term in title.lower()
                                    for term in ["dissertation", "thesis", "phd"]
                                ):
                                    thesis_works.append(work_detail)
        except Exception as e:
            logger.error(f"Error fetching works for {orcid}: {e}")

        return thesis_works

    async def _fetch_work_detail(
        self, session: aiohttp.ClientSession, orcid: str, work_id: str, headers: Dict
    ) -> Optional[Dict]:
        """Fetch detailed work information."""
        url = f"{self.BASE_URL}/{orcid}/work/{work_id}"
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching work {work_id} for {orcid}: {e}")
        return None

    async def _fetch_person(
        self, session: aiohttp.ClientSession, orcid: str, headers: Dict
    ) -> Optional[Dict]:
        """Fetch person data from ORCID."""
        url = f"{self.BASE_URL}/{orcid}/person"
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching person {orcid}: {e}")
        return None

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse API response into AuthorityData.

        Args:
            response: Raw API response

        Returns:
            Parsed AuthorityData
        """
        # For ORCID ETD, we already handle parsing in fetch()
        # This method is for compatibility with the base class
        return AuthorityData(
            source="ORCID_ETD",
            source_id=response.get("orcid", ""),
            canonical_name=response.get("name", ""),
            metadata=response,
        )

    def _extract_advisor(self, dept_text: str) -> Optional[str]:
        """Extract advisor name from department text."""
        # Common patterns: "Advisor: Name", "Supervised by Name"
        patterns = [
            r"advisor[:\s]+([^,;]+)",
            r"supervised by[:\s]+([^,;]+)",
            r"supervisor[:\s]+([^,;]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, dept_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich GMNAP entry with ORCID ETD data.

        Args:
            entry: GMNAP entry

        Returns:
            Enriched entry
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        if not name:
            return entry

        # Search for ORCID with thesis/dissertation
        orcids = await self.search(name, limit=5)

        for orcid in orcids:
            record = await self.fetch(orcid)
            if record and self._is_match(name, record):
                # Add ETD metadata
                if not entry.get("ExternalIDs"):
                    entry["ExternalIDs"] = []

                entry["ExternalIDs"].append(
                    {"type": "ORCID_ETD", "value": orcid, "confidence": record.confidence}
                )

                # Add thesis metadata
                if record.thesis_title:
                    if not entry.get("Publications"):
                        entry["Publications"] = []

                    entry["Publications"].append(
                        {
                            "title": record.thesis_title,
                            "type": "dissertation",
                            "year": record.thesis_year,
                            "university": record.university,
                            "doi": record.thesis_doi,
                            "url": record.thesis_url,
                        }
                    )

                # Add advisor if found
                if record.advisor_name:
                    if not entry.get("Advisors"):
                        entry["Advisors"] = []

                    entry["Advisors"].append(
                        {"name": record.advisor_name, "type": "doctoral", "source": "ORCID_ETD"}
                    )

                # Add university affiliation
                if record.university:
                    if not entry.get("Affiliations"):
                        entry["Affiliations"] = []

                    entry["Affiliations"].append(
                        {
                            "institution": record.university,
                            "type": "PhD",
                            "year": record.thesis_year,
                            "source": "ORCID_ETD",
                        }
                    )

                logger.info(f"Enriched {name} with ORCID ETD data")
                break

        return entry

    def _is_match(self, query_name: str, record: ORCIDETDRecord) -> bool:
        """Check if record matches query name."""
        if not record.canonical_latin:
            return False

        query_lower = query_name.lower().strip()
        record_lower = record.canonical_latin.lower().strip()

        # Exact match
        if query_lower == record_lower:
            return True

        # Check if all parts of query name are in record
        query_parts = set(query_lower.split())
        record_parts = set(record_lower.split())

        return query_parts.issubset(record_parts) or record_parts.issubset(query_parts)
