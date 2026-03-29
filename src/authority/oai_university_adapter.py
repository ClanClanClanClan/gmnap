from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlencode

from .common import AuthorityContext, canonical_query_key


class OAIUniversityAdapter:
    name = "OAI_University"

    def __init__(self, cfg: Dict[str, Any] = None):
        base = (cfg or {}).get("base_url", "https://example.edu/oai")
        self.ctx = AuthorityContext(self.name, base, rps=2, burst=2, cache_ttl=86400)

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        q = {"verb": "ListRecords", "metadataPrefix": "oai_dc", "from": "2000-01-01"}
        key = canonical_query_key({"svc": self.name, "q": q})
        c = await self.ctx.cache.get_json(key)
        if c is not None:
            return c
        await self.ctx.limiter.acquire()
        url = f"{self.ctx.base_url}?{urlencode(q)}"
        out = {"_source": {"service": self.name, "url": url}}
        await self.ctx.cache.set_json(key, out)
        return out
