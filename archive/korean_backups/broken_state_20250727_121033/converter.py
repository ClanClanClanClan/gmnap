import pynini as pn, pathlib
from fst_utils import first_output
from preprocess_fixed import tokenise
from segment_fixed import segment
from lookup import rom2han
import unicodedata
import re

def _dice(a,b):
    # Normalize like validation does - remove punctuation and normalize
    a = "" if not a else a.replace(",", "").replace("-", " ")
    b = "" if not b else b.replace(",", "").replace("-", " ")
    a = b"" if not a else unicodedata.normalize("NFC",a.casefold().replace(" ","")).encode()
    b = b"" if not b else unicodedata.normalize("NFC",b.casefold().replace(" ","")).encode()
    bigr=lambda s:{s[i:i+2] for i in range(len(s)-1)}
    x,y=bigr(a),bigr(b); return (2*len(x&y))/(len(x)+len(y) or 1)
import os
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM2 = pn.Fst.read(os.path.join(_BASE_DIR, "models/rom2han_multi.fst"))
HAN2 = pn.Fst.read(os.path.join(_BASE_DIR, "models/han2rom_multi.fst"))
TOK=None      # default token‑type

# ---------- build position‑aware variant dict ----------
import csv
_var = {}           # roman → {tag: hangul}
try:
    for row in csv.reader(open(
            pathlib.Path(__file__).parent.parent / "resources" / "variant_map.csv",
            encoding="utf8")):
        if not row:  # Skip empty rows
            continue
        if len(row) < 2:
            continue
        h, r = row[0], row[1]
        tag = row[2] if len(row) > 2 else ""
        if not r or r.startswith("#") or h.startswith("#"):
            continue
        key = tag.upper() if tag else ""  # "", SURNAME_0, GIVEN_0 …
        _var.setdefault(r.lower(), {})[key] = h
except FileNotFoundError:
    print("Warning: variant_map.csv not found, variant lookup disabled")
# -------------------------------------------------------
def _rr2han(rr): return first_output(pn.accep(rr)@ROM2) or rom2han().get(rr)

def _pick_variant(rr: str, is_surname: bool):
    cand = _var.get(rr)
    if not cand:
        return None
    if is_surname:
        return cand.get("SURNAME_0") or cand.get("")
    # given-name context
    return cand.get("GIVEN_0") or cand.get("") or cand.get("GIVEN_RARE")

def _token_to_hangul(tok: str, is_surname: bool = False) -> str:
    """Convert a single token to Hangul using existing logic."""
    out = []
    rom = re.sub(r"[,\s]", "", tok.lower())
    # ❶ position‑aware variant check
    h = _pick_variant(rom, is_surname=is_surname)
    if h:
        return h
    # ❷ existing hyphen split + segment fallback
    for part in tok.split("-"):
        h = _pick_variant(part.lower(), is_surname=False)
        if h:
            out.append(h)
            continue
        for syl in segment(part):
            h = _rr2han(syl)
            if h is None:
                return None
            out.append(h)
    return "".join(out)

def eng2kor(name:str):
    from name_beam import best_name
    
    tokens = tokenise(name)
    
    # Fast path: one short token → old deterministic converter
    if len(tokens) == 1 and len(tokens[0]) <= 4 and "-" not in tokens[0]:
        return _token_to_hangul(tokens[0], is_surname=True)
    
    # Multi-token or complex names → beam search
    return best_name(tokens)
def kor2eng(h:str, original_rr:str|None=None)->str|None:
    # build lattice char by char
    lat = pn.accep("", TOK)
    for i, ch in enumerate(h):
        if i > 0:
            lat = pn.concat(lat, pn.accep(" ", TOK))  # Add space between chars
        lat = pn.concat(lat, (pn.accep(ch, TOK) @ HAN2))
    # project to output to make it an acceptor
    lat = pn.project(lat, "output")
    # get top‑5 paths
    it   = pn.shortestpath(lat, nshortest=50, unique=True).paths()
    outs = list(it.ostrings())   # iterable in 2.1.5
    if not outs: return None
    if original_rr:
        scored=[(_dice(original_rr,o), o) for o in outs]
        return max(scored)[1]
    return outs[0]