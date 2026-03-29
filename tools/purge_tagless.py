#!/usr/bin/env python3
import csv, pathlib, os

os.chdir(
    "/Users/dylanpossamai/Dropbox/Work/Maths/gmnap/src/gmnap/regions/e_groups/e4_korea"
)
p = pathlib.Path("resources/variant_map.csv")
rows = list(csv.reader(p.open(encoding="utf8")))
tagged = {(h, rr) for h, rr, tag in rows if tag}
rows = [r for r in rows if r[2] or (r[0], r[1]) not in tagged]
csv.writer(p.open("w", newline="", encoding="utf8")).writerows(rows)
print("rows after purging :", len(rows))
