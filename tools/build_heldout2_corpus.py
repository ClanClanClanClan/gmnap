#!/usr/bin/env python3
"""Build held-out corpus N+2 (R60.2) — the next evaluation instrument.

Why a new corpus: the R59 discipline is "curate from corpus N, evaluate
only on corpus N+1". The 450-name held-out set (N+1) has been used to
find and fix wrong-emission classes across R59.2–R60.1 (kurt/solomon/
gomez all came from its wrong lists), so it has degraded into a dev set.
This script assembles a FRESH, person-disjoint, larger corpus with two
deliberate strata:

  A. arXiv fields untouched by the pilot (Dylan's math.PR-adjacent
     workload) and by held-out-1 (math.AG/NT/CO/AP/DG): recent author
     lists from math.ST, math.DS, math.GT, math.RT, math.LO, math.NA,
     math-ph, math.QA — a fresh population, same modality.
  B. OpenAlex-stratified under-represented regions: mathematicians
     affiliated with institutions in Africa, SEA, South Asia (non-IN),
     MENA, Latin America, Central Asia/Caucasus. These stress-test
     exactly the families (F, E6/E7, C, G1) where the system has least
     coverage. The affiliation country is ONLY a sampling key — it is
     NEVER given to the detector and NEVER treated as ground truth
     (affiliation-as-truth is the exact defect R59 forensics proved in
     the old training corpus). Adjudication stays name-etymology-based.

Exclusions: exact folded full-name matches against every prior eval set
(843 fixture, 456 pilot, 450 held-out-1) — person-level disjointness.
Single-token names are dropped.

Outputs (data/eval/heldout2/):
  heldout2_names.json    [{name, stratum, source}]
  (system snapshot + adjudication are separate steps)

Run:  PYTHONPATH=. python3 tools/build_heldout2_corpus.py
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
OUT_DIR = REPO / "data" / "eval" / "heldout2"
MAILTO = "dylan.possamai@math.ethz.ch"

ARXIV_CATS = [
    "math.ST",
    "math.DS",
    "math.GT",
    "math.RT",
    "math.LO",
    "math.NA",
    "math-ph",
    "math.QA",
]

# Sampling keys only — never truth, never detector input.
STRAT_CCS = {
    "africa": ["NG", "ZA", "EG", "TN", "MA", "DZ", "KE", "GH", "ET", "SN", "CM"],
    "sea": ["TH", "VN", "ID", "MY", "PH"],
    "south_asia_non_in": ["PK", "BD", "LK", "NP"],
    "mena": ["IR", "TR", "SA", "JO", "LB", "IQ"],
    "latam": ["BR", "MX", "AR", "CL", "CO", "PE"],
    "central_asia_caucasus": ["KZ", "UZ", "AZ", "GE", "AM"],
}
PER_CC = 12  # authors sampled per country


def _fold(s: str) -> str:
    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .strip()
    )


def prior_eval_names() -> set[str]:
    seen: set[str] = set()
    b = json.load(open(REPO / "tests" / "fixtures" / "name_origin_benchmark.json"))
    seen.update(_fold(e["full_name"]) for e in b)
    p = json.load(open(REPO / "data" / "eval" / "pilot_results_full.json"))
    seen.update(_fold(e["name"]) for e in p)
    h = json.load(open(REPO / "data" / "eval" / "heldout" / "heldout_names.json"))
    for e in h:
        seen.add(_fold(e["name"] if isinstance(e, dict) else e))
    return seen


def fetch_arxiv(cat: str, n: int = 120) -> list[str]:
    url = (
        "https://export.arxiv.org/api/query?search_query=cat:"
        + urllib.parse.quote(cat)
        + f"&sortBy=submittedDate&sortOrder=descending&max_results={n}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": f"gmnap-eval ({MAILTO})"})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml = r.read().decode()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ElementTree.fromstring(xml)
    names = []
    for author in root.iterfind(".//a:entry/a:author/a:name", ns):
        if author.text:
            names.append(author.text.strip())
    time.sleep(3.5)
    return names


def fetch_openalex_stratum(cc: str) -> list[str]:
    # Works-based sampling: recent math works with an authorship from CC;
    # keep only authors whose OWN authorship country list contains CC.
    # field 26 = Mathematics (the malformed 'domains/3' form silently
    # matched nothing — every stratum returned 0 on the first run).
    url = (
        "https://api.openalex.org/works?filter="
        + urllib.parse.quote(
            f"authorships.countries:{cc},primary_topic.field.id:26,"
            "from_publication_date:2023-01-01"
        )
        + f"&per-page=50&mailto={MAILTO}"
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {cc}: {e}", file=sys.stderr)
        return []
    names = []
    for w in data.get("results", []):
        for auth in w.get("authorships", []):
            if cc in (auth.get("countries") or []):
                n = (auth.get("author") or {}).get("display_name")
                if n:
                    names.append(n.strip())
    time.sleep(1.0)
    return names


def clean(name: str) -> str | None:
    name = re.sub(r"\s+", " ", name).strip()
    if not name or "," in name and len(name.split(",")[0]) < 2:
        return None
    toks = name.replace(",", " ").split()
    if len(toks) < 2:
        return None  # single-token names are unadjudicable
    if any(ch.isdigit() for ch in name):
        return None
    # collaboration artifacts
    if re.search(r"collaborat|consortium|group|team", name, re.I):
        return None
    return name


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    excl = prior_eval_names()
    print(f"prior-eval exclusion set: {len(excl)} names")

    rows: list[dict] = []
    seen: set[str] = set()

    def add(name: str, stratum: str, source: str) -> None:
        c = clean(name)
        if not c:
            return
        k = _fold(c)
        if k in seen or k in excl:
            return
        seen.add(k)
        rows.append({"name": c, "stratum": stratum, "source": source})

    for cat in ARXIV_CATS:
        got = fetch_arxiv(cat)
        before = len(rows)
        for n in got:
            add(n, "arxiv_fresh_fields", cat)
        print(f"arXiv {cat}: {len(got)} authors -> +{len(rows) - before}")

    for stratum, ccs in STRAT_CCS.items():
        for cc in ccs:
            got = fetch_openalex_stratum(cc)
            before = len(rows)
            for n in got[: PER_CC * 3]:
                if len(rows) - before >= PER_CC:
                    break
                add(n, f"strat_{stratum}", f"openalex:{cc}")
            print(f"OpenAlex {cc}: {len(got)} -> +{len(rows) - before}")

    out = OUT_DIR / "heldout2_names.json"
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    from collections import Counter

    print(f"\nTOTAL: {len(rows)} names -> {out.relative_to(REPO)}")
    for s, c in Counter(r["stratum"] for r in rows).most_common():
        print(f"  {s}: {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
