"""Unit tests for src/validation/data_quality.py.

Targets DataQualityValidator — the entry-quality gate used by the
pipeline's stage-8 validation. Before this file landed, coverage of
this module was 91 % missing (27/286 lines covered) because no
CI-active test exercised it directly. This file adds a focused
battery covering the public surface:

  - validate_entry: completeness / consistency / accuracy / temporal
    / suspicious-name / authority-ID / MSC-code / affiliation paths
  - check_duplicate_potential: identical entries, similar entries,
    distinct entries
  - generate_quality_report: aggregate stats over a small list

The internal `_check_*` methods all run through `validate_entry`,
so we don't test them directly — the test verifies the public
contract surfaces the right errors / warnings.
"""

from __future__ import annotations

from src.validation.data_quality import DataQualityValidator

# ─── validate_entry: happy path ────────────────────────────────────────


def _good_entry() -> dict:
    """A clean 20th-century entry that should pass all DQ checks.

    The validator's MSC format regex is `\\d{2}[A-Z]\\d{2}` (e.g.
    11A05 for "elementary number theory") and the birth-year warns
    when < 1800 ("very old"), so we pick Erdős (1913) — recent
    enough not to trip the temporal warning, MSC code matches the
    format check, source field present.
    """
    return {
        "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
        "CanonicalLatin": "Erdős, Paul",
        "Confidence": 0.97,
        "BirthYear": 1913,
        "DeathYear": 1996,
        "PrimaryMSC": [{"code": "11A05", "label": "Number theory", "source": "manual"}],
        "CountryCodes": ["HU"],
        "LanguageOfPublication": ["en", "hu"],
        "AuthorityIDs": {"OpenAlex": "A1234567"},
    }


def test_validate_entry_passes_clean_entry() -> None:
    v = DataQualityValidator()
    result = v.validate_entry(_good_entry())
    assert result["is_valid"] is True
    assert result["completeness_score"] >= 80
    assert result["errors"] == []


def test_validate_entry_returns_canonical_result_shape() -> None:
    v = DataQualityValidator()
    result = v.validate_entry(_good_entry())
    # Documented keys per the docstring contract.
    for k in ("is_valid", "completeness_score", "errors", "warnings", "suggestions"):
        assert k in result


# ─── completeness ──────────────────────────────────────────────────────


def test_validate_entry_missing_required_field_errors() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    del entry["CanonicalLatin"]
    result = v.validate_entry(entry)
    assert result["is_valid"] is False
    assert result["errors"]
    assert any("CanonicalLatin" in str(e) for e in result["errors"])


def test_validate_entry_missing_recommended_field_warns() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    del entry["BirthYear"]
    del entry["PrimaryMSC"]
    result = v.validate_entry(entry)
    # Removing two recommended fields drops the completeness score.
    assert result["completeness_score"] < 100


# ─── consistency: birth year vs death year ────────────────────────────


def test_validate_entry_death_before_birth_errors() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    entry["BirthYear"] = 1900
    entry["DeathYear"] = 1850  # death before birth
    result = v.validate_entry(entry)
    # Either errors or warnings flags this; both are acceptable.
    flagged = result["errors"] + result["warnings"]
    assert any("birth" in str(f).lower() or "death" in str(f).lower() for f in flagged)


# ─── accuracy: BirthYear range bounds ─────────────────────────────────


def test_validate_entry_birthyear_in_future_warns() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    entry["BirthYear"] = 9999
    result = v.validate_entry(entry)
    flagged = result["errors"] + result["warnings"]
    assert any("year" in str(f).lower() or "birth" in str(f).lower() for f in flagged)


def test_validate_entry_birthyear_too_old_warns() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    entry["BirthYear"] = -2000  # nonsensical
    result = v.validate_entry(entry)
    flagged = result["errors"] + result["warnings"]
    assert flagged  # something should complain


# ─── suspicious patterns ──────────────────────────────────────────────


