import pynini as pn, pathlib
from fst_utils import first_output
from preprocess_fixed import tokenise
from segment_fixed import segment
from lookup import rom2han
import unicodedata

def _dice(a,b):
    # Normalize like validation does - remove punctuation and normalize
    a = "" if not a else a.replace(",", "").replace("-", " ")
    b = "" if not b else b.replace(",", "").replace("-", " ")
    a = b"" if not a else unicodedata.normalize("NFC",a.casefold().replace(" ","")).encode()
    b = b"" if not b else unicodedata.normalize("NFC",b.casefold().replace(" ","")).encode()
    bigr=lambda s:{s[i:i+2] for i in range(len(s)-1)}
    x,y=bigr(a),bigr(b); return (2*len(x&y))/(len(x)+len(y) or 1)
ROM2 = pn.Fst.read("models/rom2han_multi.fst")
HAN2 = pn.Fst.read("models/han2rom_multi.fst")
TOK=None      # default token‑type
def _rr2han(rr): return first_output(pn.accep(rr)@ROM2) or rom2han().get(rr)
def eng2kor(name:str):
    out=[]
    for tok in tokenise(name):
        for syl in segment(tok):
            h=_rr2han(syl)
            if h is None: return None
            out.append(h)
    return "".join(out)
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
    it   = pn.shortestpath(lat, nshortest=10, unique=True).paths()
    outs = list(it.ostrings())   # iterable in 2.1.5
    if not outs: return None
    if original_rr:
        scored=[(_dice(original_rr,o), o) for o in outs]
        return max(scored)[1]
    return outs[0]