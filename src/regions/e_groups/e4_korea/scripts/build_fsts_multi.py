import csv, pathlib, pynini as pn

TOK = "utf8"


def read_rows_with_pos():
    """Read CSV rows with 5-column format: hangul,roman,weight,context,pos"""
    # 1) base RR table rows
    for row in csv.reader(open("resources/rr_syllable_map.csv", encoding="utf8")):
        if len(row) >= 2 and not row[0].startswith("#"):
            hangul, roman = row[0], row[1]
            weight = row[2] if len(row) > 2 else "0.0"
            context = row[3] if len(row) > 3 else ""
            pos = row[4] if len(row) > 4 else ""

            # Parse weight
            try:
                w = float(weight) if weight else 0.0
            except ValueError:
                w = 0.0

            yield hangul, roman, w, context, pos

    # 2) variant rows (add as general)
    for row in csv.reader(open("resources/variant_map.csv", encoding="utf8")):
        if len(row) >= 3 and not row[0].startswith("#"):
            h, r, tag = row[0], row[1], row[2]
            w = 0.0 if tag == "SURNAME_0" else 1.0
            yield h, r, w, "", ""


def build_positional(direction: str):
    """Build surname and given-name specific FSTs"""
    fst_surname = pn.Fst()
    fst_given = pn.Fst()
    fst_general = pn.Fst()

    # Initialize states
    for fst in [fst_surname, fst_given, fst_general]:
        s = fst.add_state()
        fst.set_start(s)
        fst.set_final(s)

    for hangul, roman, weight, context, pos in read_rows_with_pos():
        if direction == "rom2han":
            arc = pn.accep(roman.lower(), weight=weight) @ pn.cross(
                roman.lower(), hangul
            )
        else:
            arc = pn.accep(hangul, weight=weight) @ pn.cross(hangul, roman.lower())

        if pos == "S":  # Surname only
            fst_surname |= arc
        elif pos == "G":  # Given name only
            fst_given |= arc
        else:  # General (empty pos) - add to all
            fst_surname |= arc
            fst_given |= arc
            fst_general |= arc

    return fst_surname.optimize(), fst_given.optimize(), fst_general.optimize()


# Support atomic operations via FST_OUTPUT_DIR environment variable
import os

output_dir = os.environ.get("FST_OUTPUT_DIR", "models")
pathlib.Path(output_dir).mkdir(exist_ok=True, parents=True)

# Build position-specific FSTs
surname_rom2han, given_rom2han, general_rom2han = build_positional("rom2han")
surname_han2rom, given_han2rom, general_han2rom = build_positional("han2rom")

# Write FSTs to specified output directory
surname_rom2han.write(f"{output_dir}/rom2han_surname.fst")
given_rom2han.write(f"{output_dir}/rom2han_given.fst")
general_rom2han.write(f"{output_dir}/rom2han_multi.fst")

surname_han2rom.write(f"{output_dir}/han2rom_surname.fst")
given_han2rom.write(f"{output_dir}/han2rom_given.fst")
general_han2rom.write(f"{output_dir}/han2rom_multi.fst")

print(f"✓ Position-specific FSTs written: 6 FST files created in {output_dir}")
