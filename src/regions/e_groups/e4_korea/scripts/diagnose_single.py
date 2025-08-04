#!/usr/bin/env python3
"""Diagnose a single name conversion."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from preprocess import tokenise
from segment import segment

name = sys.argv[1] if len(sys.argv) > 1 else "Youn, Yuh-Jung"
print(f"Diagnosing: {name}")

# Tokenize
tokens = list(tokenise(name))
print(f"\nTokens: {tokens}")

# Check each token
for tok in tokens:
    segments = list(segment(tok))
    print(f"\nToken '{tok}' → segments: {segments}")
    
    # Check if segments exist in CSV
    import csv
    existing = set()
    with open("resources/rr_syllable_map.csv", 'r', encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                existing.add(row[1])  # roman column
    
    for seg in segments:
        if seg.lower() in existing:
            print(f"  ✓ '{seg}' exists in mappings")
        else:
            print(f"  ✗ '{seg}' NOT FOUND in mappings")