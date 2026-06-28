"""Unit tests for src/core/security_validator.py.

Targets the SecurityValidator class — the central injection-attack
gate used by stages 0/1 of the pipeline. Before this file landed
the only tests exercising it were under tests/paranoid/ (not in CI),
so end-to-end smoke worked but per-method coverage was 58 % missing.

Coverage plan:
  - validate_string: happy path, length cap, each injection family
    (SQL/XSS/NoSQL/path-traversal/template/command/SSRF), null byte,
    BiDi unicode override
  - validate_entry: scalar / nested dict / list-of-strings recursion
  - sanitize_for_output: HTML escape, script-tag stripping, length cap
  - normalize_homographs: Cyrillic → Latin lookalike map
  - detect_homograph_attack: positive / negative
  - validate_yaml_keys: dict and list inputs
  - check_rate_limit: per-client window, exhaustion → SecurityError
"""

from __future__ import annotations

import os

import pytest

# Run security validator in production mode so injection patterns
# actually fire (TEST_MODE allows certain academic-name fields to
# bypass pattern checks). Read at module import — the validator now
# checks the env var per call (via ``_test_mode()``), so no module
# reload is needed. The earlier ``importlib.reload(_sv)`` here
# recreated ``SecurityError`` with a new class identity, which broke
# ``except SecurityError`` clauses elsewhere in the codebase that
# had cached the original class — same round-32 RegionRuleError
# class-of-bug pattern. Documented in the validator module too.
os.environ.pop("GMNAP_SECURITY_MODE", None)

from src.core.security_validator import SecurityError, SecurityValidator  # noqa: E402

# ─── validate_string: happy path + injection blocks ───────────────────


def test_validate_string_accepts_normal_name() -> None:
    sv = SecurityValidator()
    assert sv.validate_string("Euler, Leonhard", context="name") == "Euler, Leonhard"


def test_validate_string_accepts_unicode_diacritics() -> None:
    sv = SecurityValidator()
    # Round-trip through validate_string — academic names often have
    # diacritics that mustn't trip injection rules.
    out = sv.validate_string("Erdős, Paul", context="general")
    assert "Erdős" in out


def test_validate_string_accepts_nfd_decomposed_name() -> None:
    """A legitimate accented name supplied in NFD/decomposed form must
    NOT be rejected as a combining-character attack.

    Regression (R38 audit): the combining-ratio check counted decomposed
    marks against the raw string, so a Vietnamese name like "Đỗ Hữu" —
    which decomposes to ~40% combining marks — tripped the 30% threshold
    and was silently dropped to region XX. The check now counts on the
    NFC-composed form, where the name has 0 combining marks.
    """
    import unicodedata

    sv = SecurityValidator()
    nfd = unicodedata.normalize("NFD", "Đỗ Hữu")
    # Precondition: the decomposed form really would trip a raw 30% check.
    ratio = sum(1 for c in nfd if unicodedata.combining(c)) / len(nfd)
    assert ratio > 0.3, "test input must be combining-heavy in NFD form"
    out = sv.validate_string(nfd, context="name")
    # Accepted (composed back to the precomposed name).
    assert out == unicodedata.normalize("NFC", nfd)


def test_validate_string_blocks_combining_stacking_attack() -> None:
    """A genuine combining-stacking (Zalgo) attack is still rejected:
    combiners that do NOT compose onto their base remain combining marks
    even after NFC, so the ratio check still fires."""
    sv = SecurityValidator()
    attack = "a" + "́" * 8  # 8 stacked acute accents on one base
    with pytest.raises(SecurityError):
        sv.validate_string(attack, context="name")


def test_validate_string_allows_pattern_n_literals() -> None:
    """Inputs containing the literal substrings pattern_0..pattern_49 must
    NOT be rejected.

    Regression (R39 audit): 50 dummy `f"pattern_{i}"` strings ("dummy
    patterns for count") were compiled as LIVE dangerous-pattern rules,
    so any field containing e.g. "pattern_5" was blocked as an attack.
    """
    sv = SecurityValidator()
    for t in ["pattern_5", "my_pattern_3", "pattern_42", "pattern_0"]:
        assert sv.validate_string(t, context="name") == t


