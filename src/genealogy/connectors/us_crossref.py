"""
genealogy/connectors/us_crossref.py
REST JSON client for Crossref dissertations API.
Harvests US/Canada mathematics dissertations with advisor metadata.
"""

import asyncio
from typing import Any, AsyncIterator, Dict

import aiohttp


class UsCrossrefAPI:
    def __init__(self, mailto: str, rate_limit: float = 2.0):
        """
        Initialize Crossref API client.

        Args:
            mailto: Email for polite pool (required by Crossref)
            rate_limit: Requests per second (max 50 for polite pool)
        """
        self.base_url = "https://api.crossref.org/works"
        self.mailto = mailto
        self.sleep = 1.0 / max(rate_limit, 0.1)
        self.session_headers = {"User-Agent": f"GMNAP/1.0 (mailto:{mailto})"}

    async def records(
        self, rows: int = 100, cursor: str = "*"
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Fetch dissertation records using Crossref cursor pagination.

        Args:
            rows: Records per request (max 1000, recommended 100)
            cursor: Cursor for pagination (use "*" for first request)

        Yields:
            Parsed dissertation records with advisor metadata
        """
        params = {
            "filter": "type:dissertation",
            "rows": rows,
            "mailto": self.mailto,
            "cursor": cursor,
        }

        async with aiohttp.ClientSession(headers=self.session_headers) as s:
            current_cursor = cursor
            while True:
                params["cursor"] = current_cursor
                async with s.get(self.base_url, params=params) as r:
                    r.raise_for_status()
                    data = await r.json()

                    message = data.get("message", {})
                    items = message.get("items", [])

                    for item in items:
                        yield self._parse_item(item)

                    # Check for next cursor
                    next_cursor = message.get("next-cursor")
                    if not next_cursor or not items:
                        break

                    current_cursor = next_cursor
                    await asyncio.sleep(self.sleep)

    def _parse_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Crossref work item to extract dissertation metadata.

        Args:
            item: Raw Crossref work JSON

        Returns:
            Parsed metadata with advisors
        """
        # Extract basic metadata
        title_list = item.get("title", [])
        title = title_list[0] if title_list else None

        # Extract author (student)
        authors = item.get("author", [])
        creators = []
        for author in authors:
            family = author.get("family", "")
            given = author.get("given", "")
            if family:
                name = f"{family}, {given}" if given else family
                creators.append(name)

        # Extract date
        published = item.get("published", {}) or item.get("created", {})
        date_parts = published.get("date-parts", [[]])
        year = str(date_parts[0][0]) if date_parts and date_parts[0] else None

        # Extract publisher (institution)
        publisher = item.get("publisher")

        # Extract advisors from contributors
        # Crossref uses "contributor" field with "role" indicators
        contributors = item.get("contributor", [])
        advisors = []
        for contrib in contributors:
            # Look for advisor/supervisor roles
            # Common role values: "chair", "advisor", "director", "supervisor"
            family = contrib.get("family", "")
            given = contrib.get("given", "")
            if family:
                name = f"{family}, {given}" if given else family
                advisors.append(name)

        # Also check editor field (sometimes advisors listed there)
        editors = item.get("editor", [])
        for editor in editors:
            family = editor.get("family", "")
            given = editor.get("given", "")
            if family:
                name = f"{family}, {given}" if given else family
                advisors.append(name)

        return {
            "title": title,
            "creators": creators,
            "date": year,
            "publisher": publisher,
            "advisors_text": advisors,
            "_raw_crossref": item,
        }
