#!/usr/bin/env python3
"""
Validation script for Korean converter v6
"""
import yaml
import unicodedata
import sys
from pathlib import Path

# Add src directory to path
E4_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(E4_ROOT / "src"))

from converter_fixed import eng2kor, kor2eng

def norm(s):
    """Normalize string for comparison."""
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))

def dice(a, b):
    """Calculate Dice coefficient using character bigrams."""
    a_bigrams = set(zip(a, a[1:]))
    b_bigrams = set(zip(b, b[1:]))
    if not a_bigrams and not b_bigrams:
        return 1.0
    if not a_bigrams or not b_bigrams:
        return 0.0
    return 2 * len(a_bigrams & b_bigrams) / (len(a_bigrams) + len(b_bigrams))

def validate_accuracy():
    """Validate round-trip accuracy on Korean dataset."""
    data_path = E4_ROOT / "data" / "korean.yaml"
    
    try:
        with open(data_path, encoding="utf8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Dataset not found: {data_path}")
        return False
    
    if not data:
        print("❌ Empty dataset")
        return False
    
    print(f"📊 Validating on {len(data)} entries...")
    
    ok = 0
    tot = 0
    misses = []
    
    for k, v in data.items():
        if not isinstance(v, dict):
            continue
            
        rr = v.get("CanonicalLatin", "")
        ko_exp = v.get("CJK", "")
        
        if not rr or not ko_exp:
            continue
        
        # Test English -> Korean conversion
        ko = eng2kor(rr)
        if ko != ko_exp:
            misses.append((k, "eng→kor", f"'{rr}' -> '{ko}' (expected '{ko_exp}')"))
            tot += 1
            continue
        
        # Test round-trip: Korean -> English
        rr2 = kor2eng(ko) or ""
        dice_score = dice(norm(rr), norm(rr2))
        
        if dice_score < 0.97:
            misses.append((k, "roundtrip", f"'{rr}' -> '{ko}' -> '{rr2}' (dice: {dice_score:.3f})"))
            tot += 1
            continue
        
        ok += 1
        tot += 1
    
    # Calculate accuracy
    accuracy = (ok / tot * 100) if tot > 0 else 0
    
    print(f"\n📈 RESULTS:")
    print(f"✅ Successful: {ok}")
    print(f"❌ Failed: {len(misses)}")
    print(f"📊 Total tested: {tot}")
    print(f"🎯 Accuracy: {accuracy:.2f}%")
    
    # Show compliance status
    if accuracy >= 97.0:
        print(f"✅ GMNAP v6.1 COMPLIANT (≥97% required)")
    else:
        print(f"❌ Below GMNAP v6.1 requirement (≥97% required)")
    
    # Show first few misses
    if misses:
        print(f"\n❌ First 5 failures:")
        for i, (name, error_type, details) in enumerate(misses[:5]):
            print(f"  {i+1}. {name} ({error_type}): {details}")
        
        if len(misses) > 5:
            print(f"  ... and {len(misses) - 5} more")
    
    return accuracy >= 97.0

if __name__ == "__main__":
    print("=== Korean Converter v6 Validation ===")
    success = validate_accuracy()
    
    if success:
        print("\n🎉 VALIDATION PASSED - Ready for production")
    else:
        print("\n⚠️  VALIDATION FAILED - Needs improvement")
        print("💡 Add missing syllables to resources/rr_syllable_map.csv and rebuild")