"""Stage-5 GenealogyRelation extraction + stage-6 cycle rejection (R48 §3.3).

Spec §5: stage 5 "write GenealogyRelation edges" — extraction now runs
unconditionally (was double-gated behind GMNAP_GENEALOGY_GRAPH=1 and a
broken import, so no default run ever produced edges). Spec §5 stage 6:
"reject cycles <3" — self-loops and mutual advisorship are dropped, with
target names resolved through the batch's name->GlobalID index (a raw
(gid, name) pair check can never match its mirror). The counts feed the
§7 genealogy_edge_conflict gate with real measured values.
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _run(batch, mode=PipelineMode.QUICK):
    p = V7Pipeline(mode=mode)
    asyncio.run(p.process_batch([dict(e) for e in batch]))
    return p


@pytest.mark.timeout(60)
def test_edges_extracted_unconditionally():
    p = _run(
        [
            {"CanonicalLatin": "Advisor, One"},
            {
                "CanonicalLatin": "Student, Two",
                "Advisors": [{"advisor_name": "Advisor, One"}],
            },
        ]
    )
    assert p.metrics.genealogy_edges == 1
    assert p.metrics.genealogy_edge_conflicts == 0
    assert len(p.genealogy_edges) == 1
    assert p.genealogy_edges[0]["relation_type"] == "doctoralAdvisor"


@pytest.mark.timeout(60)
def test_short_cycles_rejected_and_gate_measured():
    p = _run(
        [
            {"CanonicalLatin": "Advisor, One"},
            {
                "CanonicalLatin": "Student, Two",
                "Advisors": [{"advisor_name": "Advisor, One"}],
            },
            # mutual advisorship (length-2 cycle) — both edges bogus
            {
                "CanonicalLatin": "Cyclic, A",
                "Advisors": [{"advisor_name": "Cyclic, B"}],
            },
            {
                "CanonicalLatin": "Cyclic, B",
                "Advisors": [{"advisor_name": "Cyclic, A"}],
            },
            # self-advisorship (length-1 cycle)
            {
                "CanonicalLatin": "Selfie, Sam",
                "Advisors": [{"advisor_name": "Selfie, Sam"}],
            },
        ]
    )
    assert p.metrics.genealogy_edges == 1  # only the legitimate edge survives
    assert p.metrics.genealogy_edge_conflicts == 3
    gate = p.spec_gate_results["results"]["genealogy_edge_conflict_pct"]
    assert gate["measured"] is True
    assert gate["passed"] is False  # 3/4 = 75% conflicts, way over threshold
    assert gate["value"] == pytest.approx(75.0)


@pytest.mark.timeout(60)
def test_conflict_gate_unmeasured_without_relations():
    p = _run([{"CanonicalLatin": "Alone, Person"}])
    gate = p.spec_gate_results["results"]["genealogy_edge_conflict_pct"]
    assert gate["measured"] is False
