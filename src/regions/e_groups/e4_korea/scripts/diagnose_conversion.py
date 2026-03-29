#!/usr/bin/env python3
"""Diagnose why specific conversions fail."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# import converter as conv
from preprocess import tokenise
from segment import segment


def diagnose(name):
    """Detailed diagnosis of name conversion."""
    print(f"\n=== DIAGNOSING: {name} ===")

    # Step 1: Tokenization
    tokens = list(tokenise(name))
    print(f"\n1. Tokenization: {tokens}")

    # Step 2: Segmentation
    for idx, tok in enumerate(tokens):
        position = "surname" if idx == 0 else "given"
        segments = list(segment(tok))
        print(f"\n2. Segmentation of '{tok}' ({position}):")
        print(f"   Segments: {segments}")

        # Step 3: Syllable lookup
        for syl in segments:
            # Try position-specific lookup
            result_pos = conv._rr2han_pos(syl, position)
            # Try general lookup
            result_gen = conv._rr2han(syl)

            print(f"\n   Syllable '{syl}':")
            print(f"     Position-specific ({position}): {result_pos}")
            print(f"     General lookup: {result_gen}")

            # Check FST directly
            import pynini as pn
            from fst_utils import first_output

            # Check surname FST
            try:
                surname_result = first_output(pn.accep(syl.lower()) @ conv.ROM2_SURNAME)
                print(f"     Surname FST: {surname_result}")
            except:
                print("     Surname FST: None")

            # Check given FST
            try:
                given_result = first_output(pn.accep(syl.lower()) @ conv.ROM2_GIVEN)
                print(f"     Given FST: {given_result}")
            except:
                print("     Given FST: None")

    # Final conversion
    result = conv.eng2kor(name)
    print(f"\n3. Final result: {result}")

    # N-best results
    nbest = conv.eng2kor_nbest(name, 3)
    print(f"\n4. N-best results: {nbest}")


if __name__ == "__main__":
    test_names = ["So, Ji-Sub", "Choi, Min-Shik", "Rhee, Syngman", "Psy"]

    for name in test_names:
        diagnose(name)
