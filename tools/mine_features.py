#!/usr/bin/env python3
"""Auto-mine surname/given features from labeled data.

Phase 3: Territory-level mining with leaf roll-up.
Mines features at CC (country code) level first, then rolls up to leaf regions.
Log-odds computed against parent-group baseline (not global) with reliability scaling.

Reads golden dataset + Wikidata + OpenAlex, outputs config/learned_features.json.

Usage: PYTHONPATH=. python3 tools/mine_features.py
"""

from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.regions.base import TERRITORY_TO_REGION, get_region_for_territory
from src.regions.manager_optimized import (
    LEAF_TO_GROUP,
    REGION_GROUPS,
    SIGNATURE_SUFFIXES,
)

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
    "Lithuania": "LT",
    "Latvia": "LV",
    "Estonia": "EE",
    "Czech Republic": "CZ",
    "Czechoslovakia": "CZ",
    "Romania": "RO",
    "Portugal": "PT",
    "Spain": "ES",
    "Belgium": "BE",
    "Ireland": "IE",
    "Scotland": "GB",
    "Wales": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "New Zealand": "NZ",
    "South Africa": "ZA",
    "Argentina": "AR",
    "Colombia": "CO",
    "Peru": "PE",
    "Chile": "CL",
    "Venezuela": "VE",
    "Vietnam": "VN",
    "Thailand": "TH",
    "Philippines": "PH",
    "Indonesia": "ID",
    "Malaysia": "MY",
    "Singapore": "SG",
    "Pakistan": "PK",
    "Bangladesh": "BD",
    "Sri Lanka": "LK",
    "Nepal": "NP",
    "Nigeria": "NG",
    "Kenya": "KE",
    "Ghana": "GH",
    "Ethiopia": "ET",
    "Tanzania": "TZ",
    "Morocco": "MA",
    "Algeria": "DZ",
    "Tunisia": "TN",
    "Saudi Arabia": "SA",
    "Iraq": "IQ",
    "Syria": "SY",
    "Lebanon": "LB",
    "Jordan": "JO",
    "Armenia": "AM",
    "Georgia": "GE",
    "Azerbaijan": "AZ",
    "Kazakhstan": "KZ",
    "Uzbekistan": "UZ",
    # Historical polities from Wikidata
    "Kingdom of Italy": "IT",
    "United Kingdom of Great Britain and Ireland": "GB",
    "Kingdom of the Netherlands": "NL",
    "Empire of Japan": "JP",
    "British Raj": "IN",
    "Kingdom of Denmark": "DK",
    "People's Republic of China": "CN",
    "Dominion of India": "IN",
    "Kingdom of Great Britain": "GB",
    "Ukraine": "UA",
    "Kingdom of England": "GB",
    "Austrian Empire": "AT",
    "Slovenia": "SI",
    "Cisleithania": "AT",
    "Ottoman Empire": "TR",
    "Qing dynasty": "CN",
    "Serbia": "RS",
    "Dutch Republic": "NL",
    "Austria–Hungary": "AT",
    "Austria-Hungary": "AT",
    "Socialist Federal Republic of Yugoslavia": "RS",
    "Bulgaria": "BG",
    "Abbasid Caliphate": "IQ",
    "Kingdom of Yugoslavia": "RS",
    "Polish–Lithuanian Commonwealth": "PL",
    "Polish-Lithuanian Commonwealth": "PL",
    "Weimar Republic": "DE",
    "German Democratic Republic": "DE",
    "Russian Socialist Federative Soviet Republic": "RU",
    "Slovakia": "SK",
    "Kingdom of Serbs, Croats and Slovenes": "RS",
    "Belarus": "BY",
    "Byzantine Empire": "GR",
    "Second Polish Republic": "PL",
    "Republic of China": "CN",
    "Kingdom of Portugal": "PT",
    "Kingdom of Saxony": "DE",
    "Nazi Germany": "DE",
    "Taiwan": "TW",
    "Kingdom of Bavaria": "DE",
    "Kingdom of Scotland": "GB",
    "Classical Athens": "GR",
    "Congress Poland": "PL",
    "Uruguay": "UY",
    "Habsburg monarchy": "AT",
    "Grand Duchy of Finland": "FI",
    "Moldova": "MD",
    "Kingdom of Württemberg": "DE",
    "Electorate of Saxony": "DE",
    "Ancient Rome": "IT",
    "Papal States": "IT",
    "Albania": "AL",
    "Russian Soviet Federative Socialist Republic": "RU",
    "Luxembourg": "LU",
    "Cuba": "CU",
    "Grand Duchy of Baden": "DE",
    "Kingdom of Hanover": "DE",
    "Grand Duchy of Tuscany": "IT",
    "Habsburg Netherlands": "BE",
    "Ming dynasty": "CN",
    "Republic of Florence": "IT",
    "Duchy of Württemberg": "DE",
    "Kingdom of Romania": "RO",
    "Republic of Geneva": "CH",
    "Crown of Aragon": "ES",
    "Ukrainian People's Republic": "UA",
    "Croatia": "HR",
    "Republic of India": "IN",
    "Republic of Korea": "KR",
    "North Korea": "KR",
    "Myanmar": "MM",
    "Cambodia": "KH",
    "Iceland": "IS",
    "Costa Rica": "CR",
    "Panama": "PA",
    "Ecuador": "EC",
    "Paraguay": "PY",
    "Bolivia": "BO",
    "Honduras": "HN",
    "Guatemala": "GT",
    "Dominican Republic": "DO",
    "Puerto Rico": "PR",
    "Jamaica": "JM",
    "Trinidad and Tobago": "TT",
    "Barbados": "BB",
    "Sudan": "SD",
    "Cameroon": "CM",
    "Senegal": "SN",
    "Mali": "ML",
    "Ivory Coast": "CI",
    "Côte d'Ivoire": "CI",
    "Uganda": "UG",
    "Zimbabwe": "ZW",
    "Mozambique": "MZ",
    "Angola": "AO",
    "Botswana": "BW",
    "Namibia": "NA",
    "Rwanda": "RW",
    "Qatar": "QA",
    "United Arab Emirates": "AE",
    "Oman": "OM",
    "Kuwait": "KW",
    "Bahrain": "BH",
    "Yemen": "YE",
    "Libya": "LY",
}

