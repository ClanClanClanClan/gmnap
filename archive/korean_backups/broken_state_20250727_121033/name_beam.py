"""
Beam-search scorer for full Korean names.
Author: recovery-kit
"""

import json, math, heapq, pathlib, functools
from typing import List, Tuple, Dict
import pynini as pn
from fst_utils import first_output   # already in v6 code-base

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_ROM2  = pn.Fst.read(_ROOT / "models" / "rom2han_multi.fst")

# ---------- static resources -------------------------------------------------
# Load original synthetic bigram model - handle tuple format "a,b": count
_bigram_raw = json.load(open(_ROOT / "models" / "bigram_hangul.json"))
BIGRAM = {}
for key, count in _bigram_raw.items():
    if ',' in key:
        a, b = key.split(',', 1)
        BIGRAM[(a, b)] = count
    elif len(key) == 2:
        BIGRAM[(key[0], key[1])] = count

BIGRAM_TOTAL = sum(BIGRAM.values()) or 1
LOG10 = math.log(10)

def lm_score(a: str, b: str) -> float:
    """negative log-prob of Hangul bigram (a,b) with add-one smoothing"""
    return -math.log((BIGRAM.get((a, b), 1)) / BIGRAM_TOTAL + 1e-12)

SURNAME = {line.strip() for line in open(_ROOT / "resources" / "surnames.txt", encoding="utf8") if line.strip()}

# ---------- FST helpers ------------------------------------------------------
@functools.lru_cache(maxsize=4096)
def token_candidates(rr: str, N: int = 3) -> List[Tuple[str, float]]:
    """
    Return up to N (hangul, cost) pairs for a romanised token.
    cost = FST weight (already -log prob)
    """
    # Import here to avoid circular import
    from converter import _var, _pick_variant, _token_to_hangul
    
    # First check variant map
    candidates = []
    
    # Try exact match in variant map
    rr_lower = rr.lower()
    seen = set()
    
    if rr_lower in _var:
        # Get all variants for this token
        for tag, hangul in _var[rr_lower].items():
            if hangul not in seen:
                candidates.append((hangul, 0.0))  # Variant matches have 0 cost
                seen.add(hangul)
    
    # If token has hyphen, also try without hyphen
    if '-' in rr:
        rr_no_hyphen = rr.replace('-', '').lower()
        if rr_no_hyphen in _var:
            for tag, hangul in _var[rr_no_hyphen].items():
                if hangul not in seen:
                    candidates.append((hangul, 0.1))  # Slightly higher cost
                    seen.add(hangul)
    
    # If we have candidates from variants, return them
    if candidates:
        return candidates[:N]
    
    # Otherwise try FST
    try:
        # Remove hyphen for FST lookup
        rr_for_fst = rr.replace('-', '').lower()
        
        # For multi-syllable tokens, segment and convert
        from segment_fixed import segment
        segments = segment(rr_for_fst)
        
        if not segments:
            return []
            
        # Convert each segment
        hangul_parts = []
        total_weight = 0.0
        
        for seg in segments:
            try:
                result = first_output(pn.accep(seg) @ _ROM2)
                if result:
                    hangul_parts.append(result)
                else:
                    # Try from lookup dict
                    from lookup import rom2han
                    result = rom2han().get(seg)
                    if result:
                        hangul_parts.append(result)
                    else:
                        return []  # Can't convert this segment
            except:
                return []
                
        if hangul_parts:
            # Return as single candidate
            return [(''.join(hangul_parts), total_weight)]
        else:
            return []
    except:
        # If FST fails, return empty list
        return []

# ---------- beam search ------------------------------------------------------
WEIGHT_FST   = 1.00
WEIGHT_BIGRAM= 0.60  # Reduced to rely more on FST/variants
PENALTY_BAD_SURNAME = 2.5    # added if first syllable not in surname list

def best_name(tokens: List[str], beam_K: int = 20) -> str|None:
    """
    Jointly choose the best Hangul name for a list of RR tokens.
    Returns Hangul string or None.
    """
    # beam item = (total_cost, syllable_string, token_index)
    beam: List[Tuple[float, str, int]] = [(0.0, "", 0)]
    
    for i, tok in enumerate(tokens):
        nxt: list[Tuple[float, str, int]] = []
        for cost, sofar, _ in beam:
            cand = token_candidates(tok)
            if not cand:        # OOV token kills this path
                continue
            for h, w in cand:
                new = sofar + h
                total = cost + WEIGHT_FST * float(w)

                # add bigram cost between last char of sofar and first char of h
                if sofar:
                    total += WEIGHT_BIGRAM * lm_score(sofar[-1], h[0])
                    
                    # Also add costs for transitions within h
                    for j in range(len(h) - 1):
                        total += WEIGHT_BIGRAM * lm_score(h[j], h[j+1])
                        
                nxt.append((total, new, i+1))
                
        # keep top-K
        beam = heapq.nsmallest(beam_K, nxt)
        if not beam:
            return None

    # apply surname penalty on final beam
    penalised = []
    for cost, h, _ in beam:
        if h and h[0] not in SURNAME:
            cost += PENALTY_BAD_SURNAME
        penalised.append((cost, h))
        
    if not penalised:
        return None
        
    best = min(penalised, key=lambda x: x[0])
    return best[1]