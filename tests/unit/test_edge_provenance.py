"""R62 pins — the advisor-edge identity + provenance + confidence backbone.

These pin the safe-ingestion contract every future edge source (Wikidata
P185, theses.fr, MathTree) plugs into:
  - every edge carries source + confidence (+ QID and/or IdRef when the
    source had one — theses.fr supplies IdRef/PPN, Wikidata supplies QID);
  - identity is QID-first, then IdRef, then name-fallback (false-merge-
    resistant: two different QIDs — or two different IdRefs — are two people);
  - merge FILLS an empty slot, CORROBORATES a match (accumulating sources
    + upgrading a missing QID/IdRef), only OVERRIDES with strictly-higher
    confidence;
  - a verified/floor-locked edge is NEVER replaced by an automated source.
"""

import pytest

from tools.build_genealogy_enrichment import (
    FLOOR_LOCKED,
    SOURCE_META,
    make_edge,
    mark_vetting_status,
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
    # R65 trust ordering: MGP is `medium` and NO LONGER floor-locked, so a
    # higher-confidence source overrides it — while both provenances survive.
    name_only = make_edge("Adv", source="MGP")
    with_qid = make_edge("Adv", source="Wikidata-P184", qid="Q9")
    out = merge_advisor_edges([name_only], [with_qid])
    assert len(out) == 1
    assert out[0]["source"] == "Wikidata-P184"  # overrides MGP now
    assert out[0]["qid"] == "Q9"
    assert set(out[0]["sources"]) == {"MGP", "Wikidata-P184"}


def test_distinct_advisors_are_both_kept():
    out = merge_advisor_edges(
        [make_edge("A", source="MGP")],
        [make_edge("B", source="Wikidata-P184", qid="Q2")],
    )
    assert {e["name"] for e in out} == {"A", "B"}


# ── R63: IdRef (theses.fr / PPN) as the second persistent-identity axis ──


def test_make_edge_stamps_idref():
    e = make_edge("Bayart, Frédéric", source="theses.fr", idref="070378304")
    assert e["idref"] == "070378304"
    assert e["source"] == "theses.fr"
    assert e["confidence"] == "high"  # theses.fr is a high-confidence source


def test_merge_dedups_by_idref_not_name_spelling():
    # Same person, two accent spellings, same IdRef, neither with a QID -> ONE.
    a = make_edge("Perthame, Benoit", source="theses.fr", idref="026927489")
    b = make_edge("Perthame, Benoît", source="theses.fr", idref="026927489")
    out = merge_advisor_edges([a], [b])
    assert len(out) == 1, [e["name"] for e in out]


def test_different_idrefs_are_distinct_people():
    # Two DIFFERENT IdRefs under one name spelling are two people — the
    # false-merge-resistance guarantee, now on the IdRef axis too.
    a = make_edge("Martin, Jean", source="theses.fr", idref="111111111")
    b = make_edge("Martin, Jean", source="theses.fr", idref="222222222")
    out = merge_advisor_edges([a], [b])
    assert len(out) == 2


def test_idref_upgrades_a_name_only_edge():
    # R65: theses.fr (a primary registry, `high`) now OVERRIDES an MGP claim
    # (`medium`) rather than being blocked by it, and carries its IdRef.
    name_only = make_edge("Adv", source="MGP")
    with_idref = make_edge("Adv", source="theses.fr", idref="123456789")
    out = merge_advisor_edges([name_only], [with_idref])
    assert len(out) == 1
    assert out[0]["source"] == "theses.fr"
    assert out[0]["idref"] == "123456789"
    assert "MGP" in out[0]["sources"]  # provenance is not lost


# ── R65: MGP is distrusted-by-default and must be vetted ────────────────


def test_mgp_is_not_floor_locked_and_not_verified():
    """The maintainer's trust rule, pinned: MGP is a corroboration target, not
    an authority. A regression to MGP-supremacy must fail here."""
    assert SOURCE_META["MGP"]["confidence"] == "medium"
    assert SOURCE_META["MGP validation seed"]["confidence"] == "medium"
    assert "MGP" not in FLOOR_LOCKED
    assert "MGP validation seed" not in FLOOR_LOCKED
    assert FLOOR_LOCKED == {"curated"}  # only hand-adjudicated data is locked


def test_curated_is_still_floor_locked_against_mgp():
    curated = make_edge("Adv", source="curated")  # verified
    mgp = dict(make_edge("Adv", source="MGP"))
    mgp["confidence"] = "verified"  # even forced equal, must not win
    out = merge_advisor_edges([curated], [mgp])
    assert out[0]["source"] == "curated"


def test_mgp_only_edge_is_flagged_needs_vetting():
    by_name = {"s, x": {"Advisors": [make_edge("Adv", source="MGP")]}}
    stats = mark_vetting_status(by_name)
    e = by_name["s, x"]["Advisors"][0]
    assert e["needs_vetting"] is True
    assert stats["needs_vetting"] == 1 and stats["vetted"] == 0


def test_independently_corroborated_mgp_edge_is_vetted():
    merged = merge_advisor_edges(
        [make_edge("Adv", source="MGP")],
        [make_edge("Adv", source="theses.fr", idref="1")],
    )
    by_name = {"s, x": {"Advisors": merged}}
    stats = mark_vetting_status(by_name)
    e = by_name["s, x"]["Advisors"][0]
    assert e["vetted_by"] == ["theses.fr"]
    assert "needs_vetting" not in e
    assert stats["vetted"] == 1


def test_wikidata_statement_sourced_to_mgp_counts_as_mgp_derived():
    """A Wikidata P184 statement whose reference cites MGP is MGP at one
    remove — ~97% of referenced P184 statements are. It must not launder into
    'independent'."""
    e = make_edge(
        "Adv",
        source="Wikidata-P184",
        qid="Q1",
        stated_in="Mathematics Genealogy Project",
    )
    by_name = {"s, x": {"Advisors": [e]}}
    mark_vetting_status(by_name)
    assert by_name["s, x"]["Advisors"][0]["needs_vetting"] is True


def test_override_preserves_idref_and_stated_in():
    """Identity must survive an override — a winning edge may carry higher
    confidence but fewer identifiers."""
    low = dict(make_edge("Adv", source="theses.fr", idref="IDR"))
    low["stated_in"] = "Sudoc"
    high = make_edge("Adv", source="curated")  # verified, no ids
    out = merge_advisor_edges([low], [high])
    assert out[0]["source"] == "curated"
    assert out[0]["idref"] == "IDR"
    assert out[0]["stated_in"] == "Sudoc"


def test_qid_and_idref_coexist_after_cross_source_corroboration():
    # The real Abatangelo->Valdinoci case: a Wikidata edge (QID, no IdRef)
    # corroborated by theses.fr (IdRef, no QID, same name) ends up carrying
    # BOTH persistent ids and both sources.
    wiki = make_edge("Valdinoci, Enrico", source="Wikidata-P184", qid="Q88478244")
    thes = make_edge("Valdinoci, Enrico", source="theses.fr", idref="10843401X")
    out = merge_advisor_edges([wiki], [thes])
    assert len(out) == 1
    assert out[0]["qid"] == "Q88478244"
    assert out[0]["idref"] == "10843401X"
    assert set(out[0]["sources"]) == {"Wikidata-P184", "theses.fr"}
