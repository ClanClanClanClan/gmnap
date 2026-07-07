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
