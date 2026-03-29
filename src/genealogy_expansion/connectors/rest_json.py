from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Optional

import aiohttp

from .base import BaseConnector


class RestJsonConnector(BaseConnector):
    async def records(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        if not self._tos_allowed():
            return
        base = self.cfg["base_url"]
        params = self.cfg.get("params", {}).copy()
        async with aiohttp.ClientSession() as s:
            next_url = base
            while next_url:
                await self.rate.wait()
                async with s.get(next_url, params=params, timeout=60) as r:
                    r.raise_for_status()
                    data = await r.json(content_type=None)
                    items = (
                        data.get("message", {}).get("items")
                        or data.get("items")
                        or data.get("results")
                        or []
                    )
                    for it in items:
                        yield {"_raw_json": it}
                    next_url = data.get("next") or None

    def to_thesis(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": None,
            "degree_type": None,
            "discipline": "Mathematics",
            "author_name": None,
            "author_birth_year": None,
            "defense_date": None,
            "institution": None,
            "country": self.cfg.get("country"),
            "advisors": [],
            "committee": [],
            "pdf_url": None,
            "source_id": None,
            "source_name": self.cfg.get("country") + "_REST",
            "raw": raw,
        }
