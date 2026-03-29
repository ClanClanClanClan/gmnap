#!/usr/bin/env python3
"""
Convert JSON profiles to fastText training format

Input: JSON with profiles [{"name": "...", "region": "..."}]
Output: fastText format: __label__<region> <name>
"""

import json
import sys
from pathlib import Path


def json_to_fasttext(json_path: Path, output_path: Path):
    """Convert JSON profiles to fastText format"""

    print(f"Converting {json_path} to {output_path}...")

    # Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data.get("profiles", data if isinstance(data, list) else [])
    print(f"  Loaded {len(profiles)} profiles")

    # Convert to fastText format
    lines = []
    for profile in profiles:
        name = profile.get("name")
        region = profile.get("region")

        if name and region:
            # fastText format: __label__<region> <name>
            line = f"__label__{region} {name}"
            lines.append(line)

    print(f"  Converted {len(lines)} valid profiles")

    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  ✅ Saved to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python json_to_fasttext.py <input.json> <output.txt>")
        sys.exit(1)

    json_to_fasttext(Path(sys.argv[1]), Path(sys.argv[2]))
