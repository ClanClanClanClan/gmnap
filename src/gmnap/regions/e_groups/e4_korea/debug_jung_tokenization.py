#!/usr/bin/env python3
"""Debug how jung is tokenized and converted."""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from converter import eng2kor, tokenise, segment
from lookup import rom2han

def debug_jung_conversion(name):
    """Debug step by step conversion."""
    print(f"\nDebugging: {name}")
    print("-" * 40)
    
    # Tokenize
    tokens = tokenise(name)
    print(f"Tokens: {tokens}")
    
    # Segment each token
    for i, tok in enumerate(tokens):
        segments = segment(tok)
        print(f"Token {i} '{tok}' segments: {segments}")
        
        # Check each segment
        for seg in segments:
            # Check rom2han lookup
            from_lookup = rom2han().get(seg)
            print(f"  '{seg}' → lookup: {from_lookup}")
            
            # Check FST
            from converter import _rr2han
            from_fst = _rr2han(seg)
            print(f"  '{seg}' → FST: {from_fst}")
    
    # Final result
    result = eng2kor(name)
    print(f"Final: {name} → {result}")

def main():
    test_cases = [
        "An_JungGeun",    # Should be 안중근
        "JinJung",        # Should have 중 at end
        "Jung",           # Just Jung alone
        "JungHo",         # Should be 정호
    ]
    
    for name in test_cases:
        debug_jung_conversion(name)

if __name__ == "__main__":
    main()