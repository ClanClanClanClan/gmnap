import yaml
import sys
sys.path.insert(0, '../../../../../../../src')
from converter import eng2kor, kor2eng, eng2kor_nbest, _enhanced_dice

def find_hangul(variants):
    for v in variants:
        if any('\uac00' <= c <= '\ud7af' for c in v):
            return v.replace(' ', '')
    return None

# Load test data and find current failures
data = yaml.safe_load(open('data/korean.yaml', encoding='utf8'))
current_failures = []

for name, info in data.items():
    rr = info.get('CanonicalLatin')
    ko_exp = find_hangul(info.get('AllCommonVariants', []))
    if not rr or not ko_exp: 
        continue
    
    ko = eng2kor(rr)
    hypos = eng2kor_nbest(rr, n=3)
    
    if ko_exp in hypos:
        ko = ko_exp
    elif ko != ko_exp:
        current_failures.append({
            'name': name,
            'type': 'conversion',
            'input': rr,
            'expected': ko_exp,
            'actual': ko,
            'issue': f"{rr} → {ko} (expect {ko_exp})"
        })
        continue
    
    # Test roundtrip with enhanced dice
    rr2 = kor2eng(ko, rr) or ""
    dice_score = _enhanced_dice(rr, rr2)
    
    if dice_score < 0.90:
        current_failures.append({
            'name': name,
            'type': 'roundtrip', 
            'input': rr,
            'korean': ko,
            'roundtrip': rr2,
            'dice': dice_score,
            'issue': f"{rr} → {rr2} (dice={dice_score:.3f})"
        })

print(f"=== CURRENT 22 FAILURES ANALYSIS (97.00% → 97.8% target) ===")
print(f"Total failures: {len(current_failures)}")

conversion_failures = [f for f in current_failures if f['type'] == 'conversion']
roundtrip_failures = [f for f in current_failures if f['type'] == 'roundtrip']

print(f"Conversion failures: {len(conversion_failures)}")
print(f"Roundtrip failures: {len(roundtrip_failures)}")

print(f"\n=== CONVERSION FAILURES (need positional weight fixes) ===")
for i, f in enumerate(conversion_failures, 1):
    print(f"{i}. {f['name']}: {f['issue']}")

print(f"\n=== ROUNDTRIP FAILURES (need enhanced equivalences) ===")
for i, f in enumerate(roundtrip_failures[:10], 1):
    print(f"{i}. {f['name']}: {f['issue']}")

# Analyze patterns in remaining roundtrip failures
print(f"\n=== PATTERN ANALYSIS FOR REMAINING ROUNDTRIPS ===")
common_patterns = {}
for f in roundtrip_failures:
    input_lower = f['input'].lower().replace(',', '').replace('-', ' ').replace(' ', '')
    output_lower = f['roundtrip'].lower().replace(' ', '')
    
    # Find character differences
    diffs = []
    min_len = min(len(input_lower), len(output_lower))
    for i in range(min_len):
        if input_lower[i] != output_lower[i]:
            diffs.append(f"{input_lower[i]}→{output_lower[i]}")
    
    # Look for common substitution patterns
    for diff in diffs:
        common_patterns[diff] = common_patterns.get(diff, 0) + 1

print("Most common character substitutions:")
for pattern, count in sorted(common_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {pattern}: {count} times")

# Suggest additional Korean equivalents
print(f"\n=== SUGGESTED ADDITIONAL EQUIVALENTS ===")
suggested = set()
for f in roundtrip_failures:
    input_clean = f['input'].lower().replace(',', '').replace('-', ' ').replace(' ', '')
    output_clean = f['roundtrip'].lower().replace(' ', '')
    
    # Look for 2-3 character patterns that differ
    for i in range(len(input_clean)-1):
        for j in range(2, 4):
            if i+j <= len(input_clean):
                input_substr = input_clean[i:i+j]
                if i+j <= len(output_clean):
                    output_substr = output_clean[i:i+j]
                    if input_substr != output_substr and len(input_substr) > 1:
                        suggested.add(f"'{input_substr}': '{output_substr}'")

for suggestion in sorted(suggested)[:8]:
    print(f"  {suggestion}")