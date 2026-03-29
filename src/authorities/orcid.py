#!/usr/bin/env python3
"""
ORCID Authority API Implementation for GMNAP V7
Tier-0/1 authority source: CC0 license, 100k daily quota
Provides authoritative researcher identifiers
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)


@dataclass
class ORCIDPerson:
    """ORCID person data structure"""

    orcid: str
    given_names: Optional[str] = None
    family_name: Optional[str] = None
    credit_name: Optional[str] = None
    other_names: List[str] = field(default_factory=list)
    biography: Optional[str] = None
    emails: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    external_identifiers: List[Dict] = field(default_factory=list)
    affiliations: List[Dict] = field(default_factory=list)
    works_count: int = 0
    last_modified: Optional[str] = None
    creation_date: Optional[str] = None

    @property
    def canonical_name(self) -> str:
        """Return name in 'Family, Given' format"""
        # Prefer credit name if available
        if self.credit_name:
            # Parse credit name
            if "," in self.credit_name:
                return self.credit_name
            parts = self.credit_name.rsplit(" ", 1)
            if len(parts) == 2:
                return f"{parts[1]}, {parts[0]}"
            return self.credit_name

        # Otherwise use given and family names
        if self.family_name and self.given_names:
            return f"{self.family_name}, {self.given_names}"
        elif self.family_name:
            return self.family_name
        elif self.given_names:
            return self.given_names
        return ""

    @property
    def current_affiliations(self) -> List[Dict]:
        """Get current affiliations (no end date)"""
        return [aff for aff in self.affiliations if not aff.get("end_date")]

    @property
    def researcher_ids(self) -> Dict[str, str]:
        """Extract researcher IDs as a dictionary"""
        ids = {}
        for ext_id in self.external_identifiers:
            id_type = ext_id.get("external-id-type", "").lower()
            id_value = ext_id.get("external-id-value", "")
            if id_type and id_value:
                ids[id_type] = id_value
        return ids


class ORCIDAPI:
    """
    ORCID REST API client for V7 authority enrichment

    ORCID provides:
    - Authoritative researcher identifiers
    - Verified employment/education history
    - External identifiers (Scopus, ResearcherID, etc.)
    - Publication lists with DOIs
    - Funding information
    """

    BASE_URL = "https://pub.orcid.org/v3.0"
    SEARCH_URL = "https://pub.orcid.org/v3.0/search"
    RATE_LIMIT = 0.04  # 24 requests/second for public API
    USER_AGENT = "GMNAP/7.0 (https://github.com/gmnap; mailto:gmnap@eth.ch)"

    def __init__(self, client_id: str = None, client_secret: str = None):
        """
        Initialize ORCID API client

        Args:
            client_id: ORCID API client ID (for member API)
            client_secret: ORCID API client secret (for member API)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0
        self.last_request_time = 0
        self.access_token = None

    async def __aenter__(self):
        """Async context manager entry"""
        headers = {"User-Agent": self.USER_AGENT, "Accept": "application/json"}

        # If we have credentials, get an access token
        if self.client_id and self.client_secret:
            self.access_token = await self._get_access_token()
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token for member API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://orcid.org/oauth/token"
                data = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                    "scope": "/read-public",
                }

                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        return token_data.get("access_token")
                    else:
                        logger.warning(f"Failed to get ORCID access token: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting ORCID access token: {e}")
            return None

    async def _rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.RATE_LIMIT:
            await asyncio.sleep(self.RATE_LIMIT - elapsed)
        self.last_request_time = time.time()

    async def search(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for ORCID IDs matching a query

        Args:
            query: Search query (name, affiliation, etc.)
            limit: Maximum results to return

        Returns:
            List of ORCID identifiers
        """
        await self._rate_limit()

        # Build search query
        params = {"q": query, "rows": limit}

        try:
            async with self.session.get(self.SEARCH_URL, params=params) as response:
                self.request_count += 1

                if response.status != 200:
                    logger.warning(f"ORCID search returned {response.status} for {query}")
                    return []

                data = await response.json()

                # Extract ORCID IDs from search results
                orcids = []
                for result in data.get("result", []):
                    orcid_id = result.get("orcid-identifier", {}).get("path")
                    if orcid_id:
                        orcids.append(orcid_id)

                return orcids

        except Exception as e:
            logger.error(f"Error searching ORCID for {query}: {e}")
            return []

    async def search_by_name(
        self,
        given_name: str = None,
        family_name: str = None,
        affiliation: str = None,
        limit: int = 10,
    ) -> List[str]:
        """
        Search for ORCID IDs by structured query

        Args:
            given_name: Given/first name
            family_name: Family/last name
            affiliation: Institution affiliation
            limit: Maximum results

        Returns:
            List of ORCID identifiers
        """
        # Build structured query
        query_parts = []
        if family_name:
            query_parts.append(f'family-name:"{family_name}"')
        if given_name:
            query_parts.append(f'given-names:"{given_name}"')
        if affiliation:
            query_parts.append(f'affiliation-org-name:"{affiliation}"')

        if not query_parts:
            return []

        query = " AND ".join(query_parts)
        return await self.search(query, limit)

    async def get_person(self, orcid: str) -> Optional[ORCIDPerson]:
        """
        Get complete person record from ORCID

        Args:
            orcid: ORCID identifier (with or without URL)

        Returns:
            ORCIDPerson object or None
        """
        await self._rate_limit()

        # Handle dict input
        if isinstance(orcid, dict):
            # If we get a dict, try to extract the actual identifier
            orcid = orcid.get("identifier", orcid.get("query", orcid.get("orcid", str(orcid))))

        # Ensure it's a string
        orcid = str(orcid)

        # Clean ORCID ID
        if "/" in orcid:
            orcid = orcid.split("/")[-1]

        # Validate ORCID format
        if not re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$", orcid):
            logger.warning(f"Invalid ORCID format: {orcid}")
            return None

        url = f"{self.BASE_URL}/{orcid}/person"

        try:
            async with self.session.get(url) as response:
                self.request_count += 1

                if response.status == 404:
                    return None
                elif response.status != 200:
                    logger.warning(f"ORCID API returned {response.status} for {orcid}")
                    return None

                data = await response.json()

                # Extract person data
                person = ORCIDPerson(orcid=orcid)

                # Names
                name_data = data.get("name", {})
                if name_data:
                    person.given_names = name_data.get("given-names", {}).get("value")
                    person.family_name = name_data.get("family-name", {}).get("value")
                    person.credit_name = name_data.get("credit-name", {}).get("value")

                # Other names
                other_names = data.get("other-names", {}).get("other-name", [])
                person.other_names = [n.get("content") for n in other_names if n.get("content")]

                # Biography
                bio = data.get("biography", {})
                if bio:
                    person.biography = bio.get("content")

                # Keywords
                keywords = data.get("keywords", {}).get("keyword", [])
                person.keywords = [k.get("content") for k in keywords if k.get("content")]

                # External identifiers
                ext_ids = data.get("external-identifiers", {}).get("external-identifier", [])
                for ext_id in ext_ids:
                    person.external_identifiers.append(
                        {
                            "external-id-type": ext_id.get("external-id-type"),
                            "external-id-value": ext_id.get("external-id-value"),
                            "external-id-url": ext_id.get("external-id-url", {}).get("value"),
                        }
                    )

                # Emails
                emails = data.get("emails", {}).get("email", [])
                person.emails = [e.get("email") for e in emails if e.get("email")]

                # Dates
                person.last_modified = data.get("last-modified-date", {}).get("value")
                person.creation_date = data.get("created-date", {}).get("value")

                # Get affiliations (employment + education)
                person.affiliations = await self._get_affiliations(orcid)

                # Get works count
                person.works_count = await self._get_works_count(orcid)

                return person

        except Exception as e:
            logger.error(f"Error fetching ORCID {orcid}: {e}")
            return None

    async def _get_affiliations(self, orcid: str) -> List[Dict]:
        """Get employment and education history"""
        await self._rate_limit()

        affiliations = []

        # Get employments
        url = f"{self.BASE_URL}/{orcid}/employments"
        try:
            async with self.session.get(url) as response:
                self.request_count += 1
                if response.status == 200:
                    data = await response.json()
                    for group in data.get("employment-summary", []):
                        org = group.get("organization", {})
                        affiliations.append(
                            {
                                "type": "employment",
                                "organization": org.get("name"),
                                "department": group.get("department-name"),
                                "role": group.get("role-title"),
                                "start_date": self._format_date(group.get("start-date")),
                                "end_date": self._format_date(group.get("end-date")),
                                "city": org.get("address", {}).get("city"),
                                "country": org.get("address", {}).get("country"),
                            }
                        )
        except Exception as e:
            logger.error(f"Error fetching employments for {orcid}: {e}")

        # Get education
        url = f"{self.BASE_URL}/{orcid}/educations"
        try:
            async with self.session.get(url) as response:
                self.request_count += 1
                if response.status == 200:
                    data = await response.json()
                    for group in data.get("education-summary", []):
                        org = group.get("organization", {})
                        affiliations.append(
                            {
                                "type": "education",
                                "organization": org.get("name"),
                                "department": group.get("department-name"),
                                "role": group.get("role-title"),
                                "start_date": self._format_date(group.get("start-date")),
                                "end_date": self._format_date(group.get("end-date")),
                                "city": org.get("address", {}).get("city"),
                                "country": org.get("address", {}).get("country"),
                            }
                        )
        except Exception as e:
            logger.error(f"Error fetching education for {orcid}: {e}")

        return affiliations

    async def _get_works_count(self, orcid: str) -> int:
        """Get count of works for an ORCID"""
        await self._rate_limit()

        url = f"{self.BASE_URL}/{orcid}/works"
        try:
            async with self.session.get(url) as response:
                self.request_count += 1
                if response.status == 200:
                    data = await response.json()
                    return len(data.get("group", []))
        except Exception as e:
            logger.error(f"Error fetching works count for {orcid}: {e}")

        return 0

    def _format_date(self, date_dict: Optional[Dict]) -> Optional[str]:
        """Format ORCID date to ISO format"""
        if not date_dict:
            return None

        year = date_dict.get("year", {}).get("value")
        month = date_dict.get("month", {}).get("value")
        day = date_dict.get("day", {}).get("value")

        if year:
            date_str = str(year)
            if month:
                date_str += f"-{month:02d}"
                if day:
                    date_str += f"-{day:02d}"
            return date_str
        return None

    def _calculate_confidence(self, query_name: str, person: ORCIDPerson) -> float:
        """
        Calculate confidence score for name match

        ORCID data is authoritative, so high confidence if found
        """
        query_lower = query_name.lower().strip()

        # Check canonical name
        if person.canonical_name.lower() == query_lower:
            return 100.0

        # Check credit name
        if person.credit_name and person.credit_name.lower() == query_lower:
            return 98.0

        # Check other names
        for other_name in person.other_names:
            if other_name.lower() == query_lower:
                return 95.0

        # Partial match on family name
        if person.family_name and person.family_name.lower() in query_lower:
            return 80.0

        # Partial match on given names
        if person.given_names and person.given_names.lower() in query_lower:
            return 70.0

        return 50.0  # Found but low confidence

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a GMNAP entry with ORCID data

        Args:
            entry: GMNAP entry dictionary

        Returns:
            Enriched entry with ORCID metadata
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        if not name:
            return entry

        # Check if we already have an ORCID
        existing_orcid = None
        for ext_id in entry.get("ExternalIDs", []):
            if ext_id.get("type") == "ORCID":
                existing_orcid = ext_id.get("value")
                break

        person = None

        # If we have ORCID, fetch full record
        if existing_orcid:
            person = await self.get_person(existing_orcid)

        # Otherwise search by name
        if not person:
            # Parse name for structured search
            family = None
            given = None
            if "," in name:
                parts = name.split(",", 1)
                family = parts[0].strip()
                given = parts[1].strip() if len(parts) > 1 else None
            else:
                parts = name.rsplit(" ", 1)
                if len(parts) == 2:
                    given = parts[0]
                    family = parts[1]

            # Search ORCID
            orcids = await self.search_by_name(given, family, limit=5)

            # Get full records and find best match
            best_person = None
            best_confidence = 0.0

            for orcid_id in orcids[:3]:  # Check top 3 matches
                candidate = await self.get_person(orcid_id)
                if candidate:
                    confidence = self._calculate_confidence(name, candidate)
                    if confidence > best_confidence:
                        best_person = candidate
                        best_confidence = confidence

            if best_confidence >= 70:  # Threshold for acceptance
                person = best_person

        if not person:
            return entry

        # Enrich entry with ORCID data
        if "ExternalIDs" not in entry:
            entry["ExternalIDs"] = []

        # Add/update ORCID
        if not existing_orcid:
            entry["ExternalIDs"].append(
                {
                    "type": "ORCID",
                    "value": person.orcid,
                    "source": "ORCID",
                    "confidence": 100.0,  # ORCID is authoritative
                }
            )

        # Add other researcher IDs
        for id_type, id_value in person.researcher_ids.items():
            entry["ExternalIDs"].append({"type": id_type, "value": id_value, "source": "ORCID"})

        # Add affiliations
        if person.affiliations:
            if "Affiliations" not in entry:
                entry["Affiliations"] = []

            for aff in person.current_affiliations[:3]:  # Top 3 current
                entry["Affiliations"].append(
                    {
                        "institution": aff.get("organization"),
                        "department": aff.get("department"),
                        "role": aff.get("role"),
                        "country": aff.get("country"),
                        "source": "ORCID",
                        "type": aff.get("type"),
                    }
                )

        # Add keywords as research topics
        if person.keywords:
            entry["ResearchTopics"] = entry.get("ResearchTopics", [])
            for keyword in person.keywords[:10]:  # Top 10
                if keyword not in entry["ResearchTopics"]:
                    entry["ResearchTopics"].append(keyword)

        # Add variant names
        if person.other_names:
            if "VariantNames" not in entry:
                entry["VariantNames"] = []
            for other_name in person.other_names:
                entry["VariantNames"].append(
                    {"name": other_name, "source": "ORCID", "type": "alternative"}
                )

        # Add metrics
        entry["Metrics"] = entry.get("Metrics", {})
        entry["Metrics"]["orcid"] = {
            "works_count": person.works_count,
            "affiliations_count": len(person.affiliations),
        }

        # Add authority source metadata
        entry["AuthoritySources"] = entry.get("AuthoritySources", [])
        entry["AuthoritySources"].append(
            {
                "source": "ORCID",
                "id": person.orcid,
                "last_updated": datetime.utcnow().isoformat(),
                "confidence": 100.0,  # ORCID is authoritative
            }
        )

        return entry

    async def batch_enrich(
        self, entries: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple entries concurrently

        Note: Lower concurrency for ORCID due to rate limits
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_with_limit(entry):
            async with semaphore:
                return await self.enrich_entry(entry)

        tasks = [enrich_with_limit(entry) for entry in entries]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            "request_count": self.request_count,
            "authenticated": bool(self.access_token),
            "daily_quota": 100_000,
            "remaining_quota": 100_000 - self.request_count,
            "features": [
                "Authoritative IDs",
                "Verified affiliations",
                "External identifiers",
                "Publication lists",
                "Keywords/topics",
                "Alternative names",
            ],
        }


# Example usage for testing
async def test_orcid_api():
    """Test the ORCID API implementation"""
    async with ORCIDAPI() as api:
        print("Testing ORCID API...")

        # Search by name
        orcids = await api.search_by_name("Terence", "Tao")
        print(f"Found {len(orcids)} ORCID(s) for Terence Tao")

        if orcids:
            # Get full record
            person = await api.get_person(orcids[0])
            if person:
                print(f"\nPerson details:")
                print(f"  ORCID: {person.orcid}")
                print(f"  Name: {person.canonical_name}")
                print(f"  Credit name: {person.credit_name}")
                print(f"  Works: {person.works_count}")
                print(f"  Keywords: {', '.join(person.keywords[:5])}")
                print(f"  Current affiliations: {len(person.current_affiliations)}")

                if person.current_affiliations:
                    aff = person.current_affiliations[0]
                    print(f"    - {aff.get('organization')} ({aff.get('role')})")

                if person.researcher_ids:
                    print(f"  Other IDs: {list(person.researcher_ids.keys())}")

        # Test entry enrichment
        test_entry = {"GlobalID": "test-003", "CanonicalLatin": "Cédric Villani"}
        enriched = await api.enrich_entry(test_entry)

        if "AuthoritySources" in enriched:
            print(f"\nEnriched entry for {test_entry['CanonicalLatin']}:")
            print(f"  ORCID found: {'ORCID' in str(enriched.get('ExternalIDs', []))}")
            print(f"  Affiliations: {len(enriched.get('Affiliations', []))}")
            print(f"  Topics: {enriched.get('ResearchTopics', [])[:3]}")

        # Show stats
        print(f"\nAPI stats: {api.get_stats()}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_orcid_api())
