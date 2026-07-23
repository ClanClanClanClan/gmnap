#!/usr/bin/env python3
"""Assemble heldout2_adjudicated.json from the adjudication journal (R60.2).

The adjudication runs as a multi-agent workflow whose per-agent return
values are appended to a journal (one JSON line per completed agent).
Assembling from the JOURNAL rather than from the workflow's final return
value is deliberate: the run is 2,300+ labels, the return value can be
truncated in transport, and a partial run (session limit, API error)
still leaves every completed agent's payload on disk.

Label precedence per name:
  1. RECONCILER verdict (labels carrying an "agreement" field) — the
     adjudicated truth; last writer wins on re-runs.
  2. Mechanical merge of the two blind LENS verdicts (labels carrying a
     "confidence" field) when no reconciler covered that name: identical
     leaves -> both_agree; differing -> UNKNOWN/unresolved.
  3. A single surviving lens -> UNKNOWN/unresolved (no independent
     confirmation; excluded from precision by the scorer).

Names present in the corpus but absent from every agent payload are
reported as uncovered and simply omitted — the scorer treats a missing
label as "no_label" and excludes it, never as truth.

Run:  PYTHONPATH=. python3 tools/assemble_heldout2_adjudication.py \
          [path/to/journal.jsonl]
"""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
D = REPO / "data" / "eval" / "heldout2"
NAMES = D / "heldout2_names.json"
OUT = D / "heldout2_adjudicated.json"
DEFAULT_JOURNAL = (
    Path.home()
    / ".claude/projects"
    / "-Users-dylanpossamai-Library-CloudStorage-Dropbox-Work-Maths-gmnap--claude-worktrees-hungry-babbage"
    / "41796100-1266-459d-bc5b-ef5c53cf76dc"
    / "subagents/workflows/wf_76f64f26-982/journal.jsonl"
)


def _key(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip().lower()


def main() -> int:
    journal = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JOURNAL
    if not journal.exists():
        print(f"ERROR: journal not found: {journal}", file=sys.stderr)
        return 2

    corpus = json.load(open(NAMES))
    by_key = {_key(e["name"]): e for e in corpus}

    reconciled: dict[str, dict] = {}
    lens_votes: dict[str, list[str]] = defaultdict(list)
    n_payloads = 0

    for line in journal.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("type") != "result":
            continue
        payload = rec.get("result")
        if not isinstance(payload, dict) or "labels" not in payload:
            continue
        labels = payload.get("labels") or []
        if not isinstance(labels, list):
            continue
        n_payloads += 1
        for lab in labels:
            if not isinstance(lab, dict) or "name" not in lab or "leaf" not in lab:
                continue
            k = _key(str(lab["name"]))
            if k not in by_key:
                continue  # hallucinated / reformatted name — never invent truth
            if "agreement" in lab:
                reconciled[k] = {
                    "name": by_key[k]["name"],
                    "leaf": str(lab["leaf"]).strip(),
                    "agreement": lab["agreement"],
                    "note": lab.get("note", ""),
                    "source": "reconciler",
                }
            elif "confidence" in lab:
                lens_votes[k].append(str(lab["leaf"]).strip())

    rows: list[dict] = []
    stats = Counter()
    for k, e in by_key.items():
        if k in reconciled:
            rows.append({**reconciled[k], "stratum": e["stratum"]})
            stats["reconciler"] += 1
            continue
        votes = lens_votes.get(k, [])
        uniq = set(votes)
        if len(votes) >= 2 and len(uniq) == 1:
            rows.append(
                {
                    "name": e["name"],
                    "leaf": votes[0],
                    "agreement": "both_agree",
                    "note": "mechanical lens merge (no reconciler)",
                    "source": "lens_merge",
                    "stratum": e["stratum"],
                }
            )
            stats["lens_merge_agree"] += 1
        elif len(votes) >= 2:
            rows.append(
                {
                    "name": e["name"],
                    "leaf": "UNKNOWN",
                    "agreement": "unresolved",
                    "note": f"lenses disagree: {sorted(uniq)}",
                    "source": "lens_merge",
                    "stratum": e["stratum"],
                }
            )
            stats["lens_merge_disagree"] += 1
        elif votes:
            rows.append(
                {
                    "name": e["name"],
                    "leaf": "UNKNOWN",
                    "agreement": "unresolved",
                    "note": "single lens only — no independent confirmation",
                    "source": "single_lens",
                    "stratum": e["stratum"],
                }
            )
            stats["single_lens"] += 1
        else:
            stats["uncovered"] += 1

    rows.sort(key=lambda r: r["name"])
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"journal payloads with labels: {n_payloads}")
    print(
        f"corpus: {len(by_key)}  labeled: {len(rows)}  uncovered: {stats['uncovered']}"
    )
    for k in ("reconciler", "lens_merge_agree", "lens_merge_disagree", "single_lens"):
        if stats[k]:
            print(f"  {k}: {stats[k]}")
    agree = Counter(r["agreement"] for r in rows)
    print("agreement:", dict(agree))
    kinds = Counter(
        (
            "UNKNOWN"
            if r["leaf"] == "UNKNOWN"
            else ("GROUP_ONLY" if r["leaf"].startswith("GROUP_ONLY") else "leaf")
        )
        for r in rows
    )
    print("label kinds:", dict(kinds))
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
