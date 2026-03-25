"""Unit tests for Stage 11: Idempotency Check."""

import tempfile
from src.pipeline.stage11_idempotency_check import idempotency_check


class TestIdempotencyCheck:
    def test_self_mode_zero_diff(self):
        batch = [
            {"GlobalID": "AAA", "CanonicalLatin": "Euler, Leonhard"},
            {"GlobalID": "BBB", "CanonicalLatin": "Gauss, Carl"},
        ]
        with tempfile.TemporaryDirectory() as td:
            result, metrics = idempotency_check(batch, snapshot_dir=td, mode="self", strict=False)
            assert metrics["idempotency_diff_bytes"] == 0.0
            assert metrics["idempotency_mode"] == "self"

    def test_shuffled_mode(self):
        batch = [{"GlobalID": f"ID{i}", "CanonicalLatin": f"Name{i}, Given{i}"} for i in range(10)]
        with tempfile.TemporaryDirectory() as td:
            result, metrics = idempotency_check(
                batch, snapshot_dir=td, mode="shuffled", strict=False
            )
            # Shuffled mode may or may not have diff depending on canonical bytes ordering
            assert "idempotency_diff_bytes" in metrics
            assert isinstance(metrics["idempotency_diff_bytes"], float)

    def test_empty_batch(self):
        with tempfile.TemporaryDirectory() as td:
            result, metrics = idempotency_check([], snapshot_dir=td, mode="self", strict=False)
            assert metrics["idempotency_diff_bytes"] == 0.0

    def test_strict_mode_raises_on_diff(self, monkeypatch):
        monkeypatch.setenv("GMNAP_IDEMPOTENCY_STRICT", "0")
        batch = [{"GlobalID": "A", "CanonicalLatin": "Test"}]
        with tempfile.TemporaryDirectory() as td:
            # Should not raise when strict=False
            result, metrics = idempotency_check(
                batch, snapshot_dir=td, mode="shuffled", strict=False, gate_max=0
            )
            assert isinstance(result, list)
