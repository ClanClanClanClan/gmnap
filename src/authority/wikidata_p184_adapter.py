
from __future__ import annotations
import os
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key


class WikidataP184Adapter:
    """Wikidata SPARQL — doctoral advisor (P184) and student (P185) edges.

    Free, no auth required. Rate: ~2 req/sec recommended.
    Endpoint: query.wikidata.org/sparql
    Returns: advisor/student QIDs, birth/death years, ORCID.
    """
    name = "Wikidata_P184"

    def __init__(self, cfg: Dict[str, Any] = None):
        base = (cfg or {}).get("base_url", "https://query.wikidata.org/sparql")
        self.ctx = AuthorityContext(self.name, base, rps=2, burst=2, cache_ttl=86400)

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        nm = entry.get("CanonicalLatin", "")
        if not nm:
            return {"_source": {"service": self.name, "hit": False}}
        if os.getenv("OFFLINE", "1") == "1":
            return {"_source": {"service": self.name, "hit": False}}
        # Escape single quotes for SPARQL
        safe_name = nm.replace("'", "\\'")
        # SPARQL: find person by label, get advisors (P184) and students (P185)
        sparql = f"""
SELECT ?person ?personLabel ?advisor ?advisorLabel ?student ?studentLabel
       ?orcid ?birth ?death
WHERE {{
  ?person rdfs:label "{safe_name}"@en .
  OPTIONAL {{ ?person wdt:P184 ?advisor . }}
  OPTIONAL {{ ?person wdt:P185 ?student . }}
  OPTIONAL {{ ?person wdt:P496 ?orcid . }}
  OPTIONAL {{ ?person wdt:P569 ?birth . }}
  OPTIONAL {{ ?person wdt:P570 ?death . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}} LIMIT 10
""".strip()
        key = canonical_query_key({"svc": self.name, "q": sparql[:200]})
        c = await self.ctx.cache.get_json(key)
        if c is not None:
            return c
        await self.ctx.limiter.acquire()
        url = self.ctx.base_url
        out = {"_source": {"service": self.name, "url": url}}
        try:
            if self.ctx.http:
                r = await self.ctx.http.get(
                    url, timeout=20.0,
                    params={"query": sparql, "format": "json"},
                    headers={"Accept": "application/sparql-results+json",
                             "User-Agent": "GMNAP/7.0 (mailto:gmnap@example.com)"},
                )
                if r.status_code == 200:
                    data = r.json()
                    bindings = data.get("results", {}).get("bindings", [])
                    if bindings:
                        out["_source"]["hit"] = True
                        advisors = set()
                        students = set()
                        for b in bindings:
                            if "advisor" in b:
                                label = b.get("advisorLabel", {}).get("value", "")
                                if label:
                                    advisors.add(label)
                            if "student" in b:
                                label = b.get("studentLabel", {}).get("value", "")
                                if label:
                                    students.add(label)
                            if "orcid" in b:
                                out["ORCID"] = b["orcid"]["value"]
                            if "birth" in b:
                                bval = b["birth"]["value"]
                                try:
                                    out["BirthYear"] = int(bval[:4])
                                except (ValueError, IndexError):
                                    pass
                            if "death" in b:
                                dval = b["death"]["value"]
                                try:
                                    out["DeathYear"] = int(dval[:4])
                                except (ValueError, IndexError):
                                    pass
                        if advisors:
                            out["AdvisorNames"] = sorted(advisors)
                        if students:
                            out["StudentNames"] = sorted(students)
        except Exception:
            pass
        await self.ctx.cache.set_json(key, out)
        return out
