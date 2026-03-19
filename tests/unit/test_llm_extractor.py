"""
Unit tests for the LLM ETD extractor module.

Tests cost metering, caching, JSON validation, and stub fallback.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.llm.etd_extractor import (
    CostMeter,
    ETD_SCHEMA,
    _cache_get,
    _cache_key,
    _cache_set,
    call_llm_stub,
    validate_llm_json,
)


# ── CostMeter ────────────────────────────────────────────────────────────


class TestCostMeter:
    """Test API cost metering."""

    def test_initial_spend_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.llm.etd_extractor.COST_FILE", Path(tmpdir) / "costs.json"):
                meter = CostMeter(monthly_cap_chf=40.0)
                assert meter.spent == 0.0

    def test_add_spend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cost_file = Path(tmpdir) / "costs.json"
            with patch("src.llm.etd_extractor.COST_FILE", cost_file):
                meter = CostMeter(monthly_cap_chf=40.0)
                meter.add(5.0)
                assert meter.spent == 5.0
                assert cost_file.exists()

    def test_cap_exceeded_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cost_file = Path(tmpdir) / "costs.json"
            with patch("src.llm.etd_extractor.COST_FILE", cost_file):
                meter = CostMeter(monthly_cap_chf=10.0)
                with pytest.raises(RuntimeError, match="cost cap exceeded"):
                    meter.add(15.0)

    def test_persistent_spend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cost_file = Path(tmpdir) / "costs.json"
            with patch("src.llm.etd_extractor.COST_FILE", cost_file):
                meter1 = CostMeter(monthly_cap_chf=40.0)
                meter1.add(5.0)

                meter2 = CostMeter(monthly_cap_chf=40.0)
                assert meter2.spent == 5.0


# ── LLM Cache ────────────────────────────────────────────────────────────


class TestLLMCache:
    """Test LLM result caching."""

    def test_cache_key_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.llm.etd_extractor.LLM_CACHE_DIR", Path(tmpdir)):
                k1 = _cache_key("hello world")
                k2 = _cache_key("hello world")
                assert k1 == k2

    def test_cache_key_different_for_different_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.llm.etd_extractor.LLM_CACHE_DIR", Path(tmpdir)):
                k1 = _cache_key("hello")
                k2 = _cache_key("world")
                assert k1 != k2

    def test_cache_set_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.llm.etd_extractor.LLM_CACHE_DIR", Path(tmpdir)):
                key = _cache_key("test text")
                obj = {"title": "Test Thesis", "authors": ["Author"]}
                _cache_set(key, obj)
                result = _cache_get(key)
                assert result == obj

    def test_cache_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.llm.etd_extractor.LLM_CACHE_DIR", Path(tmpdir)):
                key = _cache_key("nonexistent")
                assert _cache_get(key) is None


# ── JSON Validation ──────────────────────────────────────────────────────


class TestValidateLLMJSON:
    """Test LLM output validation."""

    def test_valid_output(self):
        obj = {
            "title": "A Thesis",
            "authors": ["Author One"],
            "advisors": ["Advisor One"],
            "degree_date": "2024-06",
            "degree": "PhD",
            "institution": "ETH Zurich",
            "language": "en",
        }
        ok, errs = validate_llm_json(obj)
        assert ok
        assert len(errs) == 0

    def test_missing_required_field(self):
        obj = {"title": "A Thesis"}  # Missing most fields
        ok, errs = validate_llm_json(obj)
        assert not ok
        assert len(errs) > 0
        assert any("authors" in e for e in errs)

    def test_empty_object(self):
        ok, errs = validate_llm_json({})
        assert not ok
        assert len(errs) == len(ETD_SCHEMA["required"])

    def test_custom_schema(self):
        schema = {"required": ["name", "age"], "properties": {}}
        obj = {"name": "Test", "age": 30}
        ok, errs = validate_llm_json(obj, schema)
        assert ok


# ── Stub LLM ─────────────────────────────────────────────────────────────


class TestCallLLMStub:
    """Test deterministic stub LLM."""

    def test_stub_returns_valid_data(self):
        result = call_llm_stub("some text")
        ok, errs = validate_llm_json(result)
        assert ok, f"Stub output invalid: {errs}"

    def test_stub_has_all_required_fields(self):
        result = call_llm_stub("")
        for field in ETD_SCHEMA["required"]:
            assert field in result, f"Stub missing field: {field}"

    def test_stub_deterministic(self):
        r1 = call_llm_stub("text1")
        r2 = call_llm_stub("text2")
        # Stub always returns same data
        assert r1 == r2
