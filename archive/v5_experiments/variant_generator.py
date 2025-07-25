# Fixed comprehensive legacy patterns
import re

def generate_all_variants(name):
    """Generate comprehensive variant set - FIXED VERSION"""
    variants = {name, name.lower(), name.capitalize()}
    
    # Split into components for multi-word names
    if ' ' in name:
        # Handle space-separated names
        parts = name.split()
        variants.add(''.join(parts))  # CamelCase version
        variants.add(''.join(p.lower() for p in parts))  # lowercase version
        variants.add('-'.join(parts))  # hyphenated version
        variants.add('-'.join(p.lower() for p in parts))  # lowercase hyphenated
    
    if '-' in name:
        # Handle hyphenated names
        parts = name.split('-')
        variants.add(' '.join(parts))  # space-separated version
        variants.add(''.join(parts))  # concatenated version
        variants.add(''.join(p.lower() for p in parts))  # lowercase concatenated
    
    # Add common romanization variants (but only for reasonable strings)
    clean_variants = set()
    for variant in variants:
        # Only process reasonable variants (no special characters)
        if variant and all(c.isalnum() or c in ' -' for c in variant):
            clean_variants.add(variant)
            
            # Apply safe romanization patterns
            clean_variants.add(re.sub(r'\bchoe\b', 'choi', variant, flags=re.I))
            clean_variants.add(re.sub(r'\byi\b', 'lee', variant, flags=re.I))
            clean_variants.add(re.sub(r'\brhee\b', 'lee', variant, flags=re.I))
            clean_variants.add(re.sub(r'\bahn\b', 'an', variant, flags=re.I))
            clean_variants.add(re.sub(r'\bryu\b', 'yu', variant, flags=re.I))
    
    # Remove empty strings and clean up
    clean_variants = {v for v in clean_variants if v and len(v) > 1}
    
    return clean_variants