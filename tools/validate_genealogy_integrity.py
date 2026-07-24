#!/usr/bin/env python3
"""Build-time integrity gate for data/genealogy_enrichment.json.

The genealogy graph is assembled by merging several sources
(tools/build_genealogy_enrichment.py: MGP + Wikidata + theses.fr + OpenAlex).
This validates the structural invariants that merge is meant to guarantee, so
a bad harvest or a merge regression fails CI instead of shipping a corrupt
graph. Every check is HARD (exit 1 on any violation): the build's
``apply_edge_integrity()`` pass already removes the three fixable edge classes
(self-loops, mutual advisorship, same-name-two-QID dups), so a non-zero count
here means a genuine regression — either the integrity pass stopped running or
a source introduced a class it does not cover.

Checks:
  I1  no self-loop advisor edges          (nobody advises themselves)
  I2  no advisor cycles                    (nobody is their own ancestor)
  I3  no within-record duplicate advisors  (one person listed twice)
  I4  every advisor edge carries source + confidence   (R62 provenance)
  I5  no dangling advisor refs             (every advisor resolves to a node)
  I6  every record has a CanonicalLatin and a GlobalID
  I7  GlobalIDs unique + by_global_id reverse index consistent

    PYTHONPATH=. python3 tools/validate_genealogy_integrity.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_genealogy_enrichment import normalize_key  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "genealogy_enrichment.json"


def _advisors(rec: dict) -> list:
    return [
        a for a in (rec.get("Advisors") or []) if isinstance(a, dict) and a.get("name")
    ]


def _find_cycle(adj: dict[str, list[str]]) -> list[str] | None:
    """One cycle path if the advisor graph has any cycle, else None.

    Iterative 3-colour DFS (WHITE unvisited / GRAY on-stack / BLACK done).
    Edges are student -> advisor; a GRAY back-edge is a cycle.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(adj, WHITE)
    for start in list(adj):
        if color[start] != WHITE:
            continue
        color[start] = GRAY
        path = [start]
        stack = [(start, iter(adj[start]))]
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = BLACK
                stack.pop()
                path.pop()
                continue
            c = color.get(nxt, BLACK)  # leaf advisor (no out-edges) == BLACK
            if c == GRAY:
                return path[path.index(nxt) :] + [nxt]
            if c == WHITE:
                color[nxt] = GRAY
                path.append(nxt)
                stack.append((nxt, iter(adj[nxt])))
    return None


def validate(by_name: dict, by_gid: dict) -> list[str]:
    """Return a list of violation strings (empty == graph is clean)."""
    failures: list[str] = []

    self_loops: list[str] = []
    within_dups: list[str] = []
    no_prov = 0
    dangling: set[str] = set()
    # adjacency over EXISTING nodes only (dangling handled in I5)
    adj: dict[str, list[str]] = {}
    for k, rec in by_name.items():
        targets: list[str] = []
        seen: set[str] = set()
        for a in _advisors(rec):
            ak = normalize_key(a["name"])
            if ak == k:
                self_loops.append(k)
            if ak in seen:
                within_dups.append(k)
            seen.add(ak)
            if not a.get("source") or not a.get("confidence"):
                no_prov += 1
            if ak in by_name:
                targets.append(ak)
            elif ak:
                dangling.add(ak)
        adj[k] = targets

    if self_loops:  # I1
        failures.append(
            f"I1: {len(self_loops)} self-loop advisor edge(s) "
            f"(e.g. {self_loops[:3]}) — apply_edge_integrity should drop these"
        )
    cycle = _find_cycle(adj)  # I2
    if cycle:
        failures.append(f"I2: advisor cycle(s) present — one is {' -> '.join(cycle)}")
    if within_dups:  # I3
        failures.append(
            f"I3: {len(within_dups)} record(s) list one advisor twice "
            f"(e.g. {within_dups[:3]})"
        )
    if no_prov:  # I4
        failures.append(
            f"I4: {no_prov} advisor edge(s) missing source/confidence "
            f"(R62 stamps every edge — a raw list leaked in)"
        )
    if dangling:  # I5
        failures.append(
            f"I5: {len(dangling)} advisor ref(s) resolve to no node "
            f"(stub creation should cover every referenced advisor)"
        )

    # I6: every record has CanonicalLatin + GlobalID
    no_cl = [k for k, r in by_name.items() if not r.get("CanonicalLatin")]
    no_gid = [k for k, r in by_name.items() if not r.get("GlobalID")]
    if no_cl:
        failures.append(f"I6: {len(no_cl)} record(s) missing CanonicalLatin")
    if no_gid:
        failures.append(f"I6: {len(no_gid)} record(s) missing GlobalID")

    # I7: GlobalID integrity. A GID is DETERMINISTICALLY derived from the
    # canonical form, so:
    #  - two keys may share a GID iff they share a CanonicalLatin — this is the
    #    deliberate ALIAS design (ADVISOR_STUBS maps several spellings/initials
    #    of ONE person, e.g. "perelman, g." and "perelman, grigori" both
    #    "Perelman, G.", to one id so queries resolve); same person, same id is
    #    correct, not a collision;
    #  - a GID shared across DIFFERENT canonical forms IS a real hash collision;
    #  - every by_global_id value must point to an existing by_name key.
    gid_forms: dict[str, set[str]] = defaultdict(set)
    for r in by_name.values():
        if r.get("GlobalID"):
            gid_forms[r["GlobalID"]].add(r.get("CanonicalLatin") or "")
    collisions = {g: f for g, f in gid_forms.items() if len(f) > 1}
    if collisions:
        g, forms = next(iter(collisions.items()))
        failures.append(
            f"I7: {len(collisions)} GlobalID(s) shared across DIFFERENT canonical "
            f"forms (hash collision) — e.g. {g}: {sorted(forms)[:2]}"
        )
    bad_targets = [k for k in by_gid.values() if k not in by_name]
    if bad_targets:
        failures.append(
            f"I7: by_global_id has {len(bad_targets)} entries pointing to a "
            f"missing by_name key"
        )

    return failures


def main() -> int:
    if not DATA.exists():
        print(f"integrity: {DATA} not found", file=sys.stderr)
        return 1
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    by_name = payload.get("by_name") or {}
    by_gid = payload.get("by_global_id") or {}
    if len(by_name) < 1000:
        print(
            f"integrity: by_name has {len(by_name)} entries — looks like an "
            f"LFS stub; run `git lfs pull`",
            file=sys.stderr,
        )
        return 1

    failures = validate(by_name, by_gid)
    edges = sum(len(_advisors(r)) for r in by_name.values())
    if failures:
        print("GENEALOGY INTEGRITY: FAIL\n")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("GENEALOGY INTEGRITY: PASS")
    print(f"  {len(by_name):,} nodes, {edges:,} advisor edges")
    print("  I1 no self-loops · I2 acyclic · I3 no dup advisors")
    print("  I4 every edge has provenance · I5 no dangling refs")
    print("  I6 CanonicalLatin+GlobalID present · I7 GlobalID index consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
