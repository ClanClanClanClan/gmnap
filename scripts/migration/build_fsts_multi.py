import csv, pathlib, pynini as pn

TOK = None

# Collect hangul chars that have SURNAME_0 variants
pref = set()
for row in csv.reader(open("resources/variant_map.csv", encoding="utf8")):
    if len(row) >= 3 and row[2] == "SURNAME_0":
        pref.add(row[0])


def final_weight(h, base_w):
    # If a SURNAME_0 exists for this Hangul and this row is *not* that spelling,
    # bump weight slightly so it never ties with the preferred one.
    return base_w if h not in pref else 0.1


def read_rows():
    # 1) base RR table rows (weight 0)
    for row in csv.reader(open("resources/rr_syllable_map.csv", encoding="utf8")):
        if len(row) >= 2 and not row[0].startswith("#"):
            h, r = row[0], row[1]
            w = final_weight(h, 0.0)
            yield h, r, w
    # 2) variant rows
    for row in csv.reader(open("resources/variant_map.csv", encoding="utf8")):
        if len(row) >= 3 and not row[0].startswith("#"):
            h, r, tag = row[0], row[1], row[2]
            w = 0.0 if tag == "SURNAME_0" else 1.0
            yield h, r, w


def build(direction: str):
    u = pn.Fst()
    s = u.add_state()
    u.set_start(s)
    u.set_final(s)
    for h, r, w in read_rows():
        if direction == "rom2han":
            # For rom2han, create arc from romanization to hangul with weight
            u |= pn.accep(r.lower(), weight=w) @ pn.cross(r.lower(), h)
        else:
            # For han2rom, create arc from hangul to romanization with weight
            u |= pn.accep(h, weight=w) @ pn.cross(h, r.lower())
    return u.optimize()


pathlib.Path("models").mkdir(exist_ok=True)
build("rom2han").write("models/rom2han_multi.fst")
build("han2rom").write("models/han2rom_multi.fst")
print("✓ multi‑path FSTs written")