# ── Mining parameters ──
ALPHA = 0.5  # Laplace smoothing
MIN_COUNT_LEAF = 3  # minimum count(feature, leaf) to emit
MIN_COUNT_GLOBAL = 15  # minimum count(feature, all) to emit
MIN_LEAF_SUPPORT = 50  # skip leaves with fewer than this many entries
WEIGHT_CLIP = 0.8  # clip weights to [-clip, clip]
RELIABILITY_REGION_K = 200  # sqrt(n_leaf / (n_leaf + K))
RELIABILITY_FEATURE_K = 20  # sqrt(c_total / (c_total + K))


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
    """Load and unify all labeled data sources.

    Returns list of (surname_tokens, given_tokens, region, cc) tuples.
    """
    entries = []

    # 1. Golden dataset (has ExpectedRegion and CountryCodes)
    golden_path = Path("tests/fixtures/golden_mathematicians.json")
    if golden_path.exists():
        with open(golden_path) as f:
            for e in json.load(f):
                surname, given = parse_surname_given(e["CanonicalLatin"])
                region = e.get("ExpectedRegion")
                ccs = e.get("CountryCodes", [])
                cc = ccs[0] if ccs else None
                if region:
                    entries.append((tokenize(surname), tokenize(given), region, cc))

    # 2. Wikidata (has country name -> CC mapping, or direct CountryCode)
    wiki_path = Path("data/wikidata_mathematicians.json")
    n_wiki = 0
    if wiki_path.exists():
        with open(wiki_path) as f:
            for e in json.load(f):
                # Try direct CC first, then country name mapping
                cc = e.get("CountryCode") or COUNTRY_NAME_TO_CODE.get(
                    e.get("Country", "")
                )
                if not cc:
                    continue
                region = get_region_for_territory(cc)
                surname, given = parse_surname_given(e["CanonicalLatin"])
                entries.append((tokenize(surname), tokenize(given), region, cc))
                n_wiki += 1
        print(f"  Wikidata: {n_wiki} entries")

    # 3. OpenAlex robust collection
    oalex_path = Path(
        "data/real_world_collection/robust_collection_20251104_124231.json"
    )
    if oalex_path.exists():
        with open(oalex_path) as f:
            data = json.load(f)
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
                entries.append((tokenize(surname), tokenize(given), region, cc))

    # 4. OpenAlex 15K batch
    n0 = len(entries)
    oalex_15k = Path("data/ml_training/openalex_10k_mathematicians.json")
    if oalex_15k.exists():
        with open(oalex_15k) as f:
            for e in json.load(f):
                cc = e.get("country_code")
                if not cc:
                    continue
                region = get_region_for_territory(cc)
                name = e.get("name", "")
                surname, given = parse_surname_given(name)
                entries.append((tokenize(surname), tokenize(given), region, cc))
        print(f"  OpenAlex 15K: {len(entries) - n0} entries")

    return entries


def filter_disagreements(entries):
    """Remove entries where a signature suffix points to a different region than the label."""
    from src.regions.manager_optimized import _STRONG

    suffix_to_region = {}
    for region_code, patterns in _STRONG.items():
        for suf in patterns.get("surname_suffix", set()):
            if suf in SIGNATURE_SUFFIXES:
                suffix_to_region[suf] = region_code

    filtered = []
    skipped = 0
    for surname_toks, given_toks, region, cc in entries:
        disagreement = False
        for tok in surname_toks:
            for suf, suf_region in suffix_to_region.items():
                if tok.endswith(suf) and len(tok) > len(suf) + 1:
                    suf_group = LEAF_TO_GROUP.get(suf_region)
                    label_group = LEAF_TO_GROUP.get(region)
                    if suf_group and label_group and suf_group != label_group:
                        disagreement = True
                        break
            if disagreement:
                break
        if not disagreement:
            filtered.append((surname_toks, given_toks, region, cc))
        else:
            skipped += 1

    if skipped > 0:
        print(f"  Filtered {skipped} entries with signature-suffix disagreements")
    return filtered


