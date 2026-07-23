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
# Partitioned-by-birth-decade query. Round 18's offset-paginated
# version stopped at 9,216 entries because the SPARQL endpoint 504s
# on offset >28k (the engine has to skip N rows). Partitioning sends
# each decade's slice as a separate query — every slice is small
# enough to complete, and we cover the full ~28k mathematicians-with-
# advisor population on Wikidata.
#
# Birth-year partitions go from 1500 to 2010 (50 decades). A separate
# fallback query handles entries WITHOUT a recorded P569 (date of
# birth) — those would otherwise be excluded by the FILTER.
SPARQL_DECADE = """
SELECT ?person ?personLabel ?dob ?dod ?countryLabel
       ?advisor ?advisorLabel ?institutionLabel
WHERE {{
  ?person wdt:P106 wd:Q170790 ;
          wdt:P184 ?advisor ;
          wdt:P569 ?dob .
  FILTER(YEAR(?dob) >= {start} && YEAR(?dob) < {end})
  OPTIONAL {{ ?person wdt:P570 ?dod . }}
  OPTIONAL {{ ?person wdt:P27 ?country . }}
  OPTIONAL {{ ?person wdt:P69 ?institution . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
"""

# Fallback for entries with no P569 (date of birth). These would
# otherwise be silently excluded by the decade FILTER.
#
# R62: PAGINATED. This was a single ``LIMIT 5000`` query, but live
# Wikidata has ~12,900 P184 advisor edges from ~10,900 no-DOB
# mathematicians — so the cap silently TRUNCATED ~8k real advisor edges
# (the bulk of the built-graph-vs-Wikidata coverage gap). ``ORDER BY``
# makes OFFSET pagination stable; the set is ~13k rows, well under the
# ~28k offset that caused the round-18 504 timeout, so a few pages is
# safe.
SPARQL_NO_DOB = """
SELECT ?person ?personLabel ?dob ?dod ?countryLabel
       ?advisor ?advisorLabel ?institutionLabel
WHERE {{
  ?person wdt:P106 wd:Q170790 ;
          wdt:P184 ?advisor .
  FILTER NOT EXISTS {{ ?person wdt:P569 ?dob }}
  OPTIONAL {{ ?person wdt:P570 ?dod . }}
  OPTIONAL {{ ?person wdt:P27 ?country . }}
  OPTIONAL {{ ?person wdt:P69 ?institution . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
ORDER BY ?person ?advisor
LIMIT {limit} OFFSET {offset}
"""

NO_DOB_PAGE = 5000

DECADE_PARTITIONS = [
    (start, start + 10) for start in range(1500, 2020, 10)
]  # (1500, 1510), …, (2010, 2020) = 52 buckets


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


def _absorb_rows(rows: list, collected: dict[str, dict]) -> None:
    """Merge SPARQL bindings into the collected-by-QID dict.

    Idempotent: re-running the same rows produces the same dict
    (advisor + institution lists are de-duped by content). Used by
    both the per-decade query and the no-DOB fallback.
    """
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
        adv_uri = b.get("advisor", {}).get("value", "")
        adv_qid = adv_uri.rsplit("/", 1)[-1] if adv_uri else ""
        adv_label = _label(b, "advisorLabel")
        if adv_qid and adv_label:
            adv_entry = {"qid": adv_qid, "name": to_canonical(adv_label)}
            if adv_entry not in entry["Advisors"]:
                entry["Advisors"].append(adv_entry)
        inst_label = _label(b, "institutionLabel")
        if inst_label and inst_label not in entry["Institutions"]:
            entry["Institutions"].append(inst_label)


def _query(client: "httpx.Client", query: str, headers: dict, *, label: str) -> list:
    """Run one SPARQL query with 3-attempt exponential backoff."""
    for attempt in range(3):
        try:
            r = client.get(
                ENDPOINT, params={"query": query, "format": "json"}, headers=headers
            )
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as exc:
            print(f"  {label} attempt {attempt + 1}/3: {exc}", file=sys.stderr)
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    print(f"  {label}: exhausted retries; skipping bucket", file=sys.stderr)
    return []


def fetch_all(limit: int | None = None) -> list[dict]:
    """Fetch the full P184-bearing mathematicians set from Wikidata.

    Round-23: partitioned by birth-decade (1500-2020) plus a no-DOB
    fallback bucket. Each bucket is a separate SPARQL query, small
    enough to avoid the 504 timeout that round-18's offset-paginated
    version hit at offset >28k.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    collected: dict[str, dict] = {}

    with httpx.Client(timeout=120) as client:
        for start, end in DECADE_PARTITIONS:
            print(f"  decade=[{start},{end})…", end=" ", flush=True)
            query = SPARQL_DECADE.format(start=start, end=end)
            rows = _query(client, query, headers, label=f"decade {start}")
            _absorb_rows(rows, collected)
            print(
                f"rows={len(rows):4d}  cumulative={len(collected)}",
                flush=True,
            )
            if limit is not None and len(collected) >= limit:
                break
            time.sleep(2)  # be polite

        # No-DOB fallback bucket (paginated — see SPARQL_NO_DOB comment)
        fetch_no_dob(client, headers, collected)

    # Drop entries that lost their advisor for any reason
    return [e for e in collected.values() if e["Advisors"]]


def fetch_no_dob(
    client: "httpx.Client", headers: dict, collected: dict[str, dict]
) -> None:
    """Absorb the FULL no-DOB advisor set into ``collected``, paginated.

    Reusable so a targeted refresh (R62) can recover the ~8k advisor edges
    the old single ``LIMIT 5000`` truncated, without re-running the 52
    decade queries.
    """
    offset = 0
    while True:
        print(f"  no-DOB offset={offset}…", end=" ", flush=True)
        query = SPARQL_NO_DOB.format(limit=NO_DOB_PAGE, offset=offset)
        rows = _query(client, query, headers, label=f"no-dob@{offset}")
        _absorb_rows(rows, collected)
        print(f"rows={len(rows):4d}  cumulative={len(collected)}", flush=True)
        if len(rows) < NO_DOB_PAGE:
            break
        offset += NO_DOB_PAGE
        time.sleep(2)


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
