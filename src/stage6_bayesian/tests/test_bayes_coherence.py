from overlays.stage6_bayesian.src.graph.bayes_coherence import BayesCoherence


def test_bayes_stage6_quick_gate():
    entries = [
        {"GlobalID": "A", "Sources": ["Crossref"]},
        {"GlobalID": "B", "Advisors": ["A"], "Sources": ["Crossref", "ORCID_ETD"]},
        {"GlobalID": "C", "Advisors": ["B"], "Sources": ["OpenAlex", "Wikidata_P184"]},
        {"GlobalID": "D", "Advisors": ["B"], "Sources": ["OpenAlex"]},
    ]
    s = BayesCoherence().score(entries)
    assert s["stage6_score"] >= 0.85
