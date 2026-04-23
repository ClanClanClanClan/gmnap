"""Unit tests for `src.core.genealogy_lookup.GenealogyLookup`.

Covers the four operations the API depends on:

1. ``_normalize_key`` — diacritic folding, particle handling, short-form
   normalisation.
2. ``lookup_by_name`` — matches under various input spellings.
3. ``enrich`` — idempotent mutation of an entry dict.
4. ``traverse_lineage`` — returns edges whose endpoints are canonical
   display names (not opaque GlobalIDs). The web UI renders the
   endpoints verbatim and would break if this changed.

The tests run against the real ``data/genealogy_enrichment.json`` file
(committed to the repo), not a mock, because the singleton loads at
module-import time and mocking after-the-fact is fragile. Two anchor
mathematicians (Euler and Hilbert) are guaranteed to be present in the
MGP seed subset, so the tests are deterministic without needing the
full Wikidata augmentation.
"""

from __future__ import annotations

import pytest

from src.core.genealogy_lookup import (
    GenealogyLookup,
    _normalize_key,
    _fold_particles,
    _strip_diacritics,
)


class TestNormalizeKey:
    def test_diacritic_folded(self):
        assert _normalize_key("Poincaré, Henri") == "poincare, henri"
        assert _normalize_key("Erdős, Pál") == "erdos, pal"

    def test_first_last_reordered(self):
        assert _normalize_key("Leonhard Euler") == "euler, leonhard"

    def test_paren_alias_dropped(self):
        # "G. H. (Godfrey Harold) Hardy" → "hardy, g. h."
        assert _normalize_key("G. H. (Godfrey Harold) Hardy") == "hardy, g. h."

    def test_dutch_german_particle_folded(self):
        # Both spellings land on the same key
        a = _normalize_key("von Neumann, John")
        b = _normalize_key("Neumann, John von")
        assert a == b == "neumann, john von"

    def test_empty_input(self):
        assert _normalize_key("") == ""
        assert _normalize_key("   ") == ""


class TestHelpers:
    def test_strip_diacritics(self):
        assert _strip_diacritics("café") == "cafe"
        assert _strip_diacritics("Ērdős") == "Erdos"
        # ASCII passes through unchanged
        assert _strip_diacritics("smith") == "smith"

    def test_fold_particles_noop_without_particle(self):
        assert _fold_particles("euler, leonhard") == "euler, leonhard"

    def test_fold_particles_moves_leading(self):
        assert _fold_particles("von neumann, john") == "neumann, john von"

    def test_fold_particles_idempotent(self):
        once = _fold_particles("von neumann, john")
        twice = _fold_particles(once)
        assert once == twice


@pytest.fixture(scope="module")
def lookup():
    return GenealogyLookup()


class TestLookupByName:
    def test_exact_match(self, lookup):
        r = lookup.lookup_by_name("Euler, Leonhard")
        assert r is not None
        assert r["CanonicalLatin"] == "Euler, Leonhard"

    def test_case_insensitive(self, lookup):
        assert lookup.lookup_by_name("EULER, LEONHARD") is not None
        assert lookup.lookup_by_name("euler, leonhard") is not None

    def test_diacritic_variant(self, lookup):
        # Poincaré should match whether the caller writes é or e.
        a = lookup.lookup_by_name("Poincaré, Henri")
        b = lookup.lookup_by_name("Poincare, Henri")
        # If either resolves, both should.
        if a is not None or b is not None:
            assert a is not None and b is not None
            assert a["CanonicalLatin"] == b["CanonicalLatin"]

    def test_unknown_name_returns_none(self, lookup):
        assert lookup.lookup_by_name("Zzxqvwn, Notreal") is None

    def test_empty_returns_none(self, lookup):
        assert lookup.lookup_by_name("") is None


class TestEnrichIdempotent:
    def test_populates_when_missing(self, lookup):
        entry = {"CanonicalLatin": "Euler, Leonhard"}
        lookup.enrich(entry)
        assert entry.get("BirthYear") == 1707
        assert entry.get("Institution") == "University of Basel"
        assert isinstance(entry.get("Advisors"), list)
        assert entry["Advisors"]
        assert entry["Advisors"][0].get("name") == "Bernoulli, Johann"

    def test_does_not_overwrite_existing(self, lookup):
        entry = {
            "CanonicalLatin": "Euler, Leonhard",
            "BirthYear": 9999,  # deliberately wrong
        }
        lookup.enrich(entry)
        # Must NOT clobber the (wrong) caller-supplied value
        assert entry["BirthYear"] == 9999

    def test_unknown_name_no_mutation(self, lookup):
        entry = {"CanonicalLatin": "Zzxqvwn, Notreal"}
        before = dict(entry)
        lookup.enrich(entry)
        assert entry == before


class TestTraverseLineageContract:
    """Lineage edges MUST use canonical display names as endpoints.

    This contract is what the web UI relies on to render human-readable
    tree labels. Regressing to GlobalIDs would produce opaque labels
    like "KEC34SNIYM5DKIEO6L7Y4S" in the advisor tree.
    """

    def test_root_and_direct_advisor_are_names(self, lookup):
        edges = lookup.traverse_lineage("name:Euler, Leonhard", depth=1)
        assert edges, "Euler must have at least one advisor edge"
        # Root
        assert edges[0]["from"] == "Euler, Leonhard"
        # Direct advisor
        assert edges[0]["to"] == "Bernoulli, Johann"
        assert edges[0]["relation"] == "doctoralAdvisor"

    def test_multi_hop(self, lookup):
        edges = lookup.traverse_lineage("name:Euler, Leonhard", depth=5)
        # Expect at least Euler -> Johann B -> Jacob B chain
        pairs = {(e["from"], e["to"]) for e in edges}
        assert ("Euler, Leonhard", "Bernoulli, Johann") in pairs
        # Johann B's advisor is his brother Jacob B in the MGP seed
        assert ("Bernoulli, Johann", "Bernoulli, Jacob") in pairs

    def test_hilbert_multi_advisor(self, lookup):
        edges = lookup.traverse_lineage("name:Hilbert, David", depth=1)
        tos = sorted(e["to"] for e in edges)
        # Hilbert has two advisors in the MGP seed
        assert len(edges) >= 2
        # Both should be human names, not hashes
        for name in tos:
            assert "," in name or " " in name, (
                f"edge target looks like an opaque ID: {name!r}"
            )

    def test_no_edges_for_unknown_root(self, lookup):
        assert lookup.traverse_lineage("name:Zzxqvwn, Notreal", depth=3) == []

    def test_depth_zero_short_circuits(self, lookup):
        assert lookup.traverse_lineage("name:Euler, Leonhard", depth=0) == []

    def test_root_without_prefix_also_works(self, lookup):
        # The endpoint accepts bare names too (no "name:" prefix)
        edges = lookup.traverse_lineage("Euler, Leonhard", depth=1)
        assert edges
        assert edges[0]["from"] == "Euler, Leonhard"
