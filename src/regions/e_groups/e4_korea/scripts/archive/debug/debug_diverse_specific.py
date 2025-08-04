#!/usr/bin/env python3
"""
Debug specific Diverse failures to understand why fixes aren't working
"""
import sys
sys.path.append('src')
from converter import eng2kor

test_cases = [
    ("Lee, Chung-Wei", "이청위"),
    ("Han, Duk-Su", "한덕수"),
    ("Kim, Yo-Jong", "김여정"),
    ("Yi, Sun-Sin", "이순신"),
    ("An, Jung-Geun", "안중근"),
    ("Lee, Kun-Hee", "이건희"),
    ("Shim, Chang-Min", "심창민"),
    ("Han, Joseph", "한요셉"),
    ("Lee, Chun-Hyang", "이춘향"),
    ("Kang, Jin-Jung", "강진중"),
]

print("=== DEBUGGING SPECIFIC DIVERSE FAILURES ===")
print()

for name, expected in test_cases:
    result = eng2kor(name)
    status = "✅" if result == expected else "❌"
    print(f"{status} {name}")
    print(f"   Expected: {expected}")
    print(f"   Got:      {result}")
    if result != expected and result:
        # Show character-by-character difference
        print("   Diff:     ", end="")
        for i, (e, a) in enumerate(zip(expected, result)):
            if e != a:
                print(f"[{i}]{e}→{a}", end=" ")
        print()
    print()