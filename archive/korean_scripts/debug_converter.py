#!/usr/bin/env python3
"""
Debug the converter with some specific cases
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v5.converter_with_backoff import convert_with_backoff

# Test cases
test_cases = [
    "Ahn",       # Single surname
    "DaeHoon",   # Single given name  
    "Ahn DaeHoon",  # Full name
    "Kim",       # Common surname
    "Young",     # Common given name
    "Kim Young", # Full name
    "lee",       # lowercase
    "park",      # lowercase
]

print("=== DEBUGGING CONVERTER ===\n")

for test in test_cases:
    result = convert_with_backoff(test)
    status = "✅" if result else "❌"
    print(f"{status} '{test}' → {result}")