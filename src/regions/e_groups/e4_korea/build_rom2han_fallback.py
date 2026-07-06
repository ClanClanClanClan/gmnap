"""Build models/rom2han_fallback.fst — the ENG->KOR loanword fallback.

RECONSTRUCTED (R51): the converter has always read this FST (per the
2025-08-01 handoff: "rom2han_fallback.fst — Loanword mappings") but no
builder survived anywhere in git history — the sibling
build_han2rom_loan.py builds the KOR->ENG direction and notes
"ENG->KOR (already done)", referring to a script that was never
committed. This mirrors that builder in the opposite direction, with the
same weight gate so signature syllable mappings still win over loanword
fallbacks. Run with cwd = this directory (reads resources/, writes models/).
"""

import pathlib
import unicodedata

import pynini as pn

tsv = pathlib.Path("resources/loanword_en2kor.tsv").read_text().splitlines()
pairs = [(k.strip(), v.strip()) for k, v, *_ in (l.split("\t") for l in tsv)]

weighted_rom2han = pn.Fst()
for eng, han in pairs:
    eng_norm = unicodedata.normalize("NFC", eng)
    han_norm = unicodedata.normalize("NFC", han)
    arc = pn.accep(eng_norm, weight=1.5) @ pn.cross(eng_norm, han_norm)
    weighted_rom2han |= arc

pathlib.Path("models").mkdir(exist_ok=True)
weighted_rom2han.optimize().write("models/rom2han_fallback.fst")
print("🆗  rom2han_fallback.fst written")
