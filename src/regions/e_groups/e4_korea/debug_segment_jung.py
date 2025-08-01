#!/usr/bin/env python3
"""Debug segmentation of jung-containing names."""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from segment_fixed import segment, LEXICON

def debug_segmentation(token):
    """Debug how a token is segmented."""
    print(f"\nSegmenting: {token}")
    print("-" * 40)
    
    # Check what's in lexicon
    token_lower = token.lower()
    print(f"Checking lexicon for substrings of '{token_lower}':")
    
    for i in range(len(token_lower)):
        for j in range(i+1, len(token_lower)+1):
            substr = token_lower[i:j]
            if substr in LEXICON:
                print(f"  '{substr}' ✓ in lexicon")
    
    # Show actual segmentation
    result = segment(token)
    print(f"\nSegmentation result: {result}")

def main():
    test_tokens = [
        "JungGeun",
        "jung",
        "geun",
        "joong",
        "junggeun"
    ]
    
    for token in test_tokens:
        debug_segmentation(token)

if __name__ == "__main__":
    main()