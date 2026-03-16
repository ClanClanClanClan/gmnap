
from __future__ import annotations
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key

class HALAdapter:
    name = "HAL"
    def __init__(self, cfg: Dict[str, Any] = None):
        base_url = (cfg or {}).get("base_url", "https://api.archives-ouvertes.fr")
        self.ctx = AuthorityContext(self.name, base_url.rstrip("/") + "/search", rps=4, burst=4, cache_ttl=86400)
    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        q = {"wt":"json","q": f'authFullName_t:"{entry.get("CanonicalLatin","")}"', "rows": 1}
        key = canonical_query_key({"svc": self.name, "q": q})
        cached = await self.ctx.cache.get_json(key)
        if cached is not None: return cached
        await self.ctx.limiter.acquire()
        url = f'{self.ctx.base_url}/?{urlencode(q)}'
        try:
            r = await self.ctx.http.get(url, timeout=15.0)
            data = r.json()
            out = {"_source":{"service":self.name,"url":url}}
            docs = (data.get("response") or {}).get("docs") or []
            if docs:
                labs = docs[0].get("authLabStructName_fs") or []
                if labs:
                    out["Institution"] = list(sorted({*(labs if isinstance(labs, list) else [labs])}))
        except Exception:
            out = {"_source":{"service":self.name,"url":url}}
        await self.ctx.cache.set_json(key, out)
        return out
