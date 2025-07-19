"""
G1 - Latin America region implementation.

Covers: Argentina, Bolivia, Brazil, Chile, Colombia, Costa Rica, Cuba, Dominican Republic, 
Ecuador, Guatemala, Honduras, Mexico, Nicaragua, Panama, Peru, Paraguay, El Salvador, 
Uruguay, Venezuela, Puerto Rico
Features: Spanish/Portuguese names, compound surnames, particles, accents
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from src.regions.base import RegionRuleError, RegionSpec


class G1_LatinAmerica(RegionSpec):
    """
    Latin America region (G1).
    
    Handles Spanish and Portuguese names:
    - Compound surnames (paternal + maternal)
    - Name particles (de, da, del, dos, etc.)
    - Accented characters
    - Multiple given names
    """
    
    def __init__(self):
        super().__init__(
            code="G1",
            yaml_files=["g1_latin_america.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Given Family",
            romanisation_standards=[]
        )
        
        # Common Spanish/Portuguese particles
        self.particles = {
            # Spanish
            "de", "del", "de la", "de los", "de las", "y", "e",
            
            # Portuguese
            "da", "das", "do", "dos", "de", "e",
            
            # Both
            "san", "santa", "santo"
        }
        
        # Common titles to remove
        self.titles = {
            # Spanish titles
            "Dr", "Dr.", "Dra", "Dra.", "Doctor", "Doctora",
            "Prof", "Prof.", "Profesor", "Profesora",
            "Ing", "Ing.", "Ingeniero", "Ingeniera",
            "Lic", "Lic.", "Licenciado", "Licenciada",
            "Sr", "Sr.", "Señor", "Sra", "Sra.", "Señora",
            "Srta", "Srta.", "Señorita",
            "Don", "Doña", "Fray", "Sor",
            
            # Portuguese titles
            "Doutor", "Doutora", "Professor", "Professora",
            "Engenheiro", "Engenheira", "Senhor", "Senhora",
            "Senhorita", "Dom", "Dona", "Frei", "Irmã",
            
            # English equivalents
            "Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms.", "Miss"
        }
        
        # Common connecting words
        self.connectors = {"y", "e", "i", "da", "de", "do", "dos", "das"}
        
        # Common Spanish/Portuguese name patterns
        self.name_patterns = {
            # Spanish patronymic endings
            "ez": "son of",  # González, Rodríguez, etc.
            "az": "son of",  # Díaz, etc.
            "iz": "son of",  # Ruiz, etc.
            
            # Portuguese patronymic endings
            "es": "son of",  # Gomes, Lopes, etc.
            "ez": "son of",  # Mendes, etc.
        }
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to G1 rules."""
        # Clean canonical forms
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])
        
        # Clean variants
        if "Variants" in entry:
            if "Observed" in entry["Variants"]:
                for variant in entry["Variants"]["Observed"]:
                    if "str" in variant:
                        variant["str"] = self._clean_name(variant["str"])
    
    def _clean_name(self, name: str) -> str:
        """Clean a single name string."""
        if not name:
            return name
        
        # Remove titles
        name = self._remove_titles(name)
        
        # Normalize whitespace
        name = " ".join(name.split())
        
        # Normalize punctuation
        name = self._normalize_punctuation(name)
        
        return name
    
    def _remove_titles(self, text: str) -> str:
        """Remove titles from text."""
        if not text:
            return text
        
        words = text.split()
        cleaned = []
        
        for word in words:
            # Remove periods and check against titles
            clean_word = word.rstrip(".,")
            if clean_word not in self.titles:
                cleaned.append(word)
        
        return " ".join(cleaned)
    
    def _normalize_punctuation(self, name: str) -> str:
        """Normalize punctuation in names."""
        # Remove extra spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Normalize apostrophes
        name = re.sub(r'[''`]', "'", name)
        
        # Normalize dashes
        name = re.sub(r'[-—–]', '-', name)
        
        # Ensure space after comma
        name = re.sub(r',(?! )', ', ', name)
        
        # Remove trailing punctuation
        name = re.sub(r'[,;:]$', '', name)
        
        return name.strip()
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with G1-specific data."""
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not canonical:
            return
        
        # Extract components
        components = self._extract_components(canonical)
        
        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        
        entry["RegionalExtras"].update(components)
        
        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []
        
        # Add ASCII variant (remove accents)
        ascii_variant = self._generate_ascii_variant(canonical)
        if ascii_variant != canonical:
            entry["Variants"]["Synthesised"].append({
                "str": ascii_variant,
                "type": "ascii-lossy"
            })
        
        # Add shortened surname variant (first surname only)
        if components.get("compound_surname"):
            short_surname = self._generate_short_surname_variant(canonical, components)
            if short_surname and short_surname != canonical:
                entry["Variants"]["Synthesised"].append({
                    "str": short_surname,
                    "type": "short-surname"
                })
        
        # Add variant with particles normalized
        if components.get("particles"):
            normalized_particles = self._normalize_particles_variant(canonical, components)
            if normalized_particles != canonical:
                entry["Variants"]["Synthesised"].append({
                    "str": normalized_particles,
                    "type": "normalized-particles"
                })
    
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}
        
        # Handle "Family, Given" format
        if "," in name:
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
            components["original_order"] = "Family, Given"
        else:
            # Handle "Given Family" format
            words = name.split()
            
            # Try to identify where given names end and family names begin
            # Look for particles or typical patterns
            given_words = []
            family_words = []
            
            # Simple heuristic: last 1-2 words are surnames
            if len(words) >= 2:
                # Check for compound surnames (usually last 2 words)
                if len(words) >= 3 and self._looks_like_compound_surname(words[-2:]):
                    given_words = words[:-2]
                    family_words = words[-2:]
                    components["compound_surname"] = True
                else:
                    # Single surname
                    given_words = words[:-1]
                    family_words = words[-1:]
            else:
                # Single word - assume it's a surname
                family_words = words
            
            given = " ".join(given_words)
            family = " ".join(family_words)
            components["original_order"] = "Given Family"
        
        components["given_name"] = given
        components["family_name"] = family
        
        # Extract particles from family name
        if family:
            family_parts = family.split()
            particles_found = []
            main_surnames = []
            
            for word in family_parts:
                if word.lower() in self.particles:
                    particles_found.append(word)
                else:
                    main_surnames.append(word)
            
            if particles_found:
                components["particles"] = particles_found
                components["main_surnames"] = main_surnames
        
        # Extract multiple given names
        if given:
            given_parts = given.split()
            if len(given_parts) > 1:
                components["first_name"] = given_parts[0]
                components["middle_names"] = given_parts[1:]
                components["multiple_given_names"] = True
        
        # Check for patronymic patterns
        if family:
            for pattern, meaning in self.name_patterns.items():
                if family.lower().endswith(pattern):
                    components["patronymic_pattern"] = pattern
                    components["patronymic_meaning"] = meaning
                    break
        
        return components
    
    def _looks_like_compound_surname(self, words: List[str]) -> bool:
        """Check if word pair looks like a compound surname."""
        # Look for patterns like "García López", "de Silva", etc.
        if len(words) != 2:
            return False
        
        # Check if first word is a particle
        if words[0].lower() in self.particles:
            return True
        
        # Check if both words are capitalized (typical for surnames)
        if all(word[0].isupper() for word in words):
            return True
        
        return False
    
    def _generate_ascii_variant(self, name: str) -> str:
        """Generate ASCII variant without accents."""
        # Remove accents using Unicode normalization
        ascii_name = unicodedata.normalize('NFD', name)
        ascii_name = ascii_name.encode('ascii', 'ignore').decode('ascii')
        return ascii_name
    
    def _generate_short_surname_variant(self, name: str, components: Dict[str, Any]) -> Optional[str]:
        """Generate variant with only first surname."""
        given = components.get("given_name", "")
        family = components.get("family_name", "")
        
        if not given or not family:
            return None
        
        # Extract first surname
        family_parts = family.split()
        if len(family_parts) > 1:
            # Skip particles and take first actual surname
            main_surnames = components.get("main_surnames", [])
            if main_surnames:
                first_surname = main_surnames[0]
                return f"{given} {first_surname}"
        
        return None
    
    def _normalize_particles_variant(self, name: str, components: Dict[str, Any]) -> str:
        """Generate variant with normalized particles."""
        # Normalize particle capitalization
        normalized = name
        
        # Common normalizations
        replacements = {
            " De ": " de ",
            " Del ": " del ",
            " Da ": " da ",
            " Do ": " do ",
            " Y ": " y ",
            " E ": " e ",
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to G1 rules."""
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")
        
        # Check for valid Latin characters (including accented)
        if not self._is_valid_latin_name(canonical):
            raise RegionRuleError(f"Invalid characters in name: {canonical}")
        
        # Check name structure
        if "," in canonical:
            parts = canonical.split(",")
            if len(parts) != 2:
                raise RegionRuleError(f"Invalid comma usage in name: {canonical}")
            if not parts[0].strip() or not parts[1].strip():
                raise RegionRuleError(f"Empty name component: {canonical}")
        else:
            words = canonical.split()
            if len(words) < 2:
                raise RegionRuleError(f"Name should have at least 2 words: {canonical}")
        
        # Validate components
        components = entry.get("RegionalExtras", {})
        
        # Check given name
        given = components.get("given_name", "")
        if given and not re.match(r'^[A-Za-zÀ-ÿĀ-žŀ-ſ][A-Za-zÀ-ÿĀ-žŀ-ſ.\s-]*$', given):
            raise RegionRuleError(f"Invalid given name format: {given}")
        
        # Check family name
        family = components.get("family_name", "")
        if family and not re.match(r'^[A-Za-zÀ-ÿĀ-žŀ-ſ][A-Za-zÀ-ÿĀ-žŀ-ſ.\s-]*$', family):
            raise RegionRuleError(f"Invalid family name format: {family}")
    
    def _is_valid_latin_name(self, name: str) -> bool:
        """Check if name contains valid Latin characters."""
        # Allow Latin characters including accented ones
        for char in name:
            if char.isalpha() or char in " ,-'":
                continue
            # Check if it's valid Latin (including extended)
            if not (ord(char) < 0x0250):  # Basic Latin + Latin-1 + Latin Extended
                return False
        return True
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})
        
        # Primary sort by family name
        family = components.get("family_name", "")
        given = components.get("given_name", "")
        
        # Use main surnames for sorting if available
        main_surnames = components.get("main_surnames", [])
        if main_surnames:
            # Sort by first main surname
            sort_family = main_surnames[0]
        else:
            sort_family = family
        
        # Normalize for sorting - remove accents
        sort_family = self._generate_ascii_variant(sort_family.upper())
        sort_given = self._generate_ascii_variant(given.upper())
        
        # Remove punctuation for sorting
        sort_family = re.sub(r'[^\w\s]', '', sort_family)
        sort_given = re.sub(r'[^\w\s]', '', sort_given)
        
        # Generate key
        key = f"{sort_family} {sort_given}"
        
        # Ensure determinism
        key = " ".join(key.split())
        
        return key