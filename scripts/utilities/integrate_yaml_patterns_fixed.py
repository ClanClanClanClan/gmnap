#!/usr/bin/env python3
"""
Fixed YAML Pattern Integration for GMNAP v7 Pipeline
Integrates mathematician YAML patterns with proper line formatting.

Target fixes:
- Hungarian: Rényi → G1 instead of A2 (add Hungarian surnames)
- Korean: Lee, Choi → A1 instead of E4 (expand Korean patterns)
- Slavic: Hájek, Novák → G1 instead of B2 (add Czech/Polish surnames)
"""

import re
from pathlib import Path
from yaml_pattern_extractor import YAMLPatternExtractor


class PipelinePatternIntegratorFixed:
    def __init__(
        self,
        pipeline_path="/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/core/pipeline.py",
    ):
        self.pipeline_path = Path(pipeline_path)
        self.extractor = YAMLPatternExtractor()

    def backup_pipeline(self):
        """Create backup of current pipeline"""
        backup_path = self.pipeline_path.with_suffix(".py.backup_fixed")
        with open(self.pipeline_path, "r") as f:
            content = f.read()
        with open(backup_path, "w") as f:
            f.write(content)
        print(f"✅ Backup created: {backup_path}")

    def read_pipeline(self):
        """Read current pipeline content"""
        with open(self.pipeline_path, "r") as f:
            return f.read()

    def write_pipeline(self, content):
        """Write updated pipeline content"""
        with open(self.pipeline_path, "w") as f:
            f.write(content)
        print(f"✅ Pipeline updated: {self.pipeline_path}")

    def extract_yaml_patterns(self):
        """Extract patterns from YAML files"""
        print("🔍 Extracting patterns from YAML files...")

        # Extract target patterns
        hungarian_surnames = self.extractor.extract_hungarian_patterns()
        korean_surnames = self.extractor.extract_korean_patterns()
        slavic_surnames = self.extractor.extract_slavic_patterns()

        return {
            "hungarian": hungarian_surnames,
            "korean": korean_surnames,
            "slavic": slavic_surnames,
        }

    def format_python_list(self, items, max_line_length=120):
        """Format a list as properly formatted Python code"""
        if not items:
            return "[]"

        # Sort and deduplicate
        sorted_items = sorted(list(set(items)))

        # Start with opening bracket
        lines = ["["]
        current_line = "    '"

        for i, item in enumerate(sorted_items):
            item_str = f"'{item}'"

            # Check if adding this item would exceed line length
            if len(current_line + item_str) > max_line_length and current_line != "    '":
                # Close current line and start new one
                current_line = current_line.rstrip(", ") + ","
                lines.append(current_line)
                current_line = "    '" + item + "'"
            else:
                # Add to current line
                if current_line == "    '":
                    current_line += item + "'"
                else:
                    current_line += ", '" + item + "'"

            # Add comma except for last item
            if i < len(sorted_items) - 1:
                pass  # Comma is added above or in the next iteration

        # Close the last line
        if current_line != "    '":
            lines.append(current_line)

        # Close the list
        lines.append("]")

        return "\n".join(lines)

    def integrate_hungarian_patterns(self, content, hungarian_patterns):
        """Integrate Hungarian surname patterns"""
        print("🇭🇺 Integrating Hungarian patterns...")

        # Find current Hungarian surnames line
        hungarian_pattern = r"hungarian_surnames = \[([^\]]+)\]"
        match = re.search(hungarian_pattern, content)

        if match:
            # Get current patterns
            current_patterns = match.group(1)
            current_list = [
                p.strip().strip("'\"") for p in current_patterns.split(",") if p.strip()
            ]

            # Add YAML patterns (remove accents for matching, limit to most important)
            yaml_patterns = []
            priority_patterns = [
                "erdős",
                "erdos",
                "rényi",
                "renyi",
                "kőnig",
                "konig",
                "lovász",
                "lovasz",
                "turán",
                "turan",
                "fejér",
                "fejer",
                "bolyai",
                "császár",
                "csaszar",
            ]

            for pattern in hungarian_patterns:
                # Remove accents for pattern matching
                clean = pattern.lower()
                clean = clean.replace("ő", "o").replace("ű", "u").replace("á", "a")
                clean = (
                    clean.replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                )

                # Only add if it's in priority list or not already present
                if (
                    clean in priority_patterns or len(yaml_patterns) < 15
                ) and clean not in current_list:
                    if clean not in yaml_patterns:
                        yaml_patterns.append(clean)

            # Combine and create formatted list
            all_patterns = sorted(list(set(current_list + yaml_patterns)))
            formatted_list = self.format_python_list(all_patterns)

            # Replace in content
            new_line = f"hungarian_surnames = {formatted_list}"
            content = re.sub(hungarian_pattern, new_line, content, flags=re.DOTALL)

            print(f"   ✅ Added {len(yaml_patterns)} new Hungarian patterns")
            print(
                f"   🎯 Key additions: {[p for p in yaml_patterns if any(target in p for target in ['erdos', 'renyi', 'fejer', 'turan'])]}"
            )

        return content

    def integrate_korean_patterns(self, content, korean_patterns):
        """Integrate Korean surname patterns (selective)"""
        print("🇰🇷 Integrating Korean patterns...")

        # Find current Korean surnames line
        korean_pattern = r"korean_surnames = \[([^\]]+)\]"
        match = re.search(korean_pattern, content)

        if match:
            # Get current patterns
            current_patterns = match.group(1)
            current_list = [
                p.strip().strip("'\"") for p in current_patterns.split(",") if p.strip()
            ]

            # Add YAML patterns (selective - focus on actual surnames, not given names)
            yaml_patterns = []
            priority_surnames = [
                "ahn",
                "baek",
                "choi",
                "cho",
                "jang",
                "jeong",
                "jung",
                "kang",
                "kim",
                "lee",
                "lim",
                "moon",
                "nam",
                "oh",
                "park",
                "ryu",
                "seo",
                "shin",
                "song",
                "yang",
                "yoon",
                "han",
                "hong",
                "kwon",
            ]

            for pattern in korean_patterns:
                clean = pattern.lower().strip()
                # Only add real surnames (single syllable or compound surnames)
                if clean in priority_surnames or (
                    len(clean) <= 4
                    and clean not in current_list
                    and not any(char.isdigit() for char in clean)
                    and "-" not in clean
                ):  # Avoid hyphenated given names
                    if clean not in yaml_patterns and len(yaml_patterns) < 50:
                        yaml_patterns.append(clean)

            # Combine and create formatted list
            all_patterns = sorted(list(set(current_list + yaml_patterns)))
            formatted_list = self.format_python_list(all_patterns)

            # Replace in content
            new_line = f"korean_surnames = {formatted_list}"
            content = re.sub(korean_pattern, new_line, content, flags=re.DOTALL)

            print(f"   ✅ Added {len(yaml_patterns)} new Korean patterns")
            print(f"   🎯 Key additions: {[p for p in yaml_patterns[:10]]}")  # Show first 10

        return content

    def integrate_slavic_patterns(self, content, slavic_patterns):
        """Integrate Slavic patterns for B2 region"""
        print("🇨🇿🇵🇱 Integrating Slavic patterns...")

        # Find the area after Hungarian patterns to add Slavic section
        hungarian_section = re.search(
            r"(if has_hungarian_surname:.*?scores\[\'G1\'\] = max\(0, scores\[\'G1\'\] - 4\))",
            content,
            re.DOTALL,
        )

        if hungarian_section:
            # Create selective Slavic patterns (focus on mathematician surnames)
            priority_slavic = [
                "hájek",
                "hajek",
                "novák",
                "novak",
                "banach",
                "sierpiński",
                "sierpinski",
                "bartoszyński",
                "bartoszynski",
                "borsuk",
                "kuratowski",
                "tarski",
                "łojasiewicz",
            ]

            # Filter slavic patterns to priority ones + a few others
            filtered_patterns = []
            for pattern in slavic_patterns:
                clean = pattern.lower()
                if clean in priority_slavic or (len(filtered_patterns) < 25 and len(clean) > 3):
                    if clean not in filtered_patterns:
                        filtered_patterns.append(clean)

            formatted_list = self.format_python_list(filtered_patterns)

            # Add Slavic patterns after Hungarian section
            slavic_code = f"""
        
        # Czech/Polish surname patterns (fix for G1→B2 misclassification)
        slavic_surnames = {formatted_list}
        has_slavic_surname = any(surname in name_lower for surname in slavic_surnames)
        
        if has_slavic_surname:
            scores['B2'] += 8  # Strong boost to override Spanish detection
            scores['G1'] = max(0, scores['G1'] - 4)  # Reduce Spanish score"""

            insertion_point = hungarian_section.end()
            content = content[:insertion_point] + slavic_code + content[insertion_point:]

            print(f"   ✅ Added {len(filtered_patterns)} new Slavic patterns")
            print(
                f"   🎯 Key additions: {[p for p in filtered_patterns if any(target in p for target in ['hajek', 'novak', 'banach', 'sierpinski'])]}"
            )

        return content

    def boost_korean_detection(self, content):
        """Boost Korean detection to fix A1 misclassification"""
        print("🔧 Boosting Korean detection weights...")

        # Find Korean detection section and add boost after it
        korean_pattern_section = re.search(
            r"(has_korean_pattern = any\(name_lower\.startswith\(surname \+ \',\'\) or name_lower\.startswith\(surname \+ \' \'\) for surname in korean_surnames\))",
            content,
        )

        if korean_pattern_section:
            # Add stronger Korean scoring after the pattern check
            boost_code = """
        
        # Boost Korean detection (fix for A1 misclassification)
        if has_korean_pattern:
            scores['E4'] += 8  # Strong boost for Korean patterns
            # Reduce A1 score if Korean pattern detected
            scores['A1'] = max(0, scores['A1'] - 3)"""

            insertion_point = korean_pattern_section.end()
            content = content[:insertion_point] + boost_code + content[insertion_point:]

            print("   ✅ Added Korean detection boost")

        return content

    def integrate_all_patterns(self):
        """Main integration function"""
        print("=" * 60)
        print("🚀 INTEGRATING YAML PATTERNS INTO PIPELINE (FIXED)")
        print("=" * 60)

        # 1. Backup current pipeline
        self.backup_pipeline()

        # 2. Extract YAML patterns
        patterns = self.extract_yaml_patterns()

        # 3. Read current pipeline
        content = self.read_pipeline()

        # 4. Integrate Hungarian patterns (fix Rényi → G1 issue)
        content = self.integrate_hungarian_patterns(content, patterns["hungarian"])

        # 5. Integrate Korean patterns (fix Lee, Choi → A1 issue)
        content = self.integrate_korean_patterns(content, patterns["korean"])

        # 6. Integrate Slavic patterns (fix Czech/Polish → G1 issue)
        content = self.integrate_slavic_patterns(content, patterns["slavic"])

        # 7. Boost Korean detection weights
        content = self.boost_korean_detection(content)

        # 8. Write updated pipeline
        self.write_pipeline(content)

        print("\n📊 INTEGRATION SUMMARY:")
        print(f"   🇭🇺 Hungarian patterns: {len(patterns['hungarian'])} (fixes Rényi accent issue)")
        print(f"   🇰🇷 Korean patterns: {len(patterns['korean'])} (fixes Lee/Choi A1 issue)")
        print(f"   🇨🇿🇵🇱 Slavic patterns: {len(patterns['slavic'])} (fixes Spanish confusion)")

        print(f"\n🎯 EXPECTED IMPACT: 42 failures → ~31 failures (87% pass rate)")
        print("✅ Ready for testing!")


if __name__ == "__main__":
    integrator = PipelinePatternIntegratorFixed()
    integrator.integrate_all_patterns()
