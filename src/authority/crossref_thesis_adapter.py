from __future__ import annotations
import os
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key


class CrossrefThesisAdapter:
    """Crossref dissertation search — thesis DOIs and degree dates.

    Free, no auth required. 4.3M/day polite pool (with email in User-Agent).
    Endpoint: api.crossref.org/works?filter=type:dissertation
    Returns: thesis DOI, degree date, institution.
    """

    name = "CrossrefThesis"

    def __init__(self, cfg: Dict[str, Any] = None):
        base = (cfg or {}).get("base_url", "https://api.crossref.org")
        self.ctx = AuthorityContext(self.name, base, rps=8, burst=8, cache_ttl=86400)
        self.email = os.getenv("GMNAP_EMAIL", "gmnap@example.com")

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        name = entry.get("CanonicalLatin", "")
        if not name:
            return {"_source": {"service": self.name, "hit": False}}
        if os.getenv("GMNAP_NO_NETWORK", "") == "1":
            return {"_source": {"service": self.name, "hit": False}}
        q = {
            "query.author": name,
            "rows": "3",
            "filter": "type:dissertation",
            "select": "DOI,title,author,institution,created",
            "mailto": self.email,
        }
        key = canonical_query_key({"svc": self.name, "q": q})
        c = await self.ctx.cache.get_json(key)
        if c is not None:
            return c
        await self.ctx.limiter.acquire()
        url = f"{self.ctx.base_url}/works?{urlencode(q)}"
        out = {"_source": {"service": self.name, "url": url}}
        try:
            if self.ctx.http:
                r = await self.ctx.http.get(url, timeout=15.0)
                if r.status_code == 200:
                    data = r.json()
                    items = (data.get("message") or {}).get("items") or []
                    if items:
                        item = items[0]
                        doi = item.get("DOI", "")
                        if doi:
                            out["ThesisDOI"] = doi
                        # Extract degree date from 'created' date-parts
                        created = item.get("created", {})
                        dp = created.get("date-parts", [[]])[0]
                        if dp and len(dp) >= 1:
                            year = str(dp[0])
                            if len(dp) >= 2:
                                out["DegreeDate"] = {
                                    "date": f"{dp[0]}-{dp[1]:02d}",
                                    "precision": "month",
                                }
                            else:
                                out["DegreeDate"] = {"date": year, "precision": "year"}
                        # Institution
                        inst = item.get("institution")
                        if inst:
                            names = [i.get("name") for i in inst if i.get("name")]
                            if names:
                                out["Institution"] = names[0]
                                out["_InstitutionAll"] = names[:3]
                        out["_source"]["hit"] = True
        except Exception:
            pass
        await self.ctx.cache.set_json(key, out)
        return out
