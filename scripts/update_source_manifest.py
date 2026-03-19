#!/usr/bin/env python3
"""Update source manifest with current adapter status."""
import json
from pathlib import Path

ADAPTERS = {
    "OpenAlex": {"tier": 0, "status": "working"},
    "Crossref": {"tier": 0, "status": "working"},
    "ORCID_ETD": {"tier": 0, "status": "working"},
    "CrossrefThesis": {"tier": 0, "status": "working"},
    "HAL": {"tier": 1, "status": "working"},
    "GND": {"tier": 1, "status": "working"},
    "Wikidata_P184": {"tier": 1, "status": "working"},
    "OAI_University": {"tier": 1, "status": "working"},
    "zbMATH": {"tier": 1, "status": "working"},
    "MathSciNet": {"tier": 2, "status": "stub"},
    "Scopus": {"tier": 2, "status": "gated"},
    "Dimensions": {"tier": 2, "status": "gated"},
    "ProQuest": {"tier": 3, "status": "deferred"},
    "GoogleScholar": {"tier": 3, "status": "deferred"},
}

def main():
    out = Path("config/source_manifest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ADAPTERS, indent=2) + "\n")
    print(f"Source manifest written to {out}")

if __name__ == "__main__":
    main()
