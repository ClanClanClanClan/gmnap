from __future__ import annotations
from typing import Dict, Any


def contains_cyrillic(s: str) -> bool:
    return any("\u0400" <= ch <= "\u04ff" for ch in s or "")


def contains_han(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s or "")


def detect_region(entry: Dict[str, Any]) -> str:
    """Very simple script-based detector (spec suggests richer cues; this is baseline)."""
    name = entry.get("CanonicalNative") or entry.get("CanonicalLatin") or ""
    if contains_han(name):
        return "E1"  # Sinophone Mainland
    if contains_cyrillic(name):
        return "B1"  # East-Slavic (handled later)
    # Default to A1 for Latin ASCII
    return "A1"