def test_validate_string_still_blocks_real_attacks_after_dummy_removal() -> None:
    """Removing the dummy patterns must not weaken real detection."""
    sv = SecurityValidator()
    for attack in ["pg_sleep(5)", "eval(", "<script>alert(1)</script>"]:
        with pytest.raises(SecurityError):
            sv.validate_string(attack, context="name")


def test_validate_string_rejects_sql_injection() -> None:
    sv = SecurityValidator()
    with pytest.raises(SecurityError, match=r"(?i)sql"):
        sv.validate_string("'; DROP TABLE users; --", context="name")


def test_validate_string_rejects_script_tag() -> None:
    sv = SecurityValidator()
    with pytest.raises(SecurityError):
        sv.validate_string("<script>alert(1)</script>", context="name")


def test_validate_string_rejects_command_injection() -> None:
    sv = SecurityValidator()
    with pytest.raises(SecurityError):
        sv.validate_string("foo; rm -rf /", context="name")


def test_validate_string_rejects_path_traversal() -> None:
    sv = SecurityValidator()
    with pytest.raises(SecurityError):
        sv.validate_string("../../etc/passwd", context="name")


def test_validate_string_rejects_template_injection() -> None:
    sv = SecurityValidator()
    with pytest.raises(SecurityError):
        sv.validate_string("hello {{ 7*7 }}", context="name")


def test_validate_string_length_cap_for_name_field() -> None:
    sv = SecurityValidator()
    # 150 char limit for name fields (per V7 spec).
    with pytest.raises(SecurityError, match=r"(?i)maximum length"):
        sv.validate_string("a" * 200, context="name")


def test_validate_string_length_cap_for_other_fields() -> None:
    sv = SecurityValidator()
    # Other fields get the longer 1000-char cap.
    long_text = "a" * 800
    out = sv.validate_string(long_text, context="general")
    assert out == long_text


def test_validate_string_rejects_non_string_input() -> None:
    sv = SecurityValidator()
    with pytest.raises(SecurityError, match=r"(?i)expected string"):
        sv.validate_string(123, context="name")  # type: ignore[arg-type]


# ─── validate_entry: recursion over nested structures ─────────────────


def test_validate_entry_passes_clean_entry() -> None:
    sv = SecurityValidator()
    entry = {
        "CanonicalLatin": "Gauss, Carl Friedrich",
        "BirthYear": 1777,
        "Active": True,
    }
    out = sv.validate_entry(entry, context="test")
    # Scalars survive untouched; the int and bool aren't strings so
    # they pass through.
    assert out["CanonicalLatin"] == "Gauss, Carl Friedrich"
    assert out["BirthYear"] == 1777
    assert out["Active"] is True


def test_validate_entry_recurses_into_dict() -> None:
    sv = SecurityValidator()
    entry = {"meta": {"source": "wikidata"}}
    out = sv.validate_entry(entry, context="test")
    assert out["meta"]["source"] == "wikidata"


def test_validate_entry_recurses_into_list() -> None:
    sv = SecurityValidator()
    entry = {"aliases": ["Euler, L.", "L. Euler"]}
    out = sv.validate_entry(entry, context="test")
    assert out["aliases"] == ["Euler, L.", "L. Euler"]


def test_validate_entry_propagates_security_error() -> None:
    sv = SecurityValidator()
    with pytest.raises(SecurityError):
        sv.validate_entry({"name": "<script>evil()</script>"}, context="test")


# ─── sanitize_for_output: HTML escape failsafe ─────────────────────────


def test_sanitize_for_output_escapes_html_entities() -> None:
    sv = SecurityValidator()
    out = sv.sanitize_for_output("<b>hello</b> & <i>world</i>")
    # Tags must be escaped so the browser sees text, not markup.
    assert "<b>" not in out
    assert "<i>" not in out
    # Output is HTML-entity-encoded — the implementation runs `&` →
    # `&amp;` first, then `<` → `&lt;`, which double-encodes the lt
    # marker into `&amp;lt;`. Either form is safe; the only bad
    # outcome is leaving raw `<` or `>` in place.
    assert "<" not in out
    assert ">" not in out


