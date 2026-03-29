#!/usr/bin/env python3
"""
Create all missing region implementations for 100% v7 compliance.
"""

import os
from pathlib import Path

# Template for missing regions
REGION_TEMPLATE = '''"""
{full_name} ({code}) regional processor.

Implements {description}
"""

from typing import Any, Dict, List, Optional
from src.regions.base import BaseRegionHandler, RegionRuleError


class {class_name}(BaseRegionHandler):
    """Handler for {code} - {full_name}."""
    
    def __init__(self):
        super().__init__(
            code="{code}",
            yaml_files=[],  # TODO: Add actual YAML files
            territories={territories}
        )
        
    def clean(self, name: str) -> str:
        """Clean and normalize {full_name} name."""
        # Basic cleaning - to be enhanced with specific rules
        name = name.strip()
        
        # Normalize whitespace
        import re
        name = re.sub(r'\\s+', ' ', name)
        
        return name
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with {code}-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return
        
        # Extract components
        components = self._extract_components(canonical)
        
        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {{}}
        
        entry["RegionalExtras"].update(components)
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate {code} name requirements."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")
        
        # Basic validation - to be enhanced
        if len(canonical) < 3:
            raise RegionRuleError("Name too short")
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for {code} names."""
        canonical = entry.get("CanonicalLatin", "")
        
        # Simple sort by family name
        if ", " in canonical:
            family = canonical.split(", ")[0]
            return family.lower()
        
        return canonical.lower()
    
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {{}}
        
        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated
            parts = name.split(None, 1)
            if len(parts) >= 2:
                components["given_name"] = parts[0].strip()
                components["family_name"] = parts[1].strip()
            else:
                components["family_name"] = name.strip()
                components["given_name"] = ""
        
        return components
'''

# Missing regions to create
MISSING_REGIONS = [
    {
        "code": "C5",
        "class_name": "C5ArabicMaghreb",
        "full_name": "Arabic Maghreb",
        "description": "North African Arabic naming patterns with French influence",
        "territories": ["MA", "DZ", "TN", "LY", "EH", "MR"],
        "group": "c_groups",
    },
    {
        "code": "C6",
        "class_name": "C6HebrewDiaspora",
        "full_name": "Hebrew & Diaspora",
        "description": "Hebrew script and romanization patterns",
        "territories": ["IL"],
        "group": "c_groups",
    },
    {
        "code": "C7",
        "class_name": "C7Armenian",
        "full_name": "Armenian",
        "description": "Armenian script and Hübschmann-Meillet romanization",
        "territories": ["AM"],
        "group": "c_groups",
    },
    {
        "code": "C8",
        "class_name": "C8Georgian",
        "full_name": "Georgian",
        "description": "Georgian script and ISO 9984 transliteration",
        "territories": ["GE"],
        "group": "c_groups",
    },
    {
        "code": "C9",
        "class_name": "C9CaucasusTurkic",
        "full_name": "Caucasus-Turkic",
        "description": "Mixed Latin/Cyrillic/Arabic hybrid patterns",
        "territories": ["RU", "AZ"],
        "group": "c_groups",
    },
    {
        "code": "D2",
        "class_name": "D2SouthAsiaDravidian",
        "full_name": "South Asia - Dravidian",
        "description": "Tamil and other Dravidian language patterns",
        "territories": ["IN", "LK"],
        "group": "d_groups",
    },
    {
        "code": "D3",
        "class_name": "D3SouthAsiaBengali",
        "full_name": "South Asia - Bengali",
        "description": "Bengali script with frequent script switching",
        "territories": ["BD", "IN"],
        "group": "d_groups",
    },
    {
        "code": "D4",
        "class_name": "D4PakistanUrdu",
        "full_name": "Pakistan & Urdu",
        "description": "Urdu script with Arabic loan patterns",
        "territories": ["PK"],
        "group": "d_groups",
    },
    {
        "code": "D5",
        "class_name": "D5Sinhala",
        "full_name": "Sinhala",
        "description": "Sinhala script with UN 2003 transliteration",
        "territories": ["LK"],
        "group": "d_groups",
    },
    {
        "code": "E5",
        "class_name": "E5Vietnam",
        "full_name": "Vietnam",
        "description": "Vietnamese with tone marks and numeric tone variants",
        "territories": ["VN"],
        "group": "e_groups",
    },
    {
        "code": "E6",
        "class_name": "E6MainlandSEA",
        "full_name": "Mainland SEA",
        "description": "Thai RTGS, Khmer UNGEGN, Lao MOICT romanization",
        "territories": ["TH", "KH", "LA"],
        "group": "e_groups",
    },
    {
        "code": "E7",
        "class_name": "E7MaritimeSEA",
        "full_name": "Maritime SEA",
        "description": "Malay bin/binti, Indonesian mononyms, Filipino patterns",
        "territories": ["ID", "MY", "SG", "BN", "PH", "TL"],
        "group": "e_groups",
    },
    {
        "code": "F1",
        "class_name": "F1SSAFrancophone",
        "full_name": "SSA - Francophone",
        "description": "Sub-Saharan Africa with French naming influence",
        "territories": [
            "BJ",
            "BF",
            "CM",
            "CF",
            "CG",
            "CI",
            "DJ",
            "GA",
            "GN",
            "ML",
            "NE",
            "SN",
            "TG",
            "TD",
            "KM",
            "SC",
            "MG",
            "BI",
        ],
        "group": "f_groups",
    },
    {
        "code": "F2",
        "class_name": "F2SSAAnglophone",
        "full_name": "SSA - Anglophone",
        "description": "Sub-Saharan Africa with English naming patterns",
        "territories": [
            "GH",
            "NG",
            "KE",
            "UG",
            "TZ",
            "ZW",
            "ZM",
            "MW",
            "GM",
            "LR",
            "SL",
            "BW",
            "LS",
            "NA",
            "RW",
            "SZ",
            "MU",
            "SS",
        ],
        "group": "f_groups",
    },
    {
        "code": "F3",
        "class_name": "F3HornOfAfrica",
        "full_name": "Horn of Africa",
        "description": "Ge'ez script with patronymic chains",
        "territories": ["ET", "ER"],
        "group": "f_groups",
    },
    {
        "code": "F4",
        "class_name": "F4LusophoneAfrica",
        "full_name": "Lusophone Africa",
        "description": "Portuguese colonial naming patterns in Africa",
        "territories": ["AO", "MZ", "CV", "GW", "ST"],
        "group": "f_groups",
    },
    {
        "code": "H1",
        "class_name": "H1Historical",
        "full_name": "Historical (≤1850)",
        "description": "Pre-modern Latinized names and epithets",
        "territories": ["GLOBAL_PRE_1850"],
        "group": "special",
    },
    {
        "code": "R0",
        "class_name": "R0ResidualLatinASCII",
        "full_name": "Residual Latin-ASCII",
        "description": "Catch-all for unmapped territories",
        "territories": ["ANY_UNMAPPED"],
        "group": "special",
    },
    {
        "code": "Z0",
        "class_name": "Z0Quarantine",
        "full_name": "Quarantine",
        "description": "Low confidence or problematic entries",
        "territories": [],
        "group": "special",
    },
]


