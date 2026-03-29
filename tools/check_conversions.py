#!/usr/bin/env python3
"""Check actual conversions"""

import sys

sys.path.append("src")

from v5.converter_with_backoff import convert_with_backoff

test_names = ["kim", "ahn", "baek", "jung", "han", "cho", "lee", "park"]

print("Checking conversions:")
for name in test_names:
    result = convert_with_backoff(name)
    print(f"  {name} → {result if result else '[FAILED]'}")
