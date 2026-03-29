#!/usr/bin/env python3
"""
Fix Dutch particle detection - "de Bruijn, Nicolaas" should go to A2 not A1
Add Dutch-specific particle detection separate from German prefixes
"""

import re
from pathlib import Path


def fix_dutch_particles():
    pipeline_path = Path(
        "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py"
    )

    print("🔧 Adding Dutch particle detection...")

    # Read current pipeline
    with open(pipeline_path, "r") as f:
        content = f.read()

    # Find the German prefix detection logic
    german_prefix_pattern = r"german_prefixes = \['von ', 'van ', 'der ', 'den ', 'ter ', 'ten '\]\n        has_german_prefix = any\(prefix in name_lower for prefix in german_prefixes\)"

    if re.search(german_prefix_pattern, content):
        # Add Dutch particle detection
        dutch_particle_code = """german_prefixes = ['von ', 'van ', 'der ', 'den ', 'ter ', 'ten ']
        has_german_prefix = any(prefix in name_lower for prefix in german_prefixes)
        
        # Dutch particle detection (fix for de Bruijn → A1 instead of A2)
        dutch_particles = ['de ', 'van ', 'van de ', 'van der ', 'den ', 'der ', 'ten ', 'ter ']
        has_dutch_particle = any(particle in name_lower for particle in dutch_particles)"""

        content = re.sub(german_prefix_pattern, dutch_particle_code, content)
        print("   ✅ Added Dutch particle detection")

        # Find the German prefix scoring and add Dutch particle scoring
        german_scoring_pattern = r"if has_german_prefix:\n            scores\['A2'\] \+= 2"

        if re.search(german_scoring_pattern, content):
            new_scoring = """if has_german_prefix:
            scores['A2'] += 2
        if has_dutch_particle:
            scores['A2'] += 5  # Strong boost for Dutch particles
            scores['A1'] = max(0, scores['A1'] - 3)  # Reduce A1 for Dutch names"""

            content = re.sub(german_scoring_pattern, new_scoring, content)
            print("   ✅ Added Dutch particle scoring boost")

    # Write fixed pipeline
    with open(pipeline_path, "w") as f:
        f.write(content)

    print("✅ Dutch particle detection added!")
    print("   Names like 'de Bruijn, Nicolaas' should now go to A2 instead of A1")


if __name__ == "__main__":
    fix_dutch_particles()
