"""Tests for the runtime PAV-isotonic calibration helper.

The fitter and the runtime apply path are independent: the fitter
lives in ``tools/calibration.py`` and is exercised by running it
end-to-end on the benchmark; this test pins down the *apply* side
in isolation, with synthetic knots.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from src.regions import calibration


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    """Each test starts with a clean cache and the env var unset."""
    monkeypatch.delenv("GMNAP_CALIBRATE_CONFIDENCE", raising=False)
    calibration.reset_cache()
    yield
    calibration.reset_cache()


def test_apply_is_identity_when_env_unset():
    # No env var → identity, no file read.
    assert calibration.apply(0.95) == 0.95
    assert calibration.apply(0.5) == 0.5
    assert calibration.apply(0.0) == 0.0


def test_apply_returns_calibrated_when_enabled(monkeypatch, tmp_path):
    # Synthetic knots: anything ≤ 0.5 → 0.10, anything ≤ 0.9 → 0.50,
    # anything else (including > 0.9) → 0.99 via the >last_knot clip.
    knots_path = tmp_path / "calibration_isotonic.json"
    knots_path.write_text(
        json.dumps({"knots": [[0.5, 0.10], [0.9, 0.50], [1.0, 0.99]]})
    )
    monkeypatch.setattr(calibration, "_KNOTS_PATH", knots_path)
    monkeypatch.setenv("GMNAP_CALIBRATE_CONFIDENCE", "1")
    calibration.reset_cache()

    assert calibration.apply(0.3) == pytest.approx(0.10)
    assert calibration.apply(0.5) == pytest.approx(0.10)  # boundary inclusive
    assert calibration.apply(0.7) == pytest.approx(0.50)
    assert calibration.apply(0.95) == pytest.approx(0.99)


def test_clips_input_to_unit_interval(monkeypatch, tmp_path):
    knots_path = tmp_path / "calibration_isotonic.json"
    knots_path.write_text(json.dumps({"knots": [[1.0, 0.5]]}))
    monkeypatch.setattr(calibration, "_KNOTS_PATH", knots_path)
    monkeypatch.setenv("GMNAP_CALIBRATE_CONFIDENCE", "1")
    calibration.reset_cache()

    # Out-of-range inputs get clipped before mapping; result is the
    # closest knot's calibrated value.
    assert calibration.apply(-0.5) == pytest.approx(0.5)
    assert calibration.apply(1.5) == pytest.approx(0.5)


def test_missing_knots_file_falls_back_to_identity(monkeypatch, tmp_path):
    monkeypatch.setattr(
        calibration, "_KNOTS_PATH", tmp_path / "definitely_not_there.json"
    )
    monkeypatch.setenv("GMNAP_CALIBRATE_CONFIDENCE", "1")
    calibration.reset_cache()
    # File missing → identity, no exception.
    assert calibration.apply(0.42) == 0.42


def test_unparseable_knots_file_falls_back_to_identity(monkeypatch, tmp_path):
    knots_path = tmp_path / "calibration_isotonic.json"
    knots_path.write_text("{not valid json")
    monkeypatch.setattr(calibration, "_KNOTS_PATH", knots_path)
    monkeypatch.setenv("GMNAP_CALIBRATE_CONFIDENCE", "1")
    calibration.reset_cache()
    assert calibration.apply(0.42) == 0.42


def test_empty_knots_list_falls_back_to_identity(monkeypatch, tmp_path):
    knots_path = tmp_path / "calibration_isotonic.json"
    knots_path.write_text(json.dumps({"knots": []}))
    monkeypatch.setattr(calibration, "_KNOTS_PATH", knots_path)
    monkeypatch.setenv("GMNAP_CALIBRATE_CONFIDENCE", "1")
    calibration.reset_cache()
    assert calibration.apply(0.42) == 0.42


def test_malformed_knot_entries_are_dropped(monkeypatch, tmp_path):
    knots_path = tmp_path / "calibration_isotonic.json"
    # Mix of valid and bogus entries: only valid pairs should survive.
    knots_path.write_text(
        json.dumps(
            {
                "knots": [
                    [0.5, 0.30],  # valid
                    "not_a_pair",  # rejected
                    [0.7, "bad_value"],  # rejected (non-numeric)
                    [1.5, 0.4],  # rejected (out of [0,1])
                    [0.9, 0.85],  # valid
                ]
            }
        )
    )
    monkeypatch.setattr(calibration, "_KNOTS_PATH", knots_path)
    monkeypatch.setenv("GMNAP_CALIBRATE_CONFIDENCE", "1")
    calibration.reset_cache()
    assert calibration.apply(0.4) == pytest.approx(0.30)
    assert calibration.apply(0.8) == pytest.approx(0.85)


def test_real_fitted_knots_match_calibration_tool_output():
    """The committed knots in data/calibration_isotonic.json should
    reproduce the calibrated values shown in docs/calibration.md.
    Smoke-test that the file shape is what the apply path expects."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    knots_path = repo_root / "data" / "calibration_isotonic.json"
    if not knots_path.exists():
        pytest.skip("calibration knots file not committed")
    payload = json.loads(knots_path.read_text(encoding="utf-8"))
    assert "knots" in payload
    assert isinstance(payload["knots"], list)
    assert payload["knots"], "fitted knots list must be non-empty"
    for k in payload["knots"]:
        assert isinstance(k, list) and len(k) == 2
        threshold, cal_p = k
        assert 0.0 <= threshold <= 1.0
        assert 0.0 <= cal_p <= 1.0
