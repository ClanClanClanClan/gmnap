"""
Korean converter with fallback implementation for environments without PyNini
"""
import os
from fst_utils_fallback import PYNINI_AVAILABLE, ROM2HAN_LOOKUP, HAN2ROM_LOOKUP, first_output
from preprocess import tokenise
from segment import segment

if PYNINI_AVAILABLE:
    import pynini as pn
    # Load FST models if available
    try:
        ROM2 = pn.Fst.read("models/rom2han.fst")
        HAN2 = pn.Fst.read("models/han2rom.fst")
        TOK = "utf8"
        FST_AVAILABLE = True
    except:
        FST_AVAILABLE = False
        print("FST files not found - using lookup fallback")
else:
    FST_AVAILABLE = False

def _rr2han_fallback(rr: str) -> str | None:
    """Convert romanization to Hangul using lookup table fallback."""
    return ROM2HAN_LOOKUP.get(rr.lower())

def _han2rom_fallback(han: str) -> str | None:
    """Convert Hangul to romanization using lookup table fallback."""
    return HAN2ROM_LOOKUP.get(han)

def _rr2han(rr: str) -> str | None:
    """Convert romanization to Hangul - FST or fallback."""
    if FST_AVAILABLE:
        try:
            result = first_output(pn.accep(rr, TOK) @ ROM2)
            if result:
                return result
        except:
            pass
    
    # Fallback to lookup table
    return _rr2han_fallback(rr)

def _han2rom(han: str) -> str | None:
    """Convert Hangul to romanization - FST or fallback."""
    if FST_AVAILABLE:
        try:
            result = first_output(pn.accep(han, TOK) @ HAN2)
            if result:
                return result
        except:
            pass
    
    # Fallback to lookup table
    return _han2rom_fallback(han)

def eng2kor(name: str) -> str | None:
    """Convert English name to Korean."""
    if not name:
        return None
        
    out = []
    for tok in tokenise(name):
        for syl in segment(tok):
            h = _rr2han(syl)
            if h is None:
                return None
            out.append(h)
    return "".join(out)

def kor2eng(hangul: str) -> str | None:
    """Convert Korean name to English."""
    if not hangul:
        return None
    
    # For multi-character Hangul, try character by character
    result_parts = []
    for char in hangul:
        rom = _han2rom(char)
        if rom:
            result_parts.append(rom)
        else:
            # If individual character fails, return None
            return None
    
    return " ".join(result_parts) if result_parts else None