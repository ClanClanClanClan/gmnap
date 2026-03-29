#!/usr/bin/env python3
"""
Mathematics Genealogy Project API Implementation for GMNAP V7
Tier-1 authority source: Academic genealogy data
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class Mathematician:
    """Mathematics Genealogy Project mathematician data"""

    mgp_id: str
    name: str
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[int] = None
    country: Optional[str] = None
    advisors: List[Tuple[str, str]] = None  # List of (name, id) tuples
    students: List[Tuple[str, str]] = None  # List of (name, id) tuples
    dissertation_title: Optional[str] = None
    subject_area: Optional[str] = None


class MathGenealogyAPI:
    """
    Mathematics Genealogy Project API client

    Provides:
    - Academic genealogy (advisors/students)
    - Dissertation information
    - Institution history
    - Degree information
    """

    BASE_URL = "https://www.mathgenealogy.org"
    SEARCH_URL = f"{BASE_URL}/search"
    PERSON_URL = f"{BASE_URL}/id.php"

    def __init__(self):
        """Initialize Math Genealogy API client"""
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_count = 0

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "GMNAP/7.0 (Academic Research Tool)"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _parse_person_page(self, html: str, mgp_id: str) -> Optional[Mathematician]:
        """Parse a mathematician's page"""
        soup = BeautifulSoup(html, "html.parser")

        # Extract name
        name_elem = soup.find("h2")
        if not name_elem:
            return None
        name = name_elem.text.strip()

        # Extract degree info
        degree = None
        institution = None
        year = None
        country = None
        dissertation_title = None
        subject_area = None

        # Find the main content div
        content = soup.find("div", {"id": "paddingWrapper"})
        if content:
            # Extract degree type
            degree_match = re.search(
                r"(Ph\.D\.|M\.A\.|M\.S\.|Dr\.|Habilitation)", content.text
            )
            if degree_match:
                degree = degree_match.group(1)

            # Extract institution and year
            for line in content.text.split("\n"):
                if degree and degree in line:
                    # Try to extract institution and year
                    inst_match = re.search(
                        rf"{re.escape(degree)}\s+([^0-9]+?)(\d{{4}})", line
                    )
                    if inst_match:
                        institution = inst_match.group(1).strip()
                        year = int(inst_match.group(2))

            # Extract country
            country_elem = soup.find("img", {"src": re.compile(r"flags/")})
            if country_elem and country_elem.get("title"):
                country = country_elem["title"]

            # Extract dissertation title
            diss_elem = soup.find("span", {"id": "thesisTitle"})
            if not diss_elem:
                # Alternative: look for italic text that might be the title
                diss_elem = soup.find("i")
            if diss_elem:
                dissertation_title = diss_elem.text.strip()

            # Extract subject area
            subject_elem = soup.find("div", {"style": re.compile("msc")})
            if subject_elem:
                subject_area = subject_elem.text.strip()

        # Extract advisors
        advisors = []
        advisor_section = soup.find("p", string=re.compile("Advisor"))
        if advisor_section:
            for link in advisor_section.find_next_siblings("a"):
                if "id.php?id=" in link.get("href", ""):
                    advisor_id = link["href"].split("id=")[1]
                    advisor_name = link.text.strip()
                    advisors.append((advisor_name, advisor_id))

        # Extract students
        students = []
        student_section = soup.find("p", string=re.compile("Student"))
        if student_section:
            table = student_section.find_next("table")
            if table:
                for row in table.find_all("tr")[1:]:  # Skip header
                    link = row.find("a")
                    if link and "id.php?id=" in link.get("href", ""):
                        student_id = link["href"].split("id=")[1]
                        student_name = link.text.strip()
                        students.append((student_name, student_id))

        return Mathematician(
            mgp_id=mgp_id,
            name=name,
            degree=degree,
            institution=institution,
            year=year,
            country=country,
            advisors=advisors or [],
            students=students or [],
            dissertation_title=dissertation_title,
            subject_area=subject_area,
        )

    async def search_by_name(self, name: str) -> List[Tuple[str, str]]:
        """
        Search for mathematicians by name

        Args:
            name: Name to search

        Returns:
            List of (name, mgp_id) tuples
        """
        params = {"name": name, "submit": "Search"}

        try:
            async with self.session.get(self.SEARCH_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"MGP search returned {response.status}")
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                results = []
                # Parse search results
                for link in soup.find_all("a", href=re.compile(r"id\.php\?id=\d+")):
                    mgp_id = link["href"].split("id=")[1]
                    person_name = link.text.strip()
                    results.append((person_name, mgp_id))

                return results[:10]  # Return top 10 matches

        except Exception as e:
            logger.error(f"Error searching MGP for {name}: {e}")
            return []

    async def get_person(self, mgp_id: str) -> Optional[Mathematician]:
        """
        Get person details by MGP ID

        Args:
            mgp_id: Mathematics Genealogy Project ID

        Returns:
            Mathematician object or None
        """
        params = {"id": mgp_id}

        try:
            async with self.session.get(self.PERSON_URL, params=params) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                return self._parse_person_page(html, mgp_id)

        except Exception as e:
            logger.error(f"Error fetching MGP person {mgp_id}: {e}")
            return None

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich GMNAP entry with Math Genealogy data

        Args:
            entry: GMNAP entry dictionary

        Returns:
            Enriched entry
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        if not name:
            return entry

        # Search for the person
        search_results = await self.search_by_name(name)

        if not search_results:
            return entry

        # Get details for the first match
        person_name, mgp_id = search_results[0]
        person = await self.get_person(mgp_id)

        if not person:
            return entry

        # Add MGP ID
        if "ExternalIDs" not in entry:
            entry["ExternalIDs"] = []
        entry["ExternalIDs"].append(
            {"type": "MGP", "value": mgp_id, "source": "Mathematics Genealogy Project"}
        )

        # Add degree information
        if person.degree:
            entry["HighestDegree"] = {
                "degree": person.degree,
                "institution": person.institution,
                "year": person.year,
                "country": person.country,
            }

        # Add dissertation info
        if person.dissertation_title:
            entry["Dissertation"] = {
                "title": person.dissertation_title,
                "subject": person.subject_area,
            }

        # Add academic genealogy
        if person.advisors or person.students:
            entry["AcademicGenealogy"] = {
                "advisors": [
                    {"name": name, "mgp_id": id} for name, id in person.advisors
                ],
                "students": [
                    {"name": name, "mgp_id": id} for name, id in person.students[:10]
                ],  # Limit to 10
            }

        # Add to authority sources
        entry["AuthoritySources"] = entry.get("AuthoritySources", [])
        entry["AuthoritySources"].append(
            {
                "source": "Mathematics Genealogy Project",
                "mgp_id": mgp_id,
                "student_count": len(person.students),
                "advisor_count": len(person.advisors),
            }
        )

        return entry


# Test function
async def test_mgp_api():
    """Test Mathematics Genealogy Project API"""
    async with MathGenealogyAPI() as api:
        # Search for a mathematician
        results = await api.search_by_name("T. Tao")
        print(f"Found {len(results)} results for T. Tao")

        if results:
            name, mgp_id = results[0]
            print(f"First match: {name} (ID: {mgp_id})")

            # Get person details
            person = await api.get_person(mgp_id)
            if person:
                print(
                    f"Degree: {person.degree} from {person.institution} ({person.year})"
                )
                print(f"Advisors: {len(person.advisors)}")
                print(f"Students: {len(person.students)}")

        # Test enrichment
        test_entry = {"GlobalID": "test-003", "CanonicalLatin": "A. Wiles"}
        enriched = await api.enrich_entry(test_entry)
        print(f"Enriched: {enriched.get('HighestDegree', {})}")

        return len(results) > 0


if __name__ == "__main__":
    asyncio.run(test_mgp_api())
