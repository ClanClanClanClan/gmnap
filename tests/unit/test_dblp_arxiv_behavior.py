"""Behavioral tests for the DBLP + arXiv bonus fetchers (R53 §2b.5/.6).

Both were only construction-guarded (the AST/concreteness roster tests);
their matching/scoring logic ran untested. These pin the pure helpers with
canned data — no network.
"""

import pytest

from src.authorities.base import AuthorityData
from src.authorities.tier1.arxiv import ArXivFetcher
from src.authorities.tier1.dblp import DBLPFetcher


@pytest.fixture()
def dblp():
    return DBLPFetcher({})


@pytest.fixture()
def arxiv():
    return ArXivFetcher({})


def test_dblp_best_match_prefers_name_overlap(dblp):
    results = [
        {"name": "Leonhard Euler", "publications": 5},
        {"name": "Someone Else", "publications": 500},
    ]
    best = dblp._find_best_match(results, "Leonhard Euler")
    assert best["name"] == "Leonhard Euler"  # similarity beats pub-count boost


def test_dblp_best_match_empty_and_threshold(dblp):
    assert dblp._find_best_match([], "Euler") is None
    # nothing crosses the 30% similarity bar -> falls back to first result
    results = [{"name": "Zzz Qqq", "publications": 0}]
    assert dblp._find_best_match(results, "Leonhard Euler") == results[0]


def test_dblp_confidence_monotonic_in_signal(dblp):
    thin = AuthorityData(source="DBLP", source_id="x", canonical_name="A B")
    rich = AuthorityData(
        source="DBLP",
        source_id="x",
        canonical_name="A B",
        name_variants=["A. B", "B, A"],
        metadata={"publications_total": 40},
    )
    assert dblp.calculate_confidence(rich) >= dblp.calculate_confidence(thin)


def test_arxiv_names_similar_variants(arxiv):
    assert arxiv._names_similar("T. Tao", "Terence C. Tao")
    assert arxiv._names_similar("T. Tao", "terence tao")
    assert not arxiv._names_similar("T. Tao", "Emmy Noether")


def test_arxiv_parse_response_defensive(arxiv):
    # parse_response must never raise on junk input
    out = arxiv.parse_response(None)
    assert isinstance(out, AuthorityData)
    out2 = arxiv.parse_response({})
    assert isinstance(out2, AuthorityData)


def test_dblp_parse_response_defensive(dblp):
    out = dblp.parse_response(None)
    assert isinstance(out, AuthorityData)
