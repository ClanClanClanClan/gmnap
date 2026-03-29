from __future__ import annotations


def contains_range(s: str, start: int, end: int) -> bool:
    return any(start <= ord(ch) <= end for ch in s or "")


def has_cyrillic(s: str) -> bool:
    return contains_range(s, 0x0400, 0x04FF)


def has_greek(s: str) -> bool:
    return contains_range(s, 0x0370, 0x03FF)


def has_han(s: str) -> bool:
    return contains_range(s, 0x4E00, 0x9FFF) or contains_range(s, 0x3400, 0x4DBF)


def has_hangul(s: str) -> bool:
    return contains_range(s, 0xAC00, 0xD7AF) or contains_range(s, 0x1100, 0x11FF)


def has_arabic(s: str) -> bool:
    return contains_range(s, 0x0600, 0x06FF) or contains_range(s, 0x0750, 0x077F)


def has_hebrew(s: str) -> bool:
    return contains_range(s, 0x0590, 0x05FF)


def has_devanagari(s: str) -> bool:
    return contains_range(s, 0x0900, 0x097F)


def has_thai(s: str) -> bool:
    return contains_range(s, 0x0E00, 0x0E7F)


def has_khmer(s: str) -> bool:
    return contains_range(s, 0x1780, 0x17FF)


def has_lao(s: str) -> bool:
    return contains_range(s, 0x0E80, 0x0EFF)


def has_georgian(s: str) -> bool:
    return contains_range(s, 0x10A0, 0x10FF)


def has_armenian(s: str) -> bool:
    return contains_range(s, 0x0530, 0x058F)


def primary_script(name: str) -> str:
    s = name or ""
    if has_han(s):
        return "Han"
    if has_hangul(s):
        return "Hangul"
    if has_cyrillic(s):
        return "Cyrillic"
    if has_greek(s):
        return "Greek"
    if has_arabic(s):
        return "Arabic"
    if has_hebrew(s):
        return "Hebrew"
    if has_devanagari(s):
        return "Devanagari"
    if has_thai(s):
        return "Thai"
    if has_khmer(s):
        return "Khmer"
    if has_lao(s):
        return "Lao"
    if has_georgian(s):
        return "Georgian"
    if has_armenian(s):
        return "Armenian"
    return "Latin"
