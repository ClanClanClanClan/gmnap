import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.ops.yaml_deterministic import (
    canonicalise_entry,
    dump_yaml_deterministic,
    to_canonical_bytes,
)


@pytest.mark.timeout(15)
def test_yaml_is_deterministic():
    e1 = {"GlobalID": "B", "Source": "X", "CanonicalLatin": "Noether, Emmy", "Advisors": ["A", "C"]}
    e2 = {"Source": "X", "Advisors": ["C", "A"], "CanonicalLatin": "Noether, Emmy", "GlobalID": "B"}
    # Canonical forms must be identical
    c1 = canonicalise_entry(e1)
    c2 = canonicalise_entry(e2)
    assert c1 == c2
    # YAML bytes should be stable regardless of input order
    y1 = dump_yaml_deterministic([c1])
    y2 = dump_yaml_deterministic([c2])
    assert y1 == y2
    # Batch canonical bytes stable
    b1 = to_canonical_bytes([e1])
    b2 = to_canonical_bytes([e2])
    assert b1 == b2
