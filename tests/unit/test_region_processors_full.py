"""Comprehensive per-region hook coverage.

For each of the 37 region processors, run a realistic entry through
the full hook chain (``clean → augment → validate → order_key``).
Existing tests like ``test_simple_detection.py`` and
``test_region_processors.py`` exercise the *manager*-level dispatch
but stop short of the inner clean / augment / validate paths on most
processors, leaving 200-400 uncovered lines per region.

Round-20 strengthening: the tests now **fail loudly** if a hook
raises on the representative entry. Original draft used
``try/except: pass`` to swallow any exception, which made the tests
coverage-padding (a regression that broke clean() would still let
them pass). Now each test asserts behaviour:

- ``clean(entry)`` runs without raising and ``CanonicalLatin`` is
  preserved (or canonicalized to a non-empty string).
- ``augment(entry)`` runs without raising and ``entry`` is still a
  populated dict.
- ``validate(entry)`` runs without raising on the representative
  entry — that's the point of choosing realistic inputs.
- ``order_key(entry)`` returns a non-empty string.

If any region processor breaks on its representative entry, that's a
real regression signal (either the input drifted out of the region's
accepted shape, or the hook is broken).
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest

from src.regions.manager_optimized import RegionManager

# A representative entry per region. V7 spec: ``CanonicalLatin`` MUST
# be the romanized (Latin-script) form; ``CanonicalNative`` carries
# the native-script form (or duplicates the Latin for natively-Latin
# regions). For B1 Cyrillic / B3 Greek / C* Arabic+Hebrew+Armenian+
# Georgian / D* Indic+Urdu / E1-E3 CJK / E6 Mainland-SEA scripts, the
# native form goes in CanonicalNative — putting it in CanonicalLatin
# trips the region's validate() (correctly).
#
# Tuple: (CanonicalLatin, CanonicalNative, country_code)
ENTRIES: Dict[str, Tuple[str, str, str]] = {
    "A1": ("Newton, Isaac", "Newton, Isaac", "GB"),
    "A2": ("Euler, Leonhard", "Euler, Leonhard", "CH"),
    "A3": ("Abel, Niels Henrik", "Abel, Niels Henrik", "NO"),
    "A4": ("Te Rangi Hiroa, Peter", "Te Rangi Hiroa, Peter", "NZ"),
    "A5": ("Marley, Bob", "Marley, Bob", "JM"),
    "B1": ("Ivanov, Ivan", "Иванов, Иван", "RU"),
    "B2": ("Nowak, Jan", "Nowak, Jan", "PL"),
    "B3": ("Papadopoulos, Yannis", "Παπαδόπουλος, Γιάννης", "GR"),
    "C1": ("Atatürk, Mustafa Kemal", "Atatürk, Mustafa Kemal", "TR"),
    "C2": ("Khwarizmi, Muhammad", "خوارزمی, محمد", "IR"),
    "C3": ("Mahfouz, Naguib", "محفوظ, نجيب", "EG"),
    "C4": ("Al-Saud, Salman", "آل سعود, سلمان", "SA"),
    "C5": ("Ben Ali, Zine El Abidine", "بن علي, زين العابدين", "TN"),
    "C6": ("Cohen, David", "כהן, דוד", "IL"),
    "C7": ("Hayrapetyan, Aram", "Հայրապետյան, Արամ", "AM"),
    "C8": ("Javakhishvili, Iakob", "ჯავახიშვილი, იაკობ", "GE"),
    "C9": ("Smetona, Antanas", "Smetona, Antanas", "LT"),
    "D1": ("Sharma, Ram", "शर्मा, राम", "IN"),
    "D2": ("Murugan, Sundar", "முருகன், சுந்தர்", "IN"),
    "D3": ("Sharma, Ram", "শর্মা, রাম", "BD"),
    "D4": ("Ali, Muhammad", "علی, محمد", "PK"),
    "D5": ("Pieris, Ralph", "Pieris, Ralph", "LK"),
    "E1": ("Zhang, Wei", "张, 伟", "CN"),
    "E2": ("Chen, Ta-Wen", "陳, 大文", "TW"),
    "E3": ("Tanaka, Taro", "田中, 太郎", "JP"),
    "E4": ("Kim, Jong-Un", "김정은", "KR"),
    "E5": ("Nguyễn, Văn A", "Nguyễn, Văn A", "VN"),
    "E6": ("Smith, John", "สมิท, จอห์น", "TH"),
    "E7": ("Soekarno, Ahmad", "Soekarno, Ahmad", "ID"),
    "F1": ("Sankara, Thomas", "Sankara, Thomas", "BF"),
    "F2": ("Adichie, Chimamanda", "Adichie, Chimamanda", "NG"),
    "F3": ("Selassie, Haile", "Selassie, Haile", "ET"),
    "F4": ("Cabral, Amílcar", "Cabral, Amílcar", "GW"),
    "G1": ("García Márquez, Gabriel", "García Márquez, Gabriel", "CO"),
    "H1": ("Pythagoras", "Pythagoras", ""),  # mononym
    "R0": ("Smith, John", "Smith, John", ""),  # generic Latin fallback
    "Z0": ("Test, User", "Test, User", ""),  # quarantine
}


@pytest.fixture(scope="module")
def manager() -> RegionManager:
    """Single shared RegionManager — region loading is expensive."""
    m = RegionManager()
    m._ensure_regions_loaded()
    return m


def _entry_for(code: str) -> Dict[str, Any]:
    latin, native, cc = ENTRIES[code]
    e: Dict[str, Any] = {
        "CanonicalLatin": latin,
        "CanonicalNative": native,
        "Confidence": 0.9,
    }
    if cc:
        e["CountryCodes"] = [cc]
    return e


# Parametrize over every region code. One test per region — keeps the
# failure surface clean (a broken hook in one region shouldn't blame
# 36 others).
@pytest.mark.parametrize("code", sorted(ENTRIES.keys()))
def test_region_processor_clean_hook(manager: RegionManager, code: str) -> None:
    processor = manager._regions.get(code)
    assert processor is not None, f"region {code} not loaded"
    entry = _entry_for(code)
    processor.clean(entry)
    # Clean must preserve identity at least — CanonicalLatin should
    # remain populated (it might be canonicalised to a different
    # case / normalisation form, but it should not be wiped).
    assert entry.get(
        "CanonicalLatin"
    ), f"{code}.clean() emptied CanonicalLatin (was {ENTRIES[code][0]!r})"


@pytest.mark.parametrize("code", sorted(ENTRIES.keys()))
def test_region_processor_augment_hook(manager: RegionManager, code: str) -> None:
    processor = manager._regions.get(code)
    assert processor is not None
    entry = _entry_for(code)
    processor.clean(entry)
    processor.augment(entry)
    assert isinstance(entry, dict) and entry, f"{code}.augment() emptied the entry"
    assert entry.get("CanonicalLatin"), f"{code}.augment() emptied CanonicalLatin"


@pytest.mark.parametrize("code", sorted(ENTRIES.keys()))
def test_region_processor_validate_hook(manager: RegionManager, code: str) -> None:
    processor = manager._regions.get(code)
    assert processor is not None
    entry = _entry_for(code)
    processor.clean(entry)
    processor.augment(entry)
    # validate() raises RegionRuleError on a bad entry. The
    # representative entry is hand-chosen to be valid, so this should
    # not raise. If it does, either the entry drifted out of the
    # region's accepted shape (fix the entry) or the hook is broken
    # (fix the hook). Either way it's a real regression signal.
    processor.validate(entry)


@pytest.mark.parametrize("code", sorted(ENTRIES.keys()))
def test_region_processor_order_key_hook(manager: RegionManager, code: str) -> None:
    processor = manager._regions.get(code)
    assert processor is not None
    entry = _entry_for(code)
    # order_key reads from `RegionalExtras` which is populated by
    # augment() — must run the full clean → augment chain first.
    processor.clean(entry)
    processor.augment(entry)
    key = processor.order_key(entry)
    assert isinstance(key, str), f"{code}.order_key() returned {type(key).__name__}"
    assert key, f"{code}.order_key() returned empty string after clean+augment"


# ─── RegionManager dispatch coverage ──────────────────────────────────


@pytest.mark.parametrize("code", sorted(ENTRIES.keys()))
def test_region_manager_detect_region_returns_result(
    manager: RegionManager, code: str
) -> None:
    """Drive RegionManager.detect_region for each region with the
    representative entry. Covers the dispatch + script analysis +
    overlay + diaspora paths in manager_optimized.py."""
    latin, native, cc = ENTRIES[code]
    entry: Dict[str, Any] = {"CanonicalLatin": latin, "CanonicalNative": native}
    if cc:
        entry["CountryCodes"] = [cc]
    result = manager.detect_region(entry)
    # We don't assert the detected region equals `code` — region
    # detection is intentionally cautious and may abstain (R0) for
    # entries the rules can't pin down. But the result must be a
    # `RegionDetectionResult` with a non-empty `region_code` and a
    # numeric confidence.
    assert result is not None, f"detect_region returned None for {code}"
    assert hasattr(
        result, "region_code"
    ), f"result for {code} missing `region_code` attr"
    assert result.region_code, f"result.region_code empty for {code}"
    assert isinstance(
        result.confidence, (int, float)
    ), f"result.confidence has type {type(result.confidence).__name__}"
    assert (
        0.0 <= float(result.confidence) <= 1.0
    ), f"result.confidence={result.confidence} out of [0, 1]"


def test_region_manager_get_region_returns_processor(manager: RegionManager) -> None:
    p = manager.get_region("A1")
    assert p is not None
    assert hasattr(p, "code")
    assert p.code == "A1"


def test_region_manager_get_region_unknown_returns_none(manager: RegionManager) -> None:
    assert manager.get_region("ZZ_NOT_REAL") is None


def test_region_manager_lists_all_37_regions(manager: RegionManager) -> None:
    assert len(manager._regions) == 37


# ─── batch detection — exercises batch path through detect_region ─────


def test_region_manager_detects_batch_of_diverse_entries(
    manager: RegionManager,
) -> None:
    # 12 mixed-region entries, run as a batch via repeated calls. The
    # point is to drive the cache hot/cold paths in manager_optimized.
    entries = [
        {
            "CanonicalLatin": ENTRIES[c][0],
            "CanonicalNative": ENTRIES[c][1],
            "CountryCodes": [ENTRIES[c][2]] if ENTRIES[c][2] else [],
        }
        for c in [
            "A1",
            "A2",
            "B1",
            "C2",
            "D1",
            "E1",
            "E3",
            "F2",
            "G1",
            "H1",
            "R0",
            "Z0",
        ]
    ]
    results = [manager.detect_region(e) for e in entries]
    assert len(results) == 12
    assert all(r is not None for r in results)


# ─── ICU + script-detect paths via mixed-script inputs ────────────────


def test_region_manager_handles_mixed_script_input(manager: RegionManager) -> None:
    """An entry with both Latin and CJK characters exercises the
    script-analyzer + script-switch fallback."""
    e = {"CanonicalLatin": "Tanaka 田中, Taro", "CountryCodes": ["JP"]}
    r = manager.detect_region(e)
    assert r is not None


def test_region_manager_handles_cyrillic_only_input(
    manager: RegionManager,
) -> None:
    e = {"CanonicalLatin": "", "CanonicalNative": "Иванов, Иван"}
    r = manager.detect_region(e)
    assert r is not None


def test_region_manager_handles_arabic_only_input(manager: RegionManager) -> None:
    e = {"CanonicalLatin": "", "CanonicalNative": "محمد بن موسى"}
    r = manager.detect_region(e)
    assert r is not None


def test_region_manager_handles_empty_entry(manager: RegionManager) -> None:
    """Pathological input — empty entry shouldn't crash, should
    abstain (R0 / Z0 / similar)."""
    r = manager.detect_region({})
    assert r is not None


def test_region_manager_handles_only_country_code(
    manager: RegionManager,
) -> None:
    """No name, just a country code — geo-only path."""
    e = {"CountryCodes": ["DE"]}
    r = manager.detect_region(e)
    assert r is not None
