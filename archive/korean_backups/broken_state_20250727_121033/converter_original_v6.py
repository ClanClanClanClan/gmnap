import pynini as pn
from fst_utils import first_output
from preprocess import tokenise
from segment import segment
from lookup import rom2han
import unicodedata
import re
import os

def _dice(a, b):
    # Normalize like validation does - remove punctuation and normalize
    a = "" if not a else a.replace(",", "").replace("-", " ")
    b = "" if not b else b.replace(",", "").replace("-", " ")
    a = b"" if not a else unicodedata.normalize("NFC", a.casefold().replace(" ", "")).encode()
    b = b"" if not b else unicodedata.normalize("NFC", b.casefold().replace(" ", "")).encode()
    bigr = lambda s: {s[i:i+2] for i in range(len(s)-1)}
    x, y = bigr(a), bigr(b); return (2*len(x&y))/(len(x)+len(y) or 1)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM2 = pn.Fst.read(os.path.join(_BASE_DIR, "models/rom2han_multi.fst"))
HAN2 = pn.Fst.read(os.path.join(_BASE_DIR, "models/han2rom_multi.fst"))
TOK = None  # default token type

# Simple variant loading - no position awareness
import csv
_var = {}  # roman -> hangul
try:
    with open(os.path.join(_BASE_DIR, "resources/variant_map.csv"), encoding="utf8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0] and row[1] and not row[0].startswith("#"):
                h, r = row[0], row[1]
                _var[r.lower()] = h
except FileNotFoundError:
    print("Warning: variant_map.csv not found, variant lookup disabled")

def _rr2han(rr): 
    return first_output(pn.accep(rr) @ ROM2) or rom2han().get(rr)

def eng2kor(name: str):
    tokens = tokenise(name)
    out = []
    
    for i, tok in enumerate(tokens):
        # Clean the token
        rom = re.sub(r"[,\s]", "", tok.lower())
        
        # First check variant map
        h = _var.get(rom)
        if h:
            out.append(h)
            continue
            
        # Handle hyphens by splitting
        tok_out = []
        for part in tok.split("-"):
            # Check variant for each part
            h = _var.get(part.lower())
            if h:
                tok_out.append(h)
                continue
                
            # Segment and convert syllables
            for syl in segment(part):
                h = _rr2han(syl)
                if h is None:
                    return None
                tok_out.append(h)
        
        out.append("".join(tok_out))
    
    return "".join(out)

def kor2eng(h: str, original_rr: str = None) -> str:
    # Build lattice char by char
    lat = pn.accep("", TOK)
    for i, ch in enumerate(h):
        if i > 0:
            lat = pn.concat(lat, pn.accep(" ", TOK))  # Add space between chars
        lat = pn.concat(lat, (pn.accep(ch, TOK) @ HAN2))
    
    # Project to output to make it an acceptor
    lat = pn.project(lat, "output")
    
    # Get top-5 paths
    it = pn.shortestpath(lat, nshortest=50, unique=True).paths()
    outs = list(it.ostrings())  # iterable in 2.1.5
    if not outs: 
        return None
        
    if original_rr:
        scored = [(_dice(original_rr, o), o) for o in outs]
        return max(scored)[1]
    
    return outs[0]