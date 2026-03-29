from __future__ import annotations
import argparse, json, sys
from overlays.stage6_bayesian.src.graph.bayes_coherence import BayesCoherence


def main():
    ap = argparse.ArgumentParser(description="GMNAP V7 Gate Runner")
    ap.add_argument("--entries", required=True)
    ap.add_argument("--coherence_quick", type=float, default=0.85)
    args = ap.parse_args()
    entries = json.loads(open(args.entries, encoding="utf-8").read())
    stage6 = BayesCoherence().score(entries)
    dup = 0
    seen = set()
    for e in entries:
        gid = e.get("GlobalID")
        if gid in seen:
            dup += 1
        seen.add(gid)
    ok = dup == 0 and stage6["stage6_score"] >= args.coherence_quick
    print(json.dumps({"duplicate_global_id": dup, **stage6, "ok": ok}, indent=2))
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
