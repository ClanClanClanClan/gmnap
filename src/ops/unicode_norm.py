from __future__ import annotations
import unicodedata, re

# Basic fold map (can be extended; spec lists several exceptions)
_FOLD = {
    "\u00df": "ss",  # ß
    "\u1e9e": "SS",  # ẞ
    "\u00a0": " ",  # NBSP
}

_CONTROL_RE = re.compile(r"[\u0000-\u001F\u007F]")  # ASCII control chars


def nfc_nfkd_fold_nfc(s: str) -> str:
    """NFC → NFKD (strip combining) → fold (few exceptions) → NFC. Also drop control chars."""
    if s is None:
        return s
    s1 = unicodedata.normalize("NFC", s)
    s2 = unicodedata.normalize("NFKD", s1)
    s3 = "".join(ch for ch in s2 if not unicodedata.combining(ch))
    # simple fold
    out = "".join(_FOLD.get(ch, ch) for ch in s3)
    out = _CONTROL_RE.sub("", out)
    return unicodedata.normalize("NFC", out)


def normalise_text(text):
    """Normalize text using Unicode normalization"""
    return unicodedata.normalize("NFC", text)


def normalise_entry_strings(entry):
    """Normalise all string values in an entry dict to NFC."""
    if isinstance(entry, dict):
        return {
            k: unicodedata.normalize("NFC", v) if isinstance(v, str) else v
            for k, v in entry.items()
        }
    return entry
