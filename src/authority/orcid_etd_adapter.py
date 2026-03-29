from __future__ import annotations
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key


class ORCIDETDAdapter:
    name = "ORCID_ETD"

    def __init__(self, cfg: Dict[str, Any] = None):
        base = (cfg or {}).get("base_url", "https://pub.orcid.org/v3.0")
        self.ctx = AuthorityContext(self.name, base, rps=6, burst=6, cache_ttl=86400)

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        name = entry.get("CanonicalLatin", "")
        q = (
            {"q": f'given-names:{name.split(",")[-1].strip()}'}
            if "," in name
            else {"q": name}
        )
        key = canonical_query_key({"svc": self.name, "q": q})
        c = await self.ctx.cache.get_json(key)
        if c is not None:
            return c
        await self.ctx.limiter.acquire()
        url = f"{self.ctx.base_url}/expanded-search/?{urlencode(q)}"
        out = {"_source": {"service": self.name, "url": url}}
        await self.ctx.cache.set_json(key, out)
        return out
