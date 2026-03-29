#!/usr/bin/env python3
"""Check how FSTs are loaded in converter."""
import sys
from pathlib import Path

sys.path.insert(0, "src")

# Check what FST files exist
print("FST files in models/:")
for fst in Path("models").glob("*.fst"):
    print(f"  - {fst.name} ({fst.stat().st_size} bytes)")

# Import converter and check FST loading
# import converter

print("\nChecking converter FST attributes:")
attrs = ["ROM2_SURNAME", "ROM2_GIVEN", "HAN2_SURNAME", "HAN2_GIVEN"]
for attr in attrs:
    if hasattr(converter, attr):
        fst = getattr(converter, attr)
        print(f"  {attr}: {type(fst)} - loaded")
    else:
        print(f"  {attr}: NOT FOUND")

# Check if converter has old ROM2HAN attribute
if hasattr(converter, "ROM2HAN"):
    print("  ROM2HAN: Found (old style)")
else:
    print("  ROM2HAN: Not found")

# Test basic conversion
print("\nTesting basic conversions:")
test_names = ["Kim", "Lee", "Park"]
for name in test_names:
    result = converter.eng2kor(name)
    print(f"  {name} → {result}")

# Check converter source for FST loading
print("\nChecking converter.py FST loading code...")
converter_path = Path("src/converter.py")
with open(converter_path, "r") as f:
    content = f.read()
    if "ROM2_SURNAME" in content:
        print("  ✓ Uses position-specific FSTs (ROM2_SURNAME, etc.)")
    if "rom2han_multi.fst" in content:
        print("  ✓ Loads rom2han_multi.fst")
    if "pn.Fst.read" in content:
        print("  ✓ Uses pynini FST reading")
