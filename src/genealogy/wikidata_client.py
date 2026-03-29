from __future__ import annotations
import os, asyncio
from typing import List, Dict, Any, Optional
import httpx

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

P184_QUERY = """
SELECT ?student ?studentLabel ?advisor ?advisorLabel ?startTime ?instLabel
WHERE {
  ?student wdt:P106 wd:Q170790 .      # occupation: mathematician
  ?student wdt:P184 ?advisor .         # doctoral advisor
  OPTIONAL {
    ?student p:P184 ?st .
    ?st ps:P184 ?advisor .
    OPTIONAL { ?st pq:P580 ?startTime }     # start time qualifier
    OPTIONAL { ?st pq:P512 ?degree .
               ?degree wdt:P1027 ?inst . }  # conferred by
  }
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}
LIMIT {limit}
"""


class WikidataClient:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.rps = float(os.getenv("WIKIDATA_RPS", "4"))
        self.timeout = int(os.getenv("WIKIDATA_TIMEOUT_SEC", "30"))
        self._limiter = asyncio.Semaphore(int(self.rps))  # crude limiter across awaits

    async def get_advisors(
        self, name: str, birth_year: Optional[int]
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        # NOTE: For name-specific lookup you'd normally run a more selective SPARQL query
        # filtered by label and (optionally) birth year. Here we keep it simple: pull a page
        # and post-filter.
        query = P184_QUERY.format(limit=200)
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "GMNAP-Genealogy/1.0 (research; contact@example.com)",
        }

        async with self._limiter:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(
                        SPARQL_ENDPOINT, params={"query": query}, headers=headers
                    )
                    resp.raise_for_status()
                    data = resp.json()
            except Exception:
                return []

        def get_binding(v: Dict[str, Any], key: str) -> Optional[str]:
            b = v.get(key)
            return b.get("value") if b else None

        rows = data.get("results", {}).get("bindings", [])
        out: List[Dict[str, Any]] = []
        name_norm = (name or "").lower()
        for r in rows:
            student_name = (get_binding(r, "studentLabel") or "").lower()
            if name_norm and student_name != name_norm:
                continue  # post-filter by exact label in this simple client

            out.append(
                {
                    "advisor_name": get_binding(r, "advisorLabel"),
                    "advisor_id": get_binding(r, "advisor"),
                    "relation_type": "doctoralAdvisor",
                    "degree_date": get_binding(r, "startTime"),
                    "institution": get_binding(r, "instLabel"),
                    "confidence": 0.95,
                    "sources": ["Wikidata_P184"],
                }
            )
        return out
