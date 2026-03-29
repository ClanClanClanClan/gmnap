import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage6_graph_consistency import enforce_graph_coherence_gate


@pytest.mark.timeout(15)
def test_two_cycle_rejection():
    batch = [
        {"GlobalID": "S", "Advisors": ["A"]},
        {"GlobalID": "A", "Advisors": ["S"]},  # 2-cycle
    ]
    with pytest.raises(ValueError):
        enforce_graph_coherence_gate(batch, mode="Quick")


@pytest.mark.timeout(15)
def test_gate_pass_on_sparse():
    batch = [{"GlobalID": "S", "Advisors": ["A"]}, {"GlobalID": "A"}]
    out, m = enforce_graph_coherence_gate(batch, mode="Quick")
    assert m["coherence"] > 0.0
