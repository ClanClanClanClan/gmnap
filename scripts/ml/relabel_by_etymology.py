#!/usr/bin/env python3
"""
Etymology-Based Relabeling System

Based on expert guidance (Oct 30, 2025):
- Current labels: Based on workplace country (affiliation)
- Correct labels: Based on name linguistic origin (etymology)

Strategy:
1. Use GMNAP's existing regional detection system (Stage 2)
2. Detect region by name only (ignoring workplace)
3. Relabel training data with detected etymology
4. Preserve original affiliation in metadata for analysis

Expected improvement: 68-70% → 85-90% accuracy
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import importlib.util

# Import GMNAP's regional detection
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.regions.manager_optimized import RegionManager

    GMNAP_AVAILABLE = True
except ImportError:
    GMNAP_AVAILABLE = False
    print("WARNING: Could not import RegionManager, will use fallback heuristics")


def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_etymology_region(name: str, manager: Any = None) -> str:
    """
    Detect regional origin by name linguistic properties

    Uses GMNAP Stage 2 regional detection (name-only, no workplace)
    """
    if manager and GMNAP_AVAILABLE:
        # Use GMNAP's existing system
        entry = {
            "CanonicalLatin": name,
            "BirthYear": None,
        }  # Don't use year for detection

        try:
            result = manager.detect_region(entry)
            if result and hasattr(result, "region_code"):
                return result.region_code
        except Exception as e:
            print(f"  Warning: Detection failed for '{name}': {e}")

    # Fallback: Basic heuristics
    return fallback_etymology_detection(name)


def fallback_etymology_detection(name: str) -> str:
    """
    Simple fallback heuristics for etymology detection
    (Used if GMNAP system unavailable)
    """
    import unicodedata

    name_lower = name.lower()

    # Check script first (strongest signal)
    for char in name:
        script = unicodedata.name(char, "").split()[0] if char.strip() else ""

        # CJK scripts
        if (
            "CJK" in script
            or "HANGUL" in script
            or "HIRAGANA" in script
            or "KATAKANA" in script
        ):
            if "HANGUL" in script:
                return "E4"  # Korean
            elif "HIRAGANA" in script or "KATAKANA" in script:
                return "E3"  # Japanese
            else:
                return "E1"  # Chinese (default CJK)

        # Cyrillic
        if "CYRILLIC" in script:
            return "B1"  # East Slavic

        # Greek
        if "GREEK" in script:
            return "B3"  # Greek

        # Arabic
        if "ARABIC" in script:
            return "C3"  # Arabic (generic)

    # Latin script - check surname patterns
    parts = name.split()
    if len(parts) >= 2:
        surname = parts[-1].lower()

        # Spanish/Portuguese patterns
        if surname.endswith(("ez", "es", "az", "iz", "oz")):
            # Check if likely Latin American vs Spain
            if any(x in name_lower for x in ["da silva", "dos santos", "de souza"]):
                return "G1"  # Latin America (Portuguese)
            else:
                return "A2"  # Western Europe (Spanish)

        # Italian patterns
        if surname.endswith(("ini", "elli", "etti", "ucci", "azzo")):
            return "A2"  # Italian

        # German patterns
        if surname.endswith(("mann", "stein", "berg", "feld", "haus")):
            return "A2"  # German

        # French patterns
        if surname.startswith("de ") or surname.startswith("du "):
            return "A2"  # French

        # Dutch patterns
        if surname.startswith("van ") or surname.startswith("de "):
            return "A2"  # Dutch

        # Scandinavian patterns
        if surname.endswith(("sen", "son", "sson", "dottir")):
            return "A3"  # Nordic/Baltic

        # Slavic patterns
        if surname.endswith(("ov", "ova", "ev", "eva", "ski", "ska", "ic", "ić")):
            if surname.endswith(("ov", "ova", "ev", "eva")):
                return "B1"  # East Slavic
            else:
                return "B2"  # South Slavic

        # English/Anglo patterns
        if surname.endswith(("ton", "ham", "ley", "ford", "wood", "field")):
            return "A1"  # Anglo

    # Default to A1 (Anglo) for unrecognized Latin names
    return "A1"


def relabel_dataset(input_path: Path, output_path: Path, dry_run: bool = False):
    """
    Relabel dataset from affiliation → etymology
    """

    print("=" * 80)
    print("ETYMOLOGY RELABELING SYSTEM")
    print("=" * 80)

    # Load data
    print(f"\n[1/5] Loading data from {input_path}...")
    data = load_json(input_path)

    profiles = data.get("profiles", data if isinstance(data, list) else [])
    print(f"  Loaded {len(profiles):,} profiles")

    # Initialize GMNAP detector
    print("\n[2/5] Initializing etymology detector...")
    manager = None
    if GMNAP_AVAILABLE:
        try:
            manager = RegionManager()
            print("  ✅ Using GMNAP Stage 2 regional detection")
        except Exception as e:
            print(f"  ⚠️  GMNAP init failed: {e}")
            print("  ⚠️  Falling back to heuristic detection")
    else:
        print("  ⚠️  Using fallback heuristic detection")

    # Relabel
    print("\n[3/5] Relabeling by etymology...")
    changes = 0
    unchanged = 0
    relabel_stats = {}

    for i, profile in enumerate(profiles):
        if (i + 1) % 1000 == 0:
            print(
                f"  Progress: {i + 1:,}/{len(profiles):,} ({(i + 1) / len(profiles) * 100:.1f}%)"
            )

        name = profile.get("name")
        old_region = profile.get("region")

        if not name or not old_region:
            continue

        # Detect etymology
        etymology_region = detect_etymology_region(name, manager)

        # Store original affiliation label
        profile["original_affiliation_region"] = old_region

        # Relabel
        if etymology_region != old_region:
            profile["region"] = etymology_region
            changes += 1

            # Track changes
            key = f"{old_region}→{etymology_region}"
            relabel_stats[key] = relabel_stats.get(key, 0) + 1
        else:
            unchanged += 1

    print(f"\n  Changed: {changes:,} ({changes / len(profiles) * 100:.1f}%)")
    print(f"  Unchanged: {unchanged:,} ({unchanged / len(profiles) * 100:.1f}%)")

    # Show top relabelings
    print("\n[4/5] Top relabelings:")
    for key, count in sorted(relabel_stats.items(), key=lambda x: x[1], reverse=True)[
        :15
    ]:
        print(f"    {key:10s} {count:5,} changes")

    # Save
    if dry_run:
        print("\n[5/5] DRY RUN - Not saving changes")
        print(f"  Would save to: {output_path}")
    else:
        print(f"\n[5/5] Saving relabeled data to {output_path}...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "metadata": {
                "total": len(profiles),
                "relabeling": {
                    "method": "etymology_detection",
                    "detector": (
                        "gmnap_stage2"
                        if GMNAP_AVAILABLE and manager
                        else "fallback_heuristics"
                    ),
                    "changes": changes,
                    "unchanged": unchanged,
                    "pct_changed": changes / len(profiles) * 100,
                },
                "original_source": str(input_path),
            },
            "profiles": profiles,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Saved {len(profiles):,} profiles")

    print("\n" + "=" * 80)
    print(
        f"RELABELING COMPLETE - {changes:,} changes ({changes / len(profiles) * 100:.1f}%)"
    )
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python relabel_by_etymology.py <input.json> <output.json> [--dry-run]"
        )
        print("\nExample:")
        print(
            "  python relabel_by_etymology.py data/ml_training/train_split.json data/ml_training/train_split_etymo.json"
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    dry_run = "--dry-run" in sys.argv

    relabel_dataset(input_path, output_path, dry_run)
