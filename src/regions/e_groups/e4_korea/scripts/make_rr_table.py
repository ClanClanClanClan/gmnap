# -*- coding: utf-8 -*-
import csv
import pathlib

BASE, L, V, T = 0xAC00, 19, 21, 28
LEADS = [
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
VOW = [
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
TAIL = [
    "",
    "k",
    "k",
    "ks",
    "n",
    "nj",
    "nh",
    "t",
    "l",
    "lk",
    "lm",
    "lb",
    "ls",
    "lt",
    "lp",
    "lh",
    "m",
    "p",
    "ps",
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
path = pathlib.Path("resources/rr_syllable_map.csv")
path.parent.mkdir(exist_ok=True)
w = csv.writer(path.open("w", encoding="utf8", newline=""))
for cp in range(BASE, BASE + 11172):
    off = cp - BASE
    lead = off // (V * T)
    v = (off // T) % V
    t = off % T
    w.writerow([chr(cp), LEADS[lead] + VOW[v] + TAIL[t]])
# critical long‑tail syllables
w.writerows([["안", "ahn"], ["철", "cheol"], ["환", "hwan"], ["김", "kim"], ["영", "young"]])
print("✓ resources/rr_syllable_map.csv lines:", sum(1 for _ in open(path)))
