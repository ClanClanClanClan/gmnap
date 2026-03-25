from __future__ import annotations
import os
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key


class OAIUniversityAdapter:
    """BASE (Bielefeld Academic Search Engine) — thesis metadata search.

    Free, no auth required. Rate: ~2 req/sec recommended.
    Endpoint: api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi
    Returns: thesis metadata, institution, degree date.
    """

    name = "OAI_University"

    def __init__(self, cfg: Dict[str, Any] = None):
        base = (cfg or {}).get(
            "base_url",
            "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi",
        )
        self.ctx = AuthorityContext(self.name, base, rps=2, burst=2, cache_ttl=86400)

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        name = entry.get("CanonicalLatin", "")
        if not name:
            return {"_source": {"service": self.name, "hit": False}}
        if os.getenv("OFFLINE", "1") == "1":
            return {"_source": {"service": self.name, "hit": False}}
        # BASE search: author name + doctoral thesis type
        q = {
            "func": "PerformSearch",
            "query": f'dcauthor:"{name}" AND dctype:Thesis',
            "format": "json",
            "hits": "3",
        }
        key = canonical_query_key({"svc": self.name, "q": q})
        c = await self.ctx.cache.get_json(key)
        if c is not None:
            return c
        await self.ctx.limiter.acquire()
        url = f"{self.ctx.base_url}?{urlencode(q)}"
        out = {"_source": {"service": self.name, "url": url}}
        try:
            if self.ctx.http:
                r = await self.ctx.http.get(url, timeout=15.0)
                if r.status_code == 200:
                    data = r.json()
                    response = data.get("response", {})
                    docs = response.get("docs") or []
                    if docs:
                        doc = docs[0]
                        out["_source"]["hit"] = True
                        # Extract title
                        title = doc.get("dctitle")
                        if title:
                            out["ThesisTitle"] = title if isinstance(title, str) else title[0]
                        # Extract institution/publisher
                        pub = doc.get("dcpublisher")
                        if pub:
                            inst = pub if isinstance(pub, str) else pub[0]
                            out["Institution"] = inst
                            out["_InstitutionAll"] = [inst]
                        # Extract year
                        year = doc.get("dcyear")
                        if year:
                            try:
                                # BASE API may return dcyear as list or string
                                year_val = year[0] if isinstance(year, list) else year
                                y = int(str(year_val)[:4])
                                out["DegreeDate"] = {"date": str(y), "precision": "year"}
                            except (ValueError, TypeError, IndexError):
                                pass
                        # DOI if available
                        doi = doc.get("dcidentifier")
                        if doi and isinstance(doi, str) and doi.startswith("10."):
                            out["ThesisDOI"] = doi
        except Exception:
            pass
        await self.ctx.cache.set_json(key, out)
        return out
