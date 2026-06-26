from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from dateutil.parser import parse as dtparse

from ..utils.caching import build_cache
from .mathgenealogy_client import MathGenealogyClient
from .wikidata_client import WikidataClient


class GenealogyAuthorityEnricher:
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
            # Prefer curated real data over the fake smoke-test stub; the
            # stub was leaking 'Advisor 1'/'STUB-1' placeholders into real
            # pipeline output.
            advisors = self._curated_advisors(name) or self._stub_advisors(name)
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

    def _curated_advisors(self, name: Optional[str]) -> List[Dict[str, Any]]:
        """Return real advisors from data/genealogy_enrichment.json if any."""
        if not name:
            return []
        try:
            from src.core.genealogy_lookup import GenealogyLookup

            record = GenealogyLookup().lookup_by_name(name)
        except Exception:
            return []
        if not record:
            return []
        advisors = record.get("Advisors") or []
        normalized: List[Dict[str, Any]] = []
        for a in advisors:
            if isinstance(a, dict):
                adv_name = a.get("name") or a.get("advisor_name")
                adv_id = str(a.get("mgp_id") or a.get("advisor_id") or "")
            else:
                adv_name = str(a)
                adv_id = ""
            if not adv_name:
                continue
            normalized.append(
                {
                    "advisor_name": adv_name,
                    "advisor_id": adv_id,
                    "relation_type": "doctoralAdvisor",
                    "degree_date": record.get("ThesisYear"),
                    "institution": record.get("Institution"),
                    "birth_year": None,
                    "confidence": 0.95,
                    "sources": [record.get("Source", "curated")],
                }
            )
        return normalized

    def _stub_advisors(self, name: Optional[str]) -> List[Dict[str, Any]]:
        """Deprecated smoke-test stub.

        Kept only as a final fallback for legacy tests that explicitly rely
        on a deterministic non-empty advisor list for random names. Returns
        an empty list by default; set GMNAP_OFFLINE_STUB_ADVISORS=1 to
        re-enable the old 'Advisor 1 / STUB-1' placeholder behavior.
        """
        if not name or os.getenv("GMNAP_OFFLINE_STUB_ADVISORS") != "1":
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