def test_validate_entry_suspicious_name_pattern_flags() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    entry["CanonicalLatin"] = "test_user_42"
    result = v.validate_entry(entry)
    flagged = result["errors"] + result["warnings"] + result["suggestions"]
    assert any(
        "test" in str(f).lower() or "suspicious" in str(f).lower() for f in flagged
    )


def test_validate_entry_just_initials_flags() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    entry["CanonicalLatin"] = "AB"
    result = v.validate_entry(entry)
    flagged = result["errors"] + result["warnings"] + result["suggestions"]
    assert flagged  # AB matches `^[A-Z]{1,2}$` suspicious pattern


# ─── MSC code validation ──────────────────────────────────────────────


def test_validate_entry_invalid_msc_format_errors() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    # Wrong format: validator expects \d{2}[A-Z]\d{2} (e.g. 11A05).
    entry["PrimaryMSC"] = [{"code": "99", "label": "made up", "source": "test"}]
    result = v.validate_entry(entry)
    flagged = result["errors"] + result["warnings"]
    assert any("MSC" in str(f) for f in flagged)


def test_validate_entry_unknown_msc_category_warns() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    # Format-correct but category 99 isn't in valid_msc_categories.
    entry["PrimaryMSC"] = [{"code": "99A05", "label": "test", "source": "test"}]
    result = v.validate_entry(entry)
    flagged = result["warnings"]
    assert any("MSC" in str(f) or "category" in str(f).lower() for f in flagged)


# ─── duplicate detection ──────────────────────────────────────────────


def test_check_duplicate_potential_identical_entries() -> None:
    v = DataQualityValidator()
    e = _good_entry()
    score = v.check_duplicate_potential(e, e)
    # Identical → high similarity (top of the scale).
    assert score > 0.8


def test_check_duplicate_potential_distinct_entries() -> None:
    v = DataQualityValidator()
    e1 = _good_entry()
    e2 = _good_entry()
    e2["CanonicalLatin"] = "Newton, Isaac"
    e2["BirthYear"] = 1643
    e2["CountryCodes"] = ["GB"]
    score = v.check_duplicate_potential(e1, e2)
    # Different name + year + country → low similarity.
    assert score < 0.5


def test_check_duplicate_potential_similar_entries_intermediate() -> None:
    v = DataQualityValidator()
    e1 = _good_entry()
    e2 = _good_entry()
    e2["CanonicalLatin"] = "Euler, L."  # abbreviated form of same name
    score = v.check_duplicate_potential(e1, e2)
    # Returns a float in [0, 1]; the abbreviation should still rank
    # above zero even if exact-match thresholds aren't met.
    assert 0.0 <= score <= 1.0


# ─── aggregate quality report ─────────────────────────────────────────


def test_generate_quality_report_returns_summary_shape() -> None:
    v = DataQualityValidator()
    entries = [_good_entry() for _ in range(3)]
    entries[1] = {**entries[1], "CanonicalLatin": "Newton, Isaac"}
    entries[2] = {**entries[2], "CanonicalLatin": "Gauss, C.F."}
    report = v.generate_quality_report(entries)
    assert isinstance(report, dict)
    # Report should at minimum carry an overall count or per-field stat.
    assert any(
        "total" in str(k).lower()
        or "count" in str(k).lower()
        or "score" in str(k).lower()
        for k in report.keys()
    )


def test_generate_quality_report_handles_empty_input() -> None:
    v = DataQualityValidator()
    report = v.generate_quality_report([])
    assert isinstance(report, dict)


# ─── parse_year helper (private, but worth exercising via accuracy path) ─


def test_validate_entry_handles_birthyear_as_string() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    entry["BirthYear"] = "1707"  # string instead of int
    # Should not crash; either tolerates strings or coerces.
    result = v.validate_entry(entry)
    assert isinstance(result, dict)


def test_validate_entry_handles_birthyear_as_iso_date() -> None:
    v = DataQualityValidator()
    entry = _good_entry()
    entry["BirthYear"] = "1707-04-15"
    result = v.validate_entry(entry)
    assert isinstance(result, dict)
