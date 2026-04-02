#!/usr/bin/env python3
"""Generate fastText training data from ALL labeled sources.

Combines:
- Golden dataset (500 entries)
- Wikidata mathematicians (39 entries)
- OpenAlex real-world collection (884 entries)
- OpenAlex 10K+ batch (when available)
"""

from __future__ import annotations
import json, sys, re, unicodedata, random
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.base import get_region_for_territory

COUNTRY_NAME_TO_CODE = {
    "Germany": "DE",
    "German Reich": "DE",
    "Kingdom of Prussia": "DE",
    "German Empire": "DE",
    "Saxe-Weimar-Eisenach": "DE",
    "France": "FR",
    "United Kingdom": "GB",
    "England": "GB",
    "United States": "US",
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
    "Israel": "IL",
    "Holy Roman Empire": "DE",
}


def normalize(name):
    nfkd = unicodedata.normalize("NFKD", name).lower()
    return re.sub(r"[^a-z\s'-]", "", nfkd).strip()


def parse_name(canonical):
    if "," in canonical:
        parts = canonical.split(",", 1)
        return normalize(parts[0].strip()), normalize(parts[1].strip())
    parts = canonical.rsplit(" ", 1)
    if len(parts) == 2:
        return normalize(parts[1]), normalize(parts[0])
    return normalize(canonical), ""


def load_all():
    entries = []

    # 1. Golden dataset
    p = Path("tests/fixtures/golden_mathematicians.json")
    if p.exists():
        for e in json.load(open(p)):
            surname, given = parse_name(e["CanonicalLatin"])
            region = e.get("ExpectedRegion")
            if region and surname:
                entries.append((surname, given, region))
        print(f"  Golden: {len(entries)} entries")

    # 2. Wikidata
    n0 = len(entries)
    p = Path("data/wikidata_mathematicians.json")
    if p.exists():
        for e in json.load(open(p)):
            cc = COUNTRY_NAME_TO_CODE.get(e.get("Country", ""))
            if not cc:
                continue
            region = get_region_for_territory(cc)
            surname, given = parse_name(e["CanonicalLatin"])
            if surname:
                entries.append((surname, given, region))
        print(f"  Wikidata: {len(entries) - n0} entries")

    # 3. OpenAlex small collection
    n0 = len(entries)
    p = Path("data/real_world_collection/robust_collection_20251104_124231.json")
    if p.exists():
        data = json.load(open(p))
        if isinstance(data, dict):
            data = data.get("all_profiles", [])
        for e in data:
            cc = e.get("country_code")
            if not cc:
                continue
            region = get_region_for_territory(cc)
            surname, given = parse_name(e.get("name", ""))
            if surname:
                entries.append((surname, given, region))
        print(f"  OpenAlex (small): {len(entries) - n0} entries")

    # 4. OpenAlex 10K+ batch
    n0 = len(entries)
    p = Path("data/ml_training/openalex_10k_mathematicians.json")
    if p.exists():
        for e in json.load(open(p)):
            cc = e.get("country_code")
            if not cc:
                continue
            region = get_region_for_territory(cc)
            surname, given = parse_name(e.get("name", ""))
            if surname:
                entries.append((surname, given, region))
        print(f"  OpenAlex (10K+): {len(entries) - n0} entries")

    return entries


def main():
    print("Loading all labeled data sources...")
    entries = load_all()
    print(f"\nTotal: {len(entries)} entries")
    print(f"Regions: {len(set(r for _,_,r in entries))}")
    print(f"Top 10: {Counter(r for _,_,r in entries).most_common(10)}")

    random.seed(42)
    random.shuffle(entries)

    n = len(entries)
    train_end = int(0.8 * n)
    val_end = int(0.9 * n)

    out = Path("data/ml_training")
    out.mkdir(parents=True, exist_ok=True)

    for split, start, end in [
        ("train", 0, train_end),
        ("val", train_end, val_end),
        ("test", val_end, n),
    ]:
        with open(out / f"surname_{split}.txt", "w") as sf, open(
            out / f"fullname_{split}.txt", "w"
        ) as ff:
            count = 0
            for surname, given, region in entries[start:end]:
                if surname:
                    sf.write(f"__label__{region} {surname}\n")
                    full = f"{surname} {given}".strip() if given else surname
                    ff.write(f"__label__{region} {full}\n")
                    count += 1
        print(f"  {split}: {count} entries")

    print(f"\nFiles saved to {out}/")


if __name__ == "__main__":
    main()
