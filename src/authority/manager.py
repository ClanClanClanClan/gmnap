from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from .crossref_thesis_adapter import CrossrefThesisAdapter
from .oai_university_adapter import OAIUniversityAdapter
from .openalex_adapter import OpenAlexAdapter
from .orcid_etd_adapter import ORCIDETDAdapter
from .wikidata_p184_adapter import WikidataP184Adapter

try:
    from .merge_authority_data import merge_authority_fragments  # provided in Push 3
except Exception:
    # Fallback simple merger
    def merge_authority_fragments(
        frags: List[Dict[str, Any]], _=None
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for f in frags:
            for k, v in f.items():
                if k == "_source":
                    continue
                if isinstance(v, list):
                    out.setdefault(k, [])
                    for x in v:
                        if x not in out[k]:
                            out[k].append(x)
                else:
                    out[k] = out.get(k, v)
        return out


ADAPTERS = [
    OpenAlexAdapter,
    CrossrefThesisAdapter,
    ORCIDETDAdapter,
    WikidataP184Adapter,
    OAIUniversityAdapter,
]


async def enrich_all(
    entry: Dict[str, Any], cfg: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    tasks = []
    instances = [cls((cfg or {}).get(cls.__name__, {})) for cls in ADAPTERS]
    for inst in instances:
        tasks.append(inst.enrich(entry))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    fragments = []
    for r in results:
        if isinstance(r, Exception):
            continue
        if isinstance(r, dict):
            fragments.append(r)
    merged = merge_authority_fragments(fragments, None)
    merged["_sources"] = [f.get("_source", {}).get("service") for f in fragments]
    return merged
