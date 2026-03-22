
from __future__ import annotations
import logging, os
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key

logger = logging.getLogger(__name__)

class GNDAdapter:
    name = "GND"
    def __init__(self, cfg: Dict[str, Any] = None):
        base_url = (cfg or {}).get("base_url", "https://lobid.org/gnd")
        self.ctx = AuthorityContext(self.name, base_url.rstrip("/"), rps=4, burst=4, cache_ttl=86400)
    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        if os.getenv("OFFLINE", "1") == "1":
            return {"_source": {"service": self.name, "hit": False}}
        q = {"q": entry.get("CanonicalLatin",""), "format":"json", "size":"1"}
        key = canonical_query_key({"svc": self.name, "q": q})
        cached = await self.ctx.cache.get_json(key)
        if cached is not None: return cached
        await self.ctx.limiter.acquire()
        url = f'{self.ctx.base_url}/search?{urlencode(q)}'
        out: Dict[str, Any] = {"_source": {"service": self.name, "url": url, "hit": False}}
        if not self.ctx.http:
            await self.ctx.cache.set_json(key, out)
            return out
        try:
            r = await self.ctx.http.get(url, timeout=15.0)
            if r.status_code != 200:
                logger.warning("GND returned %d for %s", r.status_code, entry.get("CanonicalLatin"))
                await self.ctx.cache.set_json(key, out)
                return out
            data = r.json()
            mem = (data.get("member") or [])
            if mem:
                m = mem[0]
                if m.get("preferredName"):
                    out["AlternativeLatin"] = [m["preferredName"]]
                if m.get("birthDate"):
                    try:
                        out["BirthYear"] = int(str(m["birthDate"])[:4])
                    except (ValueError, TypeError):
                        pass
                if m.get("deathDate"):
                    try:
                        out["DeathYear"] = int(str(m["deathDate"])[:4])
                    except (ValueError, TypeError):
                        pass
                out["_source"]["hit"] = True
        except Exception as exc:
            logger.debug("GND enrichment failed for %s: %s", entry.get("CanonicalLatin"), exc)
        await self.ctx.cache.set_json(key, out)
        return out
