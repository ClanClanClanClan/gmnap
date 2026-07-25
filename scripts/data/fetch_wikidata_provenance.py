#!/usr/bin/env python3
"""Harvest Wikidata STATEMENT-LEVEL provenance + degree facts for mathematicians.

Why this exists (R65). `fetch_wikidata_genealogy.py` queries only truthy
``wdt:`` statements, which by construction discard both qualifiers AND
references — so the citation behind every fact is thrown away, and with it the
single most important quality signal we have:

    ~97% of *referenced* Wikidata P184 (doctoral advisor) statements cite the
    Mathematics Genealogy Project.

That means most of the CC0 advisor graph is MGP at one remove. The maintainer's
trust rule is that MGP-derived claims must be vetted against an independent
source, so we must be able to TELL which Wikidata edges merely relay MGP. This
harvester reaches into the statement node (``p:``/``ps:``/``prov:``) to get it,
plus the degree/thesis/place facts the main harvest never requested.

Collected per person (keyed by QID), all optional:
  - ``advisor_refs``  {advisor_qid: "stated in" source label}  <- the vetting key
  - ``AcademicDegree`` (P512)  <- PhD vs Habilitation vs doctorat d'État vs
                                  Kandidat nauk; the degree-type gap
  - ``Thesis``         (P1026 doctoral thesis)
  - ``BirthPlace`` / ``DeathPlace`` (P19 / P20)

Output: data/wikidata_provenance.json — a SIDECAR. The main harvest file is not
touched, so this can be re-run independently and merged idempotently by
tools/build_genealogy_enrichment.py.

Partitioned by birth decade + a no-DOB bucket, mirroring the main harvest —
the statement-node joins are heavier than truthy ones, so a single global query
would 504.

Usage:
    python3 scripts/data/fetch_wikidata_provenance.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "GMNAP/1.0 (mathematician-genealogy research; dylan.possamai@math.ethz.ch)"
OUTPUT = Path("data/wikidata_provenance.json")

# Statement-node access: p:P184 -> ?stmt, then ps: for the value and
# prov:wasDerivedFrom -> pr:P248 for the "stated in" source.
SPARQL_DECADE = """
SELECT ?person ?advisor ?refSrcLabel ?degreeLabel ?thesisLabel
       ?birthPlaceLabel ?deathPlaceLabel
WHERE {{
  ?person wdt:P106 wd:Q170790 ;
          wdt:P569 ?dob ;
          p:P184 ?stmt .
  ?stmt ps:P184 ?advisor .
  FILTER(YEAR(?dob) >= {start} && YEAR(?dob) < {end})
  OPTIONAL {{ ?stmt prov:wasDerivedFrom ?ref . ?ref pr:P248 ?refSrc . }}
  OPTIONAL {{ ?person wdt:P512  ?degree . }}
  OPTIONAL {{ ?person wdt:P1026 ?thesis . }}
  OPTIONAL {{ ?person wdt:P19   ?birthPlace . }}
  OPTIONAL {{ ?person wdt:P20   ?deathPlace . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
"""

SPARQL_NO_DOB = """
SELECT ?person ?advisor ?refSrcLabel ?degreeLabel ?thesisLabel
       ?birthPlaceLabel ?deathPlaceLabel
WHERE {{
  ?person wdt:P106 wd:Q170790 ;
          p:P184 ?stmt .
  ?stmt ps:P184 ?advisor .
  FILTER NOT EXISTS {{ ?person wdt:P569 ?dob }}
  OPTIONAL {{ ?stmt prov:wasDerivedFrom ?ref . ?ref pr:P248 ?refSrc . }}
  OPTIONAL {{ ?person wdt:P512  ?degree . }}
  OPTIONAL {{ ?person wdt:P1026 ?thesis . }}
  OPTIONAL {{ ?person wdt:P19   ?birthPlace . }}
  OPTIONAL {{ ?person wdt:P20   ?deathPlace . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
ORDER BY ?person ?advisor
LIMIT {limit} OFFSET {offset}
"""

NO_DOB_PAGE = 5000
DECADE_PARTITIONS = [(s, s + 10) for s in range(1500, 2020, 10)]


def _qid(binding: dict, key: str) -> str | None:
    uri = (binding.get(key) or {}).get("value") or ""
    return uri.rsplit("/", 1)[-1] if uri else None


def _label(binding: dict, key: str) -> str | None:
    v = (binding.get(key) or {}).get("value") or ""
    v = v.strip()
    if not v or v.startswith("http"):
        return None
    return v


def _absorb(rows: list, collected: dict) -> None:
    """Merge SPARQL rows into the collected-by-QID dict. Idempotent."""
    for b in rows:
        pq = _qid(b, "person")
        if not pq:
            continue
        entry = collected.setdefault(pq, {"advisor_refs": {}})
        aq = _qid(b, "advisor")
        ref = _label(b, "refSrcLabel")
        if aq and ref:
            entry["advisor_refs"][aq] = ref
        for field, key in (
            ("AcademicDegree", "degreeLabel"),
            ("Thesis", "thesisLabel"),
            ("BirthPlace", "birthPlaceLabel"),
            ("DeathPlace", "deathPlaceLabel"),
        ):
            val = _label(b, key)
            if val and not entry.get(field):
                entry[field] = val


def _query(client: httpx.Client, query: str, headers: dict, *, label: str) -> list:
    for attempt in range(3):
        try:
            r = client.get(
                ENDPOINT, params={"query": query, "format": "json"}, headers=headers
            )
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as exc:  # noqa: BLE001
            print(f"  {label} attempt {attempt + 1}/3: {exc}", file=sys.stderr)
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    print(f"  {label}: exhausted retries; skipping bucket", file=sys.stderr)
    return []


def fetch_all(limit: int | None = None) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    collected: dict[str, dict] = {}
    with httpx.Client(timeout=180) as client:
        for start, end in DECADE_PARTITIONS:
            print(f"  decade=[{start},{end})…", end=" ", flush=True)
            rows = _query(
                client,
                SPARQL_DECADE.format(start=start, end=end),
                headers,
                label=f"decade {start}",
            )
            _absorb(rows, collected)
            print(f"rows={len(rows):5d}  people={len(collected)}", flush=True)
            if limit is not None and len(collected) >= limit:
                return collected
            time.sleep(2)

        offset = 0
        while True:
            print(f"  no-DOB offset={offset}…", end=" ", flush=True)
            rows = _query(
                client,
                SPARQL_NO_DOB.format(limit=NO_DOB_PAGE, offset=offset),
                headers,
                label=f"no-dob@{offset}",
            )
            _absorb(rows, collected)
            print(f"rows={len(rows):5d}  people={len(collected)}", flush=True)
            if len(rows) < NO_DOB_PAGE:
                break
            offset += NO_DOB_PAGE
            time.sleep(2)
    return collected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()

    print("Fetching Wikidata statement provenance + degree facts…")
    data = fetch_all(limit=args.limit)

    refs = sum(len(v.get("advisor_refs") or {}) for v in data.values())
    mgp = sum(
        1
        for v in data.values()
        for s in (v.get("advisor_refs") or {}).values()
        if "genealogy project" in s.lower()
    )
    print(f"\nPeople with P184 + provenance: {len(data):,}")
    print(f"  referenced advisor statements : {refs:,}")
    print(f"    of which cite MGP           : {mgp:,} ({100*mgp/max(refs,1):.1f}%)")
    for f in ("AcademicDegree", "Thesis", "BirthPlace", "DeathPlace"):
        print(f"  with {f:15}: {sum(1 for v in data.values() if v.get(f)):,}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Wrote {args.output}  ({args.output.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
