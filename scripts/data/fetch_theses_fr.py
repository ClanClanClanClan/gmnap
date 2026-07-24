#!/usr/bin/env python3
"""Fetch French mathematics doctoral theses (student→advisor edges) from theses.fr.

theses.fr is ABES' national doctoral-thesis registry. Its 2024 relaunch
exposes a JSON search API whose records carry, as STRUCTURED fields, the
author (auteurs) and the thesis advisor(s) (directeurs) — cleanly separated
from the jury (rapporteurs / examinateurs / president) — each with a PPN
(the SUDOC/IdRef persistent identifier). That makes every math thesis an
IdRef-disambiguated advisor edge, which is exactly the scarce signal the
genealogy graph needs. Licence: Etalab / Licence Ouverte 2.0 (attribution).

This is the theses.fr sibling of fetch_wikidata_genealogy.py. Where that one
harvests Wikidata P184 (QID-keyed), this one harvests theses.fr (PPN/IdRef-
keyed). The output shape mirrors data/wikidata_genealogy.json so the build
(tools/build_genealogy_enrichment.py) ingests it the same way — a
student-centric record whose Advisors carry the advisor's persistent id:

    [
      {
        "person_ppn": "260342378",
        "CanonicalLatin": "Vieira Costa Junior, Fernando",
        "DefenseYear": 2021,
        "Country": "FR",
        "Institution": "Université Clermont Auvergne",
        "Discipline": "Mathématiques",
        "nnt": "2021UCFAC022",
        "Advisors": [{"ppn": "070378304", "name": "Bayart, Frédéric"}]
      },
      ...
    ]

Only DEFENDED theses (status "soutenue") with at least one author AND one
advisor are kept — an in-preparation thesis is a provisional relationship,
and a record missing either endpoint yields no edge.

Usage:
    python3 scripts/data/fetch_theses_fr.py [--limit N] [--discipline "Mathématiques"]

Be polite: ~0.7 s between pages, descriptive User-Agent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

ENDPOINT = "https://theses.fr/api/v1/theses/recherche/"
USER_AGENT = "GMNAP/1.0 (mathematician-genealogy research; dylan.possamai@math.ethz.ch)"
OUTPUT = Path("data/theses_fr_math.json")

# Broad token match on the free-text discipline label: `discipline:Mathématiques`
# (unquoted) matches every discipline CONTAINING the token — "Mathématiques",
# "Mathématiques appliquées", "Mathématiques et applications", … — which is
# what we want (the labels are inconsistent free text; over-collect then let
# the math-genealogy consumer refine, rather than under-collect on an exact
# phrase). Measured 2026-07: ~18,635 hits.
DEFAULT_DISCIPLINE = "Mathématiques"
PAGE = 1000  # API accepts large pages; keeps the harvest to ~19 requests.


def _canonical(nom: str | None, prenom: str | None) -> str:
    """'Nom, Prenom' from the API's separate surname/given fields.

    theses.fr already splits surname (nom) and given (prenom), so we build
    the canonical "Surname, Given" form directly — no name-order guessing.
    """
    nom = (nom or "").strip()
    prenom = (prenom or "").strip()
    if nom and prenom:
        return f"{nom}, {prenom}"
    return nom or prenom


def _year(date_str: str | None) -> int | None:
    """Year from theses.fr's 'DD/MM/YYYY' (or ISO) defense date."""
    if not date_str:
        return None
    m = re.search(r"(\d{4})", date_str)
    return int(m.group(1)) if m else None


def _person(entry: dict) -> dict | None:
    """Normalize an auteur/directeur entry → {ppn?, canonical} or None."""
    if not isinstance(entry, dict):
        return None
    canonical = _canonical(entry.get("nom"), entry.get("prenom"))
    if not canonical:
        return None
    out = {"canonical": canonical}
    ppn = (entry.get("ppn") or "").strip()
    if ppn:
        out["ppn"] = ppn
    return out