def create_region_file(region_info):
    """Create a region processor file."""
    # Format territories
    territories_str = str(region_info["territories"])

    # Generate content
    content = REGION_TEMPLATE.format(
        code=region_info["code"],
        class_name=region_info["class_name"],
        full_name=region_info["full_name"],
        description=region_info["description"],
        territories=territories_str,
    )

    # Determine path
    base_path = Path(__file__).parent.parent / "src" / "regions" / region_info["group"]

    # Create directory if needed
    base_path.mkdir(parents=True, exist_ok=True)

    # Write file
    filename = f"{region_info['code'].lower()}_{region_info['full_name'].lower().replace(' & ', '_').replace(' - ', '_').replace(' ', '_')}.py"
    filepath = base_path / filename

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Created: {filepath}")

    # Also create __init__.py if needed
    init_file = base_path / "__init__.py"
    if not init_file.exists():
        init_file.write_text(
            '"""Region processors for {} group."""'.format(region_info["group"])
        )

    return filepath


def update_pipeline_imports():
    """Generate import statements for pipeline."""
    print("\n\nAdd these imports to pipeline_v6.py:\n")

    for region in MISSING_REGIONS:
        module_name = (
            region["code"].lower()
            + "_"
            + region["full_name"]
            .lower()
            .replace(" & ", "_")
            .replace(" - ", "_")
            .replace(" ", "_")
        )
        print(
            f"from src.regions.{region['group']}.{module_name} import {region['class_name']}"
        )

    print("\n\nAnd register them:\n")
    for region in MISSING_REGIONS:
        print(f"self.region_manager.register_region({region['class_name']}())")


def main():
    """Create all missing region files."""
    print("Creating missing region implementations for GMNAP v7 compliance...")

    created_files = []
    for region in MISSING_REGIONS:
        filepath = create_region_file(region)
        created_files.append(filepath)

    print(f"\n✅ Created {len(created_files)} region implementations!")

    update_pipeline_imports()

    print("\n⚠️  Note: These are basic implementations. Each region needs:")
    print("   - Specific linguistic rules")
    print("   - Proper script handling")
    print("   - Surname patterns")
    print("   - YAML file mappings")


if __name__ == "__main__":
    main()
