import pytest
import itertools, pytest
from hypothesis import given, strategies as st

REQUIRED = [
    "GlobalID",
    "CanonicalLatin",
    "Field",
    "Source",
    "LastUpdated",
    "ValidationStatus",
]


def validate_schema_local(entry: dict):
    errors = []
    for k in REQUIRED:
        if k not in entry:
            errors.append(f"Missing required field: {k}")
    if "BirthYear" in entry and not isinstance(entry["BirthYear"], int):
        errors.append("BirthYear must be int")
    if "ValidationStatus" in entry and entry["ValidationStatus"] not in {
        "verified",
        "pending",
        "disputed",
    }:
        errors.append("ValidationStatus must be one of verified|pending|disputed")

    # Check for malicious inputs
    for field, value in entry.items():
        if not isinstance(value, (str, int, float, bool, type(None))):
            errors.append(f"Invalid type for field {field}: {type(value)}")
        elif isinstance(value, str):
            # Check for SQL injection patterns
            if any(
                pattern in value.lower()
                for pattern in ["drop table", "'; --", "select * from", "union select"]
            ):
                errors.append(f"Potential SQL injection in {field}")
            # Check for XSS patterns
            if any(
                pattern in value.lower()
                for pattern in [
                    "<script",
                    "</script>",
                    "javascript:",
                    "onerror=",
                    "onclick=",
                ]
            ):
                errors.append(f"Potential XSS attack in {field}")
            # Check for excessive length
            if len(value) > 10000:
                errors.append(f"Field {field} exceeds maximum length")

    return (len(errors) == 0), errors


@pytest.mark.paranoid
@pytest.mark.timeout(15)
def test_every_combination_of_missing_required_fields():
    for r in range(1, len(REQUIRED) + 1):
        for combo in itertools.combinations(REQUIRED, r):
            entry = {k: "X" for k in REQUIRED if k not in combo}
            ok, errs = validate_schema_local(entry)
            assert not ok
            for missing in combo:
                assert any(missing in e for e in errs)


@given(
    global_id=st.text(min_size=1, max_size=64),
    canonical_latin=st.text(min_size=1, max_size=200),
    birth_year=st.integers(min_value=-2000, max_value=2100),
    extra=st.dictionaries(
        st.text(min_size=1, max_size=10), st.text(max_size=50), max_size=5
    ),
)
@pytest.mark.timeout(15)
def test_fuzz_field_combinations(global_id, canonical_latin, birth_year, extra):
    entry = {
        "GlobalID": global_id,
        "CanonicalLatin": canonical_latin,
        "Field": "Mathematics",
        "Source": "Manual",
        "LastUpdated": "2024-01-01",
        "ValidationStatus": "verified",
        "BirthYear": birth_year,
    }
    entry.update(extra)
    ok, errs = validate_schema_local(entry)
    assert isinstance(ok, bool) and isinstance(errs, list)


@pytest.mark.paranoid
@pytest.mark.timeout(15)
def test_malicious_inputs_rejected():
    malicious = [
        {
            "GlobalID": "'; DROP TABLE mathematicians; --",
            "CanonicalLatin": "x",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "pending",
        },
        {
            "GlobalID": "<script>alert(1)</script>",
            "CanonicalLatin": "x",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "pending",
        },
        {
            "GlobalID": "A" * 1_000_000,
            "CanonicalLatin": "x",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "pending",
        },
        {
            "GlobalID": {"$ne": None},
            "CanonicalLatin": "x",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "pending",
        },
    ]
    for m in malicious:
        ok, errs = validate_schema_local(m)
        assert not ok and len(errs) >= 1
