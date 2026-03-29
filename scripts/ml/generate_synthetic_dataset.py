#!/usr/bin/env python3
"""
Generate 50,000 high-quality synthetic names for Phase 2 ML training.

Strategy:
- Lexicon-based combinations (primary)
- Pattern-based generation (secondary)
- Quality validation
- Regional balance (overweight problem regions)
"""

import sys
import random
import json
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.manager_optimized import _STRONG, _MEDIUM

# Regional targets (50k total, excluding R0/Z0)
REGIONAL_TARGETS = {
    # Problem regions (overweight for better learning)
    "A4": 2000,  # Oceania - hardest problem
    "C1": 1800,  # Turkic - confusion with C9
    "C9": 1800,  # Caucasus Turkic - confusion with C1
    # Good regions (standard weight)
    "A1": 1500,
    "A2": 1500,
    "A3": 1200,
    "A5": 1000,
    "B1": 1500,
    "B2": 1200,
    "B3": 1200,
    "C2": 1500,
    "C3": 1500,
    "C4": 1200,
    "C5": 1200,
    "C6": 1500,
    "C7": 1200,
    "C8": 1000,
    "D1": 1500,
    "D2": 1200,
    "D3": 1500,
    "D4": 1200,
    "D5": 1200,
    "E1": 1500,
    "E2": 1500,
    "E3": 1200,
    "E4": 1500,
    "E5": 1200,
    "E6": 1000,
    "E7": 1200,
    "F1": 1200,
    "F2": 1200,
    "F3": 1000,
    "F4": 1000,
    "G1": 1500,
    "H1": 800,
}

# Regional naming conventions
EAST_ASIAN_REGIONS = {"E1", "E2", "E3", "E4"}  # Surname Given order
WESTERN_REGIONS = {"A1", "A2", "A3", "A4", "A5", "G1"}  # Given Surname order


def generate_lexicon_based(region, n_samples):
    """Generate names from lexicon combinations."""
    strong = _STRONG.get(region, {})
    medium = _MEDIUM.get(region, {})

    surnames = list(strong.get("surnames", set()))
    given_frags = list(strong.get("given_frag", set()))

    # Fallback to medium if strong is empty
    if not surnames:
        surnames = list(medium.get("surnames", set()))
    if not given_frags:
        # Create generic given names if none available
        given_frags = ["alex", "david", "maria", "sarah", "james", "anna"]

    if not surnames or not given_frags:
        return []

    names = set()
    attempts = 0
    max_attempts = n_samples * 10  # Prevent infinite loops

    while len(names) < n_samples and attempts < max_attempts:
        attempts += 1

        # Select components
        given = random.choice(given_frags)
        surname = random.choice(surnames)

        # Handle particles
        particles = list(strong.get("particles", set()) | medium.get("particles", set()))
        particle = random.choice(particles) if particles and random.random() < 0.2 else None

        # Handle prefixes (Arabic al-, ben-, etc.)
        prefixes = list(strong.get("surname_prefix", set()))
        prefix = random.choice(prefixes) if prefixes and random.random() < 0.3 else None

        # Construct name based on regional convention
        if region in EAST_ASIAN_REGIONS:
            # East Asian: Surname Given
            name = f"{surname.title()} {given.title()}"
        else:
            # Western/Other: Given [Particle] [Prefix]Surname
            parts = [given.title()]
            if particle:
                parts.append(particle.lower())
            if prefix:
                parts.append(f"{prefix}{surname}".title())
            else:
                parts.append(surname.title())
            name = " ".join(parts)

        names.add(name)

    return list(names)


def generate_pattern_based(region, n_samples):
    """Generate names using morphological patterns (suffixes, etc.)."""
    strong = _STRONG.get(region, {})

    surname_suffixes = list(strong.get("surname_suffix", set()))
    given_suffixes = list(strong.get("given_suffix", set()))
    surnames = list(strong.get("surnames", set()))
    given_frags = list(strong.get("given_frag", set()))

    if not surname_suffixes and not given_suffixes:
        return []

    names = set()

    # Generate names with suffix patterns
    for _ in range(n_samples):
        if surnames and given_frags:
            given = random.choice(given_frags)

            if surname_suffixes:
                # Create surname from pattern: base + suffix
                base = random.choice(surnames)[:4]  # Use first 4 chars as base
                suffix = random.choice(surname_suffixes)
                surname = f"{base}{suffix}"
            else:
                surname = random.choice(surnames)

            # Construct name
            if region in EAST_ASIAN_REGIONS:
                name = f"{surname.title()} {given.title()}"
            else:
                name = f"{given.title()} {surname.title()}"

            names.add(name)

        if len(names) >= n_samples:
            break

    return list(names)


