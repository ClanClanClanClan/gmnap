#!/usr/bin/env python3
"""Debug region detection scoring logic."""

import sys
sys.path.insert(0, 'src')

from gmnap.core.pipeline import GMNAPPipeline

pipeline = GMNAPPipeline({'database_path': ':memory:'})

def debug_scoring(name):
    """Debug the scoring logic for a name."""
    print(f"\nDEBUG: '{name}'")
    
    name_lower = name.lower()
    
    # Character detection (copy of pipeline logic)
    has_spanish_chars = any(c in name for c in 'ñáéíóúüÑÁÉÍÓÚÜ')
    has_portuguese_chars = any(c in name for c in 'ãõçâêôÃÕÇÂÊÔ')
    has_german_chars = any(c in name for c in 'äöüßÄÖÜ')
    has_nordic_chars = any(c in name for c in 'åæøðþÅÆØÐÞ')
    has_slavic_chars = any(c in name for c in 'čžšďťňľĺřČŽŠĎŤŇĽĹŘ')
    has_polish_chars = any(c in name for c in 'ąćęłńóśźżĄĆĘŁŃÓŚŹŻ')
    
    print(f"  Character detection:")
    print(f"    Spanish: {has_spanish_chars}")
    print(f"    Portuguese: {has_portuguese_chars}")
    print(f"    German: {has_german_chars}")
    print(f"    Nordic: {has_nordic_chars}")
    print(f"    Slavic: {has_slavic_chars}")
    print(f"    Polish: {has_polish_chars}")
    
    # Name patterns
    irish_prefixes = ["o'", "mc", "mac"]
    has_irish_prefix = any(name_lower.startswith(prefix) for prefix in irish_prefixes)
    
    spanish_suffixes = ['ez', 'az', 'iz', 'oz', 'uz']
    has_spanish_suffix = any(name_lower.endswith(suffix) for suffix in spanish_suffixes)
    
    german_prefixes = ['von ', 'van ', 'der ', 'den ', 'ter ', 'ten ']
    has_german_prefix = any(prefix in name_lower for prefix in german_prefixes)
    
    print(f"  Pattern detection:")
    print(f"    Irish prefix: {has_irish_prefix}")
    print(f"    Spanish suffix: {has_spanish_suffix}")
    print(f"    German prefix: {has_german_prefix}")
    
    # Scoring
    scores = {
        'A1': 0,  # Anglo-sphere
        'A2': 0,  # Western Europe
        'G1': 0,  # Latin America
        'B1': 0,  # East Slavic
        'B2': 0,  # South/Central Slavic
    }
    
    # Anglo-sphere indicators
    if has_irish_prefix:
        scores['A1'] += 3
    if not any([has_spanish_chars, has_portuguese_chars, has_german_chars, 
               has_nordic_chars, has_slavic_chars, has_polish_chars]):
        scores['A1'] += 1
        
    # Western Europe indicators
    if has_german_chars or has_nordic_chars:
        scores['A2'] += 3
    if has_german_prefix:
        scores['A2'] += 2
        
    # Latin American indicators
    if has_spanish_chars or has_portuguese_chars:
        scores['G1'] += 3
    if has_spanish_suffix:
        scores['G1'] += 2
        
    # Slavic indicators
    if has_slavic_chars:
        scores['B2'] += 3
    if has_polish_chars:
        scores['B2'] += 2
        
    # Russian endings
    russian_endings = ['ov', 'ova', 'ev', 'eva', 'sky', 'skaya', 'enko', 'uk', 'ich']
    if any(name_lower.endswith(ending) for ending in russian_endings):
        scores['B1'] += 2
    
    print(f"  Scores: {scores}")
    
    # Winner
    max_score = max(scores.values())
    print(f"  Max score: {max_score}")
    
    if max_score == 0:
        winner = 'A1'
        print(f"  Winner: {winner} (default)")
    else:
        for region, score in scores.items():
            if score == max_score:
                winner = region
                print(f"  Winner: {winner} (score {score})")
                break
    
    # Compare with actual
    entry = {"CanonicalLatin": name}
    actual = pipeline._detect_region_by_name_pattern(name)
    print(f"  Actual result: {actual}")
    print(f"  Match: {'✓' if actual == winner else '✗'}")
    
    return winner, actual

# Test cases
test_cases = [
    "Čížek, Pavel",      # Should be B2
    "González, María",   # Should be G1
    "Müller, Klaus",     # Should be A2
    "O'Sullivan, Patrick",  # Should be A1
]

for name in test_cases:
    expected, actual = debug_scoring(name)