#!/usr/bin/env python3
"""Auto-mine surname/given features from labeled data.

Reads golden dataset + Wikidata + OpenAlex, computes smoothed
log-odds weights for surnames, suffixes, char n-grams, and given names.
Outputs config/learned_features.json for use by the scorer.

Usage: PYTHONPATH=. python3 tools/mine_features.py
"""

from __future__ import annotations
import json, math, sys, unicodedata, re
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.regions.base import get_region_for_territory

# Country name -> ISO mapping for Wikidata
COUNTRY_NAME_TO_CODE = {
    "Germany": "DE",
    "German Reich": "DE",
    "Kingdom of Prussia": "DE",
    "German Empire": "DE",
    "Saxe-Weimar-Eisenach": "DE",
    "France": "FR",
    "Kingdom of France": "FR",
    "United Kingdom": "GB",
    "England": "GB",
    "United States": "US",
    "United States of America": "US",
    "Russia": "RU",
    "Russian Empire": "RU",
    "Soviet Union": "RU",
    "Italy": "IT",
    "Switzerland": "CH",
    "Netherlands": "NL",
    "Austria": "AT",
    "Poland": "PL",
    "Hungary": "HU",
    "Sweden": "SE",
    "Norway": "NO",
    "Denmark": "DK",
    "Finland": "FI",
    "Greece": "GR",
    "Turkey": "TR",
    "Iran": "IR",
    "India": "IN",
    "China": "CN",
    "Japan": "JP",
    "South Korea": "KR",
    "Brazil": "BR",
    "Mexico": "MX",
    "Israel": "IL",
    "Egypt": "EG",
    "Holy Roman Empire": "DE",
    "Republic of Venice": "IT",
    "Duchy of Brunswick": "DE",
    "Electorate of Hanover": "DE",
}

ALPHA = 0.5  # Laplace smoothing
MIN_COUNT = 2
MIN_WEIGHT = 0.3
MAX_REGION_FRAC = 0.6  # skip features in >60% of regions


def normalize(name):
    """NFKD normalize + lowercase + strip diacritics for matching."""
    nfkd = unicodedata.normalize("NFKD", name).lower()
    return "".join(
        ch for ch in nfkd if unicodedata.category(ch) != "Mn" or ch.isalnum()
    )


def tokenize(name):
    """Split name into tokens."""
    name = normalize(name)
    return re.findall(r"[a-z]+(?:['-][a-z]+)*", name)


def parse_surname_given(canonical_latin):
    """Parse 'Surname, Given' or 'Given Surname' format."""
    if "," in canonical_latin:
        parts = canonical_latin.split(",", 1)
        return parts[0].strip(), parts[1].strip()
    parts = canonical_latin.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[1], parts[0]
    return canonical_latin, ""


def char_ngrams(word, min_n=2, max_n=3):
    """Extract character n-grams from a word."""
    ngrams = []
    for n in range(min_n, max_n + 1):
        for i in range(len(word) - n + 1):
            ngrams.append(word[i : i + n])
    return ngrams


def suffixes(word, min_len=2, max_len=5):
    """Extract suffix patterns of various lengths."""
    result = []
    for n in range(min_len, min(max_len + 1, len(word))):
        result.append(word[-n:])
    return result