def _to_record(these: dict) -> dict | None:
    """Map one theses.fr API record → our student-centric enrichment record.

    Returns None when the thesis is not a usable advisor edge (not defended,
    or missing an author or an advisor).
    """
    if (these.get("status") or "").lower() != "soutenue":
        return None
    auteurs = [p for p in (_person(a) for a in these.get("auteurs") or []) if p]
    directeurs = [p for p in (_person(d) for d in these.get("directeurs") or []) if p]
    if not auteurs or not directeurs:
        return None
    # A doctoral thesis has one author in practice; if the API ever lists
    # several, the first is the doctoral candidate.
    student = auteurs[0]
    # Dedup directeurs within the thesis: theses.fr occasionally lists the
    # same director twice (e.g. once with a PPN, once without). Key on the
    # lowercased name — consistent with the name-keyed downstream graph —
    # and keep/upgrade the PPN-bearing form so the person yields one edge.
    advisors: list[dict] = []
    by_name_seen: dict[str, dict] = {}
    for d in directeurs:
        nk = d["canonical"].lower()
        if nk in by_name_seen:
            if "ppn" in d and "ppn" not in by_name_seen[nk]:
                by_name_seen[nk]["ppn"] = d["ppn"]
            continue
        entry = (
            {"ppn": d["ppn"], "name": d["canonical"]}
            if "ppn" in d
            else {"name": d["canonical"]}
        )
        by_name_seen[nk] = entry
        advisors.append(entry)
    rec = {
        "CanonicalLatin": student["canonical"],
        "DefenseYear": _year(these.get("dateSoutenance")),
        "Country": "FR",
        "Institution": these.get("etabSoutenanceN"),
        "Discipline": these.get("discipline"),
        "nnt": these.get("nnt"),
        "Advisors": advisors,
    }
    if "ppn" in student:
        rec["person_ppn"] = student["ppn"]
    return rec


def fetch_all(discipline: str, limit: int | None = None) -> list[dict]:
    """Page through theses.fr for the given discipline, newest API order."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    q = f"discipline:{discipline}"
    records: list[dict] = []
    seen_nnt: set[str] = set()
    debut = 0
    total = None

    with httpx.Client(timeout=60, headers=headers, follow_redirects=True) as client:
        while True:
            params = {"q": q, "nombre": PAGE, "debut": debut}
            for attempt in range(3):
                try:
                    r = client.get(ENDPOINT, params=params)
                    r.raise_for_status()
                    payload = r.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"  page debut={debut} attempt {attempt + 1}/3: {exc}",
                        file=sys.stderr,
                    )
                    if attempt == 2:
                        payload = {"theses": []}
                    else:
                        time.sleep(3 * (attempt + 1))

            if total is None:
                total = payload.get("totalHits")
                print(f"  totalHits for '{q}': {total}")
            batch = payload.get("theses") or []
            if not batch:
                break

            kept = 0
            for these in batch:
                # Dedup on NNT (national thesis number) — the stable key.
                nnt = these.get("nnt")
                if nnt and nnt in seen_nnt:
                    continue
                if nnt:
                    seen_nnt.add(nnt)
                rec = _to_record(these)
                if rec:
                    records.append(rec)
                    kept += 1

            print(
                f"  debut={debut:6d}  fetched={len(batch):4d}  "
                f"kept={kept:4d}  cumulative_edges_records={len(records)}",
                flush=True,
            )

            debut += PAGE
            if limit is not None and len(records) >= limit:
                records = records[:limit]
                break
            if total is not None and debut >= total:
                break
            time.sleep(0.7)  # be polite

    return records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None, help="Stop after N records")
    ap.add_argument("--discipline", default=DEFAULT_DISCIPLINE)
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()

    print(f"Fetching '{args.discipline}' theses from theses.fr…")
    records = fetch_all(args.discipline, limit=args.limit)

    n_edges = sum(len(r["Advisors"]) for r in records)
    with_ppn = sum(1 for r in records if r.get("person_ppn"))
    adv_ppn = sum(1 for r in records for a in r["Advisors"] if a.get("ppn"))
    years = [r["DefenseYear"] for r in records if r.get("DefenseYear")]
    print(f"\nDefended math theses with an advisor edge: {len(records):,}")
    print(f"  advisor edges (student→director)        : {n_edges:,}")
    print(f"  students with an IdRef/PPN              : {with_ppn:,}")
    print(f"  advisor edges carrying an IdRef/PPN     : {adv_ppn:,}")
    if years:
        print(f"  defense-year range                     : {min(years)}–{max(years)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {args.output}  ({args.output.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
