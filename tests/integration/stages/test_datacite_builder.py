import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.ops.datacite_builder import build_draft_doi


@pytest.mark.timeout(15)
def test_build_draft_doi_minimal():
    specs = {"doi_minting": {"shoulder": "10.3929/ethz-lineage"}}
    doi, payload = build_draft_doi(
        "deadbeef", specs, metrics={"batch_size": 2}, subjects=["Mathematics"]
    )
    assert doi.startswith("10.3929/ethz-lineage/")
    assert payload["data"]["attributes"]["event"] == "draft"
    assert payload["data"]["attributes"]["titles"][0]["title"].startswith(
        "MathLineage Snapshot"
    )
    assert payload["data"]["attributes"]["creators"][0]["name"] == "MathLineage Project"
