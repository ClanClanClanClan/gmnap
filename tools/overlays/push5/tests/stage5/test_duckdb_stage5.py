from src.pipeline.stage5_duckdb_analytics import stage5_duckdb
import os


def test_duckdb_collision_suffixing(tmp_path):
    batch = [
        {"GlobalID": "A", "CanonicalLatin": "Euler, Leonhard", "BirthYear": 1707, "Advisors": []},
        {
            "GlobalID": "B",
            "CanonicalLatin": "Euler, Leonhard",
            "BirthYear": 1707,
            "Advisors": ["A"],
        },
        {"GlobalID": "C", "CanonicalLatin": "Gauss, Carl F.", "BirthYear": 1777, "Advisors": []},
    ]
    out, m, csv = stage5_duckdb(batch, workdir=str(tmp_path))
    gids = [e["GlobalID"] for e in out]
    assert len(set(gids)) == len(gids)
    assert os.path.exists(csv)
