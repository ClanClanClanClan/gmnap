import json, yaml, pathlib
import sys
sys.path.insert(0, '../../../../../../../src')
from converter import eng2kor
import unicodedata

fail=[]
data=yaml.safe_load(pathlib.Path("data/diverse.yaml").read_text())
for k,v in data.items():
    rr=v["CanonicalLatin"]
    gold=[g for g in v["AllCommonVariants"] if any('\uac00'<=c<='\ud7a3' for c in g)]
    if not gold: continue
    ko=eng2kor(rr)
    if ko not in gold:
        fail.append((k, rr, ko, gold[0]))
print("Leftover diverse fails:", len(fail))
for row in fail[:10]:
    print(row)