"""
arXiv fetcher for GMNAP.

arXiv is a free distribution service and open-access archive for scholarly articles.
API Documentation: https://arxiv.org/help/api/
"""

import asyncio
import xml.etree.ElementTree as ET
import urllib.parse
from datetime import datetime
from typing import Any, Dict

from src.authorities.base import (
    AuthorityData,
    AuthorityFetcher,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)


class ArXivFetcher(AuthorityFetcher):
    """
    Fetcher for arXiv API.

    Features:
    - Free access
    - Strong in mathematics, physics, computer science
    - Pre-print server (cutting-edge research)
    - Rich metadata including categories
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service = "arXiv"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 50000  # Very generous - arXiv is free
        self.base_url = "http://export.arxiv.org/api/query"
        self.requires_auth = False

        # Rate limiting: arXiv recommends 3 seconds between requests
        self._min_request_interval = 3.0

    async def fetch(self, query: str) -> FetchResult:
        """
        Fetch researcher data from arXiv.

        Args:
            query: Researcher name

        Returns:
            FetchResult with parsed arXiv data
        """
        try:
            # Rate limiting
            await self.ensure_rate_limit()

            # Search for papers by author
            return await self._search_by_author(query)

        except asyncio.TimeoutError:
            return FetchResult(
                status=FetchStatus.NETWORK_ERROR, error_message="Request timeout"
            )

        except Exception as e:
            self.logger.error(f"arXiv fetch error: {e}")
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(e))

    async def _search_by_author(self, author_name: str) -> FetchResult:
        """Search arXiv by author name."""
        # Build search query
        # arXiv search format: au:"Last, First" OR au:"First Last"
        params = {
            "search_query": f'au:"{author_name}"',
            "start": 0,
            "max_results": 100,  # Get reasonable sample
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        # Build URL
        url = self.base_url + "?" + urllib.parse.urlencode(params)

        session = await self.get_session()

        async with session.get(url) as response:
            if response.status == 200:
                xml_data = await response.text()
                parsed = self.parse_arxiv_response(xml_data, author_name)

                if parsed.metadata.get("publications_total", 0) == 0:
                    return FetchResult(
                        status=FetchStatus.NOT_FOUND,
                        error_message="No arXiv papers found for author",
                    )

                return FetchResult(
                    status=FetchStatus.SUCCESS,
                    data=parsed,
                    raw_response={"xml_length": len(xml_data)},
                )

            elif response.status == 429:
                return FetchResult(
                    status=FetchStatus.RATE_LIMITED,
                    error_message="arXiv rate limit exceeded",
                    retry_after=300,  # 5 minutes
                )

            else:
                return FetchResult(
                    status=FetchStatus.NETWORK_ERROR,
                    error_message=f"HTTP {response.status}: {await response.text()}",
                )

    def parse_arxiv_response(self, xml_data: str, query_name: str) -> AuthorityData:
        """Parse arXiv Atom XML response."""
        try:
            # Parse XML with namespace handling
            root = ET.fromstring(xml_data)

            # arXiv uses Atom namespace
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            data = AuthorityData(
                source=self.service,
                source_id=f"arxiv_{hash(query_name)}",
                canonical_name=query_name,
            )

            # Collect paper information
            entries = root.findall(".//atom:entry", ns)

            publications = []
            categories = set()
            years = []
            coauthors = set()

            for entry in entries:
                # Extract paper info
                paper = {}

                # Title
                title_elem = entry.find("atom:title", ns)
                if title_elem is not None:
                    paper["title"] = title_elem.text.strip()

                # arXiv ID
                id_elem = entry.find("atom:id", ns)
                if id_elem is not None:
                    arxiv_url = id_elem.text
                    paper["arxiv_id"] = arxiv_url.split("/")[-1]

                # Categories (subject classifications)
                for category in entry.findall(".//arxiv:primary_category", ns):
                    term = category.get("term")
                    if term:
                        categories.add(term)
                        paper["primary_category"] = term

                # Published date
                published = entry.find("atom:published", ns)
                if published is not None:
                    try:
                        pub_date = datetime.fromisoformat(
                            published.text.replace("Z", "+00:00")
                        )
                        years.append(pub_date.year)
                        paper["year"] = pub_date.year
                    except:
                        pass

                # Authors (to find coauthors)
                authors = entry.findall(".//atom:author/atom:name", ns)
                paper_authors = []
                for author in authors:
                    if author.text:
                        author_name = author.text.strip()
                        paper_authors.append(author_name)
                        if author_name.lower() != query_name.lower():
                            coauthors.add(author_name)

                paper["authors"] = paper_authors
                publications.append(paper)

            # Calculate statistics
            data.metadata = {
                "arxiv_papers_count": len(publications),
                "publications_total": len(publications),
                "categories": list(categories),
                "primary_subjects": list(categories)[:5],  # Top 5
                "years_active": f"{min(years)}-{max(years)}" if years else "",
                "publication_years": sorted(list(set(years))),
                "coauthors_count": len(coauthors),
                "recent_papers": len(
                    [p for p in publications if p.get("year", 0) >= 2020]
                ),
            }

            # Generate name variants from author fields
            name_variants = set()
            for paper in publications:
                for author in paper.get("authors", []):
                    if self._names_similar(author, query_name):
                        name_variants.add(author)

            data.name_variants = list(name_variants - {query_name})

            # Calculate confidence
            data.confidence_score = self.calculate_confidence(data)

            return data

        except ET.ParseError as e:
            self.logger.error(f"Failed to parse arXiv XML: {e}")
            return AuthorityData(
                source=self.service,
                source_id=f"arxiv_{hash(query_name)}",
                canonical_name=query_name,
            )

    def _names_similar(self, name1: str, name2: str) -> bool:
        """Check if two names are similar enough to be variants."""
        # Simple similarity check
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())

        # Check if they share significant words
        intersection = words1.intersection(words2)
        if len(intersection) >= min(len(words1), len(words2)) - 1:
            return True

        return False

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for arXiv data.

        Higher confidence for:
        - Multiple papers
        - Recent activity
        - Diverse subject areas
        - Multiple name variants
        """
        score = 0.1  # Base score

        # Paper count
        paper_count = data.metadata.get("arxiv_papers_count", 0)
        if paper_count > 0:
            score += 0.1
        if paper_count > 5:
            score += 0.1
        if paper_count > 20:
            score += 0.1

        # Recent activity (arXiv strength)
        recent_papers = data.metadata.get("recent_papers", 0)
        if recent_papers > 0:
            score += 0.1
        if recent_papers > 3:
            score += 0.1

        # Subject diversity
        categories = data.metadata.get("categories", [])
        if len(categories) > 1:
            score += 0.1
        if len(categories) > 3:
            score += 0.1

        # Name variants
        if len(data.name_variants) > 0:
            score += 0.1

        # Coauthors (collaboration indicator)
        coauthor_count = data.metadata.get("coauthors_count", 0)
        if coauthor_count > 5:
            score += 0.1

        # arXiv is preprints, so moderate overall confidence
        score += 0.05  # Preprint bonus

        return min(score, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """Parse API response - not used for arXiv XML."""
        return AuthorityData(source=self.service, source_id="", canonical_name="")
