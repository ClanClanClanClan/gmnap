#!/usr/bin/env python3
"""
YAML Pattern Extractor for GMNAP v7 Optimization
Extracts surname patterns from mathematician YAML data to fix regional classification failures.

Target failures:
- Hungarian: Rényi → G1 instead of A2 (accent disambiguation)
- Korean: Lee, Choi → A1 instead of E4 (hyphenated patterns)
- Slavic: Hájek, Novák → G1 instead of B2 (Spanish confusion)
"""

import os
import re
from collections import defaultdict
from pathlib import Path

import yaml


class YAMLPatternExtractor:
    def __init__(
        self,
        docs_path="/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/docs",
    ):
        self.docs_path = Path(docs_path)
        self.patterns = defaultdict(set)

    def load_yaml_file(self, filename):
        """Load YAML file and return parsed data"""
        file_path = self.docs_path / filename
        if not file_path.exists():
            print(f"Warning: {file_path} not found")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return {}

    def extract_surnames_from_variants(self, variants):
        """Extract surnames from AllCommonVariants list"""
        surnames = set()

        for variant in variants:
            if not variant or not isinstance(variant, str):
                continue

            # Handle "Surname, FirstName" format (most common)
            if "," in variant:
                surname = variant.split(",")[0].strip()
                if surname and not surname.startswith('"'):
                    surnames.add(surname.lower())

            # Handle "FirstName Surname" format
            elif " " in variant and not variant.startswith('"'):
                parts = variant.strip().split()
                if len(parts) >= 2:
                    # Last part is usually surname
                    surname = parts[-1]
                    if surname and not any(char.isdigit() for char in surname):
                        surnames.add(surname.lower())

        return surnames

    def extract_hungarian_patterns(self):
        """Extract Hungarian surname patterns for A2 region"""
        print("🇭🇺 Extracting Hungarian patterns...")
        data = self.load_yaml_file("hungarian.yaml")

        hungarian_surnames = set()
        hungarian_accents = set()

        for entry_key, entry_data in data.items():
            if not isinstance(entry_data, dict):
                continue

            # Extract from AllCommonVariants
            variants = entry_data.get("AllCommonVariants", [])
            surnames = self.extract_surnames_from_variants(variants)
            hungarian_surnames.update(surnames)

            # Extract accent patterns specifically
            for variant in variants:
                if any(char in variant for char in "őűáéíóúüö"):
                    hungarian_accents.add(variant.lower())

        self.patterns["hungarian_surnames"] = hungarian_surnames
        self.patterns["hungarian_accents"] = hungarian_accents

        print(f"   ✅ Extracted {len(hungarian_surnames)} Hungarian surnames")
        print(f"   ✅ Extracted {len(hungarian_accents)} Hungarian accent patterns")

        # Show key patterns for Rényi fix
        key_patterns = [
            s
            for s in hungarian_surnames
            if "rényi" in s or "renyi" in s or "erdős" in s or "erdos" in s
        ]
        if key_patterns:
            print(f"   🎯 Key patterns for accent disambiguation: {key_patterns}")

        return hungarian_surnames

    def extract_korean_patterns(self):
        """Extract Korean surname patterns for E4 region"""
        print("🇰🇷 Extracting Korean patterns...")
        data = self.load_yaml_file("korean.yaml")

        korean_surnames = set()
        korean_hyphenated = set()

        for entry_key, entry_data in data.items():
            if not isinstance(entry_data, dict):
                continue

            # Extract from AllCommonVariants
            variants = entry_data.get("AllCommonVariants", [])
            surnames = self.extract_surnames_from_variants(variants)
            korean_surnames.update(surnames)

            # Extract hyphenated patterns specifically
            for variant in variants:
                if "-" in variant and "," in variant:
                    # Extract "Surname, First-Name" patterns
                    parts = variant.split(",")
                    if len(parts) >= 2:
                        surname = parts[0].strip().lower()
                        given = parts[1].strip()
                        if "-" in given:
                            korean_hyphenated.add(f"{surname}_hyphenated")
                            korean_surnames.add(surname)

        self.patterns["korean_surnames"] = korean_surnames
        self.patterns["korean_hyphenated"] = korean_hyphenated

        print(f"   ✅ Extracted {len(korean_surnames)} Korean surnames")
        print(f"   ✅ Extracted {len(korean_hyphenated)} Korean hyphenated patterns")

        # Show key patterns for Lee/Choi fix
        key_patterns = [
            s
            for s in korean_surnames
            if any(
                target in s for target in ["lee", "choi", "cho", "jang", "ahn", "baek"]
            )
        ]
        if key_patterns:
            print(f"   🎯 Key patterns for A1→E4 fix: {key_patterns}")

        return korean_surnames

    def extract_slavic_patterns(self):
        """Extract Czech/Polish/Slavic patterns for B2 region"""
        print("🇨🇿🇵🇱 Extracting Slavic patterns...")

        slavic_surnames = set()
        slavic_accents = set()

        # Load Czech/Polish data from east european.yaml
        east_data = self.load_yaml_file("east european.yaml")
        polish_data = self.load_yaml_file("polish.yaml")

        all_data = {}
        all_data.update(east_data)
        all_data.update(polish_data)

        for entry_key, entry_data in all_data.items():
            if not isinstance(entry_data, dict):
                continue

            # Extract from AllCommonVariants
            variants = entry_data.get("AllCommonVariants", [])
            surnames = self.extract_surnames_from_variants(variants)
            slavic_surnames.update(surnames)

            # Extract Slavic accent patterns (č, ž, š, ć, ń, ł, etc.)
            for variant in variants:
                if any(char in variant for char in "čžšćńłáéíóúýěř"):
                    slavic_accents.add(variant.lower())

        self.patterns["slavic_surnames"] = slavic_surnames
        self.patterns["slavic_accents"] = slavic_accents

        print(f"   ✅ Extracted {len(slavic_surnames)} Slavic surnames")
        print(f"   ✅ Extracted {len(slavic_accents)} Slavic accent patterns")

        # Show key patterns for Czech/Polish → Spanish confusion fix
        key_patterns = [
            s
            for s in slavic_surnames
            if any(
                target in s
                for target in ["hájek", "novák", "wójcik", "banach", "sierpiński"]
            )
        ]
        if key_patterns:
            print(f"   🎯 Key patterns for G1→B2 fix: {key_patterns}")

        return slavic_surnames

    def extract_all_patterns(self):
        """Extract patterns from all YAML files for comprehensive coverage"""
        print("🌍 Extracting patterns from all YAML files...")

        yaml_files = [
            ("hungarian.yaml", "hungarian"),
            ("korean.yaml", "korean"),
            ("indian.yaml", "indian"),
            ("german.yaml", "german"),
            ("chinese.yaml", "chinese"),
            ("polish.yaml", "polish"),
            ("east european.yaml", "east_european"),
            ("russian.yaml", "russian"),
            ("french.yaml", "french"),
            ("iranian.yaml", "iranian"),
            ("japanese.yaml", "japanese"),
            ("vietnamese.yaml", "vietnamese"),
            ("thai.yaml", "thai"),
            ("mongolian.yaml", "mongolian"),
        ]

        all_patterns = {}

        for filename, region in yaml_files:
            data = self.load_yaml_file(filename)
            region_surnames = set()

            for entry_key, entry_data in data.items():
                if not isinstance(entry_data, dict):
                    continue

                variants = entry_data.get("AllCommonVariants", [])
                surnames = self.extract_surnames_from_variants(variants)
                region_surnames.update(surnames)

            all_patterns[region] = region_surnames
            print(f"   ✅ {region}: {len(region_surnames)} surnames")

        return all_patterns

    def generate_pattern_report(self):
        """Generate comprehensive pattern extraction report"""
        print("\n" + "=" * 60)
        print("🧠 YAML PATTERN EXTRACTION REPORT")
        print("=" * 60)

        # Extract target patterns for Phase 1
        hungarian = self.extract_hungarian_patterns()
        korean = self.extract_korean_patterns()
        slavic = self.extract_slavic_patterns()

        print("\n📊 PHASE 1 QUICK WINS SUMMARY:")
        print(f"   🇭🇺 Hungarian surnames: {len(hungarian)} (fixes Rényi accent issue)")
        print(f"   🇰🇷 Korean surnames: {len(korean)} (fixes Lee/Choi A1 issue)")
        print(f"   🇨🇿🇵🇱 Slavic surnames: {len(slavic)} (fixes Spanish confusion)")

        print(
            f"\n🎯 TOTAL PHASE 1 PATTERNS: {len(hungarian) + len(korean) + len(slavic)}"
        )

        return {
            "hungarian": hungarian,
            "korean": korean,
            "slavic": slavic,
            "all_patterns": self.patterns,
        }


if __name__ == "__main__":
    extractor = YAMLPatternExtractor()
    results = extractor.generate_pattern_report()

    print("\n🚀 Ready for pipeline integration!")
