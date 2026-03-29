"""
Crossref Thesis authority source for GMNAP V7.

Tier-0 authority source: CC0 license, 100k daily quota
Focuses on thesis/dissertation metadata from Crossref.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

from ..base import AuthorityFetcher, AuthorityData

logger = logging.getLogger(__name__)


@dataclass
class CrossrefThesisRecord(AuthorityData):
    """Crossref thesis-specific record."""

    thesis_title: Optional[str] = None
    thesis_doi: Optional[str] = None
    thesis_year: Optional[int] = None
    university: Optional[str] = None
    department: Optional[str] = None
    degree: Optional[str] = None
    abstract: Optional[str] = None
    subject_areas: List[str] = None
    advisor_names: List[str] = None
    committee_members: List[str] = None

    def __post_init__(self):
        if self.subject_areas is None:
            self.subject_areas = []
        if self.advisor_names is None:
            self.advisor_names = []
        if self.committee_members is None:
            self.committee_members = []


class CrossrefThesisFetcher(AuthorityFetcher):
    """
    Crossref Thesis fetcher for V7 authority enrichment.

    Specializes in extracting thesis and dissertation metadata
    from Crossref, filtering for dissertation-type works.
    """

    BASE_URL = "https://api.crossref.org"

    def __init__(self, config_or_email=None):
        """
        Initialize Crossref Thesis fetcher.

        Args:
            config_or_email: Either a config dict or email string for API usage
        """
        # Handle both dict config and string email for backward compatibility
        if isinstance(config_or_email, dict):
            config = config_or_email
            email = config.get("email")
        elif isinstance(config_or_email, str):
            email = config_or_email
            config = {"email": email}
        else:
            email = None
            config = {}

        super().__init__(config)

        # Set Crossref-specific attributes
        self.daily_quota = 100000
        self.requests_per_second = 50 if email else 10
        self.base_url = self.BASE_URL
        self.email = email
        self._last_request_time = 0
        self._rate_limit_delay = 1.0 / self.requests_per_second

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional email."""
        headers = {
            "User-Agent": (
                f"GMNAP/7.0 (mailto:{self.email})" if self.email else "GMNAP/7.0"
            )
        }
        return headers

    async def search(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for thesis/dissertation DOIs in Crossref.

        Args:
            query: Search query (author name or keywords)
            limit: Maximum results

        Returns:
            List of DOIs for theses/dissertations
        """
        await self._rate_limit()

        params = {
            "query": query,
            "filter": "type:dissertation",  # Filter for dissertations only
            "rows": limit,
            "select": "DOI,title,author,published-print,publisher,subject",
        }

        url = f"{self.BASE_URL}/works"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, headers=self._get_headers()
            ) as response:
                if response.status != 200:
                    logger.warning(f"Crossref Thesis search returned {response.status}")
                    return []

                data = await response.json()

                # Extract DOIs
                dois = []
                for item in data.get("message", {}).get("items", []):
                    doi = item.get("DOI")
                    if doi:
                        dois.append(doi)

                return dois

    async def fetch(self, identifier: str) -> Optional[CrossrefThesisRecord]:
        """
        Fetch thesis metadata from Crossref.

        Args:
            identifier: DOI of the thesis

        Returns:
            CrossrefThesisRecord with thesis metadata
        """
        await self._rate_limit()

        # Clean DOI - handle both string and dict inputs
        if isinstance(identifier, dict):
            # If we get a dict, try to extract the actual identifier
            identifier = identifier.get(
                "identifier", identifier.get("query", str(identifier))
            )

        if isinstance(identifier, str) and identifier.startswith("http"):
            identifier = identifier.split("doi.org/")[-1]

        url = f"{self.BASE_URL}/works/{identifier}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._get_headers()) as response:
                if response.status == 404:
                    logger.info(f"DOI not found: {identifier}")
                    return None
                elif response.status != 200:
                    logger.warning(
                        f"Crossref returned {response.status} for {identifier}"
                    )
                    return None

                data = await response.json()
                message = data.get("message", {})

                # Check if it's actually a dissertation
                if message.get("type") != "dissertation":
                    logger.info(f"DOI {identifier} is not a dissertation")
                    return None

                # Build thesis record
                record = CrossrefThesisRecord(
                    source="Crossref_Thesis",
                    identifier=identifier,
                    confidence=0.95,  # Very high confidence for Crossref DOI data
                )

                # Extract title
                titles = message.get("title", [])
                if titles:
                    record.thesis_title = titles[0]

                # Extract DOI
                record.thesis_doi = message.get("DOI")

                # Extract year
                date_parts = message.get("published-print", {}).get("date-parts", [[]])
                if date_parts and date_parts[0]:
                    record.thesis_year = date_parts[0][0]

                # Extract publisher (usually the university)
                record.university = message.get("publisher")

                # Extract degree type from subtitle or title
                subtitles = message.get("subtitle", [])
                for subtitle in subtitles:
                    if "Ph.D" in subtitle or "PhD" in subtitle:
                        record.degree = "PhD"
                    elif "Master" in subtitle:
                        record.degree = "Masters"

                # Extract abstract
                abstract = message.get("abstract")
                if abstract:
                    # Remove XML/HTML tags
                    import re

                    record.abstract = re.sub("<[^<]+?>", "", abstract)[
                        :500
                    ]  # First 500 chars

                # Extract subject areas
                subjects = message.get("subject", [])
                record.subject_areas = subjects[:5]  # Top 5 subjects

                # Extract authors (the thesis author)
                authors = message.get("author", [])
                if authors:
                    first_author = authors[0]
                    given = first_author.get("given", "")
                    family = first_author.get("family", "")
                    if given and family:
                        record.canonical_latin = f"{given} {family}"

                # Try to extract advisors from contributors
                for contributor in message.get("contributor", []):
                    role = contributor.get("role", "").lower()
                    given = contributor.get("given", "")
                    family = contributor.get("family", "")
                    name = f"{given} {family}".strip()

                    if name:
                        if "advisor" in role or "supervisor" in role:
                            record.advisor_names.append(name)
                        elif "committee" in role:
                            record.committee_members.append(name)

                # Extract institution from affiliation
                if authors and authors[0].get("affiliation"):
                    affiliations = authors[0]["affiliation"]
                    if affiliations:
                        record.university = affiliations[0].get("name")
                        record.department = affiliations[0].get("department", [None])[0]

                return record

    async def search_by_author(
        self, given_name: str = None, family_name: str = None, orcid: str = None
    ) -> List[str]:
        """
        Search for theses by author name or ORCID.

        Args:
            given_name: Author's given name
            family_name: Author's family name
            orcid: Author's ORCID

        Returns:
            List of thesis DOIs
        """
        await self._rate_limit()

        # Build query
        query_parts = []
        if given_name:
            query_parts.append(f"author.given:{given_name}")
        if family_name:
            query_parts.append(f"author.family:{family_name}")
        if orcid:
            query_parts.append(f"author.orcid:{orcid}")

        if not query_parts:
            return []

        query = " ".join(query_parts)

        params = {
            "query": query,
            "filter": "type:dissertation",
            "rows": 20,
            "select": "DOI,title,author,published-print",
        }

        url = f"{self.BASE_URL}/works"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, headers=self._get_headers()
            ) as response:
                if response.status != 200:
                    logger.warning(f"Crossref search returned {response.status}")
                    return []

                data = await response.json()

                dois = []
                for item in data.get("message", {}).get("items", []):
                    doi = item.get("DOI")
                    if doi:
                        dois.append(doi)

                return dois

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich GMNAP entry with Crossref thesis data.

        Args:
            entry: GMNAP entry

        Returns:
            Enriched entry
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        if not name:
            return entry

        # Search for theses by this author
        dois = await self.search(name, limit=5)

        for doi in dois:
            record = await self.fetch(doi)
            if record and self._is_match(name, record):
                # Add thesis DOI
                if not entry.get("ExternalIDs"):
                    entry["ExternalIDs"] = []

                entry["ExternalIDs"].append(
                    {"type": "DOI", "value": doi, "source": "Crossref_Thesis"}
                )

                # Add thesis as publication
                if not entry.get("Publications"):
                    entry["Publications"] = []

                pub_entry = {
                    "title": record.thesis_title,
                    "type": "dissertation",
                    "year": record.thesis_year,
                    "doi": record.thesis_doi,
                    "publisher": record.university,
                }

                if record.abstract:
                    pub_entry["abstract"] = record.abstract

                entry["Publications"].append(pub_entry)

                # Add university affiliation
                if record.university:
                    if not entry.get("Affiliations"):
                        entry["Affiliations"] = []

                    affiliation = {
                        "institution": record.university,
                        "type": record.degree or "PhD",
                        "year": record.thesis_year,
                        "source": "Crossref_Thesis",
                    }

                    if record.department:
                        affiliation["department"] = record.department

                    entry["Affiliations"].append(affiliation)

                # Add advisors
                if record.advisor_names:
                    if not entry.get("Advisors"):
                        entry["Advisors"] = []

                    for advisor in record.advisor_names:
                        entry["Advisors"].append(
                            {
                                "name": advisor,
                                "type": "doctoral",
                                "source": "Crossref_Thesis",
                            }
                        )

                # Add committee members
                if record.committee_members:
                    if not entry.get("CommitteeMembers"):
                        entry["CommitteeMembers"] = []

                    for member in record.committee_members:
                        entry["CommitteeMembers"].append(
                            {"name": member, "source": "Crossref_Thesis"}
                        )

                # Add subject areas
                if record.subject_areas:
                    if not entry.get("ResearchAreas"):
                        entry["ResearchAreas"] = []

                    entry["ResearchAreas"].extend(record.subject_areas)
                    entry["ResearchAreas"] = list(set(entry["ResearchAreas"]))  # Dedupe

                # Estimate birth year from PhD year (typically age 28)
                if (
                    record.thesis_year
                    and record.degree == "PhD"
                    and not entry.get("BirthYear")
                ):
                    entry["BirthYear"] = record.thesis_year - 28

                logger.info(f"Enriched {name} with Crossref thesis data")
                break

        return entry

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse API response into AuthorityData.

        Args:
            response: Raw API response

        Returns:
            Parsed AuthorityData
        """
        # For Crossref Thesis, we already handle parsing in fetch()
        # This method is for compatibility with the base class
        message = response.get("message", {})

        # Extract author name
        authors = message.get("author", [])
        canonical_name = ""
        if authors:
            first_author = authors[0]
            given = first_author.get("given", "")
            family = first_author.get("family", "")
            canonical_name = f"{given} {family}".strip()

        return AuthorityData(
            source="Crossref_Thesis",
            source_id=message.get("DOI", ""),
            canonical_name=canonical_name,
            metadata=response,
        )

    def _is_match(self, query_name: str, record: CrossrefThesisRecord) -> bool:
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

        # At least 2/3 of name parts should match
        intersection = query_parts.intersection(record_parts)
        return len(intersection) >= min(2, len(query_parts) * 2 / 3)
