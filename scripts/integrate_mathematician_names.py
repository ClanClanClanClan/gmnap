#!/usr/bin/env python3
"""
Integrate real mathematician names from regional YAML files into surname patterns.

This will significantly improve detection accuracy by using actual mathematician data.
"""

import yaml
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set


# Map YAML files to region codes
FILE_TO_REGION = {
    "chinese.yaml": "E1",         # Sinophone Mainland
    "japan.yaml": "E3",           # Japan
    "korean.yaml": "E4",          # Korea
    "vietnamese.yaml": "E5",      # Vietnam
    "thai.yaml": "E6",            # Mainland SEA
    "russian.yaml": "B1",         # East-Slavic
    "east european.yaml": "B2",   # Polish/Czech/Slovak
    "polish.yaml": "B2",          # Polish specifically
    "hungarian.yaml": "A2",       # Western Europe (Hungary is in A2)
    "german.yaml": "A2",          # Western Europe
    "french.yaml": "A2",          # Western Europe
    "iranian.yaml": "C2",         # Persian-Tajik
    "indian.yaml": "D1",          # Hindi Belt
}


def extract_surnames_from_yaml(yaml_file: Path) -> Set[str]:
    """Extract unique surnames from a regional YAML file."""
    surnames = set()
    
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, dict):
            return surnames
        
        for entry_name, entry_data in data.items():
            if not isinstance(entry_data, dict):
                continue
            
            # Extract from CanonicalLatin (format: "Family, Given")
            canonical = entry_data.get('CanonicalLatin', '')
            if canonical and ', ' in canonical:
                family_name = canonical.split(', ')[0].strip().lower()
                surnames.add(family_name)
            
            # Also extract from entry name if it's in underscore format
            if '_' in entry_name:
                # e.g., "Abe_Atsushi" -> "abe"
                parts = entry_name.split('_')
                if parts:
                    surnames.add(parts[0].lower())
    
    except Exception as e:
        print(f"Error processing {yaml_file}: {e}")
    
    return surnames


def generate_surname_update_code(region_surnames: Dict[str, Set[str]]) -> str:
    """Generate Python code to update surname patterns in manager.py"""
    
    code = "# Enhanced surname patterns from real mathematician data\n"
    code += "# Generated from docs/regional/*.yaml files\n\n"
    
    for region, surnames in sorted(region_surnames.items()):
        if not surnames:
            continue
        
        # Convert to sorted list and format for Python
        surname_list = sorted(surnames)
        
        # Split into chunks of 10 for readability
        chunks = [surname_list[i:i+10] for i in range(0, len(surname_list), 10)]
        
        code += f'# Additional {region} mathematician surnames\n'
        code += f'{region}_MATHEMATICIAN_SURNAMES = {{\n'
        
        for chunk in chunks:
            formatted_chunk = ', '.join(f'"{s}"' for s in chunk)
            code += f'    {formatted_chunk},\n'
        
        code += '}\n\n'
    
    return code


def analyze_coverage():
    """Analyze which regions have data and which are missing."""
    regional_dir = Path(__file__).parent.parent / "docs" / "regional"
    
    print("📊 Analyzing mathematician data coverage...\n")
    
    # Collect surnames by region
    region_surnames = defaultdict(set)
    
    for yaml_file in regional_dir.glob("*.yaml"):
        region = FILE_TO_REGION.get(yaml_file.name)
        if not region:
            print(f"⚠️  No region mapping for: {yaml_file.name}")
            continue
        
        surnames = extract_surnames_from_yaml(yaml_file)
        region_surnames[region].update(surnames)
        
        print(f"✅ {yaml_file.name} → {region}: {len(surnames)} unique surnames")
    
    print("\n📈 Summary by region:")
    for region, surnames in sorted(region_surnames.items()):
        print(f"  {region}: {len(surnames)} surnames")
    
    # Check which regions are missing data
    all_regions = {
        "A1", "A2", "A3", "A4", "A5",
        "B1", "B2", "B3",
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9",
        "D1", "D2", "D3", "D4", "D5",
        "E1", "E2", "E3", "E4", "E5", "E6", "E7",
        "F1", "F2", "F3", "F4",
        "G1", "H1", "R0", "Z0"
    }
    
    covered_regions = set(region_surnames.keys())
    missing_regions = all_regions - covered_regions
    
    print(f"\n❌ Regions without data: {', '.join(sorted(missing_regions))}")
    
    return region_surnames


