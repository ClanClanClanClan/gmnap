#!/usr/bin/env python3
# Generate Korean name corpus (10k by default) with RR-based romanisation.
import argparse
import json
import random

CHO = [
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
JUNG = [
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
JONG = [
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
SURNAMES = [
    "이",
    "김",
    "박",
    "최",
    "정",
    "문",
    "윤",
    "임",
    "강",
    "조",
    "장",
    "한",
    "오",
    "신",
    "유",
    "황",
    "안",
    "송",
    "홍",
    "서",
    "원",
]


def decompose_hangul(ch):
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        sindex = code - 0xAC00
        cho = sindex // 588
        jung = (sindex % 588) // 28
        jong = sindex % 28
        return cho, jung, jong
    return None


def romanise_syllable(ch):
    d = decompose_hangul(ch)
    if d is None:
        return ch
    cho, jung, jong = d
    lead = CHO[cho]
    if lead == "":
        lead = ""
    if CHO[cho] == "r":
        lead = "r"
    vowel = JUNG[jung]
    tail = JONG[jong]
    return lead + vowel + tail


def romanise_name(name_native):
    name_native = name_native.strip()
    if not name_native:
        return ""
    sn = name_native[0]
    given = name_native[1:]
    surname_map = {
        "이": "Lee",
        "김": "Kim",
        "박": "Park",
        "최": "Choi",
        "정": "Jung",
        "문": "Moon",
        "윤": "Yoon",
        "임": "Lim",
        "강": "Kang",
        "조": "Cho",
        "장": "Jang",
        "한": "Han",
        "오": "Oh",
        "신": "Shin",
        "유": "Yoo",
        "황": "Hwang",
        "안": "Ahn",
        "송": "Song",
        "홍": "Hong",
        "서": "Seo",
        "원": "Won",
    }
    surname = surname_map.get(sn, romanise_syllable(sn).capitalize())
    parts = [romanise_syllable(ch).capitalize() for ch in given]
    return surname + (" " + "-".join(parts) if parts else "")


def main(N=10000, seed=42, out="datasets/korean/korean_test_corpus_10k.json"):
    random.seed(seed)
    data = []
    for i in range(N):
        sn = random.choice(SURNAMES)
        gl = random.choice([2, 2, 2, 3])
        given = ""
        for _ in range(gl):
            base = 0xAC00 + random.randint(0, 11171)
            given += chr(base)
        native = sn + given
        latin = romanise_name(native)
        data.append({"native": native, "latin": latin})
    import json
    import os
    import pathlib

    p = pathlib.Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Wrote {len(data)} pairs to {p}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--out", default="datasets/korean/korean_test_corpus_10k.json")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    main(a.n, a.seed, a.out)
