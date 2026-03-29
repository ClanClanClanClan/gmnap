#!/usr/bin/env python3
"""
Fixed enhanced dice function that properly handles Korean romanization variants
"""

import unicodedata


def enhanced_dice_fixed(a, b):
    """Enhanced dice coefficient with proper Korean romanization handling"""
    # Basic normalization
    a = "" if not a else a.replace(",", "").replace("-", " ")
    b = "" if not b else b.replace(",", "").replace("-", " ")

    # Korean-specific romanization equivalences
    # These are PAIRS that should be treated as equal
    equivalent_pairs = [
        ("jung", "jeong"),
        ("yun", "yoon"),
        ("rim", "lim"),
        ("yi", "i"),
        ("yon", "yeon"),
        ("mee", "mi"),
        ("cheon", "chun"),
        ("pak", "park"),
        ("koo", "goo"),
        ("ku", "gu"),
        ("rhee", "lee"),
        ("seung", "sueng"),
        ("hyun", "hyeon"),
        ("kyung", "kyeong"),
        ("noh", "no"),
        ("joon", "jung"),
        ("myung", "myeong"),
        ("yum", "yom"),
        # Add more as needed
        ("chul", "cheol"),
        ("soo", "su"),
        ("hee", "hui"),
    ]

    # Normalize both strings by replacing variants with canonical forms
    a_words = a.lower().split()
    b_words = b.lower().split()

    # Create a normalization map (always map to first variant)
    norm_map = {}
    for pair in equivalent_pairs:
        canonical = pair[0]  # Use first as canonical
        for variant in pair:
            norm_map[variant] = canonical

    # Apply normalization
    a_normalized = []
    for word in a_words:
        a_normalized.append(norm_map.get(word, word))

    b_normalized = []
    for word in b_words:
        b_normalized.append(norm_map.get(word, word))

    a = " ".join(a_normalized)
    b = " ".join(b_normalized)

    # Continue with standard dice calculation
    a = unicodedata.normalize("NFC", a.casefold().replace(" ", "")).encode()
    b = unicodedata.normalize("NFC", b.casefold().replace(" ", "")).encode()

    # Calculate bigrams
    bigr = lambda s: {s[i : i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}
    x, y = bigr(a), bigr(b)

    # Handle empty sets
    if not x and not y:
        return 1.0
    if not x or not y:
        return 0.0

    # Dice coefficient
    return (2 * len(x & y)) / (len(x) + len(y))


def test_enhanced_dice():
    """Test the enhanced dice function"""
    test_pairs = [
        ("lee mi na", "lee mee na", 0.97),
        ("park young hee", "pak young hee", 0.97),
        ("kim chul soo", "kim cheol su", 0.97),
        ("jung eun ji", "jeong eun ji", 0.97),
        ("mi", "mee", 0.97),
        ("park", "pak", 0.97),
    ]

    print("Testing enhanced dice function:")
    print("-" * 50)

    all_pass = True
    for a, b, expected_min in test_pairs:
        dice = enhanced_dice_fixed(a, b)
        passes = dice >= expected_min
        all_pass = all_pass and passes

        print(f'"{a}" vs "{b}"')
        print(f'  Dice: {dice:.3f} {"✅" if passes else "❌"}')

    print(f"\nOverall: {'✅ ALL PASS' if all_pass else '❌ SOME FAILURES'}")
    return all_pass


if __name__ == "__main__":
    test_enhanced_dice()
