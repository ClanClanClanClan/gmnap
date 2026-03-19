
from __future__ import annotations
import os
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key


class CrossrefAdapter:
    """Crossref generic works search — DOIs, co-authors, publication venues.

    Free, no auth required. 4.3M/day polite pool (with mailto in query).
    Endpoint: api.crossref.org/works?query.author=
    Returns: DOIs, publication count, co-author names, venue names.
    """
    name = "Crossref"

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
            "rows": "5",
            "select": "DOI,title,author,container-title,subject,created",
            "mailto": self.email,
        }
        key = canonical_query_key({"svc": self.name, "q": q})
        c = await self.ctx.cache.get_json(key)
        if c is not None:
            return c
        await self.ctx.limiter.acquire()
        url = f'{self.ctx.base_url}/works?{urlencode(q)}'
        out = {"_source": {"service": self.name, "url": url}}
        try:
            if self.ctx.http:
                r = await self.ctx.http.get(url, timeout=15.0)
                if r.status_code == 200:
                    data = r.json()
                    msg = data.get("message", {})
                    items = msg.get("items") or []
                    total = msg.get("total-results", 0)
                    if items:
                        out["_source"]["hit"] = True
                        out["PublicationCount"] = total
                        # Collect unique DOIs
                        dois = [it.get("DOI") for it in items if it.get("DOI")]
                        if dois:
                            out["DOIs"] = dois[:5]
                        # Collect unique co-authors (across all items)
                        coauthors = set()
                        for it in items:
                            for auth in (it.get("author") or []):
                                family = auth.get("family", "")
                                given = auth.get("given", "")
                                if family:
                                    full = f"{family}, {given}".strip(", ")
                                    coauthors.add(full)
                        # Remove the queried author
                        coauthors.discard(name)
                        if coauthors:
                            out["CoAuthors"] = sorted(coauthors)[:10]
                        # Collect subjects / MSC-like topics
                        subjects = set()
                        for it in items:
                            for s in (it.get("subject") or []):
                                subjects.add(s)
                        if subjects:
                            out["Subjects"] = sorted(subjects)[:10]
                        # Primary venue
                        venues = set()
                        for it in items:
                            ct = it.get("container-title") or []
                            if ct:
                                venues.add(ct[0] if isinstance(ct, list) else ct)
                        if venues:
                            out["Venues"] = sorted(venues)[:5]
        except Exception:
            pass
        await self.ctx.cache.set_json(key, out)
        return out
