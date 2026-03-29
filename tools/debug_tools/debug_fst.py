#!/usr/bin/env python3
"""Debug FST conversion issues"""

import pynini as pn

# Load the FST
fst = pn.Fst.read("data/roman2hangul.fst")
print(f"FST has {fst.num_states()} states")

# Test simple conversions
test_inputs = ["kim", "lee", "a", "ga", "han"]

for input_text in test_inputs:
    print(f"\nTesting: {input_text}")

    try:
        # Create input acceptor
        input_fst = pn.accep(input_text)
        print(f"  Input FST: {input_fst.num_states()} states")

        # Compose
        composed = pn.compose(input_fst, fst)
        print(f"  Composed: {composed.num_states()} states")

        if composed.num_states() > 0:
            # Get paths
            shortest = pn.shortestpath(composed)
            print(f"  Shortest: {shortest.num_states()} states")

            # Try to extract string
            try:
                for path in shortest.paths():
                    output_labels = path.olabels
                    output_str = "".join(chr(label) for label in output_labels if label > 0)
                    print(f"  Output: '{output_str}'")
                    break
            except Exception as e:
                print(f"  String extraction error: {e}")
        else:
            print("  No paths found")

    except Exception as e:
        print(f"  Error: {e}")

# Also test the romanization tables directly
print("\nTesting romanization table lookup:")
try:
    with open("data/rr_table.csv", "r", encoding="utf8") as f:
        lines = f.readlines()[:10]  # First 10 lines
        for line in lines:
            if "," in line:
                hangul, roman = line.strip().split(",", 1)
                print(f"  {roman} → {hangul}")
except Exception as e:
    print(f"Error reading table: {e}")
