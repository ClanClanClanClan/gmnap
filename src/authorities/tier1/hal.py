"""
HAL (Hyper Articles en Ligne) Authority Fetcher - Tier 1.

HAL is France's national open archive for scholarly publications.
Over 1 million documents including theses, articles, and preprints.

API: https://api.archives-ouvertes.fr/
Documentation: https://api.archives-ouvertes.fr/docs/
License: Open Access
Daily Quota: Unlimited (open API)
"""

import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.authorities.base import (
    AuthorityFetcher,
    FetchStatus,
    AuthorityData,
    FetchResult,
    AuthorityTier,
)

logger = logging.getLogger(__name__)


class HALFetcher(AuthorityFetcher):
    """
    HAL authority source fetcher.

    Fetches author and publication data from French open archive.
    Particularly strong for French mathematics and European coverage.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize HAL fetcher."""
        super().__init__(config or {})
        self.service = "HAL"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 999999  # Unlimited (open API)
        self.base_url = "https://api.archives-ouvertes.fr/search/"
        self.requires_auth = False
        self._min_request_interval = 0.2  # 200ms between requests (be polite)

    async def fetch(self, identifier: str) -> FetchResult:
        """
        Fetch authority data from HAL.

        Args:
            identifier: Author name to search

        Returns:
            FetchResult with authority data
        """
        try:
            # Search for author documents
            results = await self._search_author(identifier)

            if not results or len(results) == 0:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND, source=self.service, query=identifier
                )

            # Parse results to extract author information
            author_data = self._parse_author_data(identifier, results)

            if not author_data:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND, source=self.service, query=identifier
                )

            return FetchResult(
                status=FetchStatus.SUCCESS,
                source=self.service,
                query=identifier,
                data=author_data,
            )

        except Exception as e:
            logger.error(f"HAL fetch error: {e}")
            return FetchResult(
                status=FetchStatus.ERROR,
                source=self.service,
                query=identifier,
                error=str(e),
            )

    async def _search_author(
        self, author_name: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search HAL for documents by author.

        Args:
            author_name: Author name to search
            max_results: Maximum number of results to return

        Returns:
            List of document records
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        # HAL API parameters
        params = {
            "q": f'authFullName_t:"{author_name}"',  # Search in author full names
            "wt": "json",  # Response format
            "rows": max_results,  # Number of results
            "fl": "docid,title_s,authFullName_s,docType_s,publicationDate_s,"
            "structId_i,structName_s,domain_s,halId_s,uri_s",  # Fields to return
        }

        try:
            async with self._session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    docs = data.get("response", {}).get("docs", [])
                    logger.info(f"HAL: Found {len(docs)} documents for '{author_name}'")
                    return docs
                else:
                    logger.warning(f"HAL search failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"HAL search error: {e}")
            return []

    def _parse_author_data(
        self, query_name: str, documents: List[Dict[str, Any]]
    ) -> Optional[AuthorityData]:
        """
        Parse HAL documents to extract author information.

        Args:
            query_name: Original query name
            documents: List of HAL documents

        Returns:
            AuthorityData object or None
        """
        if not documents:
            return None

        # Extract information from documents
        affiliations = set()
        publications = []
        domains = set()
        hal_ids = set()

        # Process each document
        for doc in documents:
            # Extract affiliations (French institutions)
            if "structName_s" in doc:
                structs = doc["structName_s"]
                if isinstance(structs, list):
                    affiliations.update(structs)
                else:
                    affiliations.add(structs)

            # Extract research domains
            if "domain_s" in doc:
                doms = doc["domain_s"]
                if isinstance(doms, list):
                    domains.update(doms)
                else:
                    domains.add(doms)

            # Extract HAL IDs
            if "halId_s" in doc:
                hal_ids.add(doc["halId_s"])

            # Extract publication info
            pub = {
                "title": (
                    doc.get("title_s", [""])[0]
                    if isinstance(doc.get("title_s"), list)
                    else doc.get("title_s", "")
                ),
                "type": doc.get("docType_s", ""),
                "date": doc.get("publicationDate_s", ""),
                "uri": doc.get("uri_s", ""),
            }
            publications.append(pub)

        # Build AuthorityData
        authority_data = AuthorityData(
            source=self.service,
            source_id=(
                list(hal_ids)[0] if hal_ids else f"hal_{query_name.replace(' ', '_')}"
            ),
            canonical_name=query_name,
            name_variants=[],
            affiliations=[
                {"institution": aff, "country": "FR"}
                for aff in list(affiliations)[:5]  # Top 5 affiliations
            ],
            identifiers={"HAL": list(hal_ids)[0] if hal_ids else None},
            msc_codes=[],  # HAL doesn't provide MSC codes directly
            metadata={
                "publications": publications[:10],  # Top 10 publications
                "domains": list(domains),
                "document_count": len(documents),
                "hal_ids": list(hal_ids),
            },
            confidence_score=self._calculate_confidence(documents, affiliations),
            fetch_timestamp=datetime.now(),
            personal_data_scrubbed=True,
        )

        return authority_data

    def _calculate_confidence(self, documents: List[Dict], affiliations: set) -> float:
        """
        Calculate confidence score for HAL data.

        Args:
            documents: List of documents found
            affiliations: Set of affiliations found

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.5  # Base confidence

        # More documents = higher confidence
        if len(documents) >= 10:
            confidence += 0.2
        elif len(documents) >= 5:
            confidence += 0.1
        elif len(documents) >= 2:
            confidence += 0.05

        # Affiliations increase confidence
        if len(affiliations) > 0:
            confidence += 0.1

        # French institutions are authoritative in HAL
        french_keywords = ["université", "cnrs", "inria", "école", "institut"]
        has_french_affiliation = any(
            any(keyword in str(aff).lower() for keyword in french_keywords)
            for aff in affiliations
        )
        if has_french_affiliation:
            confidence += 0.1

        return min(confidence, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse HAL response into AuthorityData.

        Args:
            response: Raw HAL API response

        Returns:
            AuthorityData object
        """
        # Extract documents from response
        docs = response.get("response", {}).get("docs", [])

        if not docs:
            return None

        # Use first document's author as canonical name
        author_names = docs[0].get("authFullName_s", [])
        canonical_name = (
            author_names[0]
            if isinstance(author_names, list) and author_names
            else "Unknown"
        )

        return self._parse_author_data(canonical_name, docs)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for parsed data.

        Args:
            data: AuthorityData object

        Returns:
            Confidence score (0.0-1.0)
        """
        return data.confidence_score if data else 0.0
