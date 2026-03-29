#!/usr/bin/env python3
"""Analyze region detection issues."""

import sys

sys.path.insert(0, "src")

from gmnap.core.pipeline import GMNAPPipeline

pipeline = GMNAPPipeline({"database_path": ":memory:"})

# Test cases with expected vs actual
test_cases = [
    ("Čížek, Pavel", "B2", "Czech name with háček"),
    ("González, María", "G1", "Spanish name"),
    ("Müller, Klaus", "A2", "German name"),
    ("O'Sullivan, Patrick", "A1", "Irish name"),
    ("Wang, Ming", "E1", "Chinese name romanized"),
    ("Kowalski, Janusz", "B2", "Polish name"),
    ("Петров, Иван", "B1", "Russian Cyrillic"),
    ("Test, Name", "A1", "Plain ASCII should default to A1"),
]

print("Region Detection Analysis")
print("=" * 60)

for name, expected, description in test_cases:
    entry = {"CanonicalLatin": name}

    # For non-Latin scripts, set CanonicalNative
    if any(ord(c) > 127 and ord(c) >= 0x0400 for c in name):
        entry["CanonicalNative"] = name
        entry["CanonicalLatin"] = "Test, Name"  # Placeholder

    detected = pipeline._stage_detect_region(entry)

    status = "✓" if detected == expected else "✗"
    print(f"{status} {name:25} Expected: {expected:3} Got: {detected:3} ({description})")

    if detected != expected:
        # Debug why it was misdetected
        if entry.get("CanonicalNative") and entry["CanonicalNative"] != entry["CanonicalLatin"]:
            script_detected = pipeline._detect_region_by_script(entry["CanonicalNative"])
            print(f"   Script detection: {script_detected}")
        else:
            pattern_detected = pipeline._detect_region_by_name_pattern(name)
            print(f"   Pattern detection: {pattern_detected}")

            # Show character analysis
            name_lower = name.lower()
            print(f"   Has Spanish chars: {'ñáéíóúü' in name_lower}")
            print(f"   Has German chars: {'äöüß' in name_lower}")
            print(f"   Has Slavic chars: {any(c in name for c in 'čžšďťňľĺŕ')}")
            print(f"   Has Polish chars: {any(c in name for c in 'ąćęłńóśźż')}")
