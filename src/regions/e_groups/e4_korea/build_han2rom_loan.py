import pathlib
import unicodedata

import pynini as pn

tsv = pathlib.Path("resources/loanword_en2kor.tsv").read_text().splitlines()
pairs = [(k.strip(), v.strip()) for k, v, *_ in (l.split("\t") for l in tsv)]
# Build ENG→KOR (already done), now KOR→ENG:
han2rom = pn.Fst()
for eng, han in pairs:
    eng_norm = unicodedata.normalize("NFC", eng)
    han_norm = unicodedata.normalize("NFC", han)
    han2rom |= pn.cross(han_norm, eng_norm)
han2rom = pn.optimize(han2rom)
# Add weight gate to protect Math
han2rom = pn.arcmap(han2rom, map_type="to_log")
han2rom = han2rom.closure()  # Make sure it's a proper acceptor
# Create weighted version
weighted_han2rom = pn.Fst()
for eng, han in pairs:
    eng_norm = unicodedata.normalize("NFC", eng)
    han_norm = unicodedata.normalize("NFC", han)
    arc = pn.accep(han_norm, weight=1.5) @ pn.cross(han_norm, eng_norm)
    weighted_han2rom |= arc
weighted_han2rom.optimize().write("models/han2rom_loan.fst")
print("🆗  han2rom_loan.fst written")
