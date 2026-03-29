#!/usr/bin/env python3
"""
ArXiv Authority API Implementation for GMNAP V7
Tier-0 authority source: Open access, no rate limits
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ArXivAuthor:
    """ArXiv author data structure"""

    name: str
    affiliation: Optional[str] = None


@dataclass
class ArXivPaper:
    """ArXiv paper data structure"""

    arxiv_id: str
    title: str
    authors: List[ArXivAuthor]
    abstract: str
    categories: List[str]
    published: str
    updated: str
    doi: Optional[str] = None
    journal_ref: Optional[str] = None


class ArXivAPI:
    """
    ArXiv API client for V7 authority enrichment

    Implements:
    - Author search via papers
    - Mathematical subject classification
    - Open access paper retrieval
    """

    BASE_URL = "http://export.arxiv.org/api/query"
    MAX_RESULTS = 100

    def __init__(self):
        """Initialize ArXiv API client"""
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _parse_atom_entry(self, entry: ET.Element) -> ArXivPaper:
        """Parse ArXiv Atom feed entry"""
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        # Extract basic info
        arxiv_id = entry.find("atom:id", ns).text.split("/")[-1]
        title = entry.find("atom:title", ns).text.strip()
        abstract = entry.find("atom:summary", ns).text.strip()
        published = entry.find("atom:published", ns).text
        updated = entry.find("atom:updated", ns).text

        # Extract authors
        authors = []
        for author_elem in entry.findall("atom:author", ns):
            name = author_elem.find("atom:name", ns).text
            affil_elem = author_elem.find("arxiv:affiliation", ns)
            affiliation = affil_elem.text if affil_elem is not None else None
            authors.append(ArXivAuthor(name=name, affiliation=affiliation))

        # Extract categories
        categories = []
        for cat_elem in entry.findall("atom:category", ns):
            categories.append(cat_elem.get("term"))

        # Extract DOI if present
        doi = None
        doi_elem = entry.find("arxiv:doi", ns)
        if doi_elem is not None:
            doi = doi_elem.text

        # Extract journal ref if present
        journal_ref = None
        journal_elem = entry.find("arxiv:journal_ref", ns)
        if journal_elem is not None:
            journal_ref = journal_elem.text

        return ArXivPaper(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=abstract,
            categories=categories,
            published=published,
            updated=updated,
            doi=doi,
            journal_ref=journal_ref,
        )

    async def search_author(self, name: str, max_results: int = 10) -> List[ArXivPaper]:
        """
        Search for papers by author name

        Args:
            name: Author name to search
            max_results: Maximum papers to return

        Returns:
            List of ArXiv papers
        """
        # Build query
        query = f'au:"{name}"'
        params = {
            "search_query": query,
            "start": 0,
            "max_results": min(max_results, self.MAX_RESULTS),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            async with self.session.get(self.BASE_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"ArXiv API returned {response.status}")
                    return []

                content = await response.text()

                # Parse XML
                root = ET.fromstring(content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}

                papers = []
                for entry in root.findall("atom:entry", ns):
                    try:
                        paper = self._parse_atom_entry(entry)
                        papers.append(paper)
                    except Exception as e:
                        logger.error(f"Failed to parse ArXiv entry: {e}")

                return papers

        except Exception as e:
            logger.error(f"Error searching ArXiv for {name}: {e}")
            return []

    async def search_category(
        self, category: str = "math", max_results: int = 10
    ) -> List[ArXivPaper]:
        """
        Search for recent papers in a category

        Args:
            category: ArXiv category (e.g., 'math.AG', 'cs.AI')
            max_results: Maximum papers to return

        Returns:
            List of ArXiv papers
        """
        params = {
            "search_query": f"cat:{category}",
            "start": 0,
            "max_results": min(max_results, self.MAX_RESULTS),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            async with self.session.get(self.BASE_URL, params=params) as response:
                if response.status != 200:
                    return []

                content = await response.text()
                root = ET.fromstring(content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}

                papers = []
                for entry in root.findall("atom:entry", ns):
                    try:
                        paper = self._parse_atom_entry(entry)
                        papers.append(paper)
                    except Exception as e:
                        logger.error(f"Failed to parse entry: {e}")

                return papers

        except Exception as e:
            logger.error(f"Error searching category {category}: {e}")
            return []

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a GMNAP entry with ArXiv data

        Args:
            entry: GMNAP entry dictionary

        Returns:
            Enriched entry with ArXiv metadata
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        if not name:
            return entry

        # Search for papers
        papers = await self.search_author(name, max_results=5)

        if not papers:
            return entry

        # Add ArXiv data
        if "ExternalIDs" not in entry:
            entry["ExternalIDs"] = []

        # Add ArXiv IDs
        arxiv_ids = [p.arxiv_id for p in papers[:3]]  # Top 3 papers
        entry["ExternalIDs"].append(
            {"type": "ArXiv", "value": arxiv_ids, "source": "ArXiv API"}
        )

        # Extract unique affiliations
        affiliations = set()
        for paper in papers:
            for author in paper.authors:
                if author.affiliation and author.name.lower() in name.lower():
                    affiliations.add(author.affiliation)

        if affiliations:
            if "Affiliations" not in entry:
                entry["Affiliations"] = []
            for aff in affiliations:
                entry["Affiliations"].append({"institution": aff, "source": "ArXiv"})

        # Extract research areas from categories
        categories = set()
        for paper in papers:
            categories.update(paper.categories)

        if categories:
            entry["ResearchAreas"] = list(categories)[:5]  # Top 5 categories

        # Add metadata
        entry["AuthoritySources"] = entry.get("AuthoritySources", [])
        entry["AuthoritySources"].append(
            {
                "source": "ArXiv",
                "paper_count": len(papers),
                "categories": list(categories)[:3],
            }
        )

        return entry


# Test function
async def test_arxiv_api():
    """Test ArXiv API implementation"""
    async with ArXivAPI() as api:
        # Test author search
        papers = await api.search_author("T. Tao")
        print(f"Found {len(papers)} papers by T. Tao")
        if papers:
            print(f"Latest paper: {papers[0].title}")
            print(f"Categories: {papers[0].categories}")

        # Test entry enrichment
        test_entry = {"GlobalID": "test-002", "CanonicalLatin": "T. Tao"}
        enriched = await api.enrich_entry(test_entry)
        print(f"Enriched entry: {enriched.get('ResearchAreas', [])}")

        return len(papers) > 0


if __name__ == "__main__":
    asyncio.run(test_arxiv_api())
