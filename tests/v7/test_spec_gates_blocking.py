"""Spec §7 quality gates must ENFORCE, mode-aware (MASTERPLAN §3.2, R47).

The complete, tested QualityGateChecker had zero production callers; the
pipeline warned-then-passed. Now: QUICK = advisory (warn, complete);
FULL/EXTREME = blocking (QualityGateBlockedException) — on gates whose
inputs were actually measured this run. Unmeasured gates (e.g. graph
coherence on a batch with no advisor/student relations, where stage 6 only
has its field-frequency fallback proxy) are reported as skipped, never
spuriously failed. GMNAP_GATES_ADVISORY=1 is the kill-switch.
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline
from src.quality.strict_gates import QualityGateBlockedException

# A 2-node advisor graph scores ~0.5 coherence (betweenness path) — far
# below FULL's 0.92 threshold, so the measured gate must block in FULL.
_REL_BATCH = [
    {"CanonicalLatin": "Advisor, One"},
    {"CanonicalLatin": "Student, Two", "Advisors": [{"name": "Advisor, One"}]},
]
_PLAIN_BATCH = [
    {"CanonicalLatin": "Distinct, One"},
    {"CanonicalLatin": "Other, Two"},
]


def _run(mode, batch):
    p = V7Pipeline(mode=mode)
    out = asyncio.run(p.process_batch([dict(e) for e in batch]))
    return p, out


@pytest.mark.timeout(60)
def test_full_mode_blocks_on_measured_gate_failure():
    with pytest.raises(QualityGateBlockedException) as exc:
        _run(PipelineMode.FULL, _REL_BATCH)
    assert "graph_coherence_score" in exc.value.failures


@pytest.mark.timeout(60)
def test_quick_mode_is_advisory_on_same_failure():
    p, out = _run(PipelineMode.QUICK, _REL_BATCH)
    assert len(out) == 2  # completed despite the failing gate
    res = p.spec_gate_results["results"]
    assert res["graph_coherence_score"]["passed"] is False
    assert res["graph_coherence_score"]["measured"] is True


@pytest.mark.timeout(60)
def test_unmeasured_coherence_gate_never_blocks():
    """No advisor/student relations -> no genealogy graph -> the coherence
    gate is unmeasurable and must be skipped, not spuriously failed on the
    stage-6 fallback proxy score."""
    p, out = _run(PipelineMode.FULL, _PLAIN_BATCH)
    assert len(out) == 2
    res = p.spec_gate_results["results"]
    assert res["graph_coherence_score"]["measured"] is False
    assert res["duplicate_global_id"] == {
        "passed": True,
        "value": 0,
        "measured": True,
    }


@pytest.mark.timeout(60)
def test_gates_advisory_kill_switch(monkeypatch):
    monkeypatch.setenv("GMNAP_GATES_ADVISORY", "1")
    p, out = _run(PipelineMode.FULL, _REL_BATCH)  # would block without switch
    assert len(out) == 2
    assert not hasattr(p, "spec_gate_results")


@pytest.mark.timeout(60)
def test_all_eight_spec_gates_recorded():
    """Spec §7 defines EIGHT gates; every run must record all of them
    (measured or explicitly unmeasured). R55: warm_cache_runtime_per_1M_min
    was never recorded — only 7 of 8 gates existed in spec_gate_results,
    and the missing one was exactly the gate that would have flagged the
    retracted fake 1M perf claim."""
    p, _ = _run(PipelineMode.QUICK, _PLAIN_BATCH)
    recorded = set(p.spec_gate_results["results"])
    expected = {
        "duplicate_global_id",
        "duplicate_external_id_pct",
        "roundtrip_script_rate",
        "genealogy_edge_conflict_pct",
        "graph_coherence_score",
        "peak_rss_gb",
        "warm_cache_runtime_per_1M_min",
        "idempotent_diff_bytes",
    }
    assert recorded == expected, f"missing: {expected - recorded}"


@pytest.mark.timeout(60)
def test_runtime_gate_unmeasured_on_small_batches():
    """Sub-500 batches can't produce a meaningful 1M projection (setup
    overhead dominates) — the runtime gate must be skipped, never failed."""
    p, out = _run(PipelineMode.FULL, _PLAIN_BATCH)
    assert len(out) == 2  # completed: unmeasured gate never blocks
    gate = p.spec_gate_results["results"]["warm_cache_runtime_per_1M_min"]
    assert gate["measured"] is False
    assert gate["passed"] is True
