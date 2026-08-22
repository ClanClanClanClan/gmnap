"""R67 pins — two claims that were FALSE, and must not become false again.

Both are the same failure class: the project asserted a guarantee that the
code did not deliver, and the guard that should have caught it was measuring
the wrong thing.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.build_genealogy_enrichment import (  # noqa: E402
    _traces_to_mgp,
    strip_mgp_derived_edges,
)

# ── 1. --no-mgp must actually be MGP-free ───────────────────────────────


def test_strip_removes_laundered_wikidata_edges_not_just_mgp_tagged():
    """The laundering case is the whole point: an edge sourced to Wikidata but
    STATED_IN MGP is MGP-derived. 28,901 of 54,818 shipped edges (52.7%) were
    exactly this, and --no-mgp kept every one while claiming CC0-clean."""
    by_name = {
        "a": {
            "Advisors": [
                {
                    "name": "X",
                    "source": "Wikidata-P184",
                    "stated_in": "Mathematics Genealogy Project",
                },
                {"name": "Y", "source": "theses.fr", "idref": "1"},
                {"name": "Z", "source": "MGP"},
            ]
        }
    }
    stats = strip_mgp_derived_edges(by_name)
    kept = [e["name"] for e in by_name["a"]["Advisors"]]
    assert kept == ["Y"], kept  # only the independent edge survives
    assert stats["dropped"] == 2


def test_strip_is_idempotent():
    by_name = {"a": {"Advisors": [{"name": "X", "source": "MGP"}]}}
    strip_mgp_derived_edges(by_name)
    assert strip_mgp_derived_edges(by_name)["dropped"] == 0


def test_traces_to_mgp_is_the_shared_definition():
    """Both the vetting stratification and the licence strip must agree on
    what 'MGP-derived' means, or one of them is wrong."""
    assert _traces_to_mgp({"source": "MGP"})
    assert _traces_to_mgp(
        {"source": "Wikidata-P184", "stated_in": "Mathematics Genealogy Project"}
    )
    assert not _traces_to_mgp({"source": "theses.fr"})


def test_shipped_corpus_is_the_full_build_not_the_cc0_one():
    """Sanity: the committed artefact is the FULL build. If this ever flips,
    the licence tier of what we publish changed and DATA_SOURCES.md is stale."""
    p = Path(__file__).resolve().parents[2] / "data" / "genealogy_enrichment.json"
    if not p.exists():
        import pytest

        pytest.skip("enrichment not materialised")
    bn = json.loads(p.read_text(encoding="utf-8")).get("by_name") or {}
    if len(bn) < 1000:
        import pytest

        pytest.skip("LFS stub")
    mgp = sum(
        1
        for r in bn.values()
        for a in (r.get("Advisors") or [])
        if isinstance(a, dict) and _traces_to_mgp(a)
    )
    assert (
        mgp > 0
    ), "shipped corpus has no MGP-derived edges — is this a --no-mgp build?"


# ── 2. no name-origin field may reach an anonymous caller ───────────────


def test_every_region_code_spelling_is_stripped_for_anonymous():
    """R57's gate withholds the name-origin classification from anonymous
    callers. 11 region processors stamp "RegionCode" — that exact key was
    NOT in _ORIGIN_FIELDS, so the classification shipped anyway. The strip is
    now regex-backed so a twelfth spelling cannot silently re-open it."""
    from src.api.server import _strip_origin_fields

    for key in (
        "RegionCode",
        "region_code",
        "_region_code",
        "Region_Code",
        "regioncode",
        "RegionCodeV2",
    ):
        entry = {key: "B2", "CanonicalLatin": "X", "Advisors": [{"name": "Y"}]}
        _strip_origin_fields(entry)
        assert key not in entry, f"{key} leaked to an anonymous caller"
        assert "name_origin" in entry, f"{key} stripped without the restriction note"


def test_strip_keeps_the_genealogy_payload():
    """The gate must withhold ORIGIN, not the genealogy — those fields are the
    product, and are ordinary personal data already published elsewhere."""
    from src.api.server import _strip_origin_fields

    entry = {
        "RegionCode": "B2",
        "CanonicalLatin": "Euler, Leonhard",
        "BirthYear": 1707,
        "Institution": "Basel",
        "Advisors": [{"name": "Bernoulli, Johann", "confidence": "high"}],
    }
    _strip_origin_fields(entry)
    assert entry["BirthYear"] == 1707
    assert entry["Institution"] == "Basel"
    assert entry["Advisors"][0]["confidence"] == "high"
