# \!/usr/bin/env python3
"""
Exit‑0 if no regression, non‑zero otherwise.
"""
import json
import sys
import unicodedata
import yaml
from pathlib import Path

# Add src to path for converter import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import converter as conv


def norm(s):  # same as make_locks.py
    import re

    s = unicodedata.normalize("NFKC", s).casefold()
    return re.sub(r"\W+", "", s)


def lock_ok(lock_path: Path) -> list[str]:
    errors = []
    data_set = lock_path.stem.split("_")[0]
    corpus = Path(
        {
            "math": "data/korean.yaml",
            "diverse": "data/diverse.yaml",
            "independent": "data/expanded_independent_validation_dataset.json",
        }[data_set]
    )

    # Load corpus file
    if str(corpus).endswith(".json"):
        raw_data = json.loads(corpus.read_text(encoding="utf8"))
        # Handle independent dataset structure
        if isinstance(raw_data, dict) and "test_cases" in raw_data:
            all_cases = {
                f"case_{i}": {
                    "CanonicalLatin": tc["name"],
                    "AllCommonVariants": [tc["expected_korean"]],
                }
                for i, tc in enumerate(raw_data["test_cases"])
            }
        else:
            all_cases = raw_data
    else:
        all_cases = yaml.safe_load(corpus.read_text(encoding="utf8"))

    locked = json.loads(lock_path.read_text(encoding="utf8"))

    for rec in locked:
        obj = all_cases.get(rec["case_id"])
        if not obj:
            errors.append(f"{rec['case_id']} missing from corpus")
            continue

        rr = obj["CanonicalLatin"]

        # Try to get Korean translation
        kor = conv.eng2kor(rr) or ""

        # Check n-best for tolerance
        if kor != rec["kor"]:
            kor_candidates = conv.eng2kor_nbest(rr, 3)
            if rec["kor"] in kor_candidates:
                kor = rec["kor"]

        if kor != rec["kor"]:
            errors.append(f"{rec['case_id']} kor mismatch {kor} ≠ {rec['kor']}")
            continue

        rr_back = conv.kor2eng(kor, rr) or ""
        dice_score = conv._enhanced_dice(rr, rr_back)
        if dice_score < 0.90:
            errors.append(f"{rec['case_id']} dice < 0.90 (got {dice_score:.3f})")
    return errors


failures = []
for lp in Path("locks").glob("*_sha256.json"):
    failures += lock_ok(lp)

if failures:
    print("❌ REGRESSION DETECTED:")
    for f in failures:
        print("   •", f)
    sys.exit(1)
print("✅ No regression versus lock files.")
