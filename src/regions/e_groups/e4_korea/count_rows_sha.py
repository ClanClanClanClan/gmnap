import yaml, hashlib, pathlib, sys, json, unicodedata, os
for f in ["data/korean.yaml","data/korean_diverse_test.yaml"]:
    p=pathlib.Path(f); y=yaml.safe_load(p.read_text())
    h=hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    print(f"{p.name:24} rows={len(y):3}  sha={h}")