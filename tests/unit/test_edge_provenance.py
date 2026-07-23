"""R62 pins — the advisor-edge identity + provenance + confidence backbone.

These pin the safe-ingestion contract every future edge source (Wikidata
P185, theses.fr, MathTree) plugs into:
  - every edge carries source + confidence (+ QID when the source had one);
  - identity is QID-first (false-merge-resistant), name-fallback;
  - merge FILLS an empty slot, CORROBORATES a match (accumulating sources
    + upgrading a QID), and only OVERRIDES with strictly-higher confidence;
  - a verified/floor-locked edge is NEVER replaced by an automated source.
"""

import pytest

from tools.build_genealogy_enrichment import (
    FLOOR_LOCKED,
    SOURCE_META,
    make_edge,
    merge_advisor_edges,
)


def test_make_edge_stamps_source_and_confidence():
    e = make_edge("Euler, Leonhard", source="Wikidata-P184", qid="Q7604")
    assert e["name"] == "Euler, Leonhard"
    assert e["source"] == "Wikidata-P184"
    assert e["confidence"] == "high"  # from SOURCE_META
    assert e["qid"] == "Q7604"
    assert e["relation"] == "doctoral"


def test_make_edge_unknown_source_is_low_confidence():
    assert make_edge("X", source="some-new-scraper")["confidence"] == "low"


def test_every_known_source_has_a_confidence_tier():
    for src, meta in SOURCE_META.items():
        assert meta["confidence"] in {"verified", "high", "medium", "low"}, src
        assert "license" in meta, src


def test_merge_fills_empty():
    out = merge_advisor_edges([], [make_edge("A", source="theses.fr")])
    assert len(out) == 1 and out[0]["name"] == "A"


def test_merge_dedups_by_qid_not_name_spelling():
    # Same person, two name spellings, same QID -> ONE edge.
    a = make_edge("Bernoulli, Johann", source="MGP", qid="Q227897")
    b = make_edge("Johann Bernoulli", source="Wikidata-P184", qid="Q227897")
    out = merge_advisor_edges([a], [b])
    assert len(out) == 1, [e["name"] for e in out]
    assert set(out[0]["sources"]) == {"MGP", "Wikidata-P184"}  # corroborated


def test_merge_corroborates_by_name_when_no_qid():
    a = make_edge("Hermite, Charles", source="curated")
    b = make_edge("Hermite, Charles", source="theses.fr")
    out = merge_advisor_edges([a], [b])
    assert len(out) == 1
    assert set(out[0]["sources"]) == {"curated", "theses.fr"}


def test_floor_locked_verified_edge_is_never_overridden():
    # A verified curated edge must survive even if a (hypothetically higher)
    # automated source asserts the same advisor.
    verified = make_edge("Advisor", source="curated")  # confidence verified
    assert "curated" in FLOOR_LOCKED
    automated = dict(make_edge("Advisor", source="theses.fr"))
    automated["confidence"] = "verified"  # force equal/higher to probe the lock
    out = merge_advisor_edges([verified], [automated])
    assert len(out) == 1
    assert out[0]["source"] == "curated"  # not replaced
    assert "theses.fr" in out[0]["sources"]  # but corroboration recorded


def test_higher_confidence_upgrades_a_low_edge_but_keeps_provenance():
    low = make_edge("Adv", source="referenced advisor (no metadata)")  # low
    high = make_edge("Adv", source="Wikidata-P184", qid="Q1")  # high
    out = merge_advisor_edges([low], [high])
    assert len(out) == 1
    assert out[0]["source"] == "Wikidata-P184"  # upgraded
    assert out[0]["qid"] == "Q1"  # qid carried
    assert "referenced advisor (no metadata)" in out[0]["sources"]


def test_qid_upgrades_a_name_only_edge():
    name_only = make_edge("Adv", source="MGP")  # verified, no qid
    with_qid = make_edge("Adv", source="Wikidata-P184", qid="Q9")
    out = merge_advisor_edges([name_only], [with_qid])
    assert len(out) == 1
    # verified MGP stays the source (floor-locked), but gains the QID
    assert out[0]["source"] == "MGP"
    assert out[0]["qid"] == "Q9"


def test_distinct_advisors_are_both_kept():
    out = merge_advisor_edges(
        [make_edge("A", source="MGP")],
        [make_edge("B", source="Wikidata-P184", qid="Q2")],
    )
    assert {e["name"] for e in out} == {"A", "B"}
