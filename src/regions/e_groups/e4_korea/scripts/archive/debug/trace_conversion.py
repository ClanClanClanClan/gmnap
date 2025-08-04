#!/usr/bin/env python3
"""
Trace the conversion process to understand how syllables are processed
"""
import sys
sys.path.append('src')
from preprocess import tokenise
from segment import segment
from converter import _rr2han_pos

# Test case: Lee, Chung-Wei -> 이청위
test_name = "Lee, Chung-Wei"
print(f"=== TRACING CONVERSION: {test_name} ===")
print()

# Step 1: Tokenization
tokens = list(tokenise(test_name))
print(f"1. Tokenized: {tokens}")

# Step 2: Segmentation and position assignment
for idx, tok in enumerate(tokens):
    pos = "surname" if idx == 0 else "given"
    print(f"\n2. Token '{tok}' (position: {pos}):")
    
    # Segment into syllables
    syllables = list(segment(tok))
    print(f"   Syllables: {syllables}")
    
    # Process each syllable
    for syl in syllables:
        result = _rr2han_pos(syl, pos)
        print(f"   '{syl}' -> '{result}' (using {pos} FST)")

# Now trace the specific problem: chung -> 정 instead of 청
print("\n=== INVESTIGATING 'chung' MAPPING ===")
print(f"chung as surname: {_rr2han_pos('chung', 'surname')}")
print(f"chung as given: {_rr2han_pos('chung', 'given')}")