import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import random

from helpers.determinism import sha256_hex, to_canonical_bytes


@pytest.mark.paranoid
@pytest.mark.timeout(15)
def test_bit_perfect_reproducibility(pipeline_process, tiny_dataset):
    hashes = []
    for _ in range(10):
        out = pipeline_process(list(tiny_dataset))
        hashes.append(sha256_hex(to_canonical_bytes(out)))
    assert len(set(hashes)) == 1, "Idempotency violated across exact reruns"


@pytest.mark.paranoid
@pytest.mark.timeout(15)
def test_idempotency_random_input_orders(pipeline_process, tiny_dataset):
    base_hash = sha256_hex(to_canonical_bytes(pipeline_process(list(tiny_dataset))))
    for _ in range(5):
        sh = list(tiny_dataset)
        random.shuffle(sh)
        out = pipeline_process(sh)
        h = sha256_hex(to_canonical_bytes(out))
        assert h == base_hash, "Idempotency violated under input reorder"
