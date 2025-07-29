"""
FST utilities with fallback for environments without PyNini
"""
import json
import os

# Try to import PyNini, fallback to lookup tables if not available
try:
    import pynini as pn
    PYNINI_AVAILABLE = True
    
    def first_output(fst: pn.Fst) -> str | None:
        for p in pn.shortestpath(fst, nshortest=1, unique=True).paths():
            return p.ostring()
        return None
        
except ImportError:
    PYNINI_AVAILABLE = False
    print("PyNini not available - using lookup table fallback")
    
    def first_output(lookup_result: str) -> str | None:
        return lookup_result

# Load lookup tables for fallback
def load_lookup_tables():
    """Load JSON lookup tables for fallback when PyNini is not available."""
    rom2han_path = "models/rom2han_lookup.json"
    han2rom_path = "models/han2rom_lookup.json"
    
    rom2han = {}
    han2rom = {}
    
    if os.path.exists(rom2han_path):
        with open(rom2han_path, encoding="utf8") as f:
            rom2han = json.load(f)
    
    if os.path.exists(han2rom_path):
        with open(han2rom_path, encoding="utf8") as f:
            han2rom = json.load(f)
    
    return rom2han, han2rom

# Global lookup tables
ROM2HAN_LOOKUP, HAN2ROM_LOOKUP = load_lookup_tables()