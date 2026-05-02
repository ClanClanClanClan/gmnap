#!/usr/bin/env python3
"""Fetch mathematicians with doctoral-advisor chains from Wikidata.

Sister script to fetch_wikidata_mathematicians.py. That one grabs all
mathematicians with a country (10 k+ entries, no genealogy fields).
This one grabs only mathematicians who have P184 (doctoral advisor),
so every entry is immediately useful for building advisor chains, plus
best-effort P569 (birth date), P108 (employer) / P69 (educated at),
and the advisor's own metadata.

Output: data/wikidata_genealogy.json

    [
        {
            "person_qid": "Q7298",
            "CanonicalLatin": "Hilbert, David",
            "BirthYear": 1862,
            "DeathYear": 1943,
            "Country": "Germany",
            "Institutions": ["Universität Königsberg"],
            "Advisors": [
                {"qid": "Q76373", "name": "Lindemann, Ferdinand"},
                {"qid": "Q76376", "name": "Weber, Heinrich Martin"}
            ]
        },
        ...
    ]

Usage:
    python3 scripts/data/fetch_wikidata_genealogy.py [--limit N]

Be polite: 2 s sleep between pages, User-Agent set.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "GMNAP/1.0 (mathematician-name-project; dylan.possamai@math.ethz.ch)"
OUTPUT = Path("data/wikidata_genealogy.json")

# Query pulls one row per (person, advisor, institution) triple. We
# aggregate on the client side to collapse multiple advisors and
# institutions per person. Limiting to P184-bearing entities keeps the
# result set to a few-thousand rows — well under the 504-timeout
# threshold.
SPARQL_TEMPLATE = """
SELECT ?person ?personLabel ?dob ?dod ?countryLabel
       ?advisor ?advisorLabel ?institutionLabel
WHERE {{
  ?person wdt:P106 wd:Q170790 ;
          wdt:P184 ?advisor .
  OPTIONAL {{ ?person wdt:P569 ?dob . }}
  OPTIONAL {{ ?person wdt:P570 ?dod . }}
  OPTIONAL {{ ?person wdt:P27 ?country . }}
  OPTIONAL {{ ?person wdt:P69 ?institution . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT {limit}
OFFSET {offset}
"""

BATCH_SIZE = 2000


def to_canonical(name: str) -> str:
    """Convert 'First Last' → 'Last, First', strip parenthetical aliases.

    Matches the normalization conventions in tools/build_genealogy_enrichment.py.
    """
    if not name:
        return ""
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = re.sub(r"\s+", " ", name.strip())
    if "," in name:
        return name.strip(" ,")
    parts = name.split()
    if len(parts) < 2:
        return name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def _year(dt: str | None) -> int | None:
    """Extract 4-digit year from a Wikidata date literal (any era)."""
    if not dt:
        return None
    m = re.search(r"(-?)(\d{1,4})-\d\d-\d\d", dt)
    if not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    try:
        return sign * int(m.group(2))
    except ValueError:
        return None


def _label(binding: dict, key: str) -> str | None:
    """Pull the label text; drop raw QIDs that leaked past the label service."""
    if key not in binding:
        return None
    value = binding[key].get("value") or ""
    if not value:
        return None
    if re.fullmatch(r"Q\d+", value):
        return None  # unresolved QID
    return value


def fetch_all(limit: int | None = None) -> list[dict]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    collected: dict[str, dict] = {}
    offset = 0

    with httpx.Client(timeout=120) as client:
        while True:
            query = SPARQL_TEMPLATE.format(limit=BATCH_SIZE, offset=offset)
            print(f"  offset={offset}…", flush=True)
            # Retry on 504 — Wikidata's SPARQL endpoint sometimes
            # times out on deep-offset queries (the engine has to
            # skip N rows before returning the next batch). A single
            # retry usually succeeds because the cache warms up.
            rows = None
            for attempt in range(3):
                try:
                    r = client.get(
                        ENDPOINT,
                        params={"query": query, "format": "json"},
                        headers=headers,
                    )
                    r.raise_for_status()
                    rows = r.json()["results"]["bindings"]
                    break
                except Exception as exc:
                    print(
                        f"  attempt {attempt + 1}/3 at offset {offset}: {exc}",
                        file=sys.stderr,
                    )
                    if attempt < 2:
                        time.sleep(5 * (attempt + 1))
            if rows is None:
                print(
                    f"  exhausted retries at offset {offset}; stopping",
                    file=sys.stderr,
                )
                break

            if not rows:
                break

            for b in rows:
                person_uri = b.get("person", {}).get("value", "")
                qid = person_uri.rsplit("/", 1)[-1] if person_uri else ""
                if not qid:
                    continue
                person_label = _label(b, "personLabel")
                if not person_label:
                    continue
                canonical = to_canonical(person_label)
                entry = collected.setdefault(
                    qid,
                    {
                        "person_qid": qid,
                        "CanonicalLatin": canonical,
                        "BirthYear": _year(b.get("dob", {}).get("value")),
                        "DeathYear": _year(b.get("dod", {}).get("value")),
                        "Country": _label(b, "countryLabel"),
                        "Institutions": [],
                        "Advisors": [],
                    },
                )
                # Accumulate unique advisors
                adv_uri = b.get("advisor", {}).get("value", "")
                adv_qid = adv_uri.rsplit("/", 1)[-1] if adv_uri else ""
                adv_label = _label(b, "advisorLabel")
                if adv_qid and adv_label:
                    adv_entry = {
                        "qid": adv_qid,
                        "name": to_canonical(adv_label),
                    }
                    if adv_entry not in entry["Advisors"]:
                        entry["Advisors"].append(adv_entry)
                # Accumulate unique institutions
                inst_label = _label(b, "institutionLabel")
                if inst_label and inst_label not in entry["Institutions"]:
                    entry["Institutions"].append(inst_label)

            print(
                f"    rows={len(rows):4d}  cumulative people={len(collected)}",
                flush=True,
            )
            if limit is not None and len(collected) >= limit:
                break
            if len(rows) < BATCH_SIZE:
                break  # last page
            offset += BATCH_SIZE
            time.sleep(2)  # be polite

    # Drop entries that lost their advisor for any reason
    return [e for e in collected.values() if e["Advisors"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--limit", type=int, default=None, help="Stop after collecting N people"
    )
    args = ap.parse_args()

    print("Fetching mathematicians with doctoral-advisor data from Wikidata…")
    entries = fetch_all(limit=args.limit)
    print(f"Total unique people with advisors: {len(entries)}")

    # Stats
    with_birth = sum(1 for e in entries if e["BirthYear"])
    with_inst = sum(1 for e in entries if e["Institutions"])
    avg_adv = sum(len(e["Advisors"]) for e in entries) / len(entries) if entries else 0
    print(
        f"  with BirthYear: {with_birth}  with Institution: {with_inst}  "
        f"avg advisors/person: {avg_adv:.2f}"
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    print(f"Wrote {OUTPUT}  ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