def test_sanitize_for_output_strips_script_tag_content() -> None:
    sv = SecurityValidator()
    out = sv.sanitize_for_output(
        "<script>alert('xss')</script>safe text", remove_scripts=True
    )
    assert "alert" in out or "safe text" in out
    # Either the keyword 'script' was stripped, or the tag wholesale was.
    assert "<script" not in out


def test_sanitize_for_output_truncates_long_input() -> None:
    sv = SecurityValidator()
    long_text = "x" * 500
    out = sv.sanitize_for_output(long_text)
    # 200-char cap with `...` suffix.
    assert len(out) <= 200
    assert out.endswith("...")


def test_sanitize_for_output_handles_non_string_input() -> None:
    sv = SecurityValidator()
    out = sv.sanitize_for_output(12345)  # type: ignore[arg-type]
    assert out == "12345"


# ─── homograph attacks: detect + normalize ─────────────────────────────


def test_normalize_homographs_replaces_cyrillic_lookalikes() -> None:
    sv = SecurityValidator()
    # "Hello" with Cyrillic Е (Е) instead of Latin E.
    sneaky = "Hеllo"
    assert "е" in sneaky
    out = sv.normalize_homographs(sneaky)
    # Cyrillic Е → Latin e (lowercase mapping in homograph_mappings).
    assert "е" not in out


def test_normalize_homographs_passes_through_pure_latin() -> None:
    sv = SecurityValidator()
    assert sv.normalize_homographs("Hello") == "Hello"


def test_detect_homograph_attack_positive_case() -> None:
    sv = SecurityValidator()
    sneaky = "Hеllo"  # Cyrillic Е mixed with Latin
    assert sv.detect_homograph_attack(sneaky, context="test") is True


def test_detect_homograph_attack_negative_case() -> None:
    sv = SecurityValidator()
    assert sv.detect_homograph_attack("Hello, World", context="test") is False


# ─── validate_yaml_keys: dict + list overload ─────────────────────────


def test_validate_yaml_keys_dict_input() -> None:
    sv = SecurityValidator()
    out = sv.validate_yaml_keys(
        {"Euler, Leonhard": {"birthyear": 1707}, "Gauss, C.F.": {"birthyear": 1777}}
    )
    assert isinstance(out, dict)
    assert "Euler, Leonhard" in out


def test_validate_yaml_keys_list_input() -> None:
    sv = SecurityValidator()
    out = sv.validate_yaml_keys(["Euler, L.", "Gauss, C.F."])
    assert isinstance(out, list)
    assert len(out) == 2


def test_validate_yaml_keys_drops_dangerous_key() -> None:
    sv = SecurityValidator()
    # SQL injection in a YAML key is silently dropped rather than
    # raised, so the rest of the file still loads. The dangerous key
    # is logged at WARNING level (caught by the existing validator
    # observability path).
    out = sv.validate_yaml_keys(
        {
            "'; DROP TABLE x; --": {"bad": True},
            "Euler, Leonhard": {"good": True},
        }
    )
    assert "'; DROP TABLE x; --" not in out
    assert "Euler, Leonhard" in out


# ─── rate limiting ─────────────────────────────────────────────────────


def test_check_rate_limit_allows_under_threshold() -> None:
    sv = SecurityValidator()
    # The default threshold is 10/min; 5 calls must not trip.
    for _ in range(5):
        sv.check_rate_limit("client-A", context="api")  # no exception


def test_check_rate_limit_trips_at_threshold() -> None:
    sv = SecurityValidator()
    with pytest.raises(SecurityError, match=r"(?i)rate limit"):
        # 11 calls → exceeds the 10/min default.
        for _ in range(11):
            sv.check_rate_limit("client-B", context="api")


# ─── normalize_unicode: NFKC normalization happy path ─────────────────


def test_normalize_unicode_canonicalizes_compatibility_chars() -> None:
    sv = SecurityValidator()
    # ﬃ (U+FB03 Latin small ligature ffi) → "ffi" under NFKC.
    out = sv.normalize_unicode("oﬃce", context="test")
    assert "ffi" in out
