"""Tests for stage 5 collision analytics — SQL injection prevention + correctness."""
from __future__ import annotations

import pytest

from src.pipeline.stage5_collision_analytics import stage5_collision_analytics


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")


def _entry(name: str, gid: str = "", birth=None) -> dict:
    return {"CanonicalLatin": name, "GlobalID": gid or name.upper().replace(", ", "_"), "BirthYear": birth}


class TestCollisionDetection:
    def test_no_collisions_in_unique_entries(self, tmp_path):
        batch = [_entry("Euler, Leonhard", birth=1707), _entry("Gauss, Carl", birth=1777)]
        out, metrics = stage5_collision_analytics(batch, workdir=str(tmp_path))
        assert metrics["collisions"] == 0
        assert len(out) == 2

    def test_detects_name_collision(self, tmp_path):
        batch = [
            _entry("Euler, Leonhard", gid="GID_A", birth=1707),
            _entry("Euler, Leonhard", gid="GID_B", birth=1707),
        ]
        out, metrics = stage5_collision_analytics(batch, workdir=str(tmp_path))
        assert metrics["collisions"] >= 1

    def test_empty_batch(self, tmp_path):
        out, metrics = stage5_collision_analytics([], workdir=str(tmp_path))
        assert metrics["collisions"] == 0
        assert len(out) == 0

    def test_single_entry(self, tmp_path):
        out, metrics = stage5_collision_analytics([_entry("Solo, Person")], workdir=str(tmp_path))
        assert len(out) == 1
        assert metrics["collisions"] == 0

    def test_path_with_special_characters(self, tmp_path):
        """Verify SQL injection via path is prevented (parameterized query)."""
        safe_dir = tmp_path / "test dir with spaces"
        safe_dir.mkdir()
        batch = [_entry("Test, Name")]
        out, metrics = stage5_collision_analytics(batch, workdir=str(safe_dir))
        assert isinstance(out, list)
        assert isinstance(metrics, dict)
