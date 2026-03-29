import pytest
from src.quality.gates import QualityGates


@pytest.mark.timeout(15)
def test_dup_gids():
    g = QualityGates()
    entries = [{"GlobalID": "X"}, {"GlobalID": "X"}, {"GlobalID": "X--1"}]
    assert g.duplicate_global_id(entries) == 1
