import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage5_collision_analytics import ensure_unique_global_ids


@pytest.mark.timeout(15)
def test_suffixing_and_remap():
    batch = [
        {"GlobalID": "A", "Advisors": ["B"]},
        {"GlobalID": "A", "Advisors": ["A"]},
        {"GlobalID": "B", "Advisors": []},
    ]
    out, m = ensure_unique_global_ids(batch)
    gids = [e["GlobalID"] for e in out]
    assert len(set(gids)) == len(gids)
    assert any(g.startswith("A--") for g in gids if g != "A")
