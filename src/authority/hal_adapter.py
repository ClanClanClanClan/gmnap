
from __future__ import annotations
import logging, os
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key, retry_with_backoff

logger = logging.getLogger(__name__)

class HALAdapter:
    name = "HAL"
    def __init__(self, cfg: Dict[str, Any] = None):
        base_url = (cfg or {}).get("base_url", "https://api.archives-ouvertes.fr")
        self.ctx = AuthorityContext(self.name, base_url.rstrip("/") + "/search", rps=4, burst=4, cache_ttl=86400)
    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        if os.getenv("OFFLINE", "1") == "1":
            return {"_source": {"service": self.name, "hit": False}}
        q = {"wt":"json","q": f'authFullName_t:"{entry.get("CanonicalLatin","")}"', "rows": 1}
        key = canonical_query_key({"svc": self.name, "q": q})
        cached = await self.ctx.cache.get_json(key)
        if cached is not None: return cached
        await self.ctx.limiter.acquire()
        url = f'{self.ctx.base_url}/?{urlencode(q)}'
        out: Dict[str, Any] = {"_source": {"service": self.name, "url": url, "hit": False}}
        if not self.ctx.http:
            await self.ctx.cache.set_json(key, out)
            return out
        try:
            r = await retry_with_backoff(lambda: self.ctx.http.get(url, timeout=15.0))
            if r.status_code != 200:
                logger.warning("HAL returned %d for %s", r.status_code, entry.get("CanonicalLatin"))
                await self.ctx.cache.set_json(key, out)
                return out
            data = r.json()
            docs = (data.get("response") or {}).get("docs") or []
            if docs:
                labs = docs[0].get("authLabStructName_fs") or []
                if labs:
                    sorted_labs = sorted({*(labs if isinstance(labs, list) else [labs])})
                    out["Institution"] = sorted_labs[0]
                    out["_InstitutionAll"] = sorted_labs
                    out["_source"]["hit"] = True
        except Exception as exc:
            logger.debug("HAL enrichment failed for %s: %s", entry.get("CanonicalLatin"), exc)
        await self.ctx.cache.set_json(key, out)
        return out
