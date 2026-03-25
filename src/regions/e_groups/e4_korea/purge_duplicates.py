import csv
import unicodedata as ud
import pathlib

rows, best = [], {}
for row in csv.reader(open("resources/rr_syllable_map.csv")):
    if len(row) < 3:
        continue
    han, rom, w, *rest = [ud.normalize("NFC", c.strip()) for c in row[:4]]
    key = (
        han,
        rom.lower(),
        rest[0] if rest else "",
        rest[1] if len(rest) > 1 else "",
    )  # han,rom,pos,context
    try:
        w = float(w)
        row[2] = f"{w:.4f}"
    except Exception:
        continue
    if key not in best or w < float(best[key][2]):  # Keep most negative (best) weight
        best[key] = row
out = pathlib.Path("resources/rr_syllable_map.csv")
csv.writer(out.open("w")).writerows(best.values())
print(f"✓  deduplicated: kept {len(best)} rows")
