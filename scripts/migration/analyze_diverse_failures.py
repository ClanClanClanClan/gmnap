#!/usr/bin/env python3
"""
Detailed analysis of failures in diverse dataset to identify patterns.
"""

import yaml
import sys
import pathlib
from collections import defaultdict, Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
# from converter import eng2kor, kor2eng


def find_hangul(variants):
    """Find the Hangul (Korean) variant from the list"""
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


def extract_category(comment):
    """Extract category from comment field"""
    if not comment:
        return "Unknown"

    comment_lower = comment.lower()
    if (
        "sport" in comment_lower
        or "football" in comment_lower
        or "baseball" in comment_lower
    ):
        return "Sports"
    elif (
        "entertainment" in comment_lower
        or "actor" in comment_lower
        or "singer" in comment_lower
        or "k-pop" in comment_lower
    ):
        return "Entertainment"
    elif (
        "business" in comment_lower
        or "chaebol" in comment_lower
        or "ceo" in comment_lower
    ):
        return "Business"
    elif (
        "politics" in comment_lower
        or "president" in comment_lower
        or "minister" in comment_lower
    ):
        return "Politics"
    elif (
        "literature" in comment_lower
        or "author" in comment_lower
        or "poet" in comment_lower
    ):
        return "Literature"
    elif "science" in comment_lower or "researcher" in comment_lower:
        return "Science"
    elif "mathematics" in comment_lower or "mathematician" in comment_lower:
        return "Mathematics"
    else:
        return "Other"


def main():
    # Load diverse dataset
    with open("data/korean_diverse_test.yaml", encoding="utf8") as f:
        data = yaml.safe_load(f)

    failures_by_category = defaultdict(list)
    romanization_styles = defaultdict(int)

    print("Analyzing failures in diverse dataset...")
    print("=" * 60)

    for name, entry in data.items():
        canonical_latin = entry.get("CanonicalLatin")
        ko_expected = find_hangul(entry.get("AllCommonVariants", []))
        comment = entry.get("Comments", "")
        category = extract_category(comment)

        if not canonical_latin or not ko_expected:
            continue

        # Check for special romanization patterns in the name
        if "Yu-Na" in canonical_latin or "Yuna" in canonical_latin:
            romanization_styles["Yu-Na/Yuna pattern"] += 1
        if any(
            part.lower() in ["lee", "rhee", "yi", "li"]
            for part in canonical_latin.split()
        ):
            romanization_styles["Lee/Rhee/Yi/Li variations"] += 1
        if any(
            part.lower() in ["park", "pak", "bak"] for part in canonical_latin.split()
        ):
            romanization_styles["Park/Pak/Bak variations"] += 1

        # Test conversion
        ko_actual = eng2kor(canonical_latin)

        if ko_actual != ko_expected:
            failures_by_category[category].append(
                {
                    "name": name,
                    "canonical": canonical_latin,
                    "expected": ko_expected,
                    "actual": ko_actual,
                    "comment": comment,
                }
            )

    # Print failures by category
    for category in ["Politics", "Business", "Entertainment", "Sports", "Other"]:
        if category in failures_by_category:
            failures = failures_by_category[category]
            print(f"\n{category} Category Failures ({len(failures)} total):")
            print("-" * 60)

            for fail in failures[:5]:  # Show up to 5 examples
                print(f"\nName: {fail['name']}")
                print(f"Canonical: {fail['canonical']}")
                print(f"Expected: {fail['expected']}")
                print(f"Actual: {fail['actual']}")
                if fail["comment"]:
                    print(f"Comment: {fail['comment'][:80]}...")

    # Analyze common patterns in failed names
    print("\n\nCommon Patterns in Failed Names:")
    print("=" * 60)

    all_failures = []
    for failures in failures_by_category.values():
        all_failures.extend(failures)

    # Check for specific issues
    patterns = {
        "Names with 'Jung/Jeong/Chung'": [],
        "Names with 'Chang/Jang'": [],
        "Names with special vowels": [],
        "Names with hyphenation issues": [],
        "Non-standard romanization": [],
    }

    for fail in all_failures:
        canonical = fail["canonical"]
        if any(part in canonical for part in ["Jung", "Jeong", "Chung"]):
            patterns["Names with 'Jung/Jeong/Chung'"].append(fail["name"])
        if any(part in canonical for part in ["Chang", "Jang"]):
            patterns["Names with 'Chang/Jang'"].append(fail["name"])
        if "-" in canonical and canonical.count("-") > 1:
            patterns["Names with hyphenation issues"].append(fail["name"])

        # Check for non-standard patterns
        parts = canonical.replace(",", "").split()
        for part in parts:
            if len(part) > 1 and part[0].isupper() and not part[1:].islower():
                patterns["Non-standard romanization"].append(fail["name"])
                break

    for pattern, names in patterns.items():
        if names:
            print(f"\n{pattern}: {len(names)} cases")
            print(f"  Examples: {', '.join(names[:5])}")

    print("\n\nRomanization Style Distribution:")
    print("=" * 60)
    for style, count in romanization_styles.items():
        print(f"{style}: {count} occurrences")


if __name__ == "__main__":
    main()
