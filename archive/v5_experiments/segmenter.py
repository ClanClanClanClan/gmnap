import pynini as pn
import heapq
import math

# Load syllable FSA
SYLL = pn.Fst.read("data/korean_syllable.fsa")

def segment(rr_str, beam=24):
    """Segment romanized string into syllables using beam search"""
    N = len(rr_str)
    chart = [[] for _ in range(N + 1)]
    chart[0] = [(0, [])]  # (cost, path)
    
    for i in range(N):
        for cost, path in chart[i]:
            # Try all possible syllable lengths (1-7 chars typical)
            for j in range(i + 1, min(i + 8, N) + 1):
                syl = rr_str[i:j].lower()
                
                # Check if valid syllable
                try:
                    if pn.compose(pn.accep(syl, token_type="utf8"), SYLL).num_states() > 0:
                        # Simple length-based cost (can use frequency later)
                        ncost = cost + len(syl)
                        heapq.heappush(chart[j], (ncost, path + [syl]))
                except:
                    continue
        
        # Keep only top beam candidates
        if chart[i + 1]:
            chart[i + 1] = heapq.nsmallest(beam, chart[i + 1])
    
    return chart[N]

# Enhanced with frequency scoring
def segment_with_freq(rr_str, freq_map, beam=24):
    """Segment using syllable frequencies"""
    N = len(rr_str)
    chart = [[] for _ in range(N + 1)]
    chart[0] = [(0, [])]
    
    for i in range(N):
        for cost, path in chart[i]:
            for j in range(i + 1, min(i + 8, N) + 1):
                syl = rr_str[i:j].lower()
                
                # Check validity and get frequency cost
                if is_valid_syllable(syl):
                    # Use -log P(syllable) as cost
                    syl_cost = -math.log(freq_map.get(syl, 1e-6))
                    ncost = cost + syl_cost
                    heapq.heappush(chart[j], (ncost, path + [syl]))
        
        if chart[i + 1]:
            chart[i + 1] = heapq.nsmallest(beam, chart[i + 1])
    
    return chart[N]

def is_valid_syllable(syl):
    """Check if string is valid Korean syllable in romanization"""
    try:
        composed = pn.compose(pn.accep(syl, token_type="utf8"), SYLL)
        return composed.num_states() > 0
    except:
        return False