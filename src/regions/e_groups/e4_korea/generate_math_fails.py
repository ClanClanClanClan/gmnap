import yaml, pathlib
import sys

sys.path.append("src")
# from converter import eng2kor, kor2eng, _enhanced_dice

data = yaml.safe_load(pathlib.Path("data/korean.yaml").read_text())
fails = []
for k, v in data.items():
    rr = v["CanonicalLatin"]
    gold = v["AllCommonVariants"][0].replace(" ", "")
    kor = eng2kor(rr)
    if kor is None:
        rr2 = ""
    else:
        rr2 = kor2eng(kor, rr) or ""
    if _enhanced_dice(rr, rr2) < 0.9:
        fails.append((k, rr, kor, rr2))
fails.sort()
open("/tmp/math_fails.txt", "w").write(
    "\n".join(f"{a}|{b}|{c}|{d}" for a, b, c, d in fails)
)
print(f"{len(fails)} fails  ➜  /tmp/math_fails.txt")
