#!/usr/bin/env python3
"""Debug conversion issues."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import converter as conv

# Test some of the failing names
test_names = [
    "Youn, Yuh-Jung",
    "Choi, Min-Shik", 
    "So, Ji-Sub",
    "Psy",
    "Rhee, Syngman"
]

print("=== DEBUGGING CONVERSIONS ===")
for name in test_names:
    result = conv.eng2kor(name)
    print(f"\n{name}:")
    print(f"  Result: {result}")
    
    # Try individual parts
    parts = name.replace(",", "").split()
    for part in parts:
        part_result = conv.eng2kor(part.lower())
        print(f"  {part.lower()} → {part_result}")

# Check if FST files exist
import os
base_dir = os.path.dirname(os.path.dirname(__file__))
models = ["rom2han_multi.fst", "rom2han_surname.fst", "rom2han_given.fst"]
print("\n=== FST FILES ===")
for model in models:
    path = os.path.join(base_dir, "models", model)
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    print(f"{model}: {'EXISTS' if exists else 'MISSING'} ({size} bytes)")