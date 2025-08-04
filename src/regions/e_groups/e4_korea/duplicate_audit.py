import csv, collections, pathlib, sys, unicodedata as ud
dup_in, dup_out = collections.defaultdict(list), collections.defaultdict(list)
with open("resources/rr_syllable_map.csv") as f:
    for i,row in enumerate(csv.reader(f)):
        if len(row)<3: continue
        han, rom, w, *rest = [ud.normalize("NFC", c.strip()) for c in row[:4]]
        key_in  = (rom.lower(), rest[1] if len(rest)>1 else "", rest[0] if rest else "")  # rom,pos,context
        key_out = (han, rest[1] if len(rest)>1 else "", rest[0] if rest else "")          # han,pos,context
        dup_in[key_in].append((i, row))
        dup_out[key_out].append((i, row))
bad = {k:v for k,v in dup_in.items() if len(v)>1}
print(f"✎  duplicate romanisation keys: {len(bad)}")
path="/tmp/dup.csv"; pathlib.Path(path).write_text(
    "\n".join(",".join(map(str,[i,*r])) for v in bad.values() for i,r in v))
print(f"  →  list written to {path}")