"""
Scopus (Elsevier) Authority Fetcher - Tier 1.

Scopus is Elsevier's abstract and citation database.
Comprehensive coverage with h-index, citations, and affiliation history.

API: https://api.elsevier.com/
Documentation: https://dev.elsevier.com/
License: Requires API key + institutional access
Daily Quota: 20,000 calls/week (institutional)
"""

import asyncio
import aiohttp
import logging
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from src.authorities.base import (
    AuthorityFetcher, FetchStatus, AuthorityData,
    FetchResult, AuthorityTier
)

logger = logging.getLogger(__name__)


class ScopusFetcher(AuthorityFetcher):
    """
    Scopus authority source fetcher.

    Fetches author profiles with citation metrics from Scopus database.
    Provides h-index, affiliation history, and publication counts.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Scopus fetcher."""
        super().__init__(config or {})
        self.service = "Scopus"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 20000 // 7  # Weekly quota divided by 7
        self.base_url = "https://api.elsevier.com"
        self.requires_auth = True
        self._min_request_interval = 1.0  # 1 second between requests

        # Load API key from config
        self.api_key = self._load_api_key(config)

    def _load_api_key(self, config: Optional[Dict[str, Any]]) -> str:
        """Load Scopus API key from config or file."""
        # Try config first
        if config and 'api_key' in config:
            return config['api_key']

        # Try loading from YAML file
        try:
            keys_file = Path('config/authority_api_keys.yaml')
            if keys_file.exists():
                with open(keys_file) as f:
                    keys_config = yaml.safe_load(f)
                    return keys_config.get('elsevier', {}).get('api_key', '')
        except Exception as e:
            logger.warning(f"Could not load Scopus API key from file: {e}")

        return ''

    async def fetch(self, identifier: str) -> FetchResult:
        """
        Fetch authority data from Scopus.

        Args:
            identifier: Author name to search

        Returns:
            FetchResult with authority data
        """
        if not self.api_key:
            return FetchResult(
                status=FetchStatus.AUTH_FAILED,
                source=self.service,
                query=identifier,
                error="Scopus API key not configured"
            )

        try:
            # Search for author
            author_results = await self._search_author(identifier)

            if not author_results or len(author_results) == 0:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND,
                    source=self.service,
                    query=identifier
                )

            # Get detailed author profile
            author_id = author_results[0].get('dc:identifier', '').replace('AUTHOR_ID:', '')
            if author_id:
                author_profile = await self._get_author_profile(author_id)
            else:
                author_profile = author_results[0]

            # Parse author data
            author_data = self._parse_author_data(identifier, author_profile, author_results)

            if not author_data:
                return FetchResult(
                    status=FetchStatus.NOT_FOUND,
                    source=self.service,
                    query=identifier
                )

            return FetchResult(
                status=FetchStatus.SUCCESS,
                source=self.service,
                query=identifier,
                data=author_data
            )

        except Exception as e:
            logger.error(f"Scopus fetch error: {e}")
            return FetchResult(
                status=FetchStatus.ERROR,
                source=self.service,
                query=identifier,
                error=str(e)
            )

    async def _search_author(self, author_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Scopus for author.

        Args:
            author_name: Author name to search
            max_results: Maximum number of results

        Returns:
            List of author records
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        params = {
            'query': f'AUTHNAME({author_name})',
            'count': max_results,
            'view': 'ENHANCED'
        }

        headers = {
            'X-ELS-APIKey': self.api_key,
            'Accept': 'application/json'
        }

        try:
            url = f"{self.base_url}/content/search/author"
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    entries = data.get('search-results', {}).get('entry', [])
                    logger.info(f"Scopus: Found {len(entries)} authors for '{author_name}'")
                    return entries
                elif response.status == 401:
                    logger.error("Scopus: Authentication failed")
                    return []
                elif response.status == 429:
                    logger.warning("Scopus: Rate limit exceeded")
                    return []
                else:
                    logger.warning(f"Scopus search failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Scopus search error: {e}")
            return []

    async def _get_author_profile(self, author_id: str) -> Dict[str, Any]:
        """
        Get detailed author profile from Scopus.

        Args:
            author_id: Scopus author ID

        Returns:
            Author profile data
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        headers = {
            'X-ELS-APIKey': self.api_key,
            'Accept': 'application/json'
        }

        try:
            url = f"{self.base_url}/content/author/author_id/{author_id}"
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('author-retrieval-response', [{}])[0] if isinstance(data.get('author-retrieval-response'), list) else data.get('author-retrieval-response', {})
                else:
                    logger.warning(f"Scopus profile fetch failed with status {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Scopus profile error: {e}")
            return {}

    def _parse_author_data(self, query_name: str, profile: Dict[str, Any],
                          search_results: List[Dict[str, Any]]) -> Optional[AuthorityData]:
        """
        Parse Scopus data to extract author information.

        Args:
            query_name: Original query name
            profile: Author profile data
            search_results: Search results

        Returns:
            AuthorityData object or None
        """
        if not (profile or search_results):
            return None

        # Use first search result if no profile
        data = profile if profile else search_results[0]

        # Extract author ID
        author_id = data.get('dc:identifier', '').replace('AUTHOR_ID:', '')
        if not author_id and search_results:
            author_id = search_results[0].get('dc:identifier', '').replace('AUTHOR_ID:', '')

        # Extract name
        preferred_name = data.get('preferred-name', {})
        canonical_name = f"{preferred_name.get('given-name', '')} {preferred_name.get('surname', '')}".strip()
        if not canonical_name:
            canonical_name = query_name

        # Extract affiliations
        affiliations = []
        affiliation_current = data.get('affiliation-current', {})
        if affiliation_current:
            aff_info = affiliation_current.get('affiliation', {})
            if aff_info:
                affiliations.append({
                    'institution': aff_info.get('ip-doc', {}).get('afdispname', ''),
                    'country': aff_info.get('ip-doc', {}).get('address', {}).get('country', '')
                })

        # Extract affiliation history
        aff_history = data.get('affiliation-history', {}).get('affiliation', [])
        if isinstance(aff_history, dict):
            aff_history = [aff_history]
        for aff in aff_history[:3]:  # Top 3 historical
            ip_doc = aff.get('ip-doc', {})
            if ip_doc:
                affiliations.append({
                    'institution': ip_doc.get('afdispname', ''),
                    'country': ip_doc.get('address', {}).get('country', '')
                })

        # Extract metrics
        h_index = None
        citation_count = 0
        document_count = 0

        coredata = data.get('coredata', {})
        if coredata:
            citation_count = int(coredata.get('citation-count', 0))
            document_count = int(coredata.get('document-count', 0))

        # H-index from profile
        if 'h-index' in data:
            h_index = int(data['h-index'])

        # Build AuthorityData
        authority_data = AuthorityData(
            source=self.service,
            source_id=author_id or f"scopus_{query_name.replace(' ', '_')}",
            canonical_name=canonical_name,
            name_variants=[],
            affiliations=affiliations[:5],  # Top 5
            identifiers={
                'Scopus_Author_ID': author_id,
                'ORCID': data.get('coredata', {}).get('orcid')
            },
            msc_codes=[],
            metadata={
                'h_index': h_index,
                'citation_count': citation_count,
                'document_count': document_count,
                'subject_areas': data.get('subject-area', [])
            },
            confidence_score=self._calculate_confidence(h_index, citation_count, document_count),
            fetch_timestamp=datetime.now(),
            personal_data_scrubbed=True
        )

        return authority_data

    def _calculate_confidence(self, h_index: Optional[int], citations: int, documents: int) -> float:
        """
        Calculate confidence score for Scopus data.

        Args:
            h_index: H-index value
            citations: Citation count
            documents: Document count

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.6  # Base confidence for Scopus (authoritative)

        # H-index increases confidence
        if h_index:
            if h_index >= 20:
                confidence += 0.2
            elif h_index >= 10:
                confidence += 0.1
            elif h_index >= 5:
                confidence += 0.05

        # Citations increase confidence
        if citations >= 1000:
            confidence += 0.1
        elif citations >= 100:
            confidence += 0.05

        # Documents increase confidence
        if documents >= 50:
            confidence += 0.05

        return min(confidence, 1.0)

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """
        Parse Scopus response into AuthorityData.

        Args:
            response: Raw Scopus API response

        Returns:
            AuthorityData object
        """
        entries = response.get('search-results', {}).get('entry', [])

        if not entries:
            return None

        return self._parse_author_data("Unknown", {}, entries)

    def calculate_confidence(self, data: AuthorityData) -> float:
        """
        Calculate confidence score for parsed data.

        Args:
            data: AuthorityData object

        Returns:
            Confidence score (0.0-1.0)
        """
        return data.confidence_score if data else 0.0
