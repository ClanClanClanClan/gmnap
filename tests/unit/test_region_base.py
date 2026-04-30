"""Unit tests for src/regions/base.py.

Targets RegionSpec helper methods directly via a minimal concrete
subclass. Before this file landed, coverage was 71 % missing
(83/288 covered) because per-region processor tests exercise their
own subclasses but never hit the base class's shared utilities head-on.

Coverage plan:
  - load_yaml_config / clear_yaml_cache: cache + missing-file paths
  - apply_unicode_fold_exceptions: ligature decomposition, ß handling
  - normalize_whitespace_characters: NBSP / tab / CR collapse
  - _dice_coefficient: identical / disjoint / partial overlap / empty
  - _detect_primary_script: Latin / Cyrillic / CJK / Arabic / mixed
  - security_clean_field: clean input passes, dangerous input raises
  - process(): hook ordering — clean → augment → validate → enriched
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.regions.base import RegionRuleError, RegionSpec


class _FakeRegion(RegionSpec):
    """Minimal concrete RegionSpec for unit-testing the abstract base."""

    def __init__(self) -> None:
        super().__init__(
            code="X1",
            yaml_files=[],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["ASCII"],
        )
        self._calls: List[str] = []

    # Abstract hooks — record-only so the test can verify ordering.
    def clean(self, entry: Dict[str, Any]) -> None:
        self._calls.append("clean")

    def augment(self, entry: Dict[str, Any]) -> None:
        self._calls.append("augment")

    def validate(self, entry: Dict[str, Any]) -> None:
        self._calls.append("validate")

    def order_key(self, entry: Dict[str, Any]) -> str:
        return entry.get("CanonicalLatin", "")


# ─── load_yaml_config ─────────────────────────────────────────────────


def test_load_yaml_config_returns_empty_dict_when_file_missing() -> None:
    r = _FakeRegion()
    # X1 has no yaml file in config/regions/. The loader is intentionally
    # quiet: empty dict, no exception.
    cfg = r.load_yaml_config()
    assert cfg == {}


def test_load_yaml_config_caches_repeated_calls() -> None:
    r = _FakeRegion()
    cfg1 = r.load_yaml_config()
    cfg2 = r.load_yaml_config()
    # Identity holds — second call returns the cached dict (same object).
    assert cfg1 is cfg2


def test_clear_yaml_cache_resets_state() -> None:
    r = _FakeRegion()
    r.load_yaml_config()  # populate
    RegionSpec.clear_yaml_cache()
    cfg2 = r.load_yaml_config()
    # After clear, fresh-load returns a fresh dict (still empty for
    # missing file but the cache entry is rebuilt).
    assert cfg2 == {}


# ─── apply_unicode_fold_exceptions ────────────────────────────────────


def test_unicode_fold_decomposes_latin_ligatures() -> None:
    r = _FakeRegion()
    assert r.apply_unicode_fold_exceptions("Cæsar") == "Caesar"
    assert r.apply_unicode_fold_exceptions("Œuvre") == "OEuvre"


def test_unicode_fold_handles_german_sharp_s() -> None:
    r = _FakeRegion()
    assert r.apply_unicode_fold_exceptions("Weiß") == "Weiss"
    # Capital Sharp-S → SS (proper German capitalization).
    assert r.apply_unicode_fold_exceptions("WEIẞ") == "WEISS"


def test_unicode_fold_handles_dutch_ij() -> None:
    r = _FakeRegion()
    assert r.apply_unicode_fold_exceptions("ĳsselmeer") == "ijsselmeer"


def test_unicode_fold_returns_empty_for_empty() -> None:
    r = _FakeRegion()
    assert r.apply_unicode_fold_exceptions("") == ""


def test_unicode_fold_passes_through_clean_ascii() -> None:
    r = _FakeRegion()
    assert r.apply_unicode_fold_exceptions("Newton, Isaac") == "Newton, Isaac"


# ─── normalize_whitespace_characters ──────────────────────────────────


def test_normalize_whitespace_collapses_nbsp() -> None:
    r = _FakeRegion()
    entry = {"CanonicalLatin": "Euler, Leonhard"}  # NBSP
    out = r.normalize_whitespace_characters(entry)
    # The NBSP must be normalized to ASCII space (or stripped).
    assert " " not in out["CanonicalLatin"]


def test_normalize_whitespace_handles_missing_field() -> None:
    r = _FakeRegion()
    out = r.normalize_whitespace_characters({})
    # Returns the entry unchanged (no crash on missing CanonicalLatin).
    assert out == {}


# ─── _dice_coefficient ────────────────────────────────────────────────


def test_dice_coefficient_identical_strings() -> None:
    r = _FakeRegion()
    assert r._dice_coefficient("hello", "hello") == 1.0


def test_dice_coefficient_disjoint_strings() -> None:
    r = _FakeRegion()
    assert r._dice_coefficient("xyz", "abc") == 0.0


def test_dice_coefficient_partial_overlap() -> None:
    r = _FakeRegion()
    score = r._dice_coefficient("nation", "ration")
    # Both share several bigrams; score should be between 0 and 1 exclusive.
    assert 0.0 < score < 1.0


def test_dice_coefficient_empty_inputs_return_zero() -> None:
    r = _FakeRegion()
    assert r._dice_coefficient("", "abc") == 0.0
    assert r._dice_coefficient("abc", "") == 0.0


def test_dice_coefficient_single_char_inputs() -> None:
    r = _FakeRegion()
    # Single-char strings have no bigrams; the empty-set branch returns 1.0
    # for two empty bigram sets, which is the documented convention.
    assert r._dice_coefficient("a", "a") == 1.0


# ─── _detect_primary_script ───────────────────────────────────────────


def _multiscript_region() -> RegionSpec:
    """A region claiming mixed scripts so _detect_primary_script
    actually inspects the entry's CanonicalNative field instead of
    short-circuiting to the single scripts[0] entry."""

    class _MultiScript(RegionSpec):
        def clean(self, e):
            pass

        def augment(self, e):
            pass

        def validate(self, e):
            pass

        def order_key(self, e):
            return ""

    return _MultiScript(
        code="X9",
        yaml_files=[],
        scripts=["Latin", "Cyrillic", "CJK", "Arabic"],
        mixed_scripts=True,
    )


def test_detect_primary_script_single_script_region_returns_that_script() -> None:
    r = _FakeRegion()
    # FakeRegion has scripts=["Latin"], so the method short-circuits.
    out = r._detect_primary_script({"CanonicalNative": "anything"})
    assert out == "Latin"


def test_detect_primary_script_cyrillic_via_native_field() -> None:
    r = _multiscript_region()
    out = r._detect_primary_script({"CanonicalNative": "Иванов, Иван"})
    assert "cyrillic" in out.lower()


def test_detect_primary_script_falls_back_to_first_script_on_empty() -> None:
    r = _multiscript_region()
    out = r._detect_primary_script({})
    # No CanonicalNative → first script in the list (Latin).
    assert out == "Latin"


# ─── security_clean_field ─────────────────────────────────────────────


def test_security_clean_field_passes_clean_input() -> None:
    r = _FakeRegion()
    out = r.security_clean_field("Euler, Leonhard", field_name="name")
    # Clean input survives (modulo whitespace normalization).
    assert "Euler" in out


def test_security_clean_field_blocks_sql_injection() -> None:
    r = _FakeRegion()
    with pytest.raises(RegionRuleError):
        r.security_clean_field("'; DROP TABLE x; --", field_name="name")


# ─── process(): full hook chain ───────────────────────────────────────


def test_process_runs_hooks_in_order() -> None:
    r = _FakeRegion()
    r.process({"CanonicalLatin": "Test, Person"})
    assert r._calls == ["clean", "augment", "validate"]


def test_process_returns_an_entry_dict() -> None:
    r = _FakeRegion()
    out = r.process({"CanonicalLatin": "Test, Person"})
    assert isinstance(out, dict)
    assert "CanonicalLatin" in out
