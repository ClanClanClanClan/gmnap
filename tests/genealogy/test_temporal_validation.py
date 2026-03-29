from src.pipeline.stage5_edge_extract import extract_edges_from_entries


def test_edge_extract_minimal():
    entries = [
        {
            "GlobalID": "S1",
            "CanonicalLatin": "Student, Test",
            "Advisors": [
                {
                    "advisor_name": "Advisor One",
                    "advisor_id": "A1",
                    "relation_type": "doctoralAdvisor",
                    "degree_date": "2001-01-01",
                    "institution": "Test U",
                    "confidence": 0.95,
                    "sources": ["STUB"],
                    "birth_year": 1960,
                }
            ],
        }
    ]

    edges = extract_edges_from_entries(entries)
    assert len(edges) == 1
    e = edges[0]
    assert e["source_id"] == "S1"
    assert e["target_id"] == "A1"
    assert e["relation_type"] == "doctoralAdvisor"
    assert e["confidence"] >= 0.90
