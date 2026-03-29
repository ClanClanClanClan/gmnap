"""
PubMed Authority Fetcher for V7 compliance.
Provides access to biomedical literature and author data from NCBI.
"""

import aiohttp
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.authorities.base import (
    AuthorityFetcher,
    AuthorityData,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class PubMedAuthorData:
    """PubMed author data structure."""

    author_name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None
    publications: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.publications is None:
            self.publications = []


class PubMedFetcher(AuthorityFetcher):
    """
    PubMed Authority Fetcher - Tier 1.
    Fetches author and publication data from NCBI PubMed.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize PubMed fetcher with configuration."""
        super().__init__(config)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.session = None
        self.tier = AuthorityTier.TIER_1
        # API key is optional but recommended for higher rate limits
        self.api_key = config.get("api_key") if config else None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def search_author(self, author_name: str, limit: int = 10) -> List[str]:
        """
        Search PubMed for publications by author.

        Args:
            author_name: Author name to search
            limit: Maximum number of PMIDs to return

        Returns:
            List of PubMed IDs (PMIDs)
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        # Format author name for PubMed search
        # PubMed expects "LastName FirstInitial" format
        name_parts = author_name.split()
        if len(name_parts) >= 2:
            search_term = f"{name_parts[-1]} {name_parts[0][0]}"
        else:
            search_term = author_name

        params = {
            "db": "pubmed",
            "term": f"{search_term}[Author]",
            "retmax": limit,
            "retmode": "json",
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            url = f"{self.base_url}/esearch.fcgi"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    id_list = data.get("esearchresult", {}).get("idlist", [])
                    return id_list
                else:
                    logger.warning(f"PubMed search failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return []

    async def fetch_article_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch article details for given PMIDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of article details
        """
        if not pmids:
            return []

        if not self.session:
            self.session = aiohttp.ClientSession()

        params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            url = f"{self.base_url}/efetch.fcgi"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    xml_text = await response.text()
                    return self._parse_articles_xml(xml_text)
                else:
                    logger.warning(f"PubMed fetch failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"PubMed fetch error: {e}")
            return []

    def _parse_articles_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse PubMed XML response to extract article details."""
        articles = []
        try:
            root = ET.fromstring(xml_text)
            for article in root.findall(".//PubmedArticle"):
                article_data = {}

                # Extract PMID
                pmid_elem = article.find(".//PMID")
                if pmid_elem is not None:
                    article_data["pmid"] = pmid_elem.text

                # Extract title
                title_elem = article.find(".//ArticleTitle")
                if title_elem is not None:
                    article_data["title"] = title_elem.text

                # Extract journal
                journal_elem = article.find(".//Journal/Title")
                if journal_elem is not None:
                    article_data["journal"] = journal_elem.text

                # Extract publication year
                year_elem = article.find(".//PubDate/Year")
                if year_elem is not None:
                    article_data["year"] = int(year_elem.text)

                # Extract authors
                authors = []
                for author in article.findall(".//Author"):
                    author_info = {}

                    last_name = author.find("LastName")
                    if last_name is not None:
                        author_info["last_name"] = last_name.text

                    fore_name = author.find("ForeName")
                    if fore_name is not None:
                        author_info["first_name"] = fore_name.text

                    # Check for ORCID
                    for identifier in author.findall(".//Identifier"):
                        if identifier.get("Source") == "ORCID":
                            author_info["orcid"] = identifier.text

                    # Get affiliation
                    affiliation = author.find(".//Affiliation")
                    if affiliation is not None:
                        author_info["affiliation"] = affiliation.text

                    if author_info:
                        authors.append(author_info)

                article_data["authors"] = authors
                articles.append(article_data)

        except Exception as e:
            logger.error(f"Error parsing PubMed XML: {e}")

        return articles

    async def fetch(self, identifier: str) -> FetchResult:
        """
        Fetch authority data from PubMed.

        Args:
            identifier: Author name to search

        Returns:
            FetchResult with authority data
        """
        try:
            # Search for publications
            pmids = await self.search_author(identifier, limit=10)

            if not pmids:
                return FetchResult(status=FetchStatus.NOT_FOUND, source="PubMed", query=identifier)

            # Fetch article details
            articles = await self.fetch_article_details(pmids)

            # Extract author information
            author_data = self._extract_author_data(identifier, articles)

            if not author_data:
                return FetchResult(status=FetchStatus.NOT_FOUND, source="PubMed", query=identifier)

            # Convert to AuthorityData
            authority_data = AuthorityData(
                source="PubMed",
                identifier=identifier,
                name=author_data.author_name,
                affiliations=[author_data.affiliation] if author_data.affiliation else [],
                publications=[
                    {
                        "title": pub.get("title"),
                        "journal": pub.get("journal"),
                        "year": pub.get("year"),
                        "pmid": pub.get("pmid"),
                    }
                    for pub in author_data.publications[:5]
                ],  # Limit to 5 publications
                external_ids={"ORCID": author_data.orcid} if author_data.orcid else {},
                confidence=0.8,
            )

            return FetchResult(
                status=FetchStatus.SUCCESS, source="PubMed", query=identifier, data=authority_data
            )

        except Exception as e:
            logger.error(f"PubMed fetch error: {e}")
            return FetchResult(
                status=FetchStatus.ERROR, source="PubMed", query=identifier, error=str(e)
            )

    def _extract_author_data(
        self, query_name: str, articles: List[Dict]
    ) -> Optional[PubMedAuthorData]:
        """Extract author data from articles."""
        if not articles:
            return None

        # Normalize query name
        query_parts = query_name.lower().split()

        # Find the author in the articles
        author_info = None
        affiliations = set()
        orcid = None

        for article in articles:
            for author in article.get("authors", []):
                # Check if this author matches our query
                author_name = (
                    f"{author.get('first_name', '')} {author.get('last_name', '')}".strip()
                )
                author_parts = author_name.lower().split()

                # Simple matching - last names must match
                if query_parts and author_parts:
                    if query_parts[-1] == author_parts[-1]:  # Last name match
                        if not author_info:
                            author_info = author_name

                        if author.get("affiliation"):
                            affiliations.add(author["affiliation"])

                        if author.get("orcid") and not orcid:
                            orcid = author["orcid"]

        if not author_info:
            # Fallback: use first author from first article
            if articles and articles[0].get("authors"):
                first_author = articles[0]["authors"][0]
                author_info = f"{first_author.get('first_name', '')} {first_author.get('last_name', '')}".strip()

        if author_info:
            return PubMedAuthorData(
                author_name=author_info,
                affiliation=list(affiliations)[0] if affiliations else None,
                orcid=orcid,
                publications=articles,
            )

        return None
