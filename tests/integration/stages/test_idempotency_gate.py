import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage11_idempotency_gate import enforce_idempotency_gate


def ident(x):
    return x


@pytest.mark.timeout(15)
def test_idempotency_gate_passes():
    batch = [{"GlobalID": "X", "Source": "M", "CanonicalLatin": "Test"}]
    out, b = enforce_idempotency_gate(ident, batch)
    assert isinstance(b, (bytes, bytearray))


@pytest.mark.timeout(15)
def test_idempotency_gate_detects_violation():
    def impure(xs):
        ys = []
        import time

        for e in xs:
            e2 = dict(e)
            e2["rand"] = time.time()
            ys.append(e2)
        return ys

    batch = [{"GlobalID": "X", "Source": "M", "CanonicalLatin": "Test"}]
    with pytest.raises(ValueError):
        enforce_idempotency_gate(impure, batch)