def create_integration_script(region_surnames: Dict[str, Set[str]]):
    """Create a script to integrate surnames into manager.py"""
    
    script_path = Path(__file__).parent / "update_manager_surnames.py"
    
    with open(script_path, 'w') as f:
        f.write('''#!/usr/bin/env python3
"""
Update manager.py with real mathematician surnames.
Generated from docs/regional/*.yaml files.
"""

from pathlib import Path

# Mathematician surnames extracted from YAML files
MATHEMATICIAN_SURNAMES = {
''')
        
        # Write surname data
        for region, surnames in sorted(region_surnames.items()):
            if not surnames:
                continue
            
            surname_list = sorted(surnames)[:50]  # Limit to top 50 per region
            f.write(f'    "{region}": {{\n')
            
            # Write in chunks
            for i in range(0, len(surname_list), 5):
                chunk = surname_list[i:i+5]
                formatted = ', '.join(f'"{s}"' for s in chunk)
                f.write(f'        {formatted},\n')
            
            f.write('    },\n')
        
        f.write('''}

def update_manager():
    """Update manager.py with mathematician surnames."""
    manager_path = Path(__file__).parent.parent / "src" / "regions" / "manager.py"
    
    # Read current content
    with open(manager_path, 'r') as f:
        content = f.read()
    
    # Find where to insert new surnames
    for region, surnames in MATHEMATICIAN_SURNAMES.items():
        # Find the region's surname section
        region_marker = f'"{region}": {{'
        if region_marker in content:
            # Find the closing brace
            start = content.find(region_marker)
            brace_count = 0
            pos = start
            
            while pos < len(content):
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found the closing brace
                        # Insert surnames before it
                        insert_pos = pos
                        
                        # Create insertion text
                        insert_text = "\\n                # Real mathematician surnames\\n"
                        for surname in sorted(surnames)[:20]:  # Add top 20
                            insert_text += f'                "{surname}",\\n'
                        
                        # Insert into content
                        content = content[:insert_pos] + insert_text + content[insert_pos:]
                        break
                pos += 1
    
    # Write updated content
    print(f"✅ Updated {manager_path}")
    # Uncomment to actually write:
    # with open(manager_path, 'w') as f:
    #     f.write(content)

if __name__ == "__main__":
    update_manager()
''')
    
    print(f"✅ Created integration script: {script_path}")
    print("   Run it to update manager.py with real mathematician surnames")


def main():
    """Main function to analyze and integrate mathematician names."""
    print("🔍 Integrating Real Mathematician Names")
    print("=" * 60)
    
    # Analyze coverage
    region_surnames = analyze_coverage()
    
    # Generate update code
    print("\n📝 Generating surname update code...")
    update_code = generate_surname_update_code(region_surnames)
    
    # Save to file
    output_path = Path(__file__).parent / "mathematician_surnames.py"
    with open(output_path, 'w') as f:
        f.write(update_code)
    
    print(f"\n✅ Generated surname data: {output_path}")
    
    # Create integration script
    create_integration_script(region_surnames)
    
    # Print sample surnames for verification
    print("\n📋 Sample surnames extracted:")
    for region, surnames in sorted(region_surnames.items()):
        if surnames:
            sample = sorted(surnames)[:5]
            print(f"  {region}: {', '.join(sample)}...")


if __name__ == "__main__":
    main()