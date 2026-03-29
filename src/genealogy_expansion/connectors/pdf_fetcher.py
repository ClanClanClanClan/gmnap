from __future__ import annotations

from typing import Optional

import aiohttp


async def fetch_pdf_bytes(url: str, timeout: int = 45) -> Optional[bytes]:
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=timeout) as r:
            r.raise_for_status()
            ct = r.headers.get("content-type", "")
            if "pdf" not in ct.lower():
                return None
            return await r.read()
