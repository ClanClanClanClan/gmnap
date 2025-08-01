#!/usr/bin/env python3
"""
Weight safety linter - validates weight additions before applying.
Detects conflicts, duplicates, and safety violations.
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict

class WeightLinter:
    def __init__(self):
        self.csv_path = Path("resources/rr_syllable_map.csv")
        self.existing_mappings = defaultdict(list)  # hangul -> [(roman, weight, pos)]
        self.existing_keys = set()  # (hangul, roman, pos) tuples
        self.load_existing()
    
    def load_existing(self):
        """Load existing mappings from CSV."""
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and not row[0].startswith('#'):
                    hangul = row[0]
                    roman = row[1]
                    weight = row[2] if len(row) > 2 else "0.0"
                    context = row[3] if len(row) > 3 else ""
                    pos = row[4] if len(row) > 4 else ""
                    
                    try:
                        weight_val = float(weight)
                    except:
                        weight_val = 0.0
                    
                    self.existing_mappings[hangul].append((roman, weight_val, pos))
                    self.existing_keys.add((hangul, roman, pos))
    
    def lint_weight(self, weight_line):
        """Lint a weight line and return issues."""
        issues = []
        
        # Parse the weight line
        parts = weight_line.strip().split(',')
        if len(parts) != 5:
            return ["Invalid format - need exactly 5 comma-separated fields"]
        
        hangul, roman, weight_str, context, pos = parts
        
        # Validate weight threshold
        try:
            weight = float(weight_str)
            # Allow negative weights for position-specific mappings (Tier 1 override)
            if weight < -2.5 and (not pos or pos == ""):
                issues.append(f"Weight {weight} below safety threshold -2.5")
        except ValueError:
            issues.append(f"Invalid weight value: {weight_str}")
            weight = 0.0
        
        # Check for exact duplicates
        key = (hangul, roman, pos)
        if key in self.existing_keys:
            issues.append(f"DUPLICATE: {hangul},{roman} (pos={pos}) already exists")
        
        # Check for conflicting mappings
        if hangul in self.existing_mappings:
            conflicts = []
            for existing_roman, existing_weight, existing_pos in self.existing_mappings[hangul]:
                # Same hangul, different roman = potential conflict
                if existing_roman != roman:
                    # Tier 1 override: Allow position-specific mappings with negative weights
                    # to override general mappings
                    if pos in ["S", "G"] and existing_pos == "" and weight < -2.0:
                        # Position-specific with strong negative weight can override general
                        continue
                    
                    # Original conflict detection:
                    # Conflict if:
                    # 1. Both have same position
                    # 2. Either has no position (applies globally)
                    # 3. Either has SG (applies to both S and G)
                    if (pos == existing_pos or 
                        pos == "" or existing_pos == "" or
                        pos == "SG" or existing_pos == "SG"):
                        conflicts.append(f"{hangul}→{existing_roman} (weight={existing_weight}, pos={existing_pos or 'general'})")
            
            if conflicts:
                issues.append(f"CONFLICTS with existing mappings:")
                for c in conflicts:
                    issues.append(f"  - {c}")
        
        # Position validation
        if pos not in ['S', 'G', 'SG', '']:
            issues.append(f"Invalid position: {pos} (must be S, G, SG, or empty)")
        
        # Hangul validation
        if not hangul or not any('\uac00' <= c <= '\ud7af' for c in hangul):
            issues.append("Hangul field must contain Korean characters")
        
        # Roman validation
        if not roman or not all(c.isascii() or c == '-' for c in roman):
            issues.append("Roman field must be ASCII only (with optional hyphens)")
        
        return issues
    
    def suggest_alternatives(self, hangul, roman, pos):
        """Suggest alternatives for conflicting mappings."""
        suggestions = []
        
        # Check if we can use position specificity
        if hangul in self.existing_mappings:
            has_surname = any(p == 'S' for _, _, p in self.existing_mappings[hangul])
            has_given = any(p == 'G' for _, _, p in self.existing_mappings[hangul])
            
            if pos == '' or pos == 'SG':
                if not has_surname:
                    suggestions.append(f"Try position-specific: {hangul},{roman},,S")
                if not has_given:
                    suggestions.append(f"Try position-specific: {hangul},{roman},,G")
            
        # Suggest weight adjustment for existing mapping
        for existing_roman, existing_weight, existing_pos in self.existing_mappings.get(hangul, []):
            if existing_roman == roman and existing_pos == pos:
                suggestions.append(f"Mapping exists with weight={existing_weight}. Consider adjusting weight instead.")
        
        # Check for similar romanizations
        similar_romans = []
        for h, mappings in self.existing_mappings.items():
            for r, w, p in mappings:
                if r.startswith(roman[:2]) and r != roman:
                    similar_romans.append((r, h))
        
        if similar_romans:
            suggestions.append("Similar romanizations exist:")
            for r, h in similar_romans[:3]:
                suggestions.append(f"  - {r} → {h}")
        
        return suggestions

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 lint_weights.py 'hangul,roman,weight,context,pos' [--suggest]")
        sys.exit(1)
    
    weight_line = sys.argv[1]
    suggest = "--suggest" in sys.argv
    
    linter = WeightLinter()
    issues = linter.lint_weight(weight_line)
    
    if issues:
        print("❌ WEIGHT LINTING FAILED:")
        for issue in issues:
            print(f"  • {issue}")
        
        if suggest:
            parts = weight_line.strip().split(',')
            if len(parts) >= 5:
                hangul, roman, _, _, pos = parts
                suggestions = linter.suggest_alternatives(hangul, roman, pos)
                if suggestions:
                    print("\n💡 SUGGESTIONS:")
                    for s in suggestions:
                        print(f"  • {s}")
        
        sys.exit(1)
    else:
        print("✅ Weight passed all safety checks")
        
        # Show what would be added
        parts = weight_line.strip().split(',')
        hangul, roman, weight, context, pos = parts
        pos_desc = {"S": "surname", "G": "given name", "SG": "both", "": "general"}[pos]
        print(f"  Ready to add: {roman} → {hangul} (weight={weight}, position={pos_desc})")
        sys.exit(0)

if __name__ == "__main__":
    main()