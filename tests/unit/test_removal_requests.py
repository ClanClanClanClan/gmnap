"""PRIVACY.md data-subject suppression list (R55).

The enrichment file is periodically REBUILT from upstream harvests, so a
one-off record deletion would silently reappear on the next refresh. The
builder consults data/removal_requests.txt on every build; these tests pin
that an honoured request (a) removes the record, (b) scrubs the person's
name out of other records' Advisors lists, and (c) works by GlobalID too.
"""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location(
        "build_genealogy_enrichment", REPO / "tools" / "build_genealogy_enrichment.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture_data(builder):
    by_name = {
        builder.normalize_key("Doe, Jane"): {
            "CanonicalLatin": "Doe, Jane",
            "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA",
            "Advisors": [{"name": "Mentor, Old"}],
        },
        builder.normalize_key("Mentor, Old"): {
            "CanonicalLatin": "Mentor, Old",
            "GlobalID": "BBBBBBBBBBBBBBBBBBBBBB",
        },
        builder.normalize_key("Student, Keen"): {
            "CanonicalLatin": "Student, Keen",
            "GlobalID": "CCCCCCCCCCCCCCCCCCCCCC",
            "Advisors": [{"name": "Doe, Jane"}, {"name": "Mentor, Old"}],
        },
    }
    by_gid = {rec["GlobalID"]: key for key, rec in by_name.items()}
    return by_name, by_gid


def test_no_file_is_a_noop(builder, tmp_path):
    by_name, by_gid = _fixture_data(builder)
    removed, scrubbed = builder.apply_suppression_list(
        by_name, by_gid, tmp_path / "absent.txt"
    )
    assert (removed, scrubbed) == (0, 0)
    assert len(by_name) == 3


def test_name_request_removes_record_and_advisor_refs(builder, tmp_path):
    by_name, by_gid = _fixture_data(builder)
    req = tmp_path / "removal_requests.txt"
    req.write_text("# honoured 2026-07-07\nDoe, Jane\n", encoding="utf-8")
    removed, scrubbed = builder.apply_suppression_list(by_name, by_gid, req)
    assert removed == 1
    assert scrubbed == 1  # her appearance in Student, Keen's advisor list
    assert builder.normalize_key("Doe, Jane") not in by_name
    assert "AAAAAAAAAAAAAAAAAAAAAA" not in by_gid
    student = by_name[builder.normalize_key("Student, Keen")]
    assert student["Advisors"] == [{"name": "Mentor, Old"}]


def test_globalid_request_removes_record(builder, tmp_path):
    by_name, by_gid = _fixture_data(builder)
    req = tmp_path / "removal_requests.txt"
    req.write_text("BBBBBBBBBBBBBBBBBBBBBB\n", encoding="utf-8")
    removed, _ = builder.apply_suppression_list(by_name, by_gid, req)
    assert removed == 1
    assert builder.normalize_key("Mentor, Old") not in by_name


def test_advisors_key_dropped_when_emptied(builder, tmp_path):
    by_name, by_gid = _fixture_data(builder)
    req = tmp_path / "removal_requests.txt"
    req.write_text("Doe, Jane\nMentor, Old\n", encoding="utf-8")
    builder.apply_suppression_list(by_name, by_gid, req)
    student = by_name[builder.normalize_key("Student, Keen")]
    assert "Advisors" not in student  # emptied list removed, not left as []


def test_no_mgp_build_contains_zero_mgp_records(builder, tmp_path, monkeypatch):
    """DATA_SOURCES.md 'Commercial use' contract: --no-mgp must produce an
    artefact with ZERO MGP-derived records (MGP terms are non-commercial;
    the paid API tier gates rate limits, not data rights)."""
    import json

    # Tiny fixture inputs so the test doesn't chew the real 40k build.
    wikidata = tmp_path / "wikidata.json"
    wikidata.write_text(
        json.dumps(
            [
                {
                    "CanonicalLatin": "Curie, Marie",
                    "BirthYear": 1867,
                    "Advisors": [{"name": "Lippmann, Gabriel"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    mgp_seed = tmp_path / "mgp_seed.json"
    mgp_seed.write_text(
        json.dumps([{"name": "Hilbert, David", "advisors": []}]), encoding="utf-8"
    )
    mgp_full = tmp_path / "mgp_full.jsonl"
    mgp_full.write_text(
        json.dumps({"name": "Klein, Felix", "advisors": [["Pluecker, Julius"]]}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(builder, "MGP_SOURCE", mgp_seed)
    monkeypatch.setattr(builder, "MGP_FULL", mgp_full)
    monkeypatch.setattr(builder, "WIKIDATA_GENEALOGY", wikidata)
    monkeypatch.setattr(builder, "OPENALEX_AFFILIATIONS", tmp_path / "absent.json")
    monkeypatch.setattr(builder, "ADVISOR_STUBS", {})

    default = builder.build(no_mgp=False)
    clean = builder.build(no_mgp=True)

    def mgp_count(out):
        return sum(
            1 for r in out["by_name"].values() if "MGP" in (r.get("Source") or "")
        )

    assert mgp_count(default) >= 2  # seed + bulk-harvest rows present
    assert mgp_count(clean) == 0
    # MGP people are absent from the clean build entirely
    for name in ("Hilbert, David", "Klein, Felix"):
        assert builder.normalize_key(name) not in clean["by_name"]
    # the CC0 record is still there
    assert builder.normalize_key("Curie, Marie") in clean["by_name"]
