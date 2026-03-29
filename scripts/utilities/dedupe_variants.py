#!/usr/bin/env python3
import csv, pathlib, os

os.chdir("/Users/dylanpossamai/Dropbox/Work/Maths/gmnap/src/gmnap/regions/e_groups/e4_korea")
p = pathlib.Path("resources/variant_map.csv")
rows = [r for r in csv.reader(p.open(encoding="utf8")) if r and not r[0].startswith("#")]
canon = []
seen = set()
for h, rr, *tag in rows:
    h, rr, tag = h.strip(), rr.strip().lower(), (tag[0].strip() if tag else "")
    key = (h, rr)
    if key in seen:  # keep **first**; later duplicates ignored
        continue
    seen.add(key)
    canon.append([h, rr, tag])
# stable sort: explicit tag first, tagless last
order = {"SURNAME_0": 0, "GIVEN_0": 1, "": 9}
canon.sort(key=lambda x: (x[1], order.get(x[2], 5), x[0]))
csv.writer(p.open("w", newline="", encoding="utf8")).writerows(canon)
print("canonical rows :", len(canon))
