
from __future__ import annotations
import os
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key


class OpenAlexAdapter:
    """OpenAlex authors search — publications, affiliations, ORCID.

    Free, no auth required. 864K/day (10/sec, polite pool with email).
    Endpoint: api.openalex.org/authors?search=
    Returns: OpenAlex ID, ORCID, institution, works count, h-index.
    """
    name = "OpenAlex"

    def __init__(self, cfg: Dict[str, Any] = None):
        base = (cfg or {}).get("base_url", "https://api.openalex.org")
        self.ctx = AuthorityContext(self.name, base, rps=8, burst=8, cache_ttl=86400)
        self.email = os.getenv("GMNAP_EMAIL", "gmnap@example.com")

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        name = entry.get("CanonicalLatin", "")
        if not name:
            return {"_source": {"service": self.name, "hit": False}}
        # Use /authors endpoint for author-level data
        q = {"search": name, "per_page": "1", "mailto": self.email}
        key = canonical_query_key({"svc": self.name, "q": q})
        cached = await self.ctx.cache.get_json(key)
        if cached is not None:
            return cached
        await self.ctx.limiter.acquire()
        url = f'{self.ctx.base_url}/authors?{urlencode(q)}'
        out = {"_source": {"service": self.name, "url": url}}
        try:
            if self.ctx.http:
                r = await self.ctx.http.get(url, timeout=15.0)
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("results") or []
                    if results:
                        author = results[0]
                        out["_source"]["hit"] = True
                        # OpenAlex ID
                        oa_id = author.get("id", "")
                        if oa_id:
                            out["OpenAlexID"] = oa_id.split("/")[-1]
                        # ORCID
                        orcid = author.get("orcid")
                        if orcid:
                            out["ORCID"] = orcid.split("/")[-1]
                        # Display name
                        display = author.get("display_name")
                        if display:
                            out["AlternativeLatin"] = [display]
                        # Works count
                        wc = author.get("works_count", 0)
                        if wc:
                            out["PublicationCount"] = wc
                        # Last known institution
                        last_inst = author.get("last_known_institutions") or []
                        if isinstance(last_inst, dict):
                            last_inst = [last_inst]
                        if last_inst:
                            inst = last_inst[0]
                            inst_name = inst.get("display_name")
                            if inst_name:
                                out["Institution"] = [inst_name]
                            cc = inst.get("country_code")
                            if cc:
                                out["InstitutionCountry"] = cc
                        # H-index from summary stats
                        summary = author.get("summary_stats") or {}
                        h = summary.get("h_index")
                        if h:
                            out["HIndex"] = h
        except Exception:
            pass
        await self.ctx.cache.set_json(key, out)
        return out
