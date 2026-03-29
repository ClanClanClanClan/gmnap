#!/usr/bin/env python3
"""Create SHA‑256 regression locks for all passing cases."""
import json, hashlib, os, yaml, unicodedata, sys
from pathlib import Path

# Add src to path for converter import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# import converter as conv

DATASETS = {
    "math": "data/korean.yaml",
    "diverse": "data/diverse.yaml",
    "independent": "data/expanded_independent_validation_dataset.json",
}


def norm(s: str) -> str:
    """NFKC + casefold + strip punctuation; same as validator logic."""
    s = unicodedata.normalize("NFKC", s)
    return "".join(c for c in s.casefold() if c.isalnum())


def digest(record: dict) -> str:
    blob = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def main() -> None:
    for key, path in DATASETS.items():
        locked = []

        # Skip if file doesn't exist
        if not Path(path).exists():
            print(f"⚠️  {key}: {path} not found - skipping")
            continue

        # Load data file (YAML or JSON)
        if path.endswith(".json"):
            data = json.loads(Path(path).read_text(encoding="utf8"))
            # Handle independent dataset structure
            if isinstance(data, dict) and "test_cases" in data:
                raw = {
                    f"case_{i}": {
                        "CanonicalLatin": tc["name"],
                        "AllCommonVariants": [tc["expected_korean"]],
                    }
                    for i, tc in enumerate(data["test_cases"])
                }
            else:
                raw = data
        else:
            raw = yaml.safe_load(Path(path).read_text(encoding="utf8"))

        for case_id, obj in raw.items():
            rr = obj.get("CanonicalLatin")
            if not rr:
                continue

            # Convert to Korean
            kor = conv.eng2kor(rr)
            if not kor:
                continue

            # Check if the Korean matches any expected variant
            variants = obj.get("AllCommonVariants", [])

            # For n-best tolerance
            kor_candidates = conv.eng2kor_nbest(rr, 3)
            matched = False
            for kor_cand in kor_candidates:
                if kor_cand in variants:
                    kor = kor_cand
                    matched = True
                    break

            if not matched and kor not in variants:
                continue

            # Check roundtrip
            rr_back = conv.kor2eng(kor, rr) or ""
            if conv._enhanced_dice(rr, rr_back) < 0.90:
                continue
            rec = {"case_id": case_id, "rr": norm(rr), "kor": kor}
            rec["sha256"] = digest(rec)
            rec["converter_commit"] = os.environ.get(
                "GIT_COMMIT", os.popen("git rev-parse --short HEAD").read().strip()
            )
            locked.append(rec)
        out = Path(f"locks/{key}_sha256.json")
        out.write_text(json.dumps(locked, indent=2, ensure_ascii=False) + "\n")
        print(f"✨  {key}: {len(locked)} cases locked → {out}")


if __name__ == "__main__":
    main()
