#!/usr/bin/env python3
"""Trace the conversion process for specific names."""

import sys

sys.path.insert(0, "src")
from preprocess import tokenise
from segment import segment

# import converter


def trace_name(name, expected):
    """Trace conversion step by step."""
    print(f"\n=== TRACING: {name} ===")
    print(f"Expected: {expected}")

    # Tokenize
    tokens = list(tokenise(name))
    print(f"Tokens: {tokens}")

    # Segment each token
    all_segments = []
    for i, tok in enumerate(tokens):
        segments = list(segment(tok))
        all_segments.extend(segments)
        print(f"\nToken {i}: '{tok}' → {segments}")

        # Check what each segment converts to
        for seg in segments:
            # Check general lookup
            han_general = converter._rr2han(seg)
            print(f"  '{seg}' → {han_general or 'None'} (general)")

            # Check position-specific
            pos = "surname" if i == 0 else "given"
            han_pos = converter._rr2han_pos(seg, pos)
            if han_pos != han_general:
                print(f"  '{seg}' → {han_pos or 'None'} ({pos} specific)")

    # Full conversion
    result = converter.eng2kor(name)
    print(f"\nFinal result: {result}")

    # Show differences
    if result and result != expected:
        print("\nDifferences:")
        for i, (e, a) in enumerate(zip(expected, result)):
            if e != a:
                print(f"  Position {i}: {e} → {a}")


# Test problematic names
test_cases = [
    ("Lee, Cheong-Jun", "이청준"),
    ("Yu, Gwan-Sun", "유관순"),
    ("Lee, Byung-Hun", "이병헌"),
]

for name, expected in test_cases:
    trace_name(name, expected)
