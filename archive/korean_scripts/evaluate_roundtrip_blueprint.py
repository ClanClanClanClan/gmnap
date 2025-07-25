#!/usr/bin/env python3
"""
Phase 9: Blueprint validation suite with systematic accuracy evaluation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import json
from tqdm import tqdm
from src.v5.blueprint_converter import convert_blueprint
from src.v5.smart_converter import convert_with_smart_backoff  
from src.v5.core.hangul_to_roman import HangulToRomanConverter
from scripts.dice_coefficient import dice_coefficient
import unicodedata

def roundtrip_score(name, converter_func):
    """Calculate round-trip accuracy for a name"""
    # Convert to Hangul
    hangul = converter_func(name)
    if not hangul:
        return 0.0
    
    # Convert back to romanization  
    hangul_converter = HangulToRomanConverter(system="rr")
    reconstructed = hangul_converter.convert_name(hangul)
    
    # Calculate Dice score
    return dice_coefficient(
        unicodedata.normalize('NFC', name.lower()),
        unicodedata.normalize('NFC', reconstructed.lower())
    )

def evaluate_dataset(yaml_path, converter_func, converter_name, threshold=0.97):
    """Evaluate round-trip accuracy on full dataset (from blueprint)"""
    print(f"\n=== EVALUATING {converter_name.upper()} CONVERTER ===")
    
    data = yaml.safe_load(open(yaml_path))
    
    results = []
    failed_conversions = []
    low_accuracy = []
    
    for entry_id, entry in tqdm(data.items(), desc=f"Testing {converter_name}"):
        # Extract name from entry key (Korean dataset format)
        name = entry_id.replace('_', ' ')
        
        # Skip invalid entries
        if len(name) < 2 or any(c.isdigit() for c in name):
            continue
            
        # Calculate round-trip score
        score = roundtrip_score(name, converter_func)
        
        result = {
            "id": entry_id,
            "name": name,
            "score": score,
            "pass": score >= threshold
        }
        results.append(result)
        
        if score == 0.0:
            failed_conversions.append(name)
        elif score < 0.9:
            # Get the actual conversion for analysis
            hangul = converter_func(name)
            hangul_converter = HangulToRomanConverter(system="rr")
            back_converted = hangul_converter.convert_name(hangul) if hangul else "FAILED"
            low_accuracy.append((name, hangul, back_converted, score))
    
    # Summary statistics
    passing = sum(1 for r in results if r["pass"])
    total = len(results)
    accuracy = passing / total if total > 0 else 0
    
    print(f"\n=== {converter_name.upper()} RESULTS ===")
    print(f"Overall accuracy: {accuracy:.1%} ({passing}/{total})")
    print(f"Failed conversions: {len(failed_conversions)}")
    print(f"Low accuracy (< 90%): {len(low_accuracy)}")
    
    # Show failure analysis
    if failed_conversions:
        print(f"\n=== FAILED CONVERSIONS ({converter_name}) ===")
        failure_patterns = {}
        for name in failed_conversions[:20]:
            # Analyze failure patterns
            if ' ' in name:
                failure_patterns['multi_word'] = failure_patterns.get('multi_word', 0) + 1
            elif '-' in name:
                failure_patterns['hyphenated'] = failure_patterns.get('hyphenated', 0) + 1
            elif name[0].isupper() and any(c.isupper() for c in name[1:]):
                failure_patterns['camel_case'] = failure_patterns.get('camel_case', 0) + 1
            else:
                failure_patterns['single_word'] = failure_patterns.get('single_word', 0) + 1
            print(f"  {name}")
        
        print(f"\n=== FAILURE PATTERNS ({converter_name}) ===")
        for pattern, count in sorted(failure_patterns.items(), key=lambda x: x[1], reverse=True):
            print(f"  {pattern}: {count} failures")
    
    # Show low accuracy examples
    if low_accuracy:
        print(f"\n=== LOW ACCURACY EXAMPLES ({converter_name}) ===")
        for name, hangul, back, score in low_accuracy[:10]:
            print(f"  {name} → {hangul} → {back} ({score:.1%})")
    
    # Save detailed results
    results_file = f"validation_results_{converter_name.lower()}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results saved to {results_file}")
    
    return accuracy >= threshold, accuracy, results

def main():
    yaml_path = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean.yaml"
    
    print("=== PHASE 9: SYSTEMATIC VALIDATION SUITE ===")
    print("Evaluating both converters on Korean mathematician dataset...")
    
    # Test Blueprint Converter
    bp_success, bp_accuracy, bp_results = evaluate_dataset(
        yaml_path, convert_blueprint, "Blueprint", threshold=0.97
    )
    
    # Test Smart Converter  
    sm_success, sm_accuracy, sm_results = evaluate_dataset(
        yaml_path, convert_with_smart_backoff, "Smart", threshold=0.97
    )
    
    # Comparative Analysis
    print(f"\n=== COMPARATIVE ANALYSIS ===")
    print(f"Blueprint Converter: {bp_accuracy:.2%} accuracy")
    print(f"Smart Converter: {sm_accuracy:.2%} accuracy")
    print(f"Target: 97.0% accuracy")
    
    if bp_accuracy >= 0.97:
        print("✅ Blueprint Converter meets 97% target!")
    elif sm_accuracy >= 0.97:
        print("✅ Smart Converter meets 97% target!")
    else:
        print("❌ Neither converter meets 97% target")
        
        # Identify areas for improvement
        print(f"\n=== IMPROVEMENT RECOMMENDATIONS ===")
        if bp_accuracy > sm_accuracy:
            print("- Blueprint converter shows higher accuracy potential")
            print("- Focus on fixing multi-word name handling in blueprint approach")
        else:
            print("- Smart converter shows higher coverage")
            print("- Focus on improving accuracy of successful conversions")
        
        print("- Debug incorrect single-syllable mappings (Jung→중, Min→믠)")
        print("- Enhance segmentation for complex names")
        print("- Expand V4 mappings for failed cases")

if __name__ == "__main__":
    main()