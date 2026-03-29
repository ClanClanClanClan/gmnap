#!/usr/bin/env python3
import os, asyncio, argparse, json
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from src.genealogy.authority_enricher import AuthorityEnricher


async def main(limit: int):
    enricher = AuthorityEnricher()
    # In real use, you'd load your processed DB. Here we mock minimal entries.
    demo_entries: List[Dict[str, Any]] = [
        {"GlobalID": "ID1", "CanonicalLatin": "Tao, Terence", "BirthYear": 1975},
        {"GlobalID": "ID2", "CanonicalLatin": "Hilbert, David", "BirthYear": 1862},
        {"GlobalID": "ID3", "CanonicalLatin": "Stein, Elias M.", "BirthYear": 1931},
    ][:limit]

    out = []
    for e in demo_entries:
        out.append(await enricher.enrich_entry(e, offline=os.getenv("OFFLINE") == "1"))
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()
    asyncio.run(main(args.limit))
