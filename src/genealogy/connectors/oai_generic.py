"""
genealogy/connectors/oai_generic.py
Generic OAI-PMH harvester for thesis repositories worldwide.

This connector can be configured for any OAI-PMH compliant repository
via YAML configuration (config/genealogy/sources.yaml).

Reusable for 80% of global thesis repositories.
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import AsyncIterator, Dict, Any, List, Optional
from dataclasses import dataclass

NS_OAI = "{http://www.openarchives.org/OAI/2.0/}"
NS_DC = "{http://purl.org/dc/elements/1.1/}"

# Default institution keywords (English)
DEFAULT_INSTITUTION_KEYWORDS = [
    "university",
    "college",
    "institute",
    "school",
    "academy",
    "center",
    "centre",
    "laboratory",
    "department",
    "faculty",
]


@dataclass
class OaiConfig:
    """Configuration for OAI-PMH connector."""

    base_url: str
    rate_limit: float = 1.0
    set_spec: Optional[str] = None
    metadata_prefix: str = "oai_dc"
    institution_keywords: List[str] = None
    timeout: int = 60

    def __post_init__(self):
        if self.institution_keywords is None:
            self.institution_keywords = DEFAULT_INSTITUTION_KEYWORDS
        self.sleep = 1.0 / max(self.rate_limit, 0.1)


class GenericOaiConnector:
    """
    Generic OAI-PMH connector for thesis repositories.

    Configurable for any OAI-PMH compliant repository worldwide.
    Handles pagination, rate limiting, and metadata extraction.

    Usage:
        config = OaiConfig(
            base_url="https://theses.fr/oai/thesesfr/",
            rate_limit=2.0,
            set_spec="ddc:510",
            institution_keywords=["université", "école", "institut"]
        )
        connector = GenericOaiConnector(config)

        async for record in connector.records():
            print(record['title'], record['advisors_text'])
    """

    def __init__(self, config: OaiConfig):
        self.config = config
        self.records_harvested = 0
        self.errors = []

    async def records(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_records: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Yield records from OAI-PMH repository with automatic pagination.

        Args:
            date_from: Start date (YYYY-MM-DD format)
            date_to: End date (YYYY-MM-DD format)
            max_records: Maximum records to harvest (None = all)

        Yields:
            Dict with parsed thesis metadata (title, creators, advisors, etc.)
        """
        params = {"verb": "ListRecords", "metadataPrefix": self.config.metadata_prefix}

        if self.config.set_spec:
            params["set"] = self.config.set_spec
        if date_from:
            params["from"] = date_from
        if date_to:
            params["until"] = date_to

        resumption_token = None

        async with aiohttp.ClientSession() as session:
            while True:
                # Use resumption token if available (pagination)
                request_params = (
                    {"verb": "ListRecords", "resumptionToken": resumption_token}
                    if resumption_token
                    else params
                )

                try:
                    async with session.get(
                        self.config.base_url,
                        params=request_params,
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    ) as response:
                        response.raise_for_status()
                        xml_text = await response.text()
                        root = ET.fromstring(xml_text)

                        # Process all records in this batch
                        for record_elem in root.iter(f"{NS_OAI}record"):
                            # Check for deleted records
                            header = record_elem.find(f"{NS_OAI}header")
                            if header is None or header.get("status") == "deleted":
                                continue

                            # Extract metadata
                            metadata_elem = record_elem.find(f"{NS_OAI}metadata")
                            if metadata_elem is None:
                                continue

                            # Find Dublin Core element (or other metadata format)
                            dc_elem = metadata_elem.find(".//*")
                            if dc_elem is None:
                                continue

                            # Parse metadata to structured format
                            try:
                                parsed = self.parse_dublin_core(
                                    ET.tostring(dc_elem, encoding="unicode")
                                )
                                self.records_harvested += 1
                                yield parsed

                                # Check max_records limit
                                if (
                                    max_records
                                    and self.records_harvested >= max_records
                                ):
                                    return

                            except Exception as e:
                                self.errors.append(
                                    {
                                        "type": "parsing_error",
                                        "error": str(e),
                                        "record_num": self.records_harvested,
                                    }
                                )
                                continue

                        # Check for resumption token (more results available)
                        token_elem = root.find(f".//{NS_OAI}resumptionToken")
                        resumption_token = (
                            token_elem.text
                            if token_elem is not None and token_elem.text
                            else None
                        )

                        if not resumption_token:
                            break  # No more results

                except aiohttp.ClientError as e:
                    self.errors.append(
                        {
                            "type": "http_error",
                            "error": str(e),
                            "url": self.config.base_url,
                        }
                    )
                    break
                except ET.ParseError as e:
                    self.errors.append({"type": "xml_parse_error", "error": str(e)})
                    break

                # Rate limiting
                await asyncio.sleep(self.config.sleep)

    def parse_dublin_core(self, raw_xml: str) -> Dict[str, Any]:
        """
        Parse Dublin Core XML to structured thesis metadata.

        Extracts:
        - title: Thesis title
        - creators: Author(s) (usually PhD student)
        - date: Publication/defense date
        - publisher: Institution
        - advisors_text: Doctoral advisor names (from dc:contributor)

        Args:
            raw_xml: Raw Dublin Core XML string

        Returns:
            Dict with structured metadata
        """
        root = ET.fromstring(raw_xml)

        def first(tag: str) -> Optional[str]:
            """Get first occurrence of a DC tag."""
            elem = root.find(f"{NS_DC}{tag}")
            return elem.text.strip() if elem is not None and elem.text else None

        def all_values(tag: str) -> List[str]:
            """Get all occurrences of a DC tag."""
            return [
                elem.text.strip() for elem in root.findall(f"{NS_DC}{tag}") if elem.text
            ]

        title = first("title")
        creators = all_values("creator")
        date = first("date")
        publisher = first("publisher")

        # Extract advisors from dc:contributor fields
        # Strategy: Filter out institution names, keep person names
        contributors = all_values("contributor")
        advisors = self._extract_advisors_from_contributors(contributors)

        return {
            "title": title,
            "creators": creators,
            "date": date,
            "publisher": publisher,
            "advisors_text": advisors,
            "_raw_dc": raw_xml,
        }

    def _extract_advisors_from_contributors(self, contributors: List[str]) -> List[str]:
        """
        Filter dc:contributor to extract advisor names.

        Strategy:
        1. Check if contributor contains institution keywords
        2. If yes → likely institution, skip
        3. If no → likely person name (advisor), include

        Args:
            contributors: List of dc:contributor values

        Returns:
            List of likely advisor names (person names only)
        """
        advisors = []

        for contributor in contributors:
            if not contributor:
                continue

            contributor_lower = contributor.lower()

            # Check if this looks like an institution
            is_institution = any(
                keyword in contributor_lower
                for keyword in self.config.institution_keywords
            )

            if not is_institution:
                # Looks like a person name (advisor)
                advisors.append(contributor)

        return advisors

    def get_statistics(self) -> Dict[str, Any]:
        """Get harvest statistics."""
        return {
            "records_harvested": self.records_harvested,
            "errors": len(self.errors),
            "error_details": self.errors,
        }


class OaiConnectorFactory:
    """Factory to create OAI-PMH connectors from YAML config."""

    @staticmethod
    def from_yaml_config(source_config: Dict[str, Any]) -> GenericOaiConnector:
        """
        Create connector from YAML configuration.

        Args:
            source_config: Dict from sources.yaml

        Returns:
            Configured GenericOaiConnector instance
        """
        config = OaiConfig(
            base_url=source_config["base_url"],
            rate_limit=source_config.get("rate_limit", 1.0),
            set_spec=source_config.get("set_spec"),
            metadata_prefix=source_config.get("metadata_prefix", "oai_dc"),
            institution_keywords=source_config.get("institution_keywords"),
            timeout=source_config.get("timeout", 60),
        )

        return GenericOaiConnector(config)


# Convenience function for backward compatibility
def create_connector(
    base_url: str,
    rate_limit: float = 1.0,
    set_spec: Optional[str] = None,
    institution_keywords: Optional[List[str]] = None,
) -> GenericOaiConnector:
    """
    Create OAI-PMH connector with simple parameters.

    Args:
        base_url: OAI-PMH endpoint URL
        rate_limit: Requests per second
        set_spec: OAI-PMH set specification
        institution_keywords: List of institution keywords for filtering

    Returns:
        Configured GenericOaiConnector
    """
    config = OaiConfig(
        base_url=base_url,
        rate_limit=rate_limit,
        set_spec=set_spec,
        institution_keywords=institution_keywords,
    )

    return GenericOaiConnector(config)
