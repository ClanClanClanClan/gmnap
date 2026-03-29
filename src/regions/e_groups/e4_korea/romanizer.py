"""
Context-aware Korean romanizer with standards support.
Supports RR strict, RR common (international usage), and McCune-Reischauer.
"""

from __future__ import annotations

import json
import unicodedata as _ud
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

# Hangul decomposition constants
_SBASE = 0xAC00
_LCOUNT = 19
_VCOUNT = 21
_TCOUNT = 28
_NCOUNT = _VCOUNT * _TCOUNT

# Revised Romanization tables
_CHO_RR = [
    "g",
    "kk",
    "n",
    "d",
    "tt",
    "r",
    "m",
    "b",
    "pp",
    "s",
    "ss",
    "",
    "j",
    "jj",
    "ch",
    "k",
    "t",
    "p",
    "h",
]
_JUNG_RR = [
    "a",
    "ae",
    "ya",
    "yae",
    "eo",
    "e",
    "yeo",
    "ye",
    "o",
    "wa",
    "wae",
    "oe",
    "yo",
    "u",
    "wo",
    "we",
    "wi",
    "yu",
    "eu",
    "ui",
    "i",
]
_JONG_RR = [
    "",
    "k",
    "k",
    "k",
    "n",
    "n",
    "n",
    "t",
    "l",
    "k",
    "m",
    "p",
    "l",
    "l",
    "p",
    "l",
    "m",
    "p",
    "p",
    "t",
    "t",
    "ng",
    "t",
    "t",
    "k",
    "t",
    "p",
    "t",
]

# McCune-Reischauer tables
_CHO_MR = [
    "k",
    "kk",
    "n",
    "t",
    "tt",
    "r",
    "m",
    "p",
    "pp",
    "s",
    "ss",
    "",
    "ch",
    "tch",
    "ch'",
    "k'",
    "t'",
    "p'",
    "h",
]
_JUNG_MR = [
    "a",
    "ae",
    "ya",
    "yae",
    "ŏ",
    "e",
    "yŏ",
    "ye",
    "o",
    "wa",
    "wae",
    "oe",
    "yo",
    "u",
    "wŏ",
    "we",
    "wi",
    "yu",
    "ŭ",
    "ŭi",
    "i",
]
_JONG_MR = _JONG_RR[:]  # finals largely identical

# Common-name normalizations for international usage
_GIVEN_SYLLABLE_ALIASES = {
    "yeong": "young",
    "seong": "sung",
    "jeong": "jung",
    "hui": "hee",
    "u": "woo",
}

# Title patterns (Korean, RR transliteration, English translation)
_TITLES = [("대왕", "Daewang", "King"), ("왕", "Wang", "King")]


def _is_hangul_char(ch: str) -> bool:
    """Check if character is Hangul syllable."""
    return 0xAC00 <= ord(ch) <= 0xD7A3


def _decompose(ch: str) -> Optional[Tuple[int, int, int]]:
    """Decompose Hangul syllable into L, V, T components."""
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        sindex = code - _SBASE
        L = sindex // _NCOUNT
        V = (sindex % _NCOUNT) // _TCOUNT
        T = sindex % _TCOUNT
        return L, V, T
    return None


def _romanise_syllable(ch: str, standard: str, position: str) -> str:
    """Romanize single Hangul syllable. Position currently unused but available for context."""
    d = _decompose(ch)
    if d is None:
        return ch

    L, V, T = d
    if standard.startswith("rr"):
        lead = _CHO_RR[L]
        vowel = _JUNG_RR[V]
        tail = _JONG_RR[T]
        return f"{lead}{vowel}{tail}"
    elif standard == "mr":
        lead = _CHO_MR[L]
        vowel = _JUNG_MR[V]
        tail = _JONG_MR[T]
        return f"{lead}{vowel}{tail}"
    else:
        raise ValueError(f"Unknown standard: {standard}")


def _title_rewrite(hangul: str, roman: str, mode: str) -> str:
    """Apply title transformations."""
    if mode == "none":
        return roman

    for han, rr, en in _TITLES:
        if han in hangul:
            if mode == "rr":
                # Replace romanized title with RR version
                return roman.replace(rr, rr)  # Already correct
            elif mode == "english":
                # Move title to front: "Sejong Daewang" -> "King Sejong"
                # Replace the romanized title (rr) with nothing and add English title at front
                parts = roman.replace(rr, "").strip()
                return f"{en} {parts}".strip()
    return roman


@dataclass
class NameStructure:
    """Parsed Korean name structure."""

    surname_ko: str
    given_ko: str
    title_ko: str = ""


class KoreanNameParser:
    """Parse Korean names into surname, given name, and title components."""

    def __init__(self, compound_surnames: Dict[str, str]):
        self.compound = dict(compound_surnames)

    def parse(self, name_ko: str) -> NameStructure:
        """Parse Korean name into structured components."""
        # Normalize and clean
        s = _ud.normalize("NFC", name_ko or "").replace(" ", "").replace("-", "")

        # Extract title suffix
        title = ""
        for t, _, _ in _TITLES:
            if s.endswith(t):
                title = t
                s = s[: -len(t)]
                break

        # Check for compound surname
        if len(s) >= 2 and s[:2] in self.compound:
            return NameStructure(surname_ko=s[:2], given_ko=s[2:], title_ko=title)

        # Default: first syllable is surname
        if len(s) >= 1:
            return NameStructure(surname_ko=s[:1], given_ko=s[1:], title_ko=title)

        return NameStructure(surname_ko="", given_ko="", title_ko=title)


