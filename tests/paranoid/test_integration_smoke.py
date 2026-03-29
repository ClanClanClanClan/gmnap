import pytest


@pytest.mark.integration
@pytest.mark.timeout(15)
def test_end_to_end_smoke(pipeline_process):
    batch = [
        {
            "GlobalID": "I-1",
            "CanonicalLatin": "Владимир Иванович",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "verified",
            "Advisors": ["I-0"],
        },
        {
            "GlobalID": "I-2",
            "CanonicalLatin": "張偉",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "verified",
        },
    ]
    out = pipeline_process(batch)
    assert isinstance(out, list) and len(out) == len(batch)
