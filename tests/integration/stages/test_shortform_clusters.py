import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage7_shortforms import (
    compute_short_form_clusters,
)


@pytest.mark.timeout(15)
def test_shortform_cluster():
    batch = [
        {"GlobalID": "A", "Source": "X", "CanonicalLatin": "Hardy, G. H."},
        {"GlobalID": "B", "Source": "X", "CanonicalLatin": "Littlewood, J. E."},
        {"GlobalID": "C", "Source": "X", "CanonicalLatin": "Poincaré, Henri"},
    ]
    out, clusters = compute_short_form_clusters(batch)
    assert clusters and any("Hardy" in k for k in clusters.keys())
