#!/usr/bin/env python3
"""Decide PRE-1985 French doctorate types from Sudoc (ABES), by exact IdRef.

THE PROBLEM. Before the 1984 reform France ran several parallel doctorates —
*doctorat d'État*, *doctorat de 3e cycle*, *doctorat d'université*, *doctorat
d'ingénieur* — and a mathematician routinely held TWO of them, years apart,
under DIFFERENT advisors (Brézis: 3e cycle 1966 under Choquet, doctorat d'État
1972 under Lions). theses.fr starts at 1985, so nothing we already hold can
tell them apart. That is exactly why ~657 French advisor edges sit in REVIEW:
`tools/vetting_risk.py` cannot AFFIRM which doctorate an edge belongs to.

THE JOIN — exact, never by name. Wikidata **P269** is the IdRef/SUDOC
authority PPN, and UNIMARC ``$3`` on 700/701/702 is the same identifier. So a
person we hold a QID for resolves into Sudoc with zero name matching.
Measured: 90.1% of our French people carry a P269.

WHY NO NAME MATCHING, EVER. On the real French advisor population 9.9% of
surnames map to more than one actual person, covering 23.4% of the target
edges — `lions` is Jacques-Louis AND Pierre-Louis (father and son, same field,
overlapping years); `meyer` and `berger` are eight people each; even
"Surname, Given" is not a function (69 keys map to >1 PPN). A name match here
would mint FALSE independent corroboration, which is the one thing this graph
must never do.

WHAT WE EMIT. Per person PPN: the list of their pre-1985 thesis records, each
with degree type / year / institution / title. The decisive signal for the
risk model is the COUNT:
  * exactly one pre-1985 doctorate -> unambiguous; the advisor edge can only
    refer to that one, so the edge is decidable.
  * two or more -> the Brézis pattern. Still not TRUST, but now it is a KNOWN
    multi-degree case rather than an unexplained REVIEW, and it is precisely
    where MGP tends to flatten two sequential advisors into "co-advisors".

Output: data/sudoc_thesis_types.json  (sidecar; the build merges it).

Licence: ABES data under the Etalab Licence Ouverte — cite source + retrieval
date. Be polite: 0.6 s between calls, descriptive User-Agent.

Usage:
    python3 scripts/data/fetch_sudoc_thesis_types.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

SRU = "https://www.sudoc.abes.fr/cbs/sru/"
IDREF_BIBLIO = "https://www.idref.fr/services/biblio/{ppn}.xml"
USER_AGENT = "GMNAP/1.0 (mathematician-genealogy research; dylan.possamai@math.ethz.ch)"
OUTPUT = Path("data/sudoc_thesis_types.json")
PROVENANCE = Path("data/wikidata_provenance.json")

# UNIMARC non-sorting control characters bracket the sort-ignored article in
# titles ("\x98Les \x9copérateurs monotones"). They must be stripped.
_CTRL = re.compile(r"[\x00-\x1f\x80-\x9f]")

# Degree-type normalisation. Sudoc 328$b is free text with real orthographic
# drift ("Thèse d'Etat" / "Thèse d'état" / "Thèse Etat"), so match on a folded
# form. Order matters: 3e cycle must be tested before the bare "thèse".
DEGREE_PATTERNS: list[tuple[str, str]] = [
    (r"3\s*e?\s*cycle|troisieme cycle", "doctorat_3e_cycle"),
    (r"docteur[- ]ingenieur|doctorat d ingenieur", "doctorat_ingenieur"),
    (r"d\s*etat|d etat", "doctorat_etat"),
    (r"d\s*universite|d universite", "doctorat_universite"),
    (r"habilitation", "habilitation"),
    (r"nouveau regime|doctorat unique", "doctorat_unifie"),
]


def _fold(text: str) -> str:
    """Lowercase, strip accents and punctuation — for pattern matching only."""
    import unicodedata

    t = unicodedata.normalize("NFD", text or "").lower()
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def classify_degree(raw: str) -> str | None:
    """Map a raw Sudoc 328$b string to our controlled degree token."""
    folded = _fold(raw)
    if not folded:
        return None
    for pattern, token in DEGREE_PATTERNS:
        if re.search(pattern, folded):
            return token
    if "these" in folded or "doctorat" in folded:
        return "doctorat_unspecified"
    return None


def _year(text: str | None) -> int | None:
    m = re.search(r"(1[5-9]\d\d|20\d\d)", text or "")
    return int(m.group(1)) if m else None


def parse_record(rec: ET.Element) -> dict | None:
    """Extract the thesis facts from one UNIMARC record."""
    out: dict = {}
    for df in rec.iter():
        tag = df.get("tag") if df.tag.endswith("datafield") else None
        if tag == "328":
            subs = {
                sf.get("code"): (sf.text or "")
                for sf in df
                if sf.tag.endswith("subfield")
            }
            raw = subs.get("b") or subs.get("a") or ""
            out["degree_raw"] = _CTRL.sub("", raw).strip()
            out["degree"] = classify_degree(raw or subs.get("a", ""))
            out["discipline"] = _CTRL.sub("", subs.get("c", "")).strip() or None
            out["institution"] = _CTRL.sub("", subs.get("e", "")).strip() or None
            out["year"] = _year(subs.get("d") or subs.get("a"))
        elif tag == "200":
            subs = {
                sf.get("code"): (sf.text or "")
                for sf in df
                if sf.tag.endswith("subfield")
            }
            if subs.get("a"):
                out["title"] = _CTRL.sub("", subs["a"]).strip()
    for cf in rec.iter():
        if cf.tag.endswith("controlfield") and cf.get("tag") == "001":
            out["ppn"] = (cf.text or "").strip()
    return out if out.get("degree") or out.get("year") else None


def sudoc_records_for(client: httpx.Client, ppn: str) -> list[dict]:
    """Every thesis record where this person is the AUTHOR ($4 070).

    Uses the IdRef `biblio` service, which returns records grouped by role and
    is deduplicated (the `references` service is not — 154 raw links vs 40
    unique records for the same person).
    """
    try:
        r = client.get(IDREF_BIBLIO.format(ppn=ppn))
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
    except Exception as exc:  # noqa: BLE001
        print(f"  idref {ppn}: {exc}", file=sys.stderr)
        return []
    # Collect the record PPNs where this person is the author (role 070).
    rec_ppns: list[str] = []
    for elem in root.iter():
        if elem.tag.endswith("result") or elem.tag.endswith("row"):
            text = ET.tostring(elem, encoding="unicode")
            if "070" not in text:
                continue
        if elem.tag.endswith("ppn") and elem.text:
            rec_ppns.append(elem.text.strip())
    out: list[dict] = []
    for rp in list(dict.fromkeys(rec_ppns))[:40]:
        try:
            rr = client.get(
                SRU,
                params={
                    "operation": "searchRetrieve",
                    "version": "1.1",
                    "query": f"ppn={rp}",
                    "recordSchema": "unimarc",
                    "maximumRecords": "1",
                },
            )
            if rr.status_code != 200:
                continue
            root2 = ET.fromstring(rr.text)
            for rec in root2.iter():
                if rec.tag.endswith("record") and any(
                    c.tag.endswith("datafield") for c in rec
                ):
                    parsed = parse_record(rec)
                    if parsed:
                        out.append(parsed)
                    break
        except Exception:  # noqa: BLE001, S110
            pass
        time.sleep(0.6)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()

    prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    # Only French-educated people with an exact IdRef; only they can be joined.
    targets = {
        qid: v["IdRef"]
        for qid, v in prov.items()
        if v.get("IdRef") and "FR" in (v.get("DegreeCountries") or [])
    }
    if args.limit:
        targets = dict(list(targets.items())[: args.limit])
    print(f"French people with an exact IdRef: {len(targets):,}")

    collected: dict[str, dict] = {}
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=60, headers=headers, follow_redirects=True) as client:
        for i, (qid, ppn) in enumerate(targets.items(), 1):
            recs = sudoc_records_for(client, ppn)
            # DEDUP: one thesis often has several Sudoc records (the deposit
            # copy, a microfiche, a reprint) under different PPNs. Verified on
            # Brézis: two 1971 records for the single "Problèmes unilatéraux".
            # Counting them separately would fake a multi-degree pattern, so
            # collapse on (year, folded title) — and prefer the record that
            # carries a SPECIFIC degree type over a generic one.
            best: dict[tuple, dict] = {}
            for r in recs:
                k = (r.get("year"), _fold(r.get("title") or ""))
                prev = best.get(k)
                if prev is None or (
                    prev.get("degree") in (None, "doctorat_unspecified")
                    and r.get("degree") not in (None, "doctorat_unspecified")
                ):
                    best[k] = r
            recs = list(best.values())
            # Count only records Sudoc actually TYPES as a thesis/doctorate.
            # Without this, an early-modern professor's presided disputations
            # are counted as his own degrees: Q122366 (IdRef 031854338) showed
            # SIX "pre-1985 doctorates" dated 1721-1777 — "Dissertatio
            # inauguralis physico-medica", "Positiones medicae tumultuariae" —
            # because in that era the *praeses* was catalogued as the author of
            # every disputation he chaired. They all classify to degree=None,
            # so requiring a classified degree removes them.
            pre85 = [
                r
                for r in recs
                if (r.get("year") or 9999) < 1985 and r.get("degree") is not None
            ]
            if recs:
                collected[qid] = {
                    "IdRef": ppn,
                    "theses": recs,
                    "pre1985_count": len(pre85),
                    # THE decisive field: exactly one pre-1985 doctorate means
                    # the advisor edge is unambiguous.
                    "pre1985_degree": (
                        pre85[0].get("degree") if len(pre85) == 1 else None
                    ),
                }
            if i % 25 == 0:
                print(f"  {i}/{len(targets)}  matched={len(collected)}", flush=True)
            time.sleep(0.6)

    single = sum(1 for v in collected.values() if v["pre1985_count"] == 1)
    multi = sum(1 for v in collected.values() if v["pre1985_count"] > 1)
    print(f"\npeople with >=1 Sudoc thesis record: {len(collected):,}")
    print(f"  exactly ONE pre-1985 doctorate    : {single:,}  <- decidable")
    print(f"  TWO OR MORE (the Brezis pattern)  : {multi:,}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(collected, indent=2, ensure_ascii=False))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
