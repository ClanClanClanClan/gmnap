#!/usr/bin/env python3
"""Report which advisor edges the risk model cannot affirm, and why.

WHY THIS IS A TOOL AND NOT A PARAGRAPH. The claim "~1,500 edges sit in REVIEW
purely because their country regime is unresearched" was written from memory
and was wrong twice over: the real figure was 756, and 369 of those have no
usable era at all, so no amount of country research can move them. A number
that lives in prose drifts away from the graph the moment the graph changes.
This prints it from the data.

It also makes the ceiling explicit. Country research can only ever help an
edge that HAS an era band — `_regime_tier` returns `regime_unknown_XX` before
it ever looks at the era, so adding a country row to a dateless edge just
relabels it `era_unknown` and leaves the tier exactly where it was. That is
the "all-REVIEW no-op" trap R66 fell into and R70 nearly repeated.

Usage:
    PYTHONPATH=. python3 tools/regime_coverage.py [--json]
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ENRICHMENT = Path("data/genealogy_enrichment.json")


def collect(by_name: dict) -> dict:
    parked: dict[str, list[dict]] = collections.defaultdict(list)
    tiers: collections.Counter = collections.Counter()
    reasons: collections.Counter = collections.Counter()
    total = 0
    for rec in by_name.values():
        for adv in rec.get("Advisors") or []:
            if not isinstance(adv, dict):
                continue
            vet = adv.get("vetting")
            if not isinstance(vet, dict):
                continue
            total += 1
            tiers[vet.get("tier")] += 1
            rs = vet.get("reasons") or []
            for r in rs:
                reasons[r] += 1
            unknown = [r for r in rs if r.startswith("regime_unknown_")]
            if unknown:
                parked[unknown[0].removeprefix("regime_unknown_")].append(
                    {
                        "tier": vet.get("tier"),
                        "era_lo": vet.get("era_lo"),
                        "sole_reason": len(rs) == 1,
                    }
                )
    return {"total": total, "tiers": tiers, "reasons": reasons, "parked": parked}


def report(data: dict) -> dict:
    parked = data["parked"]
    flat = [e for lst in parked.values() for e in lst]
    dated = [e for e in flat if e["era_lo"] is not None]
    sole_dated = [e for e in dated if e["sole_reason"] and e["tier"] == "REVIEW"]
    summary = {
        "classified_edges": data["total"],
        "tiers": dict(data["tiers"]),
        "parked_on_unresearched_regime": len(flat),
        "parked_countries": len(parked),
        "parked_with_an_era": len(dated),
        "parked_without_an_era": len(flat) - len(dated),
        "reachable_by_country_research": len(sole_dated),
        "top_reasons": dict(data["reasons"].most_common(10)),
        "by_country": {
            cc: {
                "edges": len(lst),
                "dated": sum(1 for e in lst if e["era_lo"] is not None),
            }
            for cc, lst in sorted(parked.items(), key=lambda kv: -len(kv[1]))
        },
    }
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--source", type=Path, default=ENRICHMENT)
    args = ap.parse_args()

    by_name = json.loads(args.source.read_text(encoding="utf-8"))["by_name"]
    summary = report(collect(by_name))
    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"classified edges         : {summary['classified_edges']:,}")
    for tier, n in sorted(summary["tiers"].items(), key=lambda kv: -kv[1]):
        print(f"   {tier:8} {n:>7,}")
    print()
    print(
        f"parked on an unresearched regime: {summary['parked_on_unresearched_regime']:,}"
        f"  across {summary['parked_countries']} countries"
    )
    print(f"   with an era band     : {summary['parked_with_an_era']:,}")
    print(
        f"   with NO era at all   : {summary['parked_without_an_era']:,}"
        "   <- country research CANNOT move these"
    )
    print(
        f"   reachable by research: {summary['reachable_by_country_research']:,}"
        "   <- the honest ceiling"
    )
    print("\nlargest parked populations:")
    for cc, v in list(summary["by_country"].items())[:12]:
        print(f"   {cc:4} {v['edges']:5,} edges  ({v['dated']:,} dated)")
    print("\ntop reasons across all classified edges:")
    for r, n in summary["top_reasons"].items():
        print(f"   {n:6,}  {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
