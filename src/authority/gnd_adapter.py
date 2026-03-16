
from __future__ import annotations
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key

class GNDAdapter:
    name = "GND"
    def __init__(self, cfg: Dict[str, Any] = None):
        base_url = (cfg or {}).get("base_url", "https://lobid.org/gnd")
        self.ctx = AuthorityContext(self.name, base_url.rstrip("/"), rps=4, burst=4, cache_ttl=86400)
    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        q = {"q": entry.get("CanonicalLatin",""), "format":"json", "size":"1"}
        key = canonical_query_key({"svc": self.name, "q": q})
        cached = await self.ctx.cache.get_json(key)
        if cached is not None: return cached
        await self.ctx.limiter.acquire()
        url = f'{self.ctx.base_url}/search?{urlencode(q)}'
        try:
            r = await self.ctx.http.get(url, timeout=15.0)
            data = r.json()
            out = {"_source":{"service":self.name,"url":url}}
            mem = (data.get("member") or [])
            if mem:
                m = mem[0]
                if m.get("preferredName"):
                    out["AlternativeLatin"] = [m["preferredName"]]
                if m.get("birthDate"):
                    out["BirthYear"] = {"GND": int(str(m["birthDate"])[:4])}
                if m.get("deathDate"):
                    out["DeathYear"] = {"GND": int(str(m["deathDate"])[:4])}
        except Exception:
            out = {"_source":{"service":self.name,"url":url}}
        await self.ctx.cache.set_json(key, out)
        return out
