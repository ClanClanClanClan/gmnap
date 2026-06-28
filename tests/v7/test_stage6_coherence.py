"""Regression guard: stage 6 (graph consistency / Bayesian coherence)
actually runs and uses the advisor graph.

Two stacked bugs disabled it (R39):
  1. src/core/graph_coherence/__init__.py did
     `from .scorer import GraphCoherenceScorer`, but no `scorer` submodule
     exists, so importing the package raised ModuleNotFoundError. That
     propagated through stage6_bayesian.bayes_coherence, and the
     pipeline's stage-6 import caught it -> "BayesCoherence not available,
     skipping stage 6" -> the whole stage produced nothing.
  2. compute_coherence added an advisor edge only when `adv in G`, but G's
     nodes are GlobalIDs while Advisors hold NAME strings/dicts, so
     edges_added was always 0 and betweenness never ran (silent fallback
     to a field-frequency proxy).
"""

import asyncio

import pytest

from src.core.graph_coherence.coherence import GraphCoherence
from src.core.pipeline_v7 import PipelineMode, V7Pipeline


@pytest.mark.timeout(60)
def test_stage6_runs_and_populates_coherence_fields():
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    out = asyncio.run(
        pipeline.process_batch(
            [
                {
                    "CanonicalNative": "Euler, Leonhard",
                    "CanonicalLatin": "Euler, Leonhard",
                }
            ]
            * 3
        )
    )
    e = out[0]
    # Stage 6 must run -> these fields are present (previously absent
    # because the whole stage was skipped on a broken package import).
    assert "BayesianCoherence" in e
    assert "stage6_score" in e or "BetweennessScore" in e


def test_compute_coherence_resolves_advisor_names_to_edges():
    """An advisor chain expressed by NAME must form graph edges, so the
    bridge node gets the highest betweenness (not a flat proxy score)."""
    entries = [
        {"GlobalID": "GID_BERN", "CanonicalLatin": "Bernoulli, Johann", "Advisors": []},
        {
            "GlobalID": "GID_EULER",
            "CanonicalLatin": "Euler, Leonhard",
            "Advisors": ["Bernoulli, Johann"],
        },
        {
            "GlobalID": "GID_LAG",
            "CanonicalLatin": "Lagrange, Joseph",
            "Advisors": ["Euler, Leonhard"],
        },
    ]
    scores = GraphCoherence().compute_coherence(entries)
    # Non-uniform => the graph actually has structure (edges were added).
    assert len(set(round(v, 4) for v in scores.values())) > 1
    # Euler is the bridge of the chain -> strictly highest score.
    assert scores["GID_EULER"] == max(scores.values())
    assert scores["GID_EULER"] > scores["GID_BERN"]
    assert scores["GID_EULER"] > scores["GID_LAG"]


def test_compute_coherence_resolves_advisor_dicts():
    """Wikidata-shaped advisor dicts ({'name': ...}) also resolve."""
    entries = [
        {"GlobalID": "A", "CanonicalLatin": "Advisor, One", "Advisors": []},
        {
            "GlobalID": "B",
            "CanonicalLatin": "Student, Two",
            "Advisors": [{"qid": "Q1", "name": "Advisor, One"}],
        },
        {
            "GlobalID": "C",
            "CanonicalLatin": "Student, Three",
            "Advisors": [{"name": "Student, Two"}],
        },
    ]
    scores = GraphCoherence().compute_coherence(entries)
    assert len(set(round(v, 4) for v in scores.values())) > 1
    assert scores["B"] == max(scores.values())
