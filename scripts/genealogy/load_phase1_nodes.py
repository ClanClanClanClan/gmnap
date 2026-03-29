#!/usr/bin/env python3
"""Load Phase 1 mathematician nodes into Memgraph."""

import os, json, asyncio
from pathlib import Path

# Add project root to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipeline.stage6_graph_consistency import populate_graph


async def main():
    # Load Phase 1 database
    db_path = "data/processed/mathematician_database.json"

    if not os.path.exists(db_path):
        print(f"❌ Phase 1 database not found at {db_path}")
        print("Run scripts/build_mathematician_database.py first")
        return

    print(f"📂 Loading Phase 1 database from {db_path}...")
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)

    entries = db.get("entries", [])
    print(f"✅ Loaded {len(entries)} mathematician entries")

    # No edges yet (will be added after Wikidata collection)
    edges = []

    print(f"🔗 Populating Memgraph with {len(entries)} nodes...")
    await populate_graph(
        entries=entries,
        edges=edges,
        compute_metrics=False,  # Skip metrics until we have edges
        batch_size=1000,
    )

    print(f"✅ Successfully loaded {len(entries)} mathematicians into Memgraph")
    print("\nNext steps:")
    print("1. Enable Wikidata: export WIKIDATA_ENABLE=1")
    print("2. Collect genealogy: python3 scripts/genealogy/collect_wikidata_p184.py")


if __name__ == "__main__":
    asyncio.run(main())