class ContextAwareRomanizer:
    """Context-aware Korean romanizer with multiple standards support."""

    def __init__(
        self,
        standard: str = "rr_common",
        hyphenate_given: bool = True,
        apply_given_aliases: bool = True,
        surname_overrides: Dict[str, str] | None = None,
        sino_overrides: Dict[str, str] | None = None,
        name_overrides: Dict[str, object] | None = None,
        title_handling: str = "english",
    ):
        self.standard = standard
        self.hyphenate_given = hyphenate_given
        self.apply_given_aliases = apply_given_aliases
        self.surname_overrides = surname_overrides or {}
        self.sino_overrides = sino_overrides or {}
        self.name_overrides = name_overrides or {}
        self.title_handling = title_handling

    def _cap(self, s: str) -> str:
        """Capitalize first letter."""
        return s[:1].upper() + s[1:] if s else s

    def romanise_name(self, name_ko: str, structure: NameStructure) -> str:
        """Romanize complete Korean name using structure."""
        # Check for complete name overrides first
        if name_ko in self.name_overrides:
            ov = self.name_overrides[name_ko]
            if isinstance(ov, str):
                return ov
            if isinstance(ov, dict):
                # Choose appropriate standard key
                k = "rr_common" if self.standard.startswith("rr") else "mr"
                return ov.get(k) or next(iter(ov.values()))

        # Check for Sino-Korean overrides
        if name_ko in self.sino_overrides:
            return self.sino_overrides[name_ko]

        # Determine effective standard
        std = (
            "rr_strict"
            if self.standard == "rr_strict"
            else ("mr" if self.standard == "mr" else "rr_common")
        )

        # Romanize surname
        sur_ko = structure.surname_ko
        if std == "mr":
            sur_lat = self._romanise_word(sur_ko, "mr")
        else:
            sur_lat_rr = self._romanise_word(sur_ko, "rr_strict")
            # Apply international usage overrides for rr_common
            sur_lat = (
                self.surname_overrides.get(sur_ko, None)
                if self.standard == "rr_common"
                else None
            )
            if not sur_lat:
                # Special case: 이 → Lee in rr_common
                if sur_ko == "이" and self.standard == "rr_common":
                    sur_lat = "Lee"
                else:
                    sur_lat = self._cap(sur_lat_rr)

        # Romanize given name
        given_lat = self._romanise_given(structure.given_ko, std)

        # Combine surname and given name
        full = f"{sur_lat} {given_lat}".strip()

        # Apply title transformations
        if structure.title_ko:
            full_name_with_title = (
                structure.surname_ko + structure.given_ko + structure.title_ko
            )
            full = _title_rewrite(
                full_name_with_title,
                full,
                self.title_handling if self.standard != "mr" else "rr",
            )

        return full.strip()

    def _romanise_given(self, given_ko: str, std: str) -> str:
        """Romanize given name with proper syllable handling."""
        if not given_ko:
            return ""

        if std == "mr":
            # McCune-Reischauer
            parts = [_romanise_syllable(ch, "mr", "initial") for ch in given_ko]
            parts = [self._cap(p) for p in parts]
            return "-".join(parts) if self.hyphenate_given else "".join(parts)

        # Revised Romanization
        parts = [_romanise_syllable(ch, "rr_strict", "initial") for ch in given_ko]

        # Apply given name aliases for international usage BEFORE capitalization
        if self.apply_given_aliases and self.standard == "rr_common":
            aliased = [_GIVEN_SYLLABLE_ALIASES.get(p, p) for p in parts]
        else:
            aliased = parts

        # Capitalize only the first syllable (Korean naming convention)
        if aliased:
            capitalized = [self._cap(aliased[0])]  # First syllable capitalized
            capitalized.extend(p.lower() for p in aliased[1:])  # Rest lowercase
        else:
            capitalized = aliased

        return "-".join(capitalized) if self.hyphenate_given else "".join(capitalized)

    def _romanise_word(self, s: str, std: str) -> str:
        """Romanize word as sequence of syllables."""
        parts = [
            _romanise_syllable(
                ch, "rr_strict" if std.startswith("rr") else "mr", "initial"
            )
            for ch in s
        ]
        return "".join(parts)


def load_resources(base: str | Path) -> tuple[dict, dict, dict]:
    """Load all Korean romanization resource files."""
    base = Path(base)

    compound = json.loads((base / "compound_surnames.json").read_text(encoding="utf-8"))
    surname_overrides = json.loads(
        (base / "surname_overrides_common.json").read_text(encoding="utf-8")
    )
    sino_overrides = json.loads(
        (base / "sino_overrides.json").read_text(encoding="utf-8")
    )

    return compound, surname_overrides, sino_overrides
