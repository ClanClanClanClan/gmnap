#!/usr/bin/env python3
"""
ORCID ETD Authority Source
Fetches thesis and dissertation data from ORCID records.
"""

import os
import logging
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ORCIDAuthorityData:
    """Data from ORCID authority source."""

    orcid_id: Optional[str] = None
    given_names: Optional[str] = None
    family_name: Optional[str] = None
    other_names: List[str] = None
    affiliations: List[Dict[str, Any]] = None
    education: List[Dict[str, Any]] = None
    works: List[Dict[str, Any]] = None
    keywords: List[str] = None

    def __post_init__(self):
        if self.other_names is None:
            self.other_names = []
        if self.affiliations is None:
            self.affiliations = []
        if self.education is None:
            self.education = []
        if self.works is None:
            self.works = []
        if self.keywords is None:
            self.keywords = []


class ORCIDETDFetcher:
    """
    ORCID ETD (Electronic Theses and Dissertations) fetcher.
    Implements V7 spec requirement for ORCID_ETD authority source.
    """

    def __init__(self, client_id: str = None, client_secret: str = None):
        """
        Initialize ORCID fetcher.

        Args:
            client_id: ORCID API client ID (or from env)
            client_secret: ORCID API client secret (or from env)
        """
        self.client_id = client_id or os.getenv("ORCID_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("ORCID_CLIENT_SECRET", "")
        self.base_url = "https://pub.orcid.org/v3.0"
        self.session = None
        self.cache = {}
        self.cache_ttl = timedelta(hours=24)

        if not self.client_id:
            logger.warning("ORCID client ID not configured")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def search_by_name(self, name: str, limit: int = 10) -> List[str]:
        """
        Search for ORCID IDs by name.

        Args:
            name: Person's name to search
            limit: Maximum results to return

        Returns:
            List of ORCID IDs
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        # Format search query
        query = f"family-name:{name} OR given-names:{name}"

        params = {"q": query, "rows": limit}

        headers = {"Accept": "application/json"}

        try:
            url = f"{self.base_url}/search"
            async with self.session.get(
                url, params=params, headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("result", [])

                    # Extract ORCID IDs
                    orcid_ids = []
                    for result in results:
                        orcid_path = result.get("orcid-identifier", {}).get("path")
                        if orcid_path:
                            orcid_ids.append(orcid_path)

                    return orcid_ids
                else:
                    logger.warning(f"ORCID search failed: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"ORCID search error: {e}")
            return []

    async def fetch_record(self, orcid_id: str) -> Optional[ORCIDAuthorityData]:
        """
        Fetch full ORCID record.

        Args:
            orcid_id: ORCID identifier

        Returns:
            ORCID authority data
        """
        # Check cache
        cache_key = f"orcid:{orcid_id}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data

        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = {"Accept": "application/json"}

        try:
            # Fetch person record
            url = f"{self.base_url}/{orcid_id}/person"
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch ORCID {orcid_id}: {response.status}"
                    )
                    return None

                person_data = await response.json()

            # Extract person information
            name_data = person_data.get("name", {})
            given_names = name_data.get("given-names", {}).get("value", "")
            family_name = name_data.get("family-name", {}).get("value", "")

            # Extract other names
            other_names = []
            for alt_name in person_data.get("other-names", {}).get("other-name", []):
                content = alt_name.get("content")
                if content:
                    other_names.append(content)

            # Extract keywords
            keywords = []
            for keyword in person_data.get("keywords", {}).get("keyword", []):
                content = keyword.get("content")
                if content:
                    keywords.append(content)

            # Fetch education (thesis info)
            education = await self._fetch_education(orcid_id)

            # Fetch affiliations
            affiliations = await self._fetch_affiliations(orcid_id)

            # Fetch works (publications)
            works = await self._fetch_works(orcid_id, limit=5)

            # Create authority data
            authority_data = ORCIDAuthorityData(
                orcid_id=orcid_id,
                given_names=given_names,
                family_name=family_name,
                other_names=other_names,
                affiliations=affiliations,
                education=education,
                works=works,
                keywords=keywords,
            )

            # Cache result
            self.cache[cache_key] = (datetime.now(), authority_data)

            return authority_data

        except Exception as e:
            logger.error(f"Error fetching ORCID record {orcid_id}: {e}")
            return None

    async def _fetch_education(self, orcid_id: str) -> List[Dict[str, Any]]:
        """Fetch education records (includes thesis information)."""
        if not self.session:
            return []

        headers = {"Accept": "application/json"}

        try:
            url = f"{self.base_url}/{orcid_id}/educations"
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                education_summaries = data.get("education-summary", [])

                education_list = []
                for edu in education_summaries:
                    education_list.append(
                        {
                            "organization": edu.get("organization", {}).get("name"),
                            "role": edu.get("role-title"),
                            "department": edu.get("department-name"),
                            "start_date": self._format_date(edu.get("start-date")),
                            "end_date": self._format_date(edu.get("end-date")),
                        }
                    )

                return education_list

        except Exception as e:
            logger.error(f"Error fetching education for {orcid_id}: {e}")
            return []

    async def _fetch_affiliations(self, orcid_id: str) -> List[Dict[str, Any]]:
        """Fetch employment/affiliation records."""
        if not self.session:
            return []

        headers = {"Accept": "application/json"}

        try:
            url = f"{self.base_url}/{orcid_id}/employments"
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                employment_summaries = data.get("employment-summary", [])

                affiliations = []
                for emp in employment_summaries:
                    affiliations.append(
                        {
                            "organization": emp.get("organization", {}).get("name"),
                            "role": emp.get("role-title"),
                            "department": emp.get("department-name"),
                            "start_date": self._format_date(emp.get("start-date")),
                            "end_date": self._format_date(emp.get("end-date")),
                        }
                    )

                return affiliations

        except Exception as e:
            logger.error(f"Error fetching affiliations for {orcid_id}: {e}")
            return []

    async def _fetch_works(self, orcid_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch work records (publications)."""
        if not self.session:
            return []

        headers = {"Accept": "application/json"}

        try:
            url = f"{self.base_url}/{orcid_id}/works"
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                work_summaries = data.get("group", [])[:limit]

                works = []
                for group in work_summaries:
                    work_summary = group.get("work-summary", [{}])[0]
                    works.append(
                        {
                            "title": work_summary.get("title", {})
                            .get("title", {})
                            .get("value"),
                            "type": work_summary.get("type"),
                            "year": self._extract_year(
                                work_summary.get("publication-date")
                            ),
                            "journal": (
                                work_summary.get("journal-title", {}).get("value")
                                if work_summary.get("journal-title")
                                else None
                            ),
                        }
                    )

                return works

        except Exception as e:
            logger.error(f"Error fetching works for {orcid_id}: {e}")
            return []

    def _format_date(self, date_obj: Optional[Dict]) -> Optional[str]:
        """Format ORCID date object to string."""
        if not date_obj:
            return None

        year = date_obj.get("year", {}).get("value")
        month = date_obj.get("month", {}).get("value")
        day = date_obj.get("day", {}).get("value")

        if year:
            if month and day:
                return f"{year}-{month:02d}-{day:02d}"
            elif month:
                return f"{year}-{month:02d}"
            else:
                return str(year)

        return None

    def _extract_year(self, date_obj: Optional[Dict]) -> Optional[int]:
        """Extract year from ORCID date object."""
        if not date_obj:
            return None

        year = date_obj.get("year", {}).get("value")
        return int(year) if year else None

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich an entry with ORCID data.

        Args:
            entry: Entry dictionary with name information

        Returns:
            Enriched entry with ORCID data
        """
        name = entry.get("CanonicalLatin", "")
        if not name:
            return entry

        # Search for ORCID IDs
        orcid_ids = await self.search_by_name(name, limit=3)

        if not orcid_ids:
            return entry

        # Fetch first matching record
        for orcid_id in orcid_ids:
            record = await self.fetch_record(orcid_id)
            if record:
                # Add ORCID data to entry
                entry["ORCID"] = orcid_id

                # Add education/thesis info
                if record.education:
                    entry["Education"] = record.education

                    # Look for PhD/thesis
                    for edu in record.education:
                        if edu.get("role") and "phd" in edu.get("role", "").lower():
                            entry["ThesisInstitution"] = edu.get("organization")
                            entry["ThesisYear"] = edu.get("end_date")

                # Add affiliations
                if record.affiliations:
                    entry["Affiliations"] = record.affiliations

                # Add keywords as research areas
                if record.keywords:
                    entry["ResearchAreas"] = record.keywords

                # Update authority sources
                if "AuthoritySources" not in entry:
                    entry["AuthoritySources"] = []
                entry["AuthoritySources"].append("ORCID_ETD")

                break

        return entry
