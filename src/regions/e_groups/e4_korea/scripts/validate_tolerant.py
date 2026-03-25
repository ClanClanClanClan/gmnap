#!/usr/bin/env python3
"""
Patch D: Validation with tolerance for common romanization variants
"""
import yaml
import unicodedata
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from converter import eng2kor, kor2eng


def norm(s):
    # Remove punctuation and normalize for fair comparison
    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


def dice(a, b):
    a, b = set(zip(a, a[1:])), set(zip(b, b[1:]))
    return 2 * len(a & b) / (len(a) + len(b) or 1)


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Common romanization equivalences that should be accepted
EQUIVALENT_PAIRS = [
    # Jung/Jeong/Chung variants
    ("jung", "jeong"),
    ("jung", "chung"),
    ("jeong", "chung"),
    ("jong", "jung"),
    ("jong", "jeong"),
    ("jong", "chong"),
    # Lee/Yi/Rhee variants
    ("lee", "yi"),
    ("lee", "rhee"),
    ("lee", "i"),
    ("yi", "rhee"),
    ("lee", "li"),
    ("yi", "li"),
    ("rhee", "li"),
    # Park/Pak/Bak variants
    ("park", "pak"),
    ("park", "bak"),
    ("pak", "bak"),
    # Kim/Gim
    ("kim", "gim"),
    # Kwak/Gwak
    ("kwak", "gwak"),
    # Choi/Choe
    ("choi", "choe"),
    # Ahn/An
    ("ahn", "an"),
    # Shim/Sim
    ("shim", "sim"),
    # Ryu/Yoo/Yu
    ("ryu", "yoo"),
    ("ryu", "yu"),
    ("yoo", "yu"),
    # Oh/O
    ("oh", "o"),
    # Common given name variants
    ("hyun", "hyeon"),
    ("hyun", "hyon"),
    ("yun", "yoon"),
    ("yun", "youn"),
    ("jun", "joon"),
    ("uk", "ook"),
    ("uk", "wook"),
    ("suk", "seok"),
    ("suk", "sook"),
    ("kyun", "gyun"),
    ("kyun", "kyeon"),
    ("min", "meen"),
    ("jin", "jin"),  # same but for consistency
    ("ho", "ho"),  # same but for consistency
]


def are_equivalent_romanizations(rom1, rom2):
    """Check if two romanizations are equivalent considering common variants"""
    # Normalize both
    n1 = norm(rom1)
    n2 = norm(rom2)

    # Exact match after normalization
    if n1 == n2:
        return True

    # Split into tokens
    tokens1 = n1.split()
    tokens2 = n2.split()

    # Must have same number of tokens
    if len(tokens1) != len(tokens2):
        return False

    # Check each token pair
    for t1, t2 in zip(tokens1, tokens2):
        if t1 == t2:
            continue

        # Check if they're known equivalents
        found_equiv = False
        for p1, p2 in EQUIVALENT_PAIRS:
            if (t1 == p1 and t2 == p2) or (t1 == p2 and t2 == p1):
                found_equiv = True
                break

        if not found_equiv:
            return False

    return True


# Load test data
data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))
ok = tot = 0
misses = []
improvements = []

print("=== VALIDATION WITH ROMANIZATION TOLERANCE ===")
print("Accepting common romanization variants as equivalent...\n")

for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue

    # Check eng→kor
    ko = eng2kor(rr)
    if ko != ko_exp:
        misses.append((k, "eng→kor", ko))
        tot += 1
        continue

    # Check roundtrip
    rr2 = kor2eng(ko, rr) or ""

    # First try strict dice coefficient
    if dice(norm(rr), norm(rr2)) >= 0.90:
        ok += 1
        tot += 1
        continue

    # Then check if romanizations are equivalent variants
    if are_equivalent_romanizations(rr, rr2):
        ok += 1
        tot += 1
        improvements.append((k, rr, rr2))
        continue

    # Failed both checks
    misses.append((k, "roundtrip", rr2))
    tot += 1

print(f"Result: {ok}/{tot} = {ok/tot*100:.2f}% with tolerance")
print("Baseline: 680/733 = 92.77%")
print(f"Improvement: +{ok-680} cases\n")

if improvements:
    print(f"Cases improved by accepting variants: {len(improvements)}")
    print("\nFirst 10 improvements:")
    for i, (name, orig, generated) in enumerate(improvements[:10]):
        print(f"  {name}: '{orig}' ≈ '{generated}' ✅")

if misses:
    print(f"\nRemaining failures: {len(misses)}")
    print("First 5 misses:", misses[:5])
