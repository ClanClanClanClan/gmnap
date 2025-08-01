import sys
sys.path.append('src')
from converter import kor2eng, _dice

# Test the multi-path selection
test_korean = "오성준"  # Oh Seong-Joon

print(f"Testing multi-path for: {test_korean}")
print("\nWithout original:")
result1 = kor2eng(test_korean)
print(f"  Result: '{result1}'")

print("\nWith original 'Oh, Seong-Joon':")
result2 = kor2eng(test_korean, "Oh, Seong-Joon")
print(f"  Result: '{result2}'")

# Let's manually check what paths are available
import pynini as pn
from converter import HAN2, TOK

# Build lattice manually
lat = pn.accep("", TOK)
for i, ch in enumerate(test_korean):
    if i > 0:
        lat = pn.concat(lat, pn.accep(" ", TOK))
    lat = pn.concat(lat, (pn.accep(ch, TOK) @ HAN2))

lat = pn.project(lat, "output")
it = pn.shortestpath(lat, nshortest=10, unique=True).paths()
outs = list(it.ostrings())

print("\nAll available paths:")
for i, path in enumerate(outs):
    dice_score = _dice("Oh, Seong-Joon", path)
    print(f"  {i+1}. '{path}' (Dice with 'Oh, Seong-Joon': {dice_score:.3f})")