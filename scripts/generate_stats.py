#!/usr/bin/env python3
"""Generate project statistics and compliance metrics."""

import json
from pathlib import Path
from collections import defaultdict

def generate_stats():
    """Generate comprehensive project statistics."""
    stats = {
        "regions": {"implemented": 0, "total": 43},
        "authorities": {"implemented": 0, "total": 25},
        "linguistic_rules": {"implemented": 0, "total": 34},
        "tests": {"count": 0, "passed": 0},
        "code_quality": {"lines": 0, "files": 0}
    }
    
    # Count implemented regions
    regions_dir = Path("src/regions")
    for group_dir in regions_dir.glob("*_groups"):
        if group_dir.is_dir():
            for region_file in group_dir.glob("*.py"):
                if region_file.name != "__init__.py":
                    stats["regions"]["implemented"] += 1
    
    # Count authority sources
    auth_dir = Path("src/authorities")
    for tier_dir in auth_dir.glob("tier*"):
        if tier_dir.is_dir():
            for auth_file in tier_dir.glob("*.py"):
                if auth_file.name != "__init__.py":
                    stats["authorities"]["implemented"] += 1
    
    # Calculate compliance percentages
    stats["compliance"] = {
        "regions": round(stats["regions"]["implemented"] / stats["regions"]["total"] * 100, 1),
        "authorities": round(stats["authorities"]["implemented"] / stats["authorities"]["total"] * 100, 1),
        "linguistic_rules": round(stats["linguistic_rules"]["implemented"] / stats["linguistic_rules"]["total"] * 100, 1)
    }
    
    print("📊 GMNAP Project Statistics")
    print("=" * 50)
    print(f"Regions: {stats['regions']['implemented']}/{stats['regions']['total']} ({stats['compliance']['regions']}%)")
    print(f"Authority Sources: {stats['authorities']['implemented']}/{stats['authorities']['total']} ({stats['compliance']['authorities']}%)")
    print(f"Linguistic Rules: {stats['linguistic_rules']['implemented']}/{stats['linguistic_rules']['total']} ({stats['compliance']['linguistic_rules']}%)")
    
    # Save stats to file
    stats_file = Path("analysis/project_stats.json")
    stats_file.parent.mkdir(exist_ok=True)
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n💾 Stats saved to {stats_file}")

if __name__ == "__main__":
    generate_stats()
