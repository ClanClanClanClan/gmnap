from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlencode

from .common import AuthorityContext, canonical_query_key


class ZbMathOpenAdapter:
    name = "zbMATH"

    def __init__(self, cfg: Dict[str, Any]):
        base_url = cfg.get("base_url", "https://api.zbmath.org")
        self.ctx = AuthorityContext(
            self.name, base_url.rstrip("/"), rps=2, burst=2, cache_ttl=86400
        )

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        q = {"q": entry.get("CanonicalLatin", ""), "limit": "1"}
        key = canonical_query_key({"svc": self.name, "q": q})
        cached = await self.ctx.cache.get_json(key)
        if cached is not None:
            return cached
        await self.ctx.limiter.acquire()
        url = f"{self.ctx.base_url}/search?{urlencode(q)}"
        try:
            r = await self.ctx.http.get(url, timeout=15.0)
            data = r.json()
            out = {"_source": {"service": self.name, "url": url}}
            if isinstance(data, dict) and data.get("hits"):
                out["Publications"] = [f"zb:{data['hits'][0].get('id')}"]
        except Exception:
            out = {"_source": {"service": self.name, "url": url}}
        await self.ctx.cache.set_json(key, out)
        return out
