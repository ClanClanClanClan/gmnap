#!/usr/bin/env python3
"""Check what mappings exist for specific hangul characters."""
import csv
from collections import defaultdict


def check_mappings(hangul_char):
    """Check all mappings for a specific hangul character."""
    mappings = []

    with open("resources/rr_syllable_map.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0] == hangul_char:
                # Handle various row lengths
                hangul = row[0]
                roman = row[1] if len(row) > 1 else ""
                weight = row[2] if len(row) > 2 else "0.0"
                context = row[3] if len(row) > 3 else ""
                pos = row[4] if len(row) > 4 else ""

                mappings.append(
                    {
                        "hangul": hangul,
                        "roman": roman,
                        "weight": weight,
                        "context": context,
                        "pos": pos,
                        "row_length": len(row),
                    }
                )

    return mappings


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 check_conflicts.py <hangul_character>")
        print("Example: python3 check_conflicts.py 여")
        sys.exit(1)

    hangul = sys.argv[1]
    mappings = check_mappings(hangul)

    print(f"\n=== Mappings for '{hangul}' ===")
    if not mappings:
        print("No mappings found")
    else:
        for m in mappings:
            pos_desc = {"S": "surname", "G": "given", "SG": "both", "": "general/unspecified"}.get(
                m["pos"], f"unknown({m['pos']})"
            )

            print(f"\n{hangul} → {m['roman']}")
            print(f"  Weight: {m['weight']}")
            print(f"  Position: {pos_desc}")
            print(f"  Context: {m['context'] or 'none'}")
            print(f"  Row length: {m['row_length']} columns")

    # Check for potential conflicts with new mapping
    if len(sys.argv) >= 3:
        new_roman = sys.argv[2]
        new_pos = sys.argv[3] if len(sys.argv) > 3 else "G"

        print(f"\n=== Conflict check for new mapping: {hangul} → {new_roman} (pos={new_pos}) ===")

        conflicts = []
        for m in mappings:
            if m["roman"] != new_roman:
                # Check if positions conflict
                existing_pos = m["pos"]
                if (
                    new_pos == existing_pos
                    or new_pos == ""
                    or existing_pos == ""
                    or new_pos == "SG"
                    or existing_pos == "SG"
                ):
                    conflicts.append(m)

        if conflicts:
            print("⚠️  CONFLICTS DETECTED:")
            for c in conflicts:
                print(f"  - {c['hangul']} → {c['roman']} (pos={c['pos'] or 'general'})")
        else:
            print("✅ No conflicts detected")
