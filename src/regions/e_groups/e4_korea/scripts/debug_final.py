#!/usr/bin/env python3
"""
Debug final implementation
"""

import sys
from pathlib import Path

# Add src directory to path
E4_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(E4_ROOT / "src"))

from preprocess import tokenise
from segment import segment

# from converter_final import eng2kor, kor2eng


def debug_final():
    """Debug the final processing pipeline."""
    print("=== Final Implementation Debug ===")

    test_cases = ["Ahn, Dae-Hoon", "Kim Young", "Lee", "Baek, Hyeong-Chan"]

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

        # Step 4: Round-trip if successful
        if result:
            back = kor2eng(result)
            print(f"  Round-trip: {result} -> {back}")


def test_simple_cases():
    """Test simple cases that should work."""
    print("\n=== Testing Simple Cases ===")

    simple_cases = ["Kim", "Lee", "Park", "Young", "Min", "Ho"]

    for name in simple_cases:
        result = eng2kor(name)
        print(f"  {name} -> {result}")


if __name__ == "__main__":
    debug_final()
    test_simple_cases()
