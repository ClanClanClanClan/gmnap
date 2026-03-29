import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.idempotency import assert_identical, canonical_batch_bytes


@pytest.mark.timeout(15)
def test_idempotency_bytes_and_assertion():
    a = [
        {"GlobalID": "1", "Source": "X", "CanonicalLatin": "A"},
        {"GlobalID": "2", "Source": "X", "CanonicalLatin": "B"},
    ]
    b = list(reversed(a))
    assert canonical_batch_bytes(a) == canonical_batch_bytes(b)
    assert_identical(a, b)
