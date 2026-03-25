import yaml
import pathlib
import sys

sys.path.append("src")
from converter import eng2kor

div = yaml.safe_load(pathlib.Path("data/korean_diverse_test.yaml").read_text())
bad = []
for k, v in div.items():
    rr = v["CanonicalLatin"]
    gold = [g for g in v["AllCommonVariants"] if all("\uac00" <= c <= "\ud7a3" for c in g)]
    ko = eng2kor(rr)
    if ko not in gold:
        bad.append((k, rr, ko, gold[0] if gold else "∅"))
open("/tmp/div_bad.txt", "w").write("\n".join("|".join(t) for t in bad))
print(len(bad))
