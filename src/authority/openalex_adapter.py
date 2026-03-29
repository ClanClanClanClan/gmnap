from __future__ import annotations
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key


class OpenAlexAdapter:
    name = "OpenAlex"

    def __init__(self, cfg: Dict[str, Any] = None):
        base = (cfg or {}).get("base_url", "https://api.openalex.org")
        self.ctx = AuthorityContext(self.name, base, rps=8, burst=8, cache_ttl=86400)

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        q = {"search": entry.get("CanonicalLatin", ""), "per_page": 1}
        key = canonical_query_key({"svc": self.name, "q": q})
        cached = await self.ctx.cache.get_json(key)
        if cached is not None:
            return cached
        await self.ctx.limiter.acquire()
        url = f"{self.ctx.base_url}/works?{urlencode(q)}"
        out = {"_source": {"service": self.name, "url": url}}
        # OFFLINE default; if httpx present & OFFLINE != "1", try a call
        try:
            import os

            if self.ctx.http and os.getenv("OFFLINE", "1") != "1":
                r = await self.ctx.http.get(url, timeout=15.0)
                if r.status_code == 200:
                    data = r.json()
                    # very light: stash a representative token
                    out["Publications"] = [
                        "openalex:" + str(data.get("meta", {}).get("count", 0))
                    ]
        except Exception:
            pass
        await self.ctx.cache.set_json(key, out)
        return out
