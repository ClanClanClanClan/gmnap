from __future__ import annotations
import unicodedata, re
from typing import Dict, Any, Iterable

# Control and zero-width characters commonly removed
_ZW = [
    "\u200B",
    "\u200C",
    "\u200D",
    "\u2060",  # ZWSP, ZWNJ, ZWJ, WJ
    "\uFEFF",  # ZWNBSP/BOM
]
_CTRL_PATTERN = re.compile(r"[\u0000-\u001F\u007F]")

# Fold exceptions (spec glossary id 16)
_FOLD_MAP = {
    "ß": "ss",
    "ẞ": "SS",
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "Æ": "AE",
    "æ": "ae",
    "Œ": "OE",
    "œ": "oe",
}


def unicode_fold_exceptions(s: str) -> str:
    out = []
    for ch in s:
        out.append(_FOLD_MAP.get(ch, ch))
    return "".join(out)


def normalise_text(s: str) -> str:
    """NFC→NFKD→fold(exceptions)→strip ZW/control→NFC (idempotent)."""
    if not isinstance(s, str):
        return s
    s = unicodedata.normalize("NFC", s)
    s = unicodedata.normalize("NFKD", s)
    s = unicode_fold_exceptions(s)
    for zw in _ZW:
        s = s.replace(zw, "")
    s = _CTRL_PATTERN.sub("", s)
    s = unicodedata.normalize("NFC", s)
    # Collapse multiple spaces; trim
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalise_entry_strings(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively normalise all string values in an entry (immutable)."""

    def norm(o):
        if isinstance(o, str):
            return normalise_text(o)
        if isinstance(o, list):
            return [norm(x) for x in o]
        if isinstance(o, dict):
            return {k: norm(v) for k, v in o.items()}
        return o

    return norm(dict(entry))
