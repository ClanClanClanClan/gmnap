from __future__ import annotations
import os, json, asyncio, pathlib, hashlib, zlib
from typing import Dict, Any, List

OFFLINE = os.getenv("OFFLINE", "1") == "1"
CACHE_DIR = pathlib.Path(os.getenv("GMNAP_CACHE_DIR", "./cache/authority")).resolve()


def _cache_key(namespace: str, payload: Dict[str, Any]) -> pathlib.Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps({"ns": namespace, "p": payload}, sort_keys=True).encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()
    return CACHE_DIR / f"{namespace}_{h}.json.zst"


def _cache_get(path: pathlib.Path) -> Dict | None:
    if path.exists():
        data = zlib.decompress(path.read_bytes())
        return json.loads(data.decode("utf-8"))
    return None


def _cache_set(path: pathlib.Path, obj: Dict) -> None:
    payload = zlib.compress(json.dumps(obj, sort_keys=True).encode("utf-8"), level=9)
    path.write_bytes(payload)


async def fetch_crossref_thesis(entry: Dict) -> Dict:
    # OFFLINE deterministic stub
    name = entry.get("CanonicalLatin", "")
    data = {"Crossref_Thesis": {"works": 0, "match": name.endswith("Thesis")}}
    return data


async def fetch_wikidata_p184(entry: Dict) -> Dict:
    # OFFLINE deterministic stub adds P184 edge if "AdvisorHint" is present
    edges = []
    for adv in entry.get("Advisors") or []:
        edges.append({"relation": "doctoralAdvisor", "target": adv, "confidence": 0.9})
    return {"Wikidata_P184": edges}


async def fetch_oai_university(entry: Dict) -> Dict:
    # OFFLINE deterministic stub
    return {"OAI_University": {"hit": False}}


async def fetch_hal(entry: Dict) -> Dict:
    return {"HAL": {"hit": False}}


async def fetch_gnd(entry: Dict) -> Dict:
    return {"GND": {"hit": False}}


async def fetch_zbmath(entry: Dict) -> Dict:
    return {"zbMATH_Open": {"hit": False}}


AUTH_HANDLERS = [
    ("Crossref_Thesis", fetch_crossref_thesis),
    ("Wikidata_P184", fetch_wikidata_p184),
    ("OAI_University", fetch_oai_university),
    ("HAL", fetch_hal),
    ("GND", fetch_gnd),
    ("zbMATH_Open", fetch_zbmath),
]


async def enrich_all(entries: List[Dict]) -> List[Dict]:
    out = []
    for e in entries:
        merged = dict(e)
        tasks = [h(e) for _, h in AUTH_HANDLERS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged["Sources"] = sorted(
            list({*(merged.get("Sources") or []), *[k for k, _ in AUTH_HANDLERS]})
        )
        # Merge advisor edges
        for (name, _), r in zip(AUTH_HANDLERS, results):
            if isinstance(r, dict) and name == "Wikidata_P184":
                edges = r.get("Wikidata_P184") or []
                if edges:
                    merged["Advisors"] = sorted(
                        list(
                            {
                                *(merged.get("Advisors") or []),
                                *[edge["target"] for edge in edges],
                            }
                        )
                    )
        out.append(merged)
    return out
