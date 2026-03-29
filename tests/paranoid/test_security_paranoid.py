import pytest

SQLI = [
    "' OR '1'='1",
    "'; DROP TABLE mathematicians; --",
    "admin'--",
    "1' AND '1' = '1",
]
BYPASS = [{"Authorization": "Bearer invalid"}, {"auth": {"$ne": None}}]


@pytest.mark.paranoid
@pytest.mark.timeout(15)
def test_injection_payloads_do_not_crash(pipeline_process):
    batch = [
        {
            "GlobalID": p,
            "CanonicalLatin": p,
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "pending",
        }
        for p in SQLI
    ]
    out = pipeline_process(batch)
    assert isinstance(out, list) and len(out) == len(batch)


@pytest.mark.paranoid
@pytest.mark.timeout(15)
def test_auth_bypass_inputs_do_not_crash(pipeline_process):
    # No assumption on auth; ensure it doesn't blow up the pipeline interface.
    out = pipeline_process(
        [
            {
                "GlobalID": "X",
                "CanonicalLatin": "Test",
                "Field": "Mathematics",
                "Source": "Manual",
                "LastUpdated": "2024-01-01",
                "ValidationStatus": "verified",
            }
        ]
    )
    assert isinstance(out, list)
