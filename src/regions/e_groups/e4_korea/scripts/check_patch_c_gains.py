#!/usr/bin/env python3
"""
Check which specific cases improved with Patch C
"""
import yaml, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
# from converter import eng2kor, kor2eng

# Load test data
with open("data/korean.yaml", encoding="utf8") as f:
    data = yaml.safe_load(f)

# Check cases that might benefit from loanword handling
loanword_patterns = ["David", "Grace", "Linda", "Michael", "J.", "Brian", "Frank"]
potential_improvements = []

print("=== CHECKING LOANWORD IMPROVEMENTS ===")

for name, info in data.items():
    if any(pattern in name for pattern in loanword_patterns):
        romanized = name.replace("_", ", ")
        actual = eng2kor(romanized)

        if actual:
            roundtrip = kor2eng(actual)
            print(f"\n{name}:")
            print(f"  Romanized: {romanized}")
            print(f"  Korean: {actual}")
            print(f"  Roundtrip: {roundtrip}")

            # Check if roundtrip is close enough
            if roundtrip:
                normalized_original = (
                    romanized.lower().replace(",", "").replace(" ", "").replace("-", "")
                )
                normalized_roundtrip = roundtrip.lower().replace(" ", "")
                if normalized_original == normalized_roundtrip:
                    print(f"  ✅ PASS")
                    potential_improvements.append(name)
                else:
                    print(f"  ❌ FAIL (roundtrip mismatch)")
            else:
                print(f"  ❌ FAIL (no roundtrip)")
        else:
            print(f"\n{name}: ❌ FAIL (no Korean output)")

print(f"\n=== SUMMARY ===")
print(f"Potential loanword improvements: {len(potential_improvements)}")
if potential_improvements:
    print("Passing cases:", potential_improvements)
