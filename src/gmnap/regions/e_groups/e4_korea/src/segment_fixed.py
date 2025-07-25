from syllable_lexicon_fixed import LEXICON

def segment(token: str, max_len: int = 8) -> list[str]:
    """Segment a token into syllables using dynamic programming."""
    token = token.lower().replace("-", "")
    n = len(token)
    best = [9e9] * (n + 1)
    back = [-1] * (n + 1)
    best[0] = 0
    
    for i in range(n):
        if best[i] == 9e9:
            continue
        for j in range(i + 1, min(i + max_len, n) + 1):
            frag = token[i:j]
            if frag in LEXICON and best[i] + 1 < best[j]:
                best[j] = best[i] + 1
                back[j] = i
    
    if back[n] == -1:
        return [token]
    
    out = []
    idx = n
    while idx > 0:
        out.append(token[back[idx]:idx])
        idx = back[idx]
    
    return out[::-1]