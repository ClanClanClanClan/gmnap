"""
genealogy/connectors/wikidata_p184.py
Bulk Wikidata P184 (doctoral advisor) relationship harvester.

Designed for mass harvesting of academic genealogy relationships from Wikidata.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

import httpx

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"


@dataclass
class WikidataP184Config:
    """Configuration for Wikidata P184 harvester."""

    endpoint: str = SPARQL_ENDPOINT
    rate_limit: float = 0.5  # Conservative for public endpoint
    timeout: int = 60
    batch_size: int = 10000  # Records per query
    user_agent: str = "GMNAP-Genealogy/1.0 (research; genealogy@gmnap.org)"


class WikidataP184Connector:
    """
    Bulk harvester for Wikidata P184 (doctoral advisor) relationships.

    Harvests all doctoral advisor relationships from Wikidata, focusing on:
    - Mathematicians (Q170790)
    - Computer scientists (Q81096)
    - Statisticians (Q593644)
    - Physicists (Q169470)
    - Other STEM fields with doctoral relationships
    """

    def __init__(self, config: WikidataP184Config = None):
        self.config = config or WikidataP184Config()
        self.records_harvested = 0
        self.errors = []

    async def records(
        self, max_records: Optional[int] = None, occupations: list = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Yield doctoral advisor relationships from Wikidata.

        Args:
            max_records: Maximum records to harvest (None = all)
            occupations: List of occupation Q-codes (default: mathematicians + STEM)

        Yields:
            Dict with student, advisor, and relationship metadata
        """
        if occupations is None:
            # Default: Mathematics and related fields
            occupations = [
                "Q170790",  # mathematician
                "Q81096",  # computer scientist
                "Q593644",  # statistician
                "Q169470",  # physicist
                "Q350979",  # applied mathematician
                "Q13570226",  # theoretical physicist
            ]

        # Build SPARQL query for bulk harvest
        query = self._build_bulk_query(occupations, self.config.batch_size)

        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": self.config.user_agent,
        }

        offset = 0
        sleep_time = 1.0 / self.config.rate_limit

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            while True:
                # Execute paginated query
                paginated_query = f"{query}\nOFFSET {offset}"

                try:
                    print(f"  Querying Wikidata: offset {offset}...")

                    response = await client.get(
                        self.config.endpoint,
                        params={"query": paginated_query},
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()

                    bindings = data.get("results", {}).get("bindings", [])

                    if not bindings:
                        print(f"  No more results at offset {offset}")
                        break

                    # Process results
                    for binding in bindings:
                        record = self._parse_binding(binding)
                        if record:
                            self.records_harvested += 1
                            yield record

                            if max_records and self.records_harvested >= max_records:
                                return

                    # Check if we got fewer results than batch size (last page)
                    if len(bindings) < self.config.batch_size:
                        print(f"  Last page reached ({len(bindings)} results)")
                        break

                    offset += self.config.batch_size

                except httpx.TimeoutException:
                    error = f"Timeout at offset {offset}"
                    print(f"  ⚠️  {error}")
                    self.errors.append({"type": "timeout", "offset": offset})
                    break  # Wikidata timeouts are hard to recover from

                except httpx.HTTPStatusError as e:
                    error = f"HTTP {e.response.status_code} at offset {offset}"
                    print(f"  ⚠️  {error}")
                    self.errors.append(
                        {
                            "type": "http_error",
                            "status": e.response.status_code,
                            "offset": offset,
                        }
                    )
                    break

                except Exception as e:
                    error = f"Error at offset {offset}: {str(e)}"
                    print(f"  ❌ {error}")
                    self.errors.append(
                        {"type": "unknown_error", "error": str(e), "offset": offset}
                    )
                    break

                # Rate limiting
                await asyncio.sleep(sleep_time)

    def _build_bulk_query(self, occupations: list, limit: int) -> str:
        """
        Build SPARQL query for bulk harvesting.

        Args:
            occupations: List of Wikidata occupation Q-codes
            limit: Maximum results per page

        Returns:
            SPARQL query string
        """
        # Build occupation filter
        occupation_filter = " || ".join(
            [f"?occupation = wd:{qid}" for qid in occupations]
        )

        query = f"""
SELECT DISTINCT
  ?student ?studentLabel
  ?advisor ?advisorLabel
  ?startTime
  ?degree ?degreeLabel
  ?institution ?institutionLabel
  ?occupation ?occupationLabel
WHERE {{
  # Person has doctoral advisor
  ?student wdt:P184 ?advisor .

  # Person has an occupation of interest
  ?student wdt:P106 ?occupation .
  FILTER({occupation_filter})

  # Optional: Get additional metadata
  OPTIONAL {{
    ?student p:P184 ?statement .
    ?statement ps:P184 ?advisor .

    # Start time (degree date)
    OPTIONAL {{ ?statement pq:P580 ?startTime }}

    # Academic degree
    OPTIONAL {{ ?statement pq:P512 ?degree }}

    # Conferred by (institution)
    OPTIONAL {{ ?statement pq:P1027 ?institution }}
  }}

  # Get labels in English
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr,de,es". }}
}}
LIMIT {limit}
"""
        return query

    def _parse_binding(self, binding: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse SPARQL result binding to structured record.

        Args:
            binding: SPARQL result binding

        Returns:
            Structured record dict, or None if invalid
        """

        def get_value(key: str) -> Optional[str]:
            """Extract value from binding."""
            item = binding.get(key, {})
            return item.get("value") if item else None

        def get_label(key: str) -> Optional[str]:
            """Extract label from binding."""
            return get_value(f"{key}Label")

        student = get_label("student")
        advisor = get_label("advisor")

        # Must have both student and advisor
        if not student or not advisor:
            return None

        # Parse date if available
        start_time = get_value("startTime")
        date = None
        if start_time:
            # Extract year from ISO date (e.g., "1990-06-15T00:00:00Z" -> "1990")
            date = start_time[:4] if len(start_time) >= 4 else start_time

        return {
            "title": f"Doctoral studies of {student}",  # Synthetic title
            "creators": [student],
            "date": date,
            "publisher": get_label("institution"),
            "advisors_text": [advisor],
            "occupation": get_label("occupation"),
            "degree": get_label("degree"),
            "student_uri": get_value("student"),
            "advisor_uri": get_value("advisor"),
            "source": "wikidata_p184",
            "_wikidata_p184": True,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get harvest statistics."""
        return {
            "records_harvested": self.records_harvested,
            "errors": len(self.errors),
            "error_details": self.errors,
        }


# Convenience function
def create_connector(
    rate_limit: float = 0.5, timeout: int = 60
) -> WikidataP184Connector:
    """
    Create Wikidata P184 connector.

    Args:
        rate_limit: Requests per second (default: 0.5 for public endpoint)
        timeout: HTTP timeout in seconds

    Returns:
        Configured WikidataP184Connector
    """
    config = WikidataP184Config(rate_limit=rate_limit, timeout=timeout)
    return WikidataP184Connector(config)
