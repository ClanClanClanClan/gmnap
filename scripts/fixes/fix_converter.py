#!/usr/bin/env python3
"""Fixed converter with correct PyNini string extraction"""

import pynini as pn


def extract_output_string(fst):
    """Extract output string from FST using correct PyNini API"""
    try:
        # Method 1: Use string() if it's a string FST
        if hasattr(fst, "string"):
            try:
                return fst.string()
            except:
                pass

        # Method 2: Use paths() iterator correctly
        paths_iter = fst.paths()
        for path in paths_iter:
            # Extract output labels
            output_str = ""
            for label in path.olabels:
                if label > 0:  # Skip epsilon (0)
                    output_str += chr(label)
            return output_str

        return None
    except Exception as e:
        print(f"String extraction error: {e}")
        return None


def test_corrected_conversion():
    """Test with corrected string extraction"""
    # Load FST
    fst = pn.Fst.read("data/roman2hangul.fst")
    print(f"FST loaded with {fst.num_states()} states")

    test_cases = ["kim", "ga", "han", "a", "park"]

    for roman in test_cases:
        print(f"\nTesting: {roman}")

        # Create input
        input_fst = pn.accep(roman)

        # Compose
        result = pn.compose(input_fst, fst)

        if result.num_states() > 0:
            # Get shortest path
            shortest = pn.shortestpath(result)

            # Extract string
            hangul = extract_output_string(shortest)
            if hangul:
                print(f"  {roman} → {hangul}")
            else:
                print(f"  {roman} → [extraction failed]")
        else:
            print(f"  {roman} → [no path]")


if __name__ == "__main__":
    test_corrected_conversion()
