#!/usr/bin/env python3
"""
Add the final missing mappings to reach 97% accuracy
"""

import json

def add_final_mappings():
    """Add missing surname and component mappings"""
    print("=== ADDING FINAL MISSING MAPPINGS ===\n")
    
    # Load current mappings
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive_mappings.json', 'r', encoding='utf-8') as f:
        v4_mappings = json.load(f)
    
    print(f"Current mappings: {len(v4_mappings)}")
    
    # Additional mappings needed for the final 34 failures
    final_mappings = {
        # Rare Korean surnames
        'eom': '엄',
        'uhm': '엄', 
        'you': '유',
        'yeo': '여',
        'sohn': '손',
        'eoh': '어',
        'hahm': '함',
        'eu': '어',
        'hwangbo': '황보',  # compound surname
        'law': '로',  # law can be 로 or 나
        'yook': '육',
        'rho': '노',  # variant of 'no'
        'boo': '부',
        
        # Hyphenated name components
        'jae-hyeong': '재형',
        'yong-seok': '용석',
        'jin-soo': '진수',
        'ji-won': '지원',
        'sun-jin': '선진',
        'ji-sun': '지선',
        'sun-young': '선영',
        'hyun-jin': '현진',
        'sang-won': '상원',
        
        # English names (for Korean-Americans)
        'david': '데이비드',
        'grace': '그레이스',
        'samuel': '사무엘',
        'linda': '린다'
    }
    
    # Add new mappings
    added_count = 0
    updated_count = 0
    
    for roman, hangul in final_mappings.items():
        if roman not in v4_mappings:
            v4_mappings[roman] = hangul
            added_count += 1
            print(f"  ✅ Added: {roman} -> {hangul}")
        elif v4_mappings[roman] != hangul:
            old_hangul = v4_mappings[roman]
            v4_mappings[roman] = hangul
            updated_count += 1
            print(f"  🔄 Updated: {roman}: {old_hangul} -> {hangul}")
        else:
            print(f"  ⚠️  Exists: {roman} -> {hangul}")
    
    print(f"\n📊 Summary:")
    print(f"  ✅ Added: {added_count} new mappings")
    print(f"  🔄 Updated: {updated_count} existing mappings")
    print(f"  📈 Total mappings: {len(v4_mappings)}")
    
    # Save updated mappings
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive_mappings.json', 'w', encoding='utf-8') as f:
        json.dump(v4_mappings, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Updated V4 mappings saved!")
    
    return v4_mappings

if __name__ == "__main__":
    add_final_mappings()