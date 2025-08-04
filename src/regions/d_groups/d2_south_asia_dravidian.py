"""
South Asia - Dravidian (D2) regional processor.

Implements Tamil and other Dravidian language patterns
"""

from typing import Any, Dict, List, Optional
from ..base import RegionSpec, RegionRuleError


class D2SouthAsiaDravidian(RegionSpec):
    """Handler for D2 - South Asia - Dravidian."""
    
    def __init__(self):
        super().__init__(
            code="D2",
            yaml_files=[],  # TODO: Add actual YAML files,
            scripts=['Tamil', 'Latin']
        )
        
    def clean(self, name: str) -> str:
        """Clean and normalize South Asia - Dravidian name."""
        # Basic cleaning - to be enhanced with specific rules
        name = name.strip()
        
        # Normalize whitespace
        import re
        name = re.sub(r'\s+', ' ', name)
        
        return name
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with D2-specific data."""
        # Add region code
        entry["RegionCode"] = self.code
        
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return
        
        # Extract components
        components = self._extract_components(canonical)
        
        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        
        entry["RegionalExtras"].update(components)
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate D2 name requirements."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")
        
        # Basic validation - to be enhanced
        if len(canonical) < 3:
            raise RegionRuleError("Name too short")
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for D2 names."""
        canonical = entry.get("CanonicalLatin", "")
        
        # Simple sort by family name
        if ", " in canonical:
            family = canonical.split(", ")[0]
            return family.lower()
        
        return canonical.lower()
    
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}
        
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
