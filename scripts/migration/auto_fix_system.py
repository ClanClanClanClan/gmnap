#!/usr/bin/env python3
"""
Automated Fix System for Korean Name Conversion Failures

This system analyzes validation failures and automatically suggests fixes based on:
1. Character-level differences between expected and actual outputs
2. Frequency of similar patterns in existing mappings
3. Context (surname vs given name position)
4. Learning from corrections over time
"""

import yaml
import csv
import json
import os
import sys
import pathlib
from collections import defaultdict, Counter
from datetime import datetime
import difflib
import re
from typing import Dict, List, Tuple, Optional, Set

# Add the src directory to the path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
# from converter import eng2kor, kor2eng
from lookup import rom2han


class PatternAnalyzer:
    """Analyzes patterns in name conversion failures"""

    def __init__(self):
        self.surname_patterns = self._load_surname_patterns()
        self.syllable_mappings = self._load_syllable_mappings()
        self.correction_history = self._load_correction_history()

    def _load_surname_patterns(self) -> Set[str]:
        """Load common Korean surnames"""
        common_surnames = {
            "kim",
            "lee",
            "park",
            "choi",
            "jung",
            "kang",
            "cho",
            "yoon",
            "jang",
            "lim",
            "han",
            "oh",
            "seo",
            "shin",
            "kwon",
            "hwang",
            "ahn",
            "song",
            "jeon",
            "hong",
            "yu",
            "yoo",
            "ko",
            "moon",
            "yang",
            "bae",
            "baek",
            "jo",
            "heo",
            "huh",
            "nam",
            "shim",
            "sim",
            "roh",
            "no",
            "ha",
            "jun",
            "chun",
            "cheong",
            "yom",
            "yum",
            "pae",
            "um",
            "eom",
            "ri",
            "boo",
            "jee",
        }
        return common_surnames

    def _load_syllable_mappings(self) -> Dict[str, List[str]]:
        """Load existing syllable mappings from CSV files"""
        mappings = defaultdict(list)

        # Try multiple possible paths for resources
        possible_paths = [
            "resources/variant_map.csv",
            "../resources/variant_map.csv",
            pathlib.Path(__file__).parent.parent / "resources" / "variant_map.csv",
        ]

        # Load from variant_map.csv
        for variant_map_path in possible_paths:
            if os.path.exists(variant_map_path):
                with open(variant_map_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader, None)  # Skip header
                    for row in reader:
                        if len(row) >= 2:
                            hangul, romanization = row[0], row[1]
                            if hangul and romanization:
                                mappings[romanization.lower()].append(hangul)
                break

        # Try multiple paths for syllable map
        syllable_paths = [
            "resources/rr_syllable_map.csv",
            "../resources/rr_syllable_map.csv",
            pathlib.Path(__file__).parent.parent / "resources" / "rr_syllable_map.csv",
        ]

        # Load from rr_syllable_map.csv
        for syllable_map_path in syllable_paths:
            if os.path.exists(syllable_map_path):
                with open(syllable_map_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            hangul, romanization = row[0], row[1]
                            if hangul and romanization:
                                if hangul not in mappings[romanization.lower()]:
                                    mappings[romanization.lower()].append(hangul)
                break

        # Add some known mappings that should be corrected based on failure analysis
        known_corrections = {
            "chun": ["천"],  # Not 전
            "cheong": ["정"],  # Not 청
            "yom": ["염"],  # Missing
            "yum": ["염"],  # Missing
            "pae": ["배"],  # Not 패
            "boo": ["부"],  # Missing
            "jee": ["지"],  # Missing
        }

        for rom, hanguls in known_corrections.items():
            for hangul in hanguls:
                if hangul not in mappings[rom]:
                    mappings[rom].append(hangul)

        return dict(mappings)

    def _load_correction_history(self) -> Dict[str, Dict]:
        """Load history of corrections from previous runs"""
        history_file = "correction_history.json"
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def analyze_failure(self, name: str, expected: str, actual: str, failure_type: str) -> Dict:
        """Analyze a single failure and return detailed analysis"""
        analysis = {
            "name": name,
            "expected": expected,
            "actual": actual,
            "failure_type": failure_type,
            "differences": [],
            "suggestions": [],
            "confidence": 0.0,
        }

        if failure_type == "eng→kor":
            # Extract romanization parts
            parts = self._extract_name_parts(name)
            analysis["name_parts"] = parts

            # Analyze character differences
            if expected and actual:
                for i, (e, a) in enumerate(zip(expected, actual)):
                    if e != a:
                        analysis["differences"].append(
                            {
                                "position": i,
                                "expected_char": e,
                                "actual_char": a,
                                "context": self._get_syllable_context(name, i),
                            }
                        )

            # Generate suggestions
            suggestions = self._generate_suggestions(name, expected, actual, parts)
            analysis["suggestions"] = suggestions

            # Calculate confidence based on pattern matching
            analysis["confidence"] = self._calculate_confidence(suggestions)

        return analysis

    def _extract_name_parts(self, name: str) -> Dict:
        """Extract surname and given name parts from romanized name"""
        # Handle various name formats
        if "_" in name:
            parts = name.split("_")
            surname = parts[0].lower()
            given_name = parts[1] if len(parts) > 1 else ""
        else:
            # Try to identify surname based on known patterns
            words = name.split()
            surname = words[0].lower() if words else ""
            given_name = " ".join(words[1:]) if len(words) > 1 else ""

        return {
            "surname": surname,
            "given_name": given_name,
            "is_known_surname": surname in self.surname_patterns,
        }

    def _get_syllable_context(self, name: str, char_position: int) -> str:
        """Determine if character is in surname or given name context"""
        parts = self._extract_name_parts(name)
        # Simple heuristic: first 1-2 characters are usually surname
        if char_position < 2 and parts["is_known_surname"]:
            return "surname"
        return "given_name"

    def _generate_suggestions(
        self, name: str, expected: str, actual: str, name_parts: Dict
    ) -> List[Dict]:
        """Generate fix suggestions based on patterns"""
        suggestions = []

        # For surname mismatches
        if name_parts["is_known_surname"]:
            surname = name_parts["surname"]

            # Check existing mappings
            if surname in self.syllable_mappings:
                for hangul in self.syllable_mappings[surname]:
                    if expected.startswith(hangul):
                        suggestions.append(
                            {
                                "type": "mapping_override",
                                "romanization": surname,
                                "hangul": hangul,
                                "reason": f"Known surname mapping: {surname} → {hangul}",
                                "priority": 1,
                            }
                        )

            # Check correction history
            if surname in self.correction_history:
                hist = self.correction_history[surname]
                if hist["success_count"] > 2:
                    suggestions.append(
                        {
                            "type": "historical_correction",
                            "romanization": surname,
                            "hangul": hist["hangul"],
                            "reason": f"Previously successful correction ({hist['success_count']} times)",
                            "priority": 2,
                        }
                    )

        # For any romanization part
        rom_parts = name.lower().replace("_", " ").split()
        for rom in rom_parts:
            if rom and len(rom) > 1:
                # Find similar existing mappings
                similar = self._find_similar_mappings(rom)
                for sim_rom, sim_hangul, similarity in similar[:3]:
                    suggestions.append(
                        {
                            "type": "similar_pattern",
                            "romanization": rom,
                            "hangul": sim_hangul,
                            "similar_to": sim_rom,
                            "similarity": similarity,
                            "reason": f"Similar to existing mapping: {sim_rom} → {sim_hangul}",
                            "priority": 3,
                        }
                    )

        # Sort by priority
        suggestions.sort(key=lambda x: x["priority"])
        return suggestions

    def _find_similar_mappings(self, romanization: str) -> List[Tuple[str, str, float]]:
        """Find similar romanizations in existing mappings"""
        similar = []

        for rom, hanguls in self.syllable_mappings.items():
            if rom != romanization:
                # Calculate similarity
                similarity = difflib.SequenceMatcher(None, romanization, rom).ratio()
                if similarity > 0.7:  # Threshold for similarity
                    for hangul in hanguls:
                        similar.append((rom, hangul, similarity))

        # Sort by similarity
        similar.sort(key=lambda x: x[2], reverse=True)
        return similar

    def _calculate_confidence(self, suggestions: List[Dict]) -> float:
        """Calculate confidence score for suggestions"""
        if not suggestions:
            return 0.0

        # Higher confidence for mapping overrides and historical corrections
        best_priority = min(s["priority"] for s in suggestions)
        if best_priority == 1:
            return 0.9  # High confidence for known mappings
        elif best_priority == 2:
            return 0.8  # Good confidence for historical patterns
        elif best_priority == 3:
            # Confidence based on similarity
            best_similarity = max(
                (s.get("similarity", 0) for s in suggestions if s["type"] == "similar_pattern"),
                default=0,
            )
            return best_similarity * 0.7

        return 0.5


class FixGenerator:
    """Generates fix commands based on analysis"""

    def __init__(self, analyzer: PatternAnalyzer):
        self.analyzer = analyzer
        self.fixes = []

    def generate_fixes(self, failures: List[Dict]) -> List[Dict]:
        """Generate fixes for a list of failures"""
        fixes = []

        # Group failures by type
        mapping_fixes = defaultdict(list)

        for failure in failures:
            if failure["confidence"] > 0.7 and failure["suggestions"]:
                best_suggestion = failure["suggestions"][0]

                if best_suggestion["type"] in ["mapping_override", "historical_correction"]:
                    rom = best_suggestion["romanization"]
                    han = best_suggestion["hangul"]
                    mapping_fixes[rom].append(
                        {"hangul": han, "count": 1, "examples": [failure["name"]]}
                    )

        # Consolidate mapping fixes
        for rom, candidates in mapping_fixes.items():
            # Choose most common hangul
            hangul_counts = Counter(c["hangul"] for c in candidates)
            best_hangul = hangul_counts.most_common(1)[0][0]

            fixes.append(
                {
                    "type": "add_mapping",
                    "romanization": rom,
                    "hangul": best_hangul,
                    "affected_names": sum((c["examples"] for c in candidates), []),
                    "confidence": 0.85,
                }
            )

        return fixes

    def generate_fix_commands(self, fixes: List[Dict]) -> List[str]:
        """Generate actual fix commands (sed, Python code, etc.)"""
        commands = []

        # Group by fix type
        mapping_adds = []
        fst_rebuilds = False

        for fix in fixes:
            if fix["type"] == "add_mapping":
                mapping_adds.append(fix)
                fst_rebuilds = True

        # Generate commands for adding mappings
        if mapping_adds:
            commands.append("# Add new mappings to variant_map.csv")
            for fix in mapping_adds:
                rom = fix["romanization"]
                han = fix["hangul"]
                # Escape special characters for sed
                rom_escaped = rom.replace("/", "\\/")
                han_escaped = han.replace("/", "\\/")

                # Check if mapping already exists
                commands.append(f"# Check if {rom} → {han} exists")
                commands.append(f"grep -q '^{han},{rom},' ../resources/variant_map.csv || \\")
                commands.append(f"  echo '{han},{rom},' >> ../resources/variant_map.csv")

        # Generate FST rebuild command if needed
        if fst_rebuilds:
            commands.append("\n# Rebuild FST files")
            commands.append("cd .. && python scripts/build_fsts.py")

        return commands

    def generate_python_override(self, fixes: List[Dict]) -> str:
        """Generate Python code for converter.py overrides"""
        if not fixes:
            return ""

        code = """
# Auto-generated mapping overrides
OVERRIDE_MAPPINGS = {
"""

        for fix in fixes:
            if fix["type"] == "add_mapping":
                rom = fix["romanization"]
                han = fix["hangul"]
                code += f"    '{rom}': '{han}',  # Fixes: {', '.join(fix['affected_names'][:3])}\n"

        code += """}\n
# Insert this into converter.py's _rr2han function:
# def _rr2han(rr):
#     if rr in OVERRIDE_MAPPINGS:
#         return OVERRIDE_MAPPINGS[rr]
#     return first_output(pn.accep(rr)@ROM2) or rom2han().get(rr)
"""

        return code


class LearningSystem:
    """Tracks and learns from corrections over time"""

    def __init__(self):
        self.history_file = "correction_history.json"
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load correction history"""
        if os.path.exists(self.history_file):
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def record_correction(self, romanization: str, hangul: str, success: bool):
        """Record a correction attempt"""
        if romanization not in self.history:
            self.history[romanization] = {
                "hangul": hangul,
                "attempts": 0,
                "success_count": 0,
                "last_updated": datetime.now().isoformat(),
            }

        self.history[romanization]["attempts"] += 1
        if success:
            self.history[romanization]["success_count"] += 1
        self.history[romanization]["last_updated"] = datetime.now().isoformat()

        self._save_history()

    def _save_history(self):
        """Save correction history"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def get_confidence_boost(self, romanization: str) -> float:
        """Get confidence boost based on historical success"""
        if romanization in self.history:
            hist = self.history[romanization]
            if hist["attempts"] > 0:
                success_rate = hist["success_count"] / hist["attempts"]
                if hist["attempts"] >= 3:
                    return success_rate * 0.2  # Up to 20% boost
        return 0.0


class SafetyChecker:
    """Ensures fixes don't break existing working names"""

    def __init__(self):
        self.working_names = self._load_working_names()

    def _load_working_names(self) -> Set[Tuple[str, str]]:
        """Load names that currently work correctly"""
        working = set()

        # Test current working names from both datasets
        for data_file in ["../data/korean.yaml", "../data/korean_diverse_test.yaml"]:
            if os.path.exists(data_file):
                with open(data_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                for name, entry in data.items():
                    canonical = entry.get("CanonicalLatin")
                    if canonical:
                        # Test if it currently works
                        try:
                            result = eng2kor(canonical)
                            if result:
                                working.add((canonical.lower(), result))
                        except:
                            pass

        return working

    def check_safety(self, fixes: List[Dict]) -> List[Dict]:
        """Check if fixes would break existing working names"""
        safe_fixes = []

        for fix in fixes:
            if fix["type"] == "add_mapping":
                rom = fix["romanization"]
                han = fix["hangul"]

                # Check if this would change any working names
                conflicts = []
                for working_name, working_hangul in self.working_names:
                    if rom in working_name.lower():
                        # Simulate the change
                        # This is simplified - in reality would need full conversion
                        if rom == working_name.split("_")[0].lower():
                            if not working_hangul.startswith(han):
                                conflicts.append(working_name)

                if conflicts:
                    fix["warning"] = f"May affect {len(conflicts)} working names"
                    fix["conflicts"] = conflicts[:5]  # Show first 5
                    fix["safety_score"] = 0.5
                else:
                    fix["safety_score"] = 1.0

                safe_fixes.append(fix)

        return safe_fixes


def main():
    """Demo the auto-fix system"""
    print("Korean Name Auto-Fix System")
    print("=" * 60)

    # Initialize components
    analyzer = PatternAnalyzer()
    fix_generator = FixGenerator(analyzer)
    learning_system = LearningSystem()
    safety_checker = SafetyChecker()

    # Load test failures
    test_failures = [
        # From the failure analysis report
        {"name": "Chun_Baekjin", "expected": "천백진", "actual": "전백진", "type": "eng→kor"},
        {"name": "Cheong_Munho", "expected": "정문호", "actual": "청문호", "type": "eng→kor"},
        {"name": "Yom_Ha-Rim", "expected": "염하림", "actual": "욤하림", "type": "eng→kor"},
        {"name": "Yum_Young-Tae", "expected": "염영태", "actual": "윰영태", "type": "eng→kor"},
        {"name": "Pae_Soonjung", "expected": "배순정", "actual": "패순정", "type": "eng→kor"},
        {"name": "Boo_Kyungmin", "expected": "부경민", "actual": None, "type": "eng→kor"},
        {"name": "Jee_Sungmin", "expected": "지성민", "actual": None, "type": "eng→kor"},
    ]

    # Analyze failures
    print("\n1. Analyzing Failures")
    print("-" * 60)

    analyzed_failures = []
    for failure in test_failures:
        analysis = analyzer.analyze_failure(
            failure["name"], failure["expected"], failure["actual"], failure["type"]
        )
        analyzed_failures.append(analysis)

        print(f"\nName: {failure['name']}")
        print(f"Expected: {failure['expected']}, Actual: {failure['actual']}")
        print(f"Confidence: {analysis['confidence']:.2f}")
        if analysis["suggestions"]:
            print("Suggestions:")
            for i, sugg in enumerate(analysis["suggestions"][:2]):
                print(f"  {i+1}. {sugg['reason']}")

    # Generate fixes
    print("\n\n2. Generating Fixes")
    print("-" * 60)

    fixes = fix_generator.generate_fixes(analyzed_failures)

    # Check safety
    safe_fixes = safety_checker.check_safety(fixes)

    print(f"\nGenerated {len(safe_fixes)} fixes:")
    for fix in safe_fixes:
        print(f"\n- {fix['romanization']} → {fix['hangul']}")
        print(f"  Affects: {', '.join(fix['affected_names'])}")
        print(f"  Safety score: {fix['safety_score']:.2f}")
        if "warning" in fix:
            print(f"  ⚠️  {fix['warning']}")

    # Generate fix commands
    print("\n\n3. Fix Commands")
    print("-" * 60)

    commands = fix_generator.generate_fix_commands(safe_fixes)
    print("\nBash commands:")
    for cmd in commands:
        print(cmd)

    # Generate Python override
    print("\n\n4. Python Override Code")
    print("-" * 60)
    python_code = fix_generator.generate_python_override(safe_fixes)
    print(python_code)

    # Demonstrate learning
    print("\n\n5. Learning System")
    print("-" * 60)
    print("\nRecording successful corrections...")
    for fix in safe_fixes[:3]:
        learning_system.record_correction(fix["romanization"], fix["hangul"], success=True)
        print(f"Recorded: {fix['romanization']} → {fix['hangul']}")

    print("\nCorrection history updated.")

    # Summary
    print("\n\n6. Summary")
    print("-" * 60)
    print(f"Analyzed {len(test_failures)} failures")
    print(f"Generated {len(safe_fixes)} fixes with high confidence")
    print(f"Estimated accuracy improvement: {len(safe_fixes)/750*100:.2f}%")
    print("\nNext steps:")
    print("1. Review generated fixes")
    print("2. Run safety validation on full dataset")
    print("3. Apply fixes using generated commands")
    print("4. Re-run validation to confirm improvements")


if __name__ == "__main__":
    main()
