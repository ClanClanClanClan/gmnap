from __future__ import annotations
import asyncio, json
from typing import Dict, Any, List
from connectors.base import load_sources
from connectors.oai_pmh import OaiPmhConnector
from connectors.rest_json import RestJsonConnector
from connectors.html_scraper import HtmlConnector
from connectors.sources.generic_mapper import map_oai_dc_xml


def connector_for(cfg: Dict[str, Any]):
    t = cfg["type"]
    if t == "oai_pmh":
        return OaiPmhConnector(cfg)
    if t == "rest_json":
        return RestJsonConnector(cfg)
    if t == "html":
        return HtmlConnector(cfg)
    raise ValueError(f"Unknown connector type: {t}")


async def harvest_one(key: str, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    conn = connector_for(cfg)
    out = []
    async for raw in conn.records():
        if "_raw_xml" in raw:
            th = map_oai_dc_xml(raw["_raw_xml"], cfg.get("country"), key)
        else:
            th = conn.to_thesis(raw)
        out.append(th)
    return out


async def main():
    sources = load_sources("config/sources.yml")
    results = []
    for key, cfg in sources.items():
        if not cfg.get("enabled"):
            continue
        if cfg.get("legal_blocked"):
            print(f"[SKIP/legal] {key}")
            continue
        print(f"[HARVEST] {key}")
        theses = await harvest_one(key, cfg)
        results.extend(theses)
    import os

    os.makedirs("data/out", exist_ok=True)
    with open("data/out/harvest.jsonl", "w", encoding="utf-8") as f:
        for th in results:
            f.write(json.dumps(th, ensure_ascii=False) + "\n")
    print(f"[DONE] harvested {len(results)} records -> data/out/harvest.jsonl")


if __name__ == "__main__":
    asyncio.run(main())
