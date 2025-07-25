import csv
import os
from pathlib import Path

# Get the E4 Korea root directory
E4_ROOT = Path(__file__).parent.parent
RESOURCE_PATH = E4_ROOT / "resources" / "rr_syllable_map.csv"

try:
    with open(RESOURCE_PATH, encoding="utf8") as f:
        LEXICON = {row[1].lower() for row in csv.reader(f)}
except FileNotFoundError:
    print(f"Warning: Could not load syllable lexicon from {RESOURCE_PATH}")
    LEXICON = set()  # Empty fallback