#!/usr/bin/env python3
"""
Debug tokenization and segmentation
"""
import sys
from pathlib import Path

# Add src directory to path
E4_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(E4_ROOT / "src"))

from preprocess import tokenise
from segment_fixed import segment
from converter_fixed import eng2kor

def debug_processing():
    """Debug the processing pipeline."""
    print("=== Debugging Processing Pipeline ===")
    
    test_cases = [
        "Ahn, Dae-Hoon",
        "Kim Young",
        "Lee",
        "Baek, Hyeong-Chan"
    ]
    
    for name in test_cases:
        print(f"\nProcessing: '{name}'")
        
        # Step 1: Tokenization
        tokens = tokenise(name)
        print(f"  Tokens: {tokens}")
        
        # Step 2: Segmentation for each token
        for i, token in enumerate(tokens):
            segments = segment(token)
            print(f"  Token {i} '{token}' -> segments: {segments}")
        
        # Step 3: Full conversion
        result = eng2kor(name)
        print(f"  Final result: {result}")

if __name__ == "__main__":
    debug_processing()