from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Optional

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseConnector


class HtmlConnector(BaseConnector):
    async def records(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        if not self._tos_allowed():
            return
        selectors = self.cfg.get("selectors", {})
        links_sel = selectors.get("item_link")
        async with aiohttp.ClientSession() as s:
            for url in self.cfg.get("listing_urls", []):
                await self.rate.wait()
                async with s.get(url, timeout=60) as r:
                    r.raise_for_status()
                    html = await r.text()
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select(links_sel or "a"):
                    yield {"_url": a.get("href"), "_html": html}