def load_data():
    """Load and unify all labeled data sources."""
    entries = []  # list of (surname_tokens, given_tokens, region)

    # 1. Golden dataset
    golden_path = Path("tests/fixtures/golden_mathematicians.json")
    if golden_path.exists():
        with open(golden_path) as f:
            for e in json.load(f):
                surname, given = parse_surname_given(e["CanonicalLatin"])
                region = e.get("ExpectedRegion")
                if region:
                    entries.append((tokenize(surname), tokenize(given), region))

    # 2. Wikidata
    wiki_path = Path("data/wikidata_mathematicians.json")
    if wiki_path.exists():
        with open(wiki_path) as f:
            for e in json.load(f):
                country = e.get("Country", "")
                cc = COUNTRY_NAME_TO_CODE.get(country)
                if not cc:
                    continue
                region = get_region_for_territory(cc)
                surname, given = parse_surname_given(e["CanonicalLatin"])
                entries.append((tokenize(surname), tokenize(given), region))

    # 3. OpenAlex
    oalex_path = Path(
        "data/real_world_collection/robust_collection_20251104_124231.json"
    )
    if oalex_path.exists():
        with open(oalex_path) as f:
            data = json.load(f)
            # Handle nested format: {"all_profiles": [...]}
            if isinstance(data, dict) and "all_profiles" in data:
                profiles = data["all_profiles"]
            elif isinstance(data, list):
                profiles = data
            else:
                profiles = []
            for e in profiles:
                cc = e.get("country_code")
                if not cc:
                    continue
                region = get_region_for_territory(cc)
                name = e.get("name", "")
                surname, given = parse_surname_given(name)
                entries.append((tokenize(surname), tokenize(given), region))

    return entries


def compute_log_odds(feature_region_counts, region_totals, all_regions):
    """Compute smoothed log-odds for each feature-region pair."""
    N = len(all_regions)
    total_overall = sum(region_totals.values())

    result = {}
    for feature, region_counts in feature_region_counts.items():
        count_overall = sum(region_counts.values())

        # Skip rare features
        if count_overall < MIN_COUNT:
            continue

        # Skip features spread across too many regions
        if len(region_counts) > MAX_REGION_FRAC * N:
            continue

        weights = {}
        for r in all_regions:
            count_r = region_counts.get(r, 0)
            total_r = region_totals.get(r, 0)

            # Smoothed log-odds
            p_feature_given_region = (count_r + ALPHA) / (total_r + ALPHA * N)
            p_feature_overall = (count_overall + ALPHA) / (total_overall + ALPHA * N)

            w = math.log(p_feature_given_region) - math.log(p_feature_overall)

            if abs(w) >= MIN_WEIGHT:
                weights[r] = round(w, 3)

        if weights:
            result[feature] = weights

    return result


def main():
    entries = load_data()
    print(f"Loaded {len(entries)} labeled entries")

    all_regions = sorted(set(r for _, _, r in entries))
    region_totals = Counter(r for _, _, r in entries)
    print(
        f"Regions: {len(all_regions)}, distribution: {dict(region_totals.most_common(10))}"
    )

    # Count features
    surname_counts = defaultdict(Counter)  # surname_token -> {region: count}
    suffix_counts = defaultdict(Counter)
    ngram_counts = defaultdict(Counter)
    given_counts = defaultdict(Counter)

    for surname_toks, given_toks, region in entries:
        for tok in surname_toks:
            if len(tok) >= 2:
                surname_counts[tok][region] += 1
                for suf in suffixes(tok):
                    suffix_counts[suf][region] += 1
                for ng in char_ngrams(tok):
                    ngram_counts[ng][region] += 1
        for tok in given_toks:
            if len(tok) >= 2:
                given_counts[tok][region] += 1

    # Compute log-odds
    surname_weights = compute_log_odds(surname_counts, region_totals, all_regions)
    suffix_weights = compute_log_odds(suffix_counts, region_totals, all_regions)
    ngram_weights = compute_log_odds(ngram_counts, region_totals, all_regions)
    given_weights = compute_log_odds(given_counts, region_totals, all_regions)

    print(f"\nMined features:")
    print(f"  Surnames: {len(surname_weights)}")
    print(f"  Suffixes: {len(suffix_weights)}")
    print(f"  N-grams:  {len(ngram_weights)}")
    print(f"  Given:    {len(given_weights)}")

    # Save
    output = {
        "version": "1.0",
        "source_count": len(entries),
        "regions": all_regions,
        "alpha": ALPHA,
        "surnames": surname_weights,
        "suffixes": suffix_weights,
        "ngrams": ngram_weights,
        "given_names": given_weights,
    }

    out_path = Path("config/learned_features.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path} ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
