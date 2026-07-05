"""Spec §5 stage 7: ShortFormClusters — the CROSS-ENTRY initials clustering
(R49 §4.7). Stage 7 previously emitted only the per-entry ShortForms list
(and in hash-randomized set order — an idempotency hazard, now sorted).
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _run(batch):
    return asyncio.run(
        V7Pipeline(mode=PipelineMode.QUICK).process_batch([dict(e) for e in batch])
    )


@pytest.mark.timeout(60)
def test_colliding_initials_form_cross_entry_clusters():
    out = _run(
        [
            {"CanonicalLatin": "Erdős, Pál"},
            {"CanonicalLatin": "Erdős, Peter"},
            {"CanonicalLatin": "Noether, Emmy"},  # no collision
        ]
    )
    by_name = {e["CanonicalLatin"]: e for e in out}
    a, b = by_name["Erdős, Pál"], by_name["Erdős, Peter"]
    assert "E.P." in a["ShortFormClusters"] and "E.P." in b["ShortFormClusters"]
    assert a["ShortFormClusters"]["E.P."] == b["ShortFormClusters"]["E.P."]
    assert len(a["ShortFormClusters"]["E.P."]) == 2  # both GlobalIDs, sorted
    assert a["ShortFormClusters"]["E.P."] == sorted(a["ShortFormClusters"]["E.P."])
    assert "ShortFormClusters" not in by_name["Noether, Emmy"]


@pytest.mark.timeout(60)
def test_short_forms_sorted_for_idempotency():
    out = _run([{"CanonicalLatin": "Einstein, Albert"}])
    forms = out[0]["ShortForms"]
    assert forms == sorted(forms)
