import os, json, pathlib
from src.db.changelog_expand import generate_arrays_cypher, generate_edges_cypher


def test_generate_arrays_and_edges(tmp_path):
    entries = [
        {
            "GlobalID": "X",
            "CanonicalLatin": "Euler, Leonhard",
            "AlternativeLatin": ["Leonhard Euler", "L. Euler"],
            "Advisors": ["Y"],
            "Students": ["Z1", "Z2"],
        }
    ]
    arrays = generate_arrays_cypher(tmp_path, entries)
    edges = generate_edges_cypher(tmp_path, entries)
    assert pathlib.Path(arrays).exists()
    assert pathlib.Path(edges).exists()
    a = pathlib.Path(arrays).read_text(encoding="utf-8")
    e = pathlib.Path(edges).read_text(encoding="utf-8")
    assert "AlternativeLatin" in a
    assert "ADVISED_BY" in e
