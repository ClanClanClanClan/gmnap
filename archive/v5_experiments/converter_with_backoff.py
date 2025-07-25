# Runtime integration with V4 back-off
import pynini as pn
from .phonotactics import SYLL, WORD
import os

# Load FSTs
try:
    ROMAN2HANGUL = pn.Fst.read("data/roman2hangul.fst")
except:
    ROMAN2HANGUL = None

# Use comprehensive V4 FST if available, otherwise fall back to basic V4
if os.path.exists("data/v4_comprehensive.fst"):
    V4_FST = pn.Fst.read("data/v4_comprehensive.fst")
elif os.path.exists("data/v4_backoff.fst"):
    V4_FST = pn.Fst.read("data/v4_backoff.fst")
else:
    V4_FST = None

def extract_output(fst):
    """Extract output string from FST result"""
    if fst.num_states() == 0:
        return None
    
    shortest = pn.shortestpath(fst)
    paths_iter = shortest.paths(input_token_type="utf8", output_token_type="utf8")
    
    if not paths_iter.done():
        return paths_iter.ostring()
    return None

def create_segment_lattice(romanized):
    """Create phonotactic segmentation lattice"""
    # Simple segmentation - could be enhanced with beam search later
    input_fst = pn.accep(romanized.lower(), token_type="utf8")
    
    # Check if the input matches valid Korean phonotactics
    composed = pn.compose(input_fst, WORD)
    if composed.num_states() > 0:
        return input_fst
    
    # If not valid, return empty FST
    return pn.Fst()

def convert_with_backoff(romanized):
    # Try main WFST first if available
    if ROMAN2HANGUL is not None:
        try:
            segment_lattice = create_segment_lattice(romanized)
            result = pn.compose(
                segment_lattice, ROMAN2HANGUL
            )
            
            if result.num_states() > 0:
                output = extract_output(result)
                if output:
                    return output
        except:
            pass
    
    # Fall back to V4 if available
    if V4_FST is not None:
        try:
            # Try lowercase first
            v4_result = pn.compose(
                pn.accep(romanized.lower(), token_type="utf8"), V4_FST
            )
            
            if v4_result.num_states() > 0:
                output = extract_output(v4_result)
                if output:
                    return output
            
            # Try as-is if lowercase didn't work
            v4_result = pn.compose(
                pn.accep(romanized, token_type="utf8"), V4_FST
            )
            
            if v4_result.num_states() > 0:
                output = extract_output(v4_result)
                if output:
                    return output
        except:
            pass
    
    return None  # Failed