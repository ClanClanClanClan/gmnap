from __future__ import annotations
import os, asyncio, json
from typing import Dict, Any, List, Optional
from .wikidata_client import WikidataClient
from .mathgenealogy_client import MathGenealogyClient
from ..utils.caching import build_cache
from dateutil.parser import parse as dtparse


class AuthorityEnricher:
    def __init__(self):
        self.cache = build_cache()
        self.wikidata = WikidataClient(enabled=os.getenv("WIKIDATA_ENABLE") == "1")
        self.mathgen = MathGenealogyClient(
            enabled=os.getenv("MATHGEN_ENABLE") == "1",
            allow_scrape=os.getenv("ALLOW_MATHGEN_SCRAPE") == "explicit-yes",
        )

    async def enrich_entry(
        self, entry: Dict[str, Any], offline: bool = False
    ) -> Dict[str, Any]:
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative")
        byr = entry.get("BirthYear")
        cache_key = f"genealogy:{name}:{byr}"
        if cached := self.cache.get(cache_key):
            entry["Advisors"] = json.loads(cached)
            return entry

        advisors: List[Dict[str, Any]] = []

        if offline:
            advisors = self._stub_advisors(name)
        else:
            tasks = []
            if self.wikidata.enabled:
                tasks.append(self.wikidata.get_advisors(name=name, birth_year=byr))
            if self.mathgen.enabled:
                tasks.append(self.mathgen.get_advisors(name=name))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, list):
                        advisors.extend(r)

        # Normalize fields and assign confidence defaults
        norm = []
        for a in advisors:
            deg = a.get("degree_date")
            if isinstance(deg, str):
                try:
                    # normalize date to YYYY-MM-DD if possible
                    yr = dtparse(deg).date().isoformat()
                except Exception:
                    yr = deg
            else:
                yr = None
            norm.append(
                {
                    "advisor_name": a.get("advisor_name") or a.get("name"),
                    "advisor_id": a.get("advisor_id"),
                    "relation_type": a.get("relation_type", "doctoralAdvisor"),
                    "degree_date": yr,
                    "institution": a.get("institution"),
                    "birth_year": a.get("birth_year"),
                    "confidence": float(a.get("confidence", 0.90)),
                    "sources": a.get("sources", []),
                }
            )

        entry["Advisors"] = norm
        self.cache.setex(cache_key, 30 * 24 * 3600, json.dumps(norm))
        return entry

    def _stub_advisors(self, name: Optional[str]) -> List[Dict[str, Any]]:
        # Deterministic offline stub for smoke tests
        if not name:
            return []
        h = sum(ord(c) for c in name) % 3
        if h == 0:
            return []
        base = {
            "relation_type": "doctoralAdvisor",
            "degree_date": "1999-01-01",
            "institution": "Stub University",
            "confidence": 0.91,
            "sources": ["STUB"],
        }
        return [
            {
                **base,
                "advisor_name": f"Advisor {h}",
                "advisor_id": f"STUB-{h}",
                "birth_year": 1950 + 3 * h,
            }
        ]
