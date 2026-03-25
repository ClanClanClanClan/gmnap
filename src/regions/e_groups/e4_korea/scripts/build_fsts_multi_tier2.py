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


def compile_for_pos(rows, want_pos, direction):
    """Compile FST for specific position with general fallback."""
    fst = pn.Fst()
    s = fst.add_state()
    fst.set_start(s)
    fst.set_final(s)

    for hangul, roman, weight, context, pos in rows:
        # Include if: 1) matches wanted position, 2) is general (empty pos)
        if pos == want_pos or pos == "":
            # Boost general mappings by +1.0 to make them tie-breakers
            final_weight = weight + (1.0 if pos == "" else 0.0)

            if direction == "rom2han":
                arc = pn.accep(roman.lower(), weight=final_weight) @ pn.cross(roman.lower(), hangul)
            else:
                arc = pn.accep(hangul, weight=final_weight) @ pn.cross(hangul, roman.lower())

            fst |= arc

    return fst.optimize()


def build_tier2_fsts(direction="rom2han"):
    """Build Tier 2 stackable FSTs with context-priority union."""
    # Read all rows once
    all_rows = list(read_rows_with_pos())

    # Create position-specific FSTs
    fst_surname = compile_for_pos(all_rows, "S", direction)
    fst_given = compile_for_pos(all_rows, "G", direction)

    # Create general-only FST (for reference, though union handles this)
    fst_general = pn.Fst()
    s = fst_general.add_state()
    fst_general.set_start(s)
    fst_general.set_final(s)

    for hangul, roman, weight, context, pos in all_rows:
        if pos == "":  # Only general mappings
            if direction == "rom2han":
                arc = pn.accep(roman.lower(), weight=weight) @ pn.cross(roman.lower(), hangul)
            else:
                arc = pn.accep(hangul, weight=weight) @ pn.cross(hangul, roman.lower())
            fst_general |= arc

    return fst_surname, fst_given, fst_general.optimize()


# Support atomic operations via FST_OUTPUT_DIR environment variable
import os

output_dir = os.environ.get("FST_OUTPUT_DIR", "models")
pathlib.Path(output_dir).mkdir(exist_ok=True, parents=True)

print("Building Tier 2 stackable FSTs with context-priority union...")

# Build Tier 2 FSTs
surname_rom2han, given_rom2han, general_rom2han = build_tier2_fsts("rom2han")
surname_han2rom, given_han2rom, general_han2rom = build_tier2_fsts("han2rom")

# Write FSTs to specified output directory
surname_rom2han.write(f"{output_dir}/rom2han_surname.fst")
given_rom2han.write(f"{output_dir}/rom2han_given.fst")
general_rom2han.write(f"{output_dir}/rom2han_general.fst")

surname_han2rom.write(f"{output_dir}/han2rom_surname.fst")
given_han2rom.write(f"{output_dir}/han2rom_given.fst")
general_han2rom.write(f"{output_dir}/han2rom_general.fst")

print(f"✓ Tier 2 stackable FSTs written: 6 FST files created in {output_dir}")
print("  - Position-specific mappings now have precedence over general ones")
print("  - General mappings serve as fallbacks with +1.0 weight boost")
