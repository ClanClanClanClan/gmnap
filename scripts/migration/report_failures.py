#!/usr/bin/env python3
import yaml, unicodedata, csv, collections, re, pathlib
import sys

sys.path.insert(0, "../../src")
# from converter import eng2kor, kor2eng, _dice

data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))
miss_rr = collections.Counter()
miss_k2e = collections.Counter()


def norm(s):
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


for rec in data.values():
    e = rec["CanonicalLatin"]
    # Find Korean Hangul in variants (starts with Korean character)
    k_exp = None
    for variant in rec.get("AllCommonVariants", []):
        if variant and any(
            "\uac00" <= c <= "\ud7af" for c in variant
        ):  # Korean Hangul range
            k_exp = variant.replace(" ", "")  # Remove spaces
            break

    if not k_exp:
        continue  # Skip if no Korean variant found

    k = eng2kor(e)
    if k != k_exp:
        miss_rr.update(
            [re.sub(r"[^A-Za-z]", "", e.split()[0]).lower()]
        )  # bucket by surname token
        continue
    e2 = kor2eng(k, e) or ""
    if _dice(norm(e), norm(e2)) < 0.97:
        miss_k2e.update([e.split()[0].lower()])

print("Top ENG→KOR fails:", miss_rr.most_common(10))
print("Top round‑trip surname failures:", miss_k2e.most_common(10))
