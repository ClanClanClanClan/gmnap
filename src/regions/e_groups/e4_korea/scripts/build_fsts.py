import csv, pathlib, pynini as pn


def build(csv_path, roman_first=True):
    u = pn.Fst()
    s = u.add_state()
    u.set_start(s)
    u.set_final(s)
    for row in csv.reader(open(csv_path, encoding="utf8")):
        if len(row) >= 2:
            h, r = row[0], row[1]  # hangul, romanization
            u |= pn.cross(r.lower(), h) if roman_first else pn.cross(h, r.lower())
    return u.optimize()


pathlib.Path("models").mkdir(exist_ok=True)
build("resources/rr_syllable_map.csv", True).write("models/rom2han.fst")
build("resources/rr_syllable_map.csv", False).write("models/han2rom.fst")
print("✓ FSTs compiled")
