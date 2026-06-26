#!/usr/bin/env python3
# Generate a realistic-looking production dataset of N entries in JSONL.
# Fields: GlobalID, CanonicalNative, Region, BirthYear, Sources, Advisors
import argparse
import json
import pathlib
import random

REGIONS = [f"R{i:02d}" for i in range(1, 38)]  # 37 regions
SOURCES = [
    "Crossref",
    "OpenAlex",
    "ORCID_ETD",
    "Wikidata_P184",
    "OAI",
    "HAL",
    "GND",
    "zbMATH",
]
SURNAMES = [
    "Lee",
    "Kim",
    "Park",
    "Choi",
    "Jung",
    "Moon",
    "Kang",
    "Lim",
    "Cho",
    "Jang",
    "Han",
    "Oh",
    "Shin",
    "Yoo",
    "Hwang",
    "Ahn",
    "Song",
    "Hong",
    "Seo",
    "Won",
]


def one(i):
    rid = f"ID-{i//10000}-{i%10000:04d}"
    region = random.choice(REGIONS)
    name = (
        random.choice(SURNAMES)
        + " "
        + random.choice(["Min", "Jae", "Sun", "Hyun", "Soo", "Young", "Hye"])
        + "-"
        + random.choice(["Woo", "Jin", "Ho", "Mi", "Kyung", "Seok", "Chul"])
    )
    by = 1900 + random.randint(0, 120)
    sources = random.sample(SOURCES, random.randint(1, 3))
    advisors = (
        [f"ID-{(i-1)//10000}-{(i-1)%10000:04d}"]
        if i > 0 and random.random() < 0.2
        else []
    )
    return {
        "GlobalID": rid,
        "CanonicalNative": name,
        "Region": region,
        "BirthYear": by,
        "Sources": sources,
        "Advisors": advisors,
    }


def main(N=1_000_000, out="datasets/scale/production_test_dataset_1m.jsonl", seed=7):
    random.seed(seed)
    p = pathlib.Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        for i in range(N):
            fh.write(
                json.dumps(one(i), ensure_ascii=True, separators=(",", ":")) + "\n"
            )
    print(f"Wrote {N} lines to {p}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1_000_000)
    ap.add_argument("--out", default="datasets/scale/production_test_dataset_1m.jsonl")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    main(a.n, a.out, a.seed)
