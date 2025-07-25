"""
Korean converter v6 - Final implementation with proper preprocessing
"""
import os
import json
from pathlib import Path
from preprocess_fixed import tokenise
from segment_fixed import segment

# Load lookup tables
E4_ROOT = Path(__file__).parent.parent
ROM2HAN_PATH = E4_ROOT / "models" / "rom2han_lookup.json"
HAN2ROM_PATH = E4_ROOT / "models" / "han2rom_lookup.json"

def load_lookup_tables():
    """Load JSON lookup tables."""
    rom2han = {}
    han2rom = {}
    
    try:
        with open(ROM2HAN_PATH, encoding="utf8") as f:
            rom2han = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {ROM2HAN_PATH} not found")
    
    try:
        with open(HAN2ROM_PATH, encoding="utf8") as f:
            han2rom = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {HAN2ROM_PATH} not found")
    
    return rom2han, han2rom

ROM2HAN_LOOKUP, HAN2ROM_LOOKUP = load_lookup_tables()

def _rr2han(rr: str) -> str | None:
    """Convert romanization to Hangul using lookup table."""
    return ROM2HAN_LOOKUP.get(rr.lower())

def _han2rom(han: str) -> str | None:
    """Convert Hangul to romanization using lookup table."""
    return HAN2ROM_LOOKUP.get(han)

def eng2kor(name: str) -> str | None:
    """Convert English name to Korean."""
    if not name or not name.strip():
        return None
        
    out = []
    for tok in tokenise(name):
        if not tok.strip():
            continue
            
        # Try direct lookup first
        direct_result = _rr2han(tok.lower())
        if direct_result:
            out.append(direct_result)
            continue
            
        # Fall back to segmentation  
        segments = segment(tok)
        tok_parts = []
        for syl in segments:
            h = _rr2han(syl)
            if h is None:
                # This token failed conversion
                return None
            tok_parts.append(h)
        
        out.extend(tok_parts)
    
    return "".join(out) if out else None

def kor2eng(hangul: str) -> str | None:
    """Convert Korean name to English."""
    if not hangul or not hangul.strip():
        return None
    
    result_parts = []
    for char in hangul.strip():
        rom = _han2rom(char)
        if rom:
            result_parts.append(rom)
        else:
            # Character not found in lookup
            return None
    
    return " ".join(result_parts) if result_parts else None