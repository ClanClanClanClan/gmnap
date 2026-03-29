#!/usr/bin/env python3
"""Debug FST output extraction in detail"""

import pynini as pn


def debug_fst_conversion(roman_input):
    """Debug FST conversion step by step"""
    print(f"\n=== Debugging conversion for: {roman_input} ===")

    # Load FST
    fst = pn.Fst.read("data/roman2hangul.fst")
    print(f"FST loaded: {fst.num_states()} states")

    # Create input with different token types
    for token_type in ["utf8", "byte", None]:
        print(f"\n--- Testing with token_type={token_type} ---")
        try:
            if token_type:
                input_fst = pn.accep(roman_input, token_type=token_type)
            else:
                input_fst = pn.accep(roman_input)

            print(f"Input FST created: {input_fst.num_states()} states")

            # Compose
            result = pn.compose(input_fst, fst)
            print(f"Composition result: {result.num_states()} states")

            if result.num_states() > 0:
                # Get shortest path
                shortest = pn.shortestpath(result)
                print(f"Shortest path: {shortest.num_states()} states")

                # Try different extraction methods
                for out_token_type in ["utf8", "byte", None]:
                    try:
                        if out_token_type:
                            paths_iter = shortest.paths(
                                output_token_type=out_token_type
                            )
                        else:
                            paths_iter = shortest.paths()

                        if not paths_iter.done():
                            output_str = paths_iter.ostring()
                            print(
                                f"  Output ({out_token_type}): '{output_str}' (length: {len(output_str)})"
                            )

                            # Also try raw bytes
                            output_labels = paths_iter.olabels()
                            print(f"  Raw labels: {list(output_labels)}")

                            # Try manual conversion
                            if output_labels:
                                manual_str = "".join(
                                    chr(label) for label in output_labels if label > 0
                                )
                                print(f"  Manual conversion: '{manual_str}'")

                    except Exception as e:
                        print(f"  Error with {out_token_type}: {e}")

        except Exception as e:
            print(f"Error with input token_type {token_type}: {e}")


# Test various inputs
test_cases = ["kim", "ga", "han"]
for case in test_cases:
    debug_fst_conversion(case)
