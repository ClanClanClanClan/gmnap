#!/usr/bin/env python3
"""R59 STEP-4 geo pilot — MEASUREMENT-ONLY harness (OFFLINE=0).

Question: how many of the pilot's CURRENT name-axis abstentions could a
live OpenAlex affiliation lookup convert into GEO fills? This is a
measurement harness, NOT a production path: nothing here may enter the
name-origin emitted-leaf-precision KPI (a geo fill is a different claim
on a different axis), and productionizing geo-fill emission needs its
own design — resolution_level/conflict semantics would currently
mislabel a geo fill as an unconflicted leaf.

Protocol (design-review judge, dim-5 ADOPT-as-harness):
  1. Re-derive the abstained set AT RUN TIME by running the detector on
     all 456 pilot names (never from the frozen 271-label file — steps
     R59.2-R59.5 changed the abstention population).
  2. One OpenAlex author search per abstained name (disk-cached JSON in
     cache/geo_pilot/; ~1 req/s politeness).
  3. MANDATORY identity gate: the hit's display_name must contain the
     query surname as a token AND some query given token as a prefix
     match. Gate failures count as abstention-preserved, never as
     conversions.
  4. Deterministic single-CC injection: among the hit's institutions,
     take the country_code of the affiliation with the MAX year (ties:
     recorded in the report; lexicographically smallest CC wins for
     determinism).
  5. Re-detect with CountryCodes injected; report conversions as
     "GeoRegion fills" discriminated by name_region == 'R0' (the
     method string is unreliable for this — verified empty on the
     public result object).
  6. Geo-vs-adjudicated divergences are DIASPORA SIGNAL, not error.

Run:  OFFLINE=0 PYTHONPATH=. python3 tools/geo_pilot_offline0.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
CACHE = REPO / "cache" / "geo_pilot"
PILOT = REPO / "data" / "eval" / "pilot_results_full.json"
ADJ = REPO / "data" / "eval" / "pilot_adjudicated.json"
OUT = REPO / "data" / "eval" / "geo_pilot_offline0_report.json"


def fetch_openalex(name: str) -> dict | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = urllib.parse.quote_plus(name.lower())[:150]
    fp = CACHE / f"{key}.json"
    if fp.exists():
        return json.loads(fp.read_text())
    url = (
        "https://api.openalex.org/authors?search="
        + urllib.parse.quote(name)
        + "&per-page=1&mailto=dylan.possamai@math.ethz.ch"
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001 - report and preserve abstention
        data = {"_error": str(e)}
    fp.write_text(json.dumps(data))
    time.sleep(1.0)
    return data


def _fold(s: str) -> str:
    import unicodedata

    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def identity_gate(query: str, display: str) -> bool:
    # R59.6 audit fixes: (a) diacritic-fold both sides — 'Possamai' was
    # rejected against its own 'Possamaï' record; (b) a bare INITIAL never
    # corroborates — 'Garrett G. Wen' matched 'Guangrui Wen' through the
    # 'G.' prefix (false accept, caught by the 10-name manual audit).
    # A query whose givens are ALL initials therefore gate-fails
    # (abstention preserved) — conservative by design.
    q = _fold(query.replace(",", " ")).split()
    d = _fold(display).split()
    if not q or not d:
        return False
    if "," in query:
        surname = _fold(query.split(",")[0]).split()[-1] if _fold(
            query.split(",")[0]
        ).split() else ""
        givens = _fold(query.split(",", 1)[1]).split()
    else:
        surname = q[-1]
        givens = q[:-1]
    if not surname or surname not in d:
        return False
    real_givens = [g.rstrip(".") for g in givens if len(g.rstrip(".")) >= 2]
    if not real_givens:
        return not givens  # surname-only query passes; initials-only fails
    return any(any(dt.startswith(g) for dt in d) for g in real_givens)


def latest_cc(author: dict) -> tuple[str | None, bool]:
    """(country_code, had_tie) from max-affiliation-year institution."""
    affs = author.get("affiliations") or []
    best_year, ccs = -1, set()
    for a in affs:
        inst = a.get("institution") or {}
        cc = inst.get("country_code")
        years = a.get("years") or []
        if not cc or not years:
            continue
        y = max(years)
        if y > best_year:
            best_year, ccs = y, {cc}
        elif y == best_year:
            ccs.add(cc)
    if not ccs:
        cc = (author.get("last_known_institutions") or [{}])[0].get("country_code")
        return (cc, False) if cc else (None, False)
    return sorted(ccs)[0], len(ccs) > 1


def main() -> int:
    if os.environ.get("OFFLINE", "1") != "0":
        print("Set OFFLINE=0 — this harness does live OpenAlex lookups.")
        return 2
    from src.regions.manager_optimized import RegionManager

    pilot = json.load(open(PILOT))
    names = [e["name"] if isinstance(e, dict) else e for e in pilot]
    adj = {a["name"]: a.get("leaf") for a in json.load(open(ADJ))}
    m = RegionManager()

    abstained = []
    for n in names:
        r = m.detect_region({"CanonicalLatin": n})
        if r.region_code in (None, "R0", "XX"):
            abstained.append(n)
    print(f"pilot names: {len(names)}; CURRENT abstentions: {len(abstained)}")

    rows = []
    filled = gate_fail = no_hit = no_cc = err = 0
    for n in abstained:
        data = fetch_openalex(n)
        if not data or data.get("_error"):
            err += 1
            rows.append({"name": n, "outcome": "fetch_error"})
            continue
        hits = data.get("results") or []
        if not hits:
            no_hit += 1
            rows.append({"name": n, "outcome": "no_hit"})
            continue
        author = hits[0]
        display = author.get("display_name") or ""
        if not identity_gate(n, display):
            gate_fail += 1
            rows.append(
                {"name": n, "outcome": "identity_gate_fail", "hit": display}
            )
            continue
        cc, tie = latest_cc(author)
        if not cc:
            no_cc += 1
            rows.append({"name": n, "outcome": "no_cc", "hit": display})
            continue
        r2 = m.detect_region({"CanonicalLatin": n, "CountryCodes": [cc]})
        geo_fill = (
            r2.region_code not in (None, "R0", "XX")
            and (r2.name_region in (None, "R0"))
        )
        rows.append(
            {
                "name": n,
                "outcome": "geo_fill" if geo_fill else "no_fill",
                "hit": display,
                "cc": cc,
                "cc_tie": tie,
                "region": r2.region_code,
                "geo_region": r2.geo_region,
                "name_region": r2.name_region,
                "adjudicated_leaf": adj.get(n),
                "diaspora_signal": bool(
                    adj.get(n)
                    and adj.get(n) not in ("GROUP_ONLY", "UNKNOWN")
                    and r2.region_code != adj.get(n)
                ),
            }
        )
        if geo_fill:
            filled += 1

    report = {
        "protocol": "R59 STEP-4 measurement harness — geo fills are NOT "
        "name-origin emissions and enter NO name-origin KPI",
        "abstained": len(abstained),
        "geo_fills": filled,
        "identity_gate_fail": gate_fail,
        "no_hit": no_hit,
        "no_cc": no_cc,
        "fetch_error": err,
        "rows": rows,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(
        f"geo_fills={filled} gate_fail={gate_fail} no_hit={no_hit} "
        f"no_cc={no_cc} fetch_error={err}"
    )
    div = [r for r in rows if r.get("diaspora_signal")]
    print(f"diaspora signals (geo != adjudicated name-origin): {len(div)}")
    for r in div[:10]:
        print("  ", r["name"], r["cc"], r["region"], "vs adj", r["adjudicated_leaf"])
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