def compute_territory_log_odds(
    leaf_feature_counts, leaf_totals, group_feature_counts, group_totals
):
    """Compute log-odds against parent-group baseline with reliability scaling.

    Expert formula:
      raw = log(p_leaf) - log(p_group)
      weight = clip(raw * sqrt(n_leaf/(n_leaf+200)) * sqrt(c_total/(c_total+20)), -0.8, 0.8)
    """
    all_leaves = sorted(leaf_totals.keys())
    K = len(all_leaves)

    result = {}
    for feature, region_counts in leaf_feature_counts.items():
        c_total = sum(region_counts.values())
        if c_total < MIN_COUNT_GLOBAL:
            continue

        weights = {}
        for leaf in all_leaves:
            c_leaf = region_counts.get(leaf, 0)
            if c_leaf < MIN_COUNT_LEAF:
                continue
            n_leaf = leaf_totals.get(leaf, 0)
            if n_leaf < MIN_LEAF_SUPPORT:
                continue

            group = LEAF_TO_GROUP.get(leaf)
            if not group:
                continue

            # Log-odds vs parent group baseline
            p_leaf = (c_leaf + ALPHA) / (n_leaf + ALPHA * K)
            c_group = group_feature_counts.get(feature, {}).get(group, 0)
            n_group = group_totals.get(group, 0)
            if n_group == 0:
                continue
            p_group = (c_group + ALPHA) / (n_group + ALPHA * K)

            raw = math.log(p_leaf) - math.log(p_group)

            # Reliability scaling
            rel_region = math.sqrt(n_leaf / (n_leaf + RELIABILITY_REGION_K))
            rel_feature = math.sqrt(c_total / (c_total + RELIABILITY_FEATURE_K))
            weight = max(-WEIGHT_CLIP, min(WEIGHT_CLIP, raw * rel_region * rel_feature))

            if abs(weight) >= 0.10:
                weights[leaf] = round(weight, 3)

        if weights:
            result[feature] = weights

    return result


def main():
    entries = load_data()
    print(f"Loaded {len(entries)} labeled entries")

    # Filter disagreements
    entries = filter_disagreements(entries)
    print(f"After filtering: {len(entries)} entries")

    # Count at leaf level (rolled up from CC)
    all_regions = sorted(set(r for _, _, r, _ in entries))
    leaf_totals = Counter(r for _, _, r, _ in entries)

    # Compute group totals
    group_totals = defaultdict(int)
    for leaf, count in leaf_totals.items():
        grp = LEAF_TO_GROUP.get(leaf)
        if grp:
            group_totals[grp] += count

    print(
        f"Regions: {len(all_regions)}, distribution: {dict(leaf_totals.most_common(10))}"
    )
    print(f"Groups: {len(group_totals)}")
    leaves_with_enough = sum(1 for n in leaf_totals.values() if n >= MIN_LEAF_SUPPORT)
    print(
        f"Leaves with >= {MIN_LEAF_SUPPORT} entries: {leaves_with_enough}/{len(all_regions)}"
    )

    # Count features at leaf level
    surname_counts = defaultdict(Counter)
    suffix_counts = defaultdict(Counter)
    ngram_counts = defaultdict(Counter)
    given_counts = defaultdict(Counter)

    for surname_toks, given_toks, region, cc in entries:
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

    # Roll up to group level for baseline computation
    def rollup_to_group(leaf_counts_dict):
        group_counts = defaultdict(Counter)
        for feature, region_counter in leaf_counts_dict.items():
            for leaf, count in region_counter.items():
                grp = LEAF_TO_GROUP.get(leaf)
                if grp:
                    group_counts[feature][grp] += count
        return group_counts

    surname_group = rollup_to_group(surname_counts)
    suffix_group = rollup_to_group(suffix_counts)
    ngram_group = rollup_to_group(ngram_counts)
    given_group = rollup_to_group(given_counts)

    # Compute territory-aware log-odds
    surname_weights = compute_territory_log_odds(
        surname_counts, leaf_totals, surname_group, group_totals
    )
    suffix_weights = compute_territory_log_odds(
        suffix_counts, leaf_totals, suffix_group, group_totals
    )
    ngram_weights = compute_territory_log_odds(
        ngram_counts, leaf_totals, ngram_group, group_totals
    )
    given_weights = compute_territory_log_odds(
        given_counts, leaf_totals, given_group, group_totals
    )

    print(f"\nMined features (territory roll-up, min_leaf={MIN_LEAF_SUPPORT}):")
    print(f"  Surnames: {len(surname_weights)}")
    print(f"  Suffixes: {len(suffix_weights)}")
    print(f"  N-grams:  {len(ngram_weights)}")
    print(f"  Given:    {len(given_weights)}")

    # Save
    output = {
        "version": "2.0",
        "mining_method": "territory_rollup",
        "source_count": len(entries),
        "min_leaf_support": MIN_LEAF_SUPPORT,
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
