"""R68 pins — the retraction primitive that makes "updatable" true.

merge_advisor_edges() is MONOTONE: fill, corroborate, override upward, never
remove. So before this there was no way to express "this edge is wrong" — and
since ~99% of our Wikidata advisor statements cite MGP, the next harvest
re-asserts every error. A one-off deletion is undone by the very next build,
which is structurally MGP's own failure mode.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.build_genealogy_enrichment import (  # noqa: E402
    FLOOR_LOCKED,
    apply_corrections,
    make_edge,
    mark_vetting_status,
    merge_advisor_edges,
)


def _ledger(tmp_path, entries):
    p = tmp_path / "corrections.json"
    p.write_text(json.dumps(entries), encoding="utf-8")
    return p


# ── retract ─────────────────────────────────────────────────────────────


def test_retract_removes_the_edge(tmp_path):
    by_name = {
        "aardal, karen": {
            "CanonicalLatin": "Aardal, Karen",
            "Advisors": [
                make_edge("Wolsey, Laurence", source="Wikidata-P184", qid="Q15825378")
            ],
        }
    }
    led = _ledger(
        tmp_path,
        [
            {
                "ticket": "T1",
                "action": "retract",
                "student": {"name": "Aardal, Karen"},
                "advisor": {"name": "Wolsey, Laurence", "qid": "Q15825378"},
            }
        ],
    )
    stats = apply_corrections(by_name, led)
    assert stats["retracted"] == 1
    assert by_name["aardal, karen"]["Advisors"] == []


def test_retract_matches_by_qid_not_name_spelling(tmp_path):
    """Identity precedence is QID first — a different spelling must still hit."""
    by_name = {"s, x": {"Advisors": [make_edge("Wolsey, L.", source="MGP", qid="Q1")]}}
    led = _ledger(
        tmp_path,
        [
            {
                "ticket": "T2",
                "action": "retract",
                "student": {"name": "S, X"},
                "advisor": {"name": "Completely Different Spelling", "qid": "Q1"},
            }
        ],
    )
    assert apply_corrections(by_name, led)["retracted"] == 1


def test_retract_that_matches_nothing_is_reported_not_silent(tmp_path):
    by_name = {"s, x": {"Advisors": [make_edge("A", source="MGP", qid="Q1")]}}
    led = _ledger(
        tmp_path,
        [
            {
                "ticket": "T3",
                "action": "retract",
                "student": {"name": "S, X"},
                "advisor": {"name": "Someone Else", "qid": "Q9"},
            }
        ],
    )
    stats = apply_corrections(by_name, led)
    assert stats["retracted"] == 0 and stats["unmatched"] == 1


# ── assert, and its identity requirement ────────────────────────────────


def test_assert_adds_a_floor_locked_curated_edge(tmp_path):
    by_name = {"s, x": {"Advisors": []}}
    led = _ledger(
        tmp_path,
        [
            {
                "ticket": "T4",
                "action": "assert",
                "student": {"name": "S, X"},
                "advisor": {"name": "Choquet, Gustave", "qid": "Q1234"},
                "evidence": "https://example.org/thesis",
            }
        ],
    )
    assert apply_corrections(by_name, led)["asserted"] == 1
    edge = by_name["s, x"]["Advisors"][0]
    assert edge["source"] == "curated" and edge["source"] in FLOOR_LOCKED
    assert edge["confidence"] == "verified"
    assert edge["adjudication_ticket"] == "T4"
    assert edge["evidence"] == "https://example.org/thesis"


def test_assert_without_an_identifier_is_REFUSED(tmp_path):
    """A floor-locked edge minted on a bare name is unremovable, and 9.9% of
    French advisor surnames map to more than one real person ('lions' is
    Jacques-Louis AND Pierre-Louis). Refuse, never silently downgrade."""
    by_name = {"s, x": {"Advisors": []}}
    led = _ledger(
        tmp_path,
        [
            {
                "ticket": "T5",
                "action": "assert",
                "student": {"name": "S, X"},
                "advisor": {"name": "Lions"},
            }
        ],
    )
    stats = apply_corrections(by_name, led)
    assert stats["refused"] == 1 and stats["asserted"] == 0
    assert by_name["s, x"]["Advisors"] == []


# ── THE test: durability against a re-asserting upstream ────────────────


def test_retraction_survives_a_rebuild_that_re_asserts_the_error(tmp_path):
    """The whole point. The upstream STILL carries the error, and a later,
    HIGHER-confidence mirror of it arrives too — neither may resurrect it."""
    led = _ledger(
        tmp_path,
        [
            {
                "ticket": "T6",
                "action": "retract",
                "student": {"name": "S, X"},
                "advisor": {"name": "Wrong Advisor", "qid": "Q99"},
            }
        ],
    )

    def rebuild():
        # Harvest re-asserts the bad edge, then a higher-confidence source
        # corroborates it — exactly what happens every real build.
        edges = merge_advisor_edges(
            [make_edge("Wrong Advisor", source="MGP", qid="Q99")],
            [make_edge("Wrong Advisor", source="Wikidata-P184", qid="Q99")],
        )
        by_name = {"s, x": {"Advisors": edges}}
        apply_corrections(by_name, led)  # ledger runs every build
        return by_name

    for _ in range(3):  # three consecutive rebuilds
        out = rebuild()
        assert out["s, x"]["Advisors"] == [], "retracted edge came back"


def test_corrections_are_idempotent(tmp_path):
    by_name = {"s, x": {"Advisors": [make_edge("A", source="MGP", qid="Q1")]}}
    led = _ledger(
        tmp_path,
        [
            {
                "ticket": "T7",
                "action": "retract",
                "student": {"name": "S, X"},
                "advisor": {"name": "A", "qid": "Q1"},
            }
        ],
    )
    apply_corrections(by_name, led)
    second = apply_corrections(by_name, led)
    assert second["retracted"] == 0  # nothing left to remove
    assert by_name["s, x"]["Advisors"] == []


# ── an adjudicated edge must stay adjudicated ───────────────────────────


def test_curated_edge_is_not_re_flagged_as_needing_vetting():
    """_traces_to_mgp is true if MGP appears in `source` OR the accumulated
    `sources` list OR `stated_in`, and merge_advisor_edges PRESERVES those
    across an override. Without a floor-locked bypass, a correction that
    overrides an MGP claim gets re-stamped needs_vetting on every build and the
    adjudication never sticks."""
    merged = merge_advisor_edges(
        [make_edge("A", source="MGP", qid="Q1")],
        [make_edge("A", source="curated", qid="Q1")],
    )
    by_name = {"s, x": {"Advisors": merged}}
    mark_vetting_status(by_name)
    edge = by_name["s, x"]["Advisors"][0]
    assert edge["source"] == "curated"
    assert "MGP" in edge["sources"], "provenance must be kept, not stripped"
    assert not edge.get("needs_vetting"), "adjudicated edge was re-flagged"


# ── ledger robustness ───────────────────────────────────────────────────


def test_missing_ledger_is_a_no_op(tmp_path):
    stats = apply_corrections({"s, x": {"Advisors": []}}, tmp_path / "nope.json")
    assert stats == {"retracted": 0, "asserted": 0, "refused": 0, "unmatched": 0}


def test_malformed_ledger_does_not_break_the_build(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert apply_corrections({"s, x": {"Advisors": []}}, bad)["retracted"] == 0


def test_shipped_ledger_is_a_valid_json_array():
    p = Path(__file__).resolve().parents[2] / "data" / "adjudicated_corrections.json"
    assert p.exists(), "the ledger must exist so the build path is always live"
    assert isinstance(json.loads(p.read_text(encoding="utf-8")), list)
