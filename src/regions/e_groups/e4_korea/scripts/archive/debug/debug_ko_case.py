#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
from converter import _rr2han
from context_lookup import apply_context
from preprocess import tokenise
from segment import segment

name = "Ko, Sueng-Kook"
print(f"=== DEBUGGING: {name} ===")

# Step 1: Tokenization
tokens = list(tokenise(name))
print(f"Tokens: {tokens}")

# Step 2: Process each token
for i, tok in enumerate(tokens):
    position = "surname" if i == 0 else "given"
    print(f"\nToken {i}: '{tok}' (position: {position})")
    
    # Step 3: Segmentation
    segments = segment(tok)
    print(f"  Segments: {segments}")
    
    # Step 4: Process each segment
    for j, syl in enumerate(segments):
        print(f"    Segment {j}: '{syl}'")
        
        # Step 5: Apply context
        context_syl = apply_context(syl, position, name)
        print(f"      Context: {syl} → {context_syl}")
        
        # Step 6: Convert to Hangul
        h = _rr2han(context_syl)
        print(f"      Hangul: {context_syl} → {h}")
        
        if h is None:
            h_fallback = _rr2han(syl)
            print(f"      Fallback: {syl} → {h_fallback}")