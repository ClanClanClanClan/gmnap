#!/usr/bin/env python3
"""
Analyze the accuracy distribution to understand what's needed for 97%
"""

import json
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v5.blueprint_converter import convert_blueprint
from src.v5.core.hangul_to_roman import HangulToRomanConverter
from scripts.dice_coefficient import dice_coefficient
import unicodedata
import yaml

def analyze_accuracy_distribution():
    """Analyze what accuracy levels we're actually achieving"""
    print("=== ACCURACY DISTRIBUTION ANALYSIS ===\n")
    
    # Load Korean dataset
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean.yaml', 'r', encoding='utf-8') as f:
        korean_data = yaml.safe_load(f)
    
    hangul_converter = HangulToRomanConverter(system="rr")
    scores = []
    successful_conversions = 0
    failed_conversions = 0
    
    print("Analyzing conversions...")
    
    for i, (key, entry) in enumerate(korean_data.items()):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(korean_data)}...")
            
        name = key.replace('_', ' ')
        
        # Skip invalid entries
        if len(name) < 2 or any(c.isdigit() for c in name):
            continue
        
        # Convert to Hangul
        hangul = convert_blueprint(name)
        
        if hangul:
            successful_conversions += 1
            # Convert back and calculate similarity
            back_converted = hangul_converter.convert_name(hangul)
            similarity = dice_coefficient(
                unicodedata.normalize('NFC', name.lower()),
                unicodedata.normalize('NFC', back_converted.lower())
            )
            scores.append(similarity)
        else:
            failed_conversions += 1
            scores.append(0.0)
    
    total = len(scores)
    print(f"\nCompleted analysis of {total} entries")
    
    # Calculate statistics
    scores_array = np.array(scores)
    
    print(f"\n=== CONVERSION STATISTICS ===")
    print(f"Successful conversions: {successful_conversions}/{total} ({successful_conversions/total*100:.1f}%)")
    print(f"Failed conversions: {failed_conversions}/{total} ({failed_conversions/total*100:.1f}%)")
    
    print(f"\n=== ACCURACY STATISTICS ===")
    print(f"Mean accuracy: {np.mean(scores_array):.2%}")
    print(f"Median accuracy: {np.median(scores_array):.2%}")
    print(f"Standard deviation: {np.std(scores_array):.2%}")
    
    # Accuracy thresholds
    thresholds = [0.5, 0.7, 0.8, 0.9, 0.95, 0.97, 0.99, 1.0]
    print(f"\n=== ACCURACY THRESHOLDS ===")
    for threshold in thresholds:
        above_threshold = np.sum(scores_array >= threshold)
        percentage = above_threshold / total * 100
        print(f"≥{threshold*100:2.0f}%: {above_threshold:4d}/{total} ({percentage:5.1f}%)")
    
    # Identify what needs improvement
    print(f"\n=== IMPROVEMENT ANALYSIS ===")
    
    # How many need to improve to reach 97%?
    current_97_plus = np.sum(scores_array >= 0.97)
    target_97_plus = int(0.97 * total)  # 97% of dataset
    needed_improvement = target_97_plus - current_97_plus
    
    print(f"Current ≥97%: {current_97_plus}/{total} ({current_97_plus/total*100:.1f}%)")
    print(f"Target ≥97%: {target_97_plus}/{total} (97.0%)")
    print(f"Need to improve: {needed_improvement} entries")
    
    # Analyze entries in the 80-97% range (most improvable)
    improvable = scores_array[(scores_array >= 0.8) & (scores_array < 0.97)]
    print(f"\nEntries in 80-97% range (most improvable): {len(improvable)} ({len(improvable)/total*100:.1f}%)")
    if len(improvable) > 0:
        print(f"  Mean accuracy in this range: {np.mean(improvable):.2%}")
        print(f"  If we improved these to 97%+, we'd have: {current_97_plus + len(improvable)}/{total} ({(current_97_plus + len(improvable))/total*100:.1f}%)")
    
    # Show distribution in ranges
    print(f"\n=== ACCURACY RANGES ===")
    ranges = [
        (0.0, 0.1, "Failed (0-10%)"),
        (0.1, 0.5, "Very Low (10-50%)"),
        (0.5, 0.8, "Low (50-80%)"),
        (0.8, 0.9, "Good (80-90%)"),
        (0.9, 0.97, "High (90-97%)"),
        (0.97, 1.0, "Excellent (97-100%)")
    ]
    
    for min_val, max_val, label in ranges:
        count = np.sum((scores_array >= min_val) & (scores_array < max_val))
        if min_val == 0.97:  # Include 100% in the excellent range
            count = np.sum(scores_array >= min_val)
        percentage = count / total * 100
        print(f"{label:20s}: {count:4d} ({percentage:5.1f}%)")

if __name__ == "__main__":
    analyze_accuracy_distribution()