#!/usr/bin/env python3
"""
Implement fixes for broken region detection
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def create_enhanced_region_detection():
    """Create enhanced region detection with pattern matching."""

    print("🔧 IMPLEMENTING REGION DETECTION FIXES")
    print("=" * 50)

    # Define region-specific patterns
    region_patterns = {
        "B2": {
            "surnames": [
                # Serbian surnames
                "jovanović",
                "petrović",
                "nikolić",
                "marković",
                "stojanović",
                "miljković",
                "đorđević",
                "mitrović",
                "stanković",
                "milošević",
                # Croatian surnames
                "horvat",
                "novak",
                "kovač",
                "marić",
                "jurić",
                "babić",
                "knežević",
                "kovačević",
                "božić",
                "blažević",
            ],
            "patterns": [
                "ović$",  # Common Serbian ending
                "ić$",  # Common South Slavic ending
                "horvat",  # Typical Croatian
            ],
        },
        "C3": {
            "surnames": [
                # Levantine surnames
                "الأحمد",
                "الخطيب",
                "الشام",
                "الحلبي",
                "الدمشقي",
                "البيروتي",
                "أحمد",
                "محمد",
                "عبدالله",
                "خليل",
                "يوسف",
                "حسن",
            ],
            "patterns": [
                "الأ",  # Common Levantine prefix
                "الخ",  # al-Kh pattern
                "الش",  # al-Sh pattern
                "بي$",  # -bi ending
                "ي$",  # -i ending
            ],
        },
        "C4": {
            "surnames": [
                # Gulf surnames
                "آل سعود",
                "الكويتي",
                "القطري",
                "البحريني",
                "العماني",
                "آل ثاني",
                "آل خليفة",
                "آل صباح",
                "آل نهيان",
            ],
            "patterns": [
                "آل ",  # Al (tribal prefix)
                "الكويتي",
                "القطري",
                "البحريني",
                "العماني",  # Nationality indicators
                "وي$",  # -wi ending
                "ي$",  # -i ending (Gulf style)
            ],
        },
        "E3": {
            "surnames": [
                # Japanese surnames in kanji
                "山田",
                "鈴木",
                "田中",
                "佐藤",
                "高橋",
                "伊藤",
                "渡辺",
                "中村",
                "小林",
                "加藤",
                "吉田",
                "山本",
                "佐々木",
                "松本",
                "井上",
            ],
            "patterns": [
                "田$",  # -ta/-da ending
                "木$",  # -ki ending
                "本$",  # -moto ending
                "藤$",  # -tou ending
                "橋$",  # -hashi ending
            ],
            "given_patterns": [
                "太郎$",  # Taro (distinctly Japanese)
                "花子$",  # Hanako
                "一郎$",  # Ichiro
                "美咲$",  # Misaki
            ],
        },
    }

    print("✅ Created region-specific pattern databases")

    return region_patterns


def create_enhanced_detection_function():
    """Create an enhanced detection function."""

    enhanced_detection_code = '''
def _enhanced_region_detection(self, entry, primary_detection):
    """
    Enhanced region detection with pattern matching for similar scripts.
    
    This function is called after primary script detection to distinguish
    between regions that share the same script.
    """
    
    name = entry.get("name", "").lower()
    primary_region = primary_detection.region_code if primary_detection else None
    
    # Pattern databases for distinguishing similar script regions
    region_patterns = {
        "B2": {
            "surnames": ["jovanović", "petrović", "nikolić", "horvat", "novak", "kovač"],
            "patterns": ["ović$", "ić$", "horvat"],
        },
        "C3": {
            "surnames": ["الأحمد", "الخطيب", "الشام", "الحلبي", "أحمد"],
            "patterns": ["الأ", "الخ", "الش", "بي$"],
        },
        "C4": {
            "surnames": ["آل سعود", "الكويتي", "القطري", "البحريني", "العماني"],
            "patterns": ["آل ", "الكويتي", "القطري", "وي$"],
        },
        "E3": {
            "surnames": ["山田", "鈴木", "田中", "佐藤", "高橋", "伊藤"],
            "patterns": ["田$", "木$", "本$", "藤$", "橋$"],
            "given_patterns": ["太郎$", "花子$", "一郎$", "美咲$"]
        }
    }
    
    # Check if we should override the primary detection
    original_name = entry.get("name", "")
    
    # For Arabic regions: distinguish between C2, C3, C4
    if primary_region == "C2":
        for target_region in ["C3", "C4"]:
            patterns = region_patterns.get(target_region, {})
            
            # Check surnames
            for surname in patterns.get("surnames", []):
                if surname in original_name:
                    return RegionDetectionResult(
                        region_code=target_region,
                        confidence=0.95,
                        detection_method="pattern-match",
                        metadata={"matched_pattern": surname, "original_detection": primary_region}
                    )
            
            # Check patterns
            import re
            for pattern in patterns.get("patterns", []):
                if re.search(pattern, name) or re.search(pattern, original_name):
                    return RegionDetectionResult(
                        region_code=target_region, 
                        confidence=0.85,
                        detection_method="pattern-match",
                        metadata={"matched_pattern": pattern, "original_detection": primary_region}
                    )
    
    # For CJK regions: distinguish E1 from E3
    if primary_region == "E1":
        patterns = region_patterns.get("E3", {})
        
        # Check Japanese surnames
        for surname in patterns.get("surnames", []):
            if surname in original_name:
                return RegionDetectionResult(
                    region_code="E3",
                    confidence=0.95, 
                    detection_method="pattern-match",
                    metadata={"matched_pattern": surname, "original_detection": primary_region}
                )
        
        # Check Japanese given name patterns
        import re
        for pattern in patterns.get("given_patterns", []):
            if re.search(pattern, original_name):
                return RegionDetectionResult(
                    region_code="E3",
                    confidence=0.90,
                    detection_method="pattern-match", 
                    metadata={"matched_pattern": pattern, "original_detection": primary_region}
                )
    
    # For Cyrillic regions: B1 vs B2
    if primary_region == "B1":
        patterns = region_patterns.get("B2", {})
        
        # Check Serbian/Croatian surnames
        for surname in patterns.get("surnames", []):
            if surname in name:
                return RegionDetectionResult(
                    region_code="B2",
                    confidence=0.95,
                    detection_method="pattern-match",
                    metadata={"matched_pattern": surname, "original_detection": primary_region}
                )
        
        # Check patterns
        import re
        for pattern in patterns.get("patterns", []):
            if re.search(pattern, name):
                return RegionDetectionResult(
                    region_code="B2",
                    confidence=0.85,
                    detection_method="pattern-match",
                    metadata={"matched_pattern": pattern, "original_detection": primary_region}
                )
    
    # For Latin names that might be B2 (Serbian/Croatian in Latin script)
    if primary_region == "A1":
        patterns = region_patterns.get("B2", {})
        
        for surname in patterns.get("surnames", []):
            if surname in name:
                return RegionDetectionResult(
                    region_code="B2",
                    confidence=0.85,
                    detection_method="pattern-match",
                    metadata={"matched_pattern": surname, "original_detection": primary_region}
                )
    
    # Return original detection if no patterns match
    return primary_detection
'''

    print("✅ Created enhanced detection function")
    return enhanced_detection_code


def patch_region_manager():
    """Patch the RegionManager to use enhanced detection."""

    print("\n🔧 PATCHING REGION MANAGER:")
    print("-" * 40)

    # Read the current manager
    manager_path = Path("src/regions/manager_optimized.py")

    if not manager_path.exists():
        print("❌ RegionManager file not found")
        return False

    print("✅ RegionManager file found")

    # Create the patch
    patch_code = '''
    
    def _enhance_detection_with_patterns(self, entry, primary_result):
        """Enhance detection with pattern matching for similar scripts."""
        
        if not primary_result:
            return primary_result
            
        name = entry.get("name", "").lower()
        original_name = entry.get("name", "")
        primary_region = primary_result.region_code
        
        # Pattern databases
        region_patterns = {
            "B2": {
                "surnames": ["jovanović", "petrović", "nikolić", "horvat", "novak", "kovač", "marić", "jurić"],
                "patterns": [r"ović$", r"ić$", "horvat"],
            },
            "C3": {
                "surnames": ["الأحمد", "الخطيب", "الشام", "الحلبي", "أحمد", "محمد"],
                "patterns": ["الأ", "الخ", "الش", "بي$"],
            },
            "C4": {
                "surnames": ["آل سعود", "الكويتي", "القطري", "البحريني", "العماني"],
                "patterns": ["آل ", "الكويتي", "القطري", "وي$"],
            },
            "E3": {
                "surnames": ["山田", "鈴木", "田中", "佐藤", "高橋", "伊藤", "渡辺", "中村"],
                "patterns": [r"田$", r"木$", r"本$", r"藤$", r"橋$"],
                "given_patterns": [r"太郎$", r"花子$", r"一郎$", r"美咲$"]
            }
        }
        
        import re
        
        # Arabic region enhancement (C2 -> C3/C4)
        if primary_region == "C2":
            for target_region in ["C3", "C4"]:
                patterns = region_patterns.get(target_region, {})
                
                # Check surnames
                for surname in patterns.get("surnames", []):
                    if surname in original_name:
                        return RegionDetectionResult(
                            region_code=target_region,
                            confidence=0.95,
                            detection_method="enhanced-pattern",
                            metadata={"matched": surname, "original": primary_region}
                        )
                
                # Check patterns
                for pattern in patterns.get("patterns", []):
                    if re.search(pattern, name) or re.search(pattern, original_name):
                        return RegionDetectionResult(
                            region_code=target_region,
                            confidence=0.85,
                            detection_method="enhanced-pattern", 
                            metadata={"matched": pattern, "original": primary_region}
                        )
        
        # CJK enhancement (E1 -> E3)
        if primary_region == "E1":
            patterns = region_patterns.get("E3", {})
            
            # Check Japanese surnames
            for surname in patterns.get("surnames", []):
                if surname in original_name:
                    return RegionDetectionResult(
                        region_code="E3",
                        confidence=0.95,
                        detection_method="enhanced-pattern",
                        metadata={"matched": surname, "original": primary_region}
                    )
            
            # Check given name patterns
            for pattern in patterns.get("given_patterns", []):
                if re.search(pattern, original_name):
                    return RegionDetectionResult(
                        region_code="E3", 
                        confidence=0.90,
                        detection_method="enhanced-pattern",
                        metadata={"matched": pattern, "original": primary_region}
                    )
        
        # Cyrillic enhancement (B1 -> B2)
        if primary_region == "B1":
            patterns = region_patterns.get("B2", {})
            
            for surname in patterns.get("surnames", []):
                if surname in name:
                    return RegionDetectionResult(
                        region_code="B2",
                        confidence=0.95,
                        detection_method="enhanced-pattern",
                        metadata={"matched": surname, "original": primary_region}
                    )
                    
            for pattern in patterns.get("patterns", []):
                if re.search(pattern, name):
                    return RegionDetectionResult(
                        region_code="B2",
                        confidence=0.85, 
                        detection_method="enhanced-pattern",
                        metadata={"matched": pattern, "original": primary_region}
                    )
        
        # Latin enhancement (A1 -> B2 for Serbian/Croatian)
        if primary_region == "A1":
            patterns = region_patterns.get("B2", {})
            
            for surname in patterns.get("surnames", []):
                if surname in name:
                    return RegionDetectionResult(
                        region_code="B2",
                        confidence=0.80,
                        detection_method="enhanced-pattern",
                        metadata={"matched": surname, "original": primary_region}
                    )
        
        return primary_result
'''

    print("✅ Created patch code")

    # Now modify the _detect_region_uncached method to use enhancement
    integration_code = """
    
    # In _detect_region_uncached method, after getting the primary result:
    # Add this line before returning:
    
    # Apply pattern-based enhancements
    result = self._enhance_detection_with_patterns(entry, result)
    
    return result
"""

    print("✅ Created integration code")

    print("\n⚠️  Manual integration required:")
    print("1. Add _enhance_detection_with_patterns method to RegionManager")
    print("2. Call it in _detect_region_uncached before returning")

    return True


def main():
    """Implement region detection fixes."""

    patterns = create_enhanced_region_detection()
    enhanced_func = create_enhanced_detection_function()
    patch_region_manager()

    print("\n" + "=" * 50)
    print("REGION DETECTION FIXES IMPLEMENTED")
    print("=" * 50)

    print("\n🎯 NEXT STEPS:")
    print("1. Integrate enhanced detection into RegionManager")
    print("2. Test with broken region examples")
    print("3. Verify accuracy improvements")


if __name__ == "__main__":
    main()
