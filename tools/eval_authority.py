#!/usr/bin/env python3
"""Live-authority quality harness.

Tier-2 audit item 2.1: the live-HTTP wiring landed in round-2's
``manager_tier01.py`` rewrite is currently verified only by mocked
unit tests (``tests/unit/test_canonical_fetcher_delegation.py``).
This script measures actual end-to-end quality against a hand-curated
30-mathematician ground-truth set
(``tests/integration/authority_ground_truth.json``) by running the
full V7 query path against the real authority APIs.

What it measures:
  - **Hit rate** — fraction of names where the OpenAlex (or Crossref/
    ORCID) lookup returned a non-empty record.
  - **BirthYear ±1 accuracy** — fraction where the returned birth
    year is within ±1 of the curated ground truth (since some sources
    only have year resolution and Wikidata sometimes records a
    one-off year delta).
  - **Institution match** — fraction where any curated affiliation
    keyword appears as a substring of any returned affiliation.

Outputs:
  - ``docs/authority_quality.md`` — markdown report with per-source
    breakdown, hit rate, accuracy.
  - ``docs/authority_quality.json`` — raw per-entry results for
    re-analysis.

Use:
  ``OFFLINE=0 PYTHONPATH=. python3 tools/eval_authority.py``

Defaults to ``OFFLINE=1`` like the rest of the pipeline; you have to
explicitly opt into the live network call. CI does **not** run this
(network-dependent + per-API rate limits); it's a manual evaluation
runnable from a workstation with API access.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
GROUND_TRUTH = REPO / "tests" / "integration" / "authority_ground_truth.json"
OUT_MD = REPO / "docs" / "authority_quality.md"
OUT_JSON = REPO / "docs" / "authority_quality.json"


def _load_ground_truth() -> List[Dict[str, Any]]:
    if not GROUND_TRUTH.exists():
        sys.exit(f"ground-truth fixture not found at {GROUND_TRUTH}")
    return json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))


def _institution_match(returned: List[Any], expected_keywords: List[str]) -> bool:
    """A loose substring-match across any returned affiliation."""
    if not expected_keywords:
        # Caller didn't pin an institution; can't fail nor pass —
        # treat as "not measured".
        return False
    flat = " ".join(
        (
            str(a.get("institution") or a.get("name") or a.get("display_name") or a)
            if isinstance(a, dict)
            else str(a)
        )
        for a in returned or []
    ).lower()
    return any(kw.lower() in flat for kw in expected_keywords)


def _coerce_year(value: Any) -> Optional[int]:
    """Best-effort year extraction from int / 'YYYY' / 'YYYY-MM-DD'."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()[:4]
        try:
            return int(s)
        except ValueError:
            return None
    return None


async def _query_one(name: str) -> Dict[str, Any]:
    """Run the tier-0 fetchers against one name and return a flat
    dict of {source: result}."""
    from src.authority.manager_tier01 import (
        _fetch_crossref,
        _fetch_openalex,
        _fetch_orcid_etd,
    )

    entry = {"CanonicalLatin": name}
    out = {}
    for source_fn in (_fetch_openalex, _fetch_crossref, _fetch_orcid_etd):
        try:
            r = await source_fn(entry)
            out.update(r)
        except Exception as exc:
            out[source_fn.__name__.replace("_fetch_", "")] = {
                "hit": False,
                "reason": f"raised:{type(exc).__name__}:{exc}",
            }
    return out


async def _evaluate(ground_truth: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for gt in ground_truth:
        name = gt["name"]
        print(f"  {name:40s} ", end="", flush=True)
        result = await _query_one(name)

        # Per-source hit / birth-year / institution evaluation.
        per_source = {}
        for source_key in ("OpenAlex", "Crossref", "ORCID_ETD"):
            inner = result.get(source_key, {})
            hit = bool(inner.get("hit"))
            by_match = None
            inst_match = None
            if hit:
                returned_year = _coerce_year(inner.get("birth_year"))
                expected_year = gt.get("birth_year")
                if expected_year is not None and returned_year is not None:
                    by_match = abs(returned_year - expected_year) <= 1
                inst_match = _institution_match(
                    inner.get("affiliations") or [],
                    gt.get("institution_keywords") or [],
                )
            per_source[source_key] = {
                "hit": hit,
                "birth_year_returned": (
                    _coerce_year(inner.get("birth_year")) if hit else None
                ),
                "birth_year_expected": gt.get("birth_year"),
                "birth_year_match": by_match,
                "institution_match": inst_match,
                "reason": inner.get("reason"),
            }

        any_hit = any(s["hit"] for s in per_source.values())
        rows.append(
            {
                "name": name,
                "wikidata": gt.get("wikidata"),
                "country": gt.get("country"),
                "any_hit": any_hit,
                "per_source": per_source,
            }
        )
        print("✓" if any_hit else "✗")
    return rows


def _summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-source hit rate, BY accuracy, institution match."""
    total = len(rows)
    summary: Dict[str, Any] = {"total_names": total, "any_hit_rate": 0.0, "sources": {}}
    if not total:
        return summary

    summary["any_hit_rate"] = sum(1 for r in rows if r["any_hit"]) / total

    for source_key in ("OpenAlex", "Crossref", "ORCID_ETD"):
        hits = [
            r["per_source"][source_key]
            for r in rows
            if r["per_source"][source_key]["hit"]
        ]
        n_hit = len(hits)
        n_by_measured = sum(1 for h in hits if h["birth_year_match"] is not None)
        n_by_correct = sum(1 for h in hits if h["birth_year_match"] is True)
        n_inst_measured = sum(1 for h in hits if h["institution_match"] is not None)
        n_inst_correct = sum(1 for h in hits if h["institution_match"] is True)
        summary["sources"][source_key] = {
            "hit_rate": n_hit / total,
            "n_hit": n_hit,
            "birth_year_measured": n_by_measured,
            "birth_year_correct": n_by_correct,
            "birth_year_accuracy": (
                (n_by_correct / n_by_measured) if n_by_measured else None
            ),
            "institution_measured": n_inst_measured,
            "institution_correct": n_inst_correct,
            "institution_accuracy": (
                (n_inst_correct / n_inst_measured) if n_inst_measured else None
            ),
        }
    return summary


def _md_report(
    summary: Dict[str, Any],
    rows: List[Dict[str, Any]],
    *,
    is_smoke: bool = False,
) -> str:
    total = summary["total_names"]
    any_hit = summary["any_hit_rate"]
    lines = [
        "# Authority enrichment — live quality measurement",
        "",
    ]
    if is_smoke:
        lines += [
            "> ⚠️  **THIS IS A SMOKE TEST, NOT LIVE DATA.** It was generated",
            "> with `--allow-offline` against the on-disk cache. Hit rates",
            "> below reflect what was already cached on the machine that",
            "> ran the script — not what the live OpenAlex / Crossref /",
            "> ORCID APIs return today.",
            ">",
            "> To get real numbers, run `OFFLINE=0 make eval-authority` on",
            "> a workstation with internet access. That will overwrite this",
            "> file and replace this banner with the live results.",
            "",
        ]
    lines += [
        "Generated by `tools/eval_authority.py` against",
        f"`tests/integration/authority_ground_truth.json` ({total} hand-curated",
        "mathematicians with Wikidata QIDs, birth years, and institution keywords).",
        "",
        f"**Any-source hit rate**: {any_hit:.1%}",
        " — fraction of queries where ANY tier-0 source (OpenAlex /",
        "Crossref / ORCID_ETD) returned a non-empty record.",
        "",
        "## Per-source breakdown",
        "",
        "| Source | Hit rate | BirthYear ±1 | Institution match |",
        "|---|---:|---:|---:|",
    ]
    for source, s in summary["sources"].items():
        hr = f"{s['hit_rate']:.1%} ({s['n_hit']}/{total})"
        if s["birth_year_measured"]:
            by = f"{s['birth_year_accuracy']:.1%} ({s['birth_year_correct']}/{s['birth_year_measured']})"
        else:
            by = "n/a"
        if s["institution_measured"]:
            inst = f"{s['institution_accuracy']:.1%} ({s['institution_correct']}/{s['institution_measured']})"
        else:
            inst = "n/a"
        lines.append(f"| {source} | {hr} | {by} | {inst} |")

    lines += [
        "",
        "## Per-entry detail",
        "",
        "| Name | Country | OpenAlex | Crossref | ORCID_ETD |",
        "|---|---|:-:|:-:|:-:|",
    ]
    for r in rows:
        cells = [r["name"], r.get("country", "")]
        for source in ("OpenAlex", "Crossref", "ORCID_ETD"):
            ps = r["per_source"][source]
            if not ps["hit"]:
                cells.append("—")
            else:
                marks = []
                if ps["birth_year_match"] is True:
                    marks.append("✅BY")
                elif ps["birth_year_match"] is False:
                    marks.append("❌BY")
                if ps["institution_match"] is True:
                    marks.append("✅Inst")
                elif ps["institution_match"] is False:
                    marks.append("❌Inst")
                cells.append("hit " + " ".join(marks) if marks else "hit")
        lines.append("| " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Reproduce",
        "",
        "```bash",
        "OFFLINE=0 PYTHONPATH=. python3 tools/eval_authority.py",
        "```",
        "",
        "Outputs `docs/authority_quality.md` (this file) and",
        "`docs/authority_quality.json` (per-entry raw data).",
        "",
        "**This script is not run in CI** — network-dependent, rate-",
        "limited per source, and would slow PR feedback. Run on demand",
        "from a workstation with the relevant API credentials.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-offline",
        action="store_true",
        help=(
            "Run even when OFFLINE=1 — useful for testing the harness "
            "shape (every source returns hit=False, but the report "
            "structure is exercised). Default refuses to run unless "
            "OFFLINE=0 so reviewers don't accidentally publish empty "
            "results as 'live'."
        ),
    )
    args = parser.parse_args()

    if os.getenv("OFFLINE", "1") == "1" and not args.allow_offline:
        sys.exit(
            "OFFLINE=1 (default). Pass OFFLINE=0 to hit the live APIs, "
            "or --allow-offline to run a structural smoke that won't "
            "produce meaningful data."
        )

    is_smoke = os.getenv("OFFLINE", "1") == "1" and args.allow_offline

    rows = asyncio.run(_evaluate(_load_ground_truth()))
    summary = _summarize(rows)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    OUT_MD.write_text(_md_report(summary, rows, is_smoke=is_smoke), encoding="utf-8")

    print()
    print(f"Any-source hit rate: {summary['any_hit_rate']:.1%}")
    for src, s in summary["sources"].items():
        print(f"  {src:12s} hit_rate={s['hit_rate']:.1%}", end="")
        if s["birth_year_measured"]:
            print(f"  BY±1={s['birth_year_accuracy']:.1%}", end="")
        if s["institution_measured"]:
            print(f"  Inst={s['institution_accuracy']:.1%}", end="")
        print()
    print(f"\nWrote {OUT_MD.relative_to(REPO)} + {OUT_JSON.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
