#!/usr/bin/env python3
import yaml
import sys

sys.path.append("src")
from converter import eng2kor, kor2eng

# Analyze all remaining failures
data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Categorize failures
eng_kor_fails = []
roundtrip_fails = []

for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue

    ko = eng2kor(rr)
    if ko != ko_exp:
        eng_kor_fails.append((rr, ko_exp, ko))
    else:
        rr2 = kor2eng(ko, rr) or ""
        # Simple check - if surnames don't match, it's a failure
        orig_surname = rr.split()[0].rstrip(",").lower()
        ret_surname = rr2.split()[0].lower() if rr2 else ""
        if orig_surname != ret_surname:
            roundtrip_fails.append((rr, ko, rr2, orig_surname, ret_surname))

print(f"Total ENG→KOR failures: {len(eng_kor_fails)}")
print(f"Total round-trip surname mismatches: {len(roundtrip_fails)}")

# Analyze patterns
print("\n=== ENG→KOR Failure Patterns ===")
from collections import Counter

patterns = Counter()
for rr, ko_exp, ko in eng_kor_fails[:30]:  # First 30
    if ko is None:
        patterns["None result"] += 1
    elif "데이비드" in ko_exp or "린다" in ko_exp or "*" in ko_exp:
        patterns["Non-Korean name"] += 1
    elif "선" in ko_exp and "순" in (ko or ""):
        patterns["선/순 confusion"] += 1
    else:
        patterns["Other"] += 1

for pattern, count in patterns.most_common():
    print(f"  {pattern}: {count}")

print("\n=== Sample 'Other' ENG→KOR Failures ===")
other_count = 0
for rr, ko_exp, ko in eng_kor_fails[:50]:
    if (
        ko is None
        or "데이비드" in ko_exp
        or "린다" in ko_exp
        or "*" in ko_exp
        or ("선" in ko_exp and "순" in (ko or ""))
    ):
        continue
    print(f"  {rr} → expected: {ko_exp}, got: {ko}")
    other_count += 1
    if other_count >= 10:
        break

print("\n=== Round-trip Surname Mismatches ===")
surname_changes = Counter((orig, ret) for _, _, _, orig, ret in roundtrip_fails)
for (orig, ret), count in surname_changes.most_common(10):
    print(f"  {orig} → {ret}: {count} cases")
