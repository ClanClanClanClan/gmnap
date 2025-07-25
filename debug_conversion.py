#!/usr/bin/env python3
"""Debug conversion process"""

import sys
sys.path.append('.')

from scripts.dice_coefficient_impl import roman_to_hangul, hangul_to_roman, dice_coefficient

test_name = "Ahn, Dae-Hoon"

print(f"Testing: {test_name}")
print(f"1. Roman to Hangul: {test_name} → ", end="")
hangul = roman_to_hangul(test_name)
print(hangul)

print(f"2. Hangul to Roman: {hangul} → ", end="")
reconstructed = hangul_to_roman(hangul)
print(reconstructed)

print(f"3. Dice coefficient: {dice_coefficient(test_name, reconstructed):.3f}")

# Also test simple names
print("\nSimple tests:")
for name in ["kim", "lee", "park"]:
    h = roman_to_hangul(name)
    r = hangul_to_roman(h)
    print(f"  {name} → {h} → {r}")