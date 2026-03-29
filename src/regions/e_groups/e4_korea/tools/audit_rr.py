#!/usr/bin/env python3
"""
Find impossible Hangul ↔ roman pairs, e.g. han='뮹', rom='myeong'.
Rule-of-thumb heuristics are encoded in SUSPECT().
"""

import csv
import json
import pathlib
import re
import unicodedata as U

RR = pathlib.Path(__file__).parents[1] / "resources" / "rr_syllable_map.csv"
suspects = []


def sus(h, r, *why):
    suspects.append(dict(h=h, r=r, line=ln, why="/".join(why)))


pattern_rom = re.compile(r"^[a-z]+$")


def SUSPECT(h, r):
    # Skip empty strings
    if not h or not r:
        return True

    # 1. Hangul should be single character in Syllables block U+AC00–U+D7A3
    if len(h) != 1 or not (0xAC00 <= ord(h) <= 0xD7A3):
        return True

    # 2. rom must be lowercase alpha
    if not pattern_rom.fullmatch(r):
        return True

    # 3. NFKD should not contain Compatibility Jamo
    if any(0x3130 <= ord(c) <= 0x318F for c in U.normalize("NFKD", h)):
        return True

    return False


for ln, row in enumerate(csv.reader(RR.open(encoding="utf8")), 1):
    if len(row) < 2 or row[0].startswith("#"):
        continue
    h, r = row[0], row[1]
    if SUSPECT(h, r):
        sus(h, r, "format")

    # heuristic: mismatch list
    wrong = {
        "뮹": "myeong",
        "밬": "bak",
        "둑": "deok",
        "쿤": "geon",
        "볶": "bok",
        "돜": "dok",
        "탴": "taek",
        "핰": "hak",
        "욜": "yeol",
    }
    if h in wrong and r == wrong[h]:
        sus(h, r, "obvious-mistake")

with open("suspects.json", "w", encoding="utf8") as f:
    json.dump(suspects, f, ensure_ascii=False, indent=2)

print(f"{len(suspects)} suspect rows written → suspects.json")