def validate_name(name):
    """Quality validation for generated names."""
    if not name or len(name) < 3 or len(name) > 50:
        return False

    # Check token count (1-4 tokens)
    tokens = name.split()
    if len(tokens) < 1 or len(tokens) > 4:
        return False

    # Check for reasonable character distribution
    vowels = sum(1 for c in name.lower() if c in "aeiouáéíóúàèìòùäëïöüâêîôû")
    consonants = sum(
        1 for c in name.lower() if c.isalpha() and c not in "aeiouáéíóúàèìòùäëïöüâêîôû"
    )
    total_alpha = vowels + consonants

    if total_alpha == 0:
        return False

    vowel_ratio = vowels / total_alpha
    if vowel_ratio < 0.15 or vowel_ratio > 0.7:  # Too few or too many vowels
        return False

    return True


def generate_region_dataset(region, target_count):
    """Generate complete dataset for one region."""
    print(f"Generating {target_count} names for {region}...")

    # Split between methods
    lexicon_count = int(target_count * 0.7)  # 70% lexicon-based
    pattern_count = target_count - lexicon_count  # 30% pattern-based

    all_names = set()

    # Generate lexicon-based
    lexicon_names = generate_lexicon_based(region, lexicon_count)
    all_names.update(n for n in lexicon_names if validate_name(n))

    # Generate pattern-based
    pattern_names = generate_pattern_based(region, pattern_count)
    all_names.update(n for n in pattern_names if validate_name(n))

    # If we didn't reach target, fill with more lexicon-based
    while len(all_names) < target_count:
        extra = generate_lexicon_based(region, target_count - len(all_names))
        all_names.update(n for n in extra if validate_name(n))

        if len(extra) == 0:  # Prevent infinite loop
            break

    # Convert to list and limit to target
    result = list(all_names)[:target_count]

    print(f"  ✅ Generated {len(result)} names for {region}")
    return result


def main():
    print("=" * 70)
    print("PHASE 2: MASSIVE SYNTHETIC DATASET GENERATION (50,000 NAMES)")
    print("=" * 70)
    print()

    # Calculate total
    total_target = sum(REGIONAL_TARGETS.values())
    print(f"Target: {total_target:,} names across {len(REGIONAL_TARGETS)} regions")
    print()

    # Generate for each region
    all_data = []
    stats = defaultdict(int)

    for region, target in sorted(REGIONAL_TARGETS.items()):
        names = generate_region_dataset(region, target)

        for name in names:
            all_data.append(
                {
                    "CanonicalNative": name,
                    "Region": region,
                    "Source": "synthetic_ml",
                    "Method": "lexicon_pattern",
                }
            )
            stats[region] += 1

    print()
    print("=" * 70)
    print(f"✅ GENERATION COMPLETE: {len(all_data):,} names")
    print("=" * 70)
    print()

    # Statistics
    print("Regional Distribution:")
    for region in sorted(stats.keys()):
        count = stats[region]
        target = REGIONAL_TARGETS[region]
        pct = (count / len(all_data)) * 100
        print(f"  {region}: {count:5,} names ({pct:5.2f}%) - target: {target:,}")
    print()

    # Save to file
    output_dir = Path("data/ml_training")
    output_dir.mkdir(exist_ok=True, parents=True)

    output_file = output_dir / "synthetic_50k.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "total": len(all_data),
                    "regions": len(stats),
                    "method": "lexicon_pattern_generation",
                    "quality_validated": True,
                },
                "data": all_data,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"✅ Saved to: {output_file}")
    print()

    # Sample names
    print("Sample names per region:")
    for region in sorted(set(REGIONAL_TARGETS.keys())):
        region_names = [d["CanonicalNative"] for d in all_data if d["Region"] == region]
        if region_names:
            samples = random.sample(region_names, min(3, len(region_names)))
            print(f"  {region}: {', '.join(samples)}")
    print()

    print("=" * 70)
    print("Next step: Create train/val/test splits")
    print("  python3 scripts/ml/create_training_splits.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
