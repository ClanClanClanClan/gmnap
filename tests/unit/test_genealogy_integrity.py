"""R64 pins — genealogy graph structural integrity.

`apply_edge_integrity()` (in the build) drops the genealogically-impossible
edge classes; `validate_genealogy_integrity.validate()` gates the invariants
in CI. These pin both — plus that the COMMITTED graph is clean (the live gate,
mirroring what CI runs).
"""

import json

from tools.build_genealogy_enrichment import apply_edge_integrity, make_edge
from tools.validate_genealogy_integrity import DATA, _find_cycle, validate


def _rec(cl, gid, advisors=None):
    r = {"CanonicalLatin": cl, "GlobalID": gid}
    if advisors is not None:
        r["Advisors"] = advisors
    return r


# ── apply_edge_integrity: the three fixable classes ─────────────────────


def test_integrity_drops_self_loop():
    by_name = {
        "euler, leonhard": _rec(
            "Euler, Leonhard", "G1", [make_edge("Euler, Leonhard", source="theses.fr")]
        )
    }
    stats = apply_edge_integrity(by_name)
    assert stats["selfloops"] == 1
    assert by_name["euler, leonhard"]["Advisors"] == []


def test_integrity_drops_mutual_advisorship_both_edges():
    by_name = {
        "a, x": _rec("A, X", "G1", [make_edge("B, Y", source="Wikidata-P184")]),
        "b, y": _rec("B, Y", "G2", [make_edge("A, X", source="Wikidata-P184")]),
    }
    stats = apply_edge_integrity(by_name)
    assert stats["mutual_edges"] == 2
    assert by_name["a, x"]["Advisors"] == []
    assert by_name["b, y"]["Advisors"] == []


def test_integrity_dedups_same_name_preserving_qid():
    by_name = {
        "s, x": _rec(
            "S, X",
            "G1",
            [
                make_edge("Stochel, Jan", source="Wikidata-P184", qid="Q1"),
                make_edge("Stochel, Jan", source="Wikidata-P184", qid="Q2"),
            ],
        )
    }
    stats = apply_edge_integrity(by_name)
    assert stats["dups"] == 1
    adv = by_name["s, x"]["Advisors"]
    assert len(adv) == 1
    assert adv[0]["qid"] == "Q1"
    assert adv[0]["qid_dup"] == "Q2"  # the collapsed dup's QID is preserved


def test_integrity_is_idempotent():
    by_name = {
        "euler, leonhard": _rec(
            "Euler, Leonhard", "G1", [make_edge("Euler, Leonhard", source="theses.fr")]
        )
    }
    apply_edge_integrity(by_name)
    stats2 = apply_edge_integrity(by_name)
    assert stats2 == {"selfloops": 0, "mutual_edges": 0, "dups": 0}


# ── validate: the invariants ────────────────────────────────────────────


def test_validate_clean_graph_passes():
    by_name = {
        "euler, leonhard": _rec(
            "Euler, Leonhard", "G1", [make_edge("Bernoulli, Johann", source="curated")]
        ),
        "bernoulli, johann": _rec("Bernoulli, Johann", "G2"),
    }
    assert validate(by_name, {"G1": "euler, leonhard", "G2": "bernoulli, johann"}) == []


def test_validate_catches_self_loop():
    by_name = {"x, y": _rec("X, Y", "G1", [make_edge("X, Y", source="curated")])}
    assert any(f.startswith("I1") for f in validate(by_name, {"G1": "x, y"}))


def test_find_cycle_detects_a_cycle():
    cyc = _find_cycle({"a": ["b"], "b": ["c"], "c": ["a"]})
    assert cyc is not None and cyc[0] == cyc[-1]


def test_find_cycle_none_on_dag():
    assert _find_cycle({"a": ["b"], "b": ["c"], "c": []}) is None


def test_validate_catches_dangling_ref():
    by_name = {"x, y": _rec("X, Y", "G1", [make_edge("Ghost, None", source="curated")])}
    assert any(f.startswith("I5") for f in validate(by_name, {"G1": "x, y"}))


def test_validate_allows_alias_gid_same_canonical():
    # Two keys, SAME CanonicalLatin + same GID = deliberate alias, NOT a bug.
    by_name = {
        "perelman, g.": _rec("Perelman, G.", "GID"),
        "perelman, grigori": _rec("Perelman, G.", "GID"),
    }
    assert not any(
        f.startswith("I7") for f in validate(by_name, {"GID": "perelman, g."})
    )


def test_validate_catches_real_gid_collision_diff_canonical():
    # Same GID across DIFFERENT canonical forms = real hash collision.
    by_name = {"a, x": _rec("A, X", "GID"), "b, y": _rec("B, Y", "GID")}
    assert any(f.startswith("I7") for f in validate(by_name, {"GID": "a, x"}))


# ── the live gate ───────────────────────────────────────────────────────


def test_committed_graph_is_clean():
    """The shipped data/genealogy_enrichment.json must satisfy every invariant."""
    if not DATA.exists():
        import pytest

        pytest.skip("genealogy_enrichment.json not materialised")
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    by_name = payload.get("by_name") or {}
    if len(by_name) < 1000:
        import pytest

        pytest.skip("LFS stub — run git lfs pull")
    assert validate(by_name, payload.get("by_global_id") or {}) == []
