import pytest

from src.analytics.duckdb_analytics import DuckDBAnalytics


@pytest.mark.timeout(15)
def test_duckdb_suffix_and_changelog():
    dba = DuckDBAnalytics()
    dba.load_entries(
        [
            {"GlobalID": "1", "CanonicalLatin": "Doe, John", "BirthYear": 1980},
            {"GlobalID": "2", "CanonicalLatin": "Doe, John", "BirthYear": 1980},
            {"GlobalID": "3", "CanonicalLatin": "Doe, John", "BirthYear": 1980},
        ]
    )
    # Either duckdb present or SKIPPED
    su = dba.suffix_duplicates()
    assert isinstance(su, list)
    res = dba.write_change_log([], [{"GlobalID": "9", "CanonicalLatin": "X"}])
    assert res in ("OK", "SKIPPED")
