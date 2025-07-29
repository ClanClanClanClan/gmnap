"""
A2 - Western Europe region implementation.

Covers: France, Germany, Italy, Spain, Portugal, Netherlands, Belgium, 
Switzerland, Austria, Luxembourg, Liechtenstein, San Marino, Monaco, 
Gibraltar, Andorra, Malta, Vatican City.

Features: Latin script with diacritics, Iberian dual surnames, 
de/von/van particles, diverse naming conventions.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

from gmnap.regions.base import RegionRuleError, RegionSpec


class A2_WesternEurope(RegionSpec):
    """
    Western Europe region (A2).
    
    Handles Western European naming conventions including:
    - Latin script with diacritics (á, é, í, ó, ú, ñ, ç, etc.)
    - Iberian dual surnames (paternal + maternal)
    - Germanic particles (de, von, van, der, den, etc.)
    - French particles (de, du, des, le, la, etc.)
    - Italian particles (di, da, del, della, etc.)
    - Portuguese/Spanish compound names
    """
    
    def __init__(self):
        super().__init__(
            code="A2",
            yaml_files=["a2_western_europe.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["Latin script with diacritics"]
        )
        
        # Germanic particles
        self.germanic_particles = {
            'von', 'van', 'der', 'den', 'de', 'het', 'ten', 'ter', 'te',
            'zum', 'zur', 'am', 'im', 'zu', 'auf', 'unter'
        }
        
        # Romance particles
        self.romance_particles = {
            'de', 'del', 'della', 'delle', 'dello', 'di', 'da', 'dal', 'dalla',
            'du', 'des', 'le', 'la', 'les', 'dos', 'das', 'do', 'da'
        }
        
        # All particles combined
        self.particles = self.germanic_particles | self.romance_particles
        
        # Common Western European name patterns
        self.name_patterns = {
            'spanish_dual': re.compile(r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?$'),
            'portuguese_compound': re.compile(r'^([A-ZÁÉÍÓÚÀÂÃÇÊÑ][a-záéíóúàâãçêñ]+(?:\s+[a-záéíóúàâãçê]+)*)\s+([A-ZÁÉÍÓÚÀÂÃÇÊÑ][a-záéíóúàâãçêñ]+)(?:\s+([A-ZÁÉÍÓÚÀÂÃÇÊÑ][a-záéíóúàâãçêñ]+))?$'),
            'french_particle': re.compile(r'^([A-ZÁÉÈÊËÍÎÏÓÔÖÚÙÛÜŸÑÇ][a-záéèêëíîïóôöúùûüÿñç]+)\s+(de|du|des|le|la|les)\s+([A-ZÁÉÈÊËÍÎÏÓÔÖÚÙÛÜŸÑÇ][a-záéèêëíîïóôöúùûüÿñç]+)$'),
            'german_particle': re.compile(r'^([A-ZÄÖÜß][a-zäöüß]+)\s+(von|van|der|den|de|het|ten|ter|te|zum|zur|am|im|zu|auf|unter)\s+([A-ZÄÖÜß][a-zäöüß]+)$'),
            'italian_particle': re.compile(r'^([A-ZÁÉÍÓÚ][a-záéíóú]+)\s+(di|da|del|della|delle|dello|dal|dalla)\s+([A-ZÁÉÍÓÚ][a-záéíóú]+)$')
        }
        
        # Diacritic patterns for validation
        self.diacritic_chars = set('áàâäéèêëíìîïóòôöúùûüñçåæøÁÀÂÄÉÈÊËÍÌÎÏÓÒÔÖÚÙÛÜÑÇÅÆØ')
        
        # Country-specific validation patterns
        self.country_patterns = {
            'ES': {'required_chars': 'ñáéíóúü', 'dual_surname': True},
            'PT': {'required_chars': 'ãàâáçéêíóôõúü', 'dual_surname': True},
            'FR': {'required_chars': 'àâäéèêëïîôöùûüÿç', 'particles': {'de', 'du', 'des', 'le', 'la', 'les'}},
            'DE': {'required_chars': 'äöüß', 'particles': {'von', 'van', 'der', 'den', 'de', 'zum', 'zur', 'am', 'im', 'zu'}},
            'IT': {'required_chars': 'àáéèíìîóòúù', 'particles': {'di', 'da', 'del', 'della', 'delle', 'dello'}},
            'NL': {'required_chars': 'áéíóúàèëïöü', 'particles': {'van', 'der', 'den', 'de', 'het', 'ten', 'ter', 'te'}}
        }
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean Western European names according to regional conventions.
        
        - Remove titles and honorifics
        - Normalize diacritics and spacing
        - Handle particles correctly
        - Preserve dual surnames where appropriate
        """
        canonical = entry.get('CanonicalLatin', '')
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin field")
        
        # Remove common titles and honorifics
        titles_pattern = re.compile(r'\b(Dr\.?|Prof\.?|Sir|Dame|Lord|Lady|Baron|Count|Comte|Duc|Herzog|Fürst|Don|Doña|Dom|Dona)\s+', re.IGNORECASE)
        cleaned = titles_pattern.sub('', canonical)
        
        # Remove degrees and suffixes
        degrees_pattern = re.compile(r'\s+\b(Ph\.?D\.?|M\.?D\.?|Jr\.?|Sr\.?|III?|IV|V)\b', re.IGNORECASE)
        cleaned = degrees_pattern.sub('', cleaned)
        
        # Normalize Unicode (NFC form for consistent diacritics)
        cleaned = unicodedata.normalize('NFC', cleaned)
        
        # Clean up spacing around particles
        for particle in self.particles:
            # Fix spacing around particles
            pattern = re.compile(rf'\s+\b{re.escape(particle)}\s+', re.IGNORECASE)
            cleaned = pattern.sub(f' {particle} ', cleaned)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        entry['CanonicalLatin'] = cleaned
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment Western European names with regional variants and metadata.
        
        - Generate ASCII variants without diacritics
        - Extract particles and handle them properly
        - Create order variants for dual surnames
        - Add country-specific variants
        """
        canonical = entry.get('CanonicalLatin', '')
        if not canonical:
            return
        
        # Initialize variants if not present
        if 'VariantsSynthesised' not in entry:
            entry['VariantsSynthesised'] = []
        
        variants = entry['VariantsSynthesised']
        
        # Generate ASCII variant (diacritic removal)
        ascii_variant = self._remove_diacritics(canonical)
        if ascii_variant != canonical:
            variants.append({
                'str': ascii_variant,
                'type': 'ascii-lossy'
            })
        
        # Extract and handle particles
        particles_found = self._extract_particles(canonical)
        if particles_found:
            entry['Particles'] = particles_found
            
            # Generate particle-drop variant
            no_particles = self._remove_particles(canonical)
            if no_particles != canonical:
                variants.append({
                    'str': no_particles,
                    'type': 'particle-drop'
                })
        
        # Handle dual surnames (Iberian pattern)
        if self._is_dual_surname_pattern(canonical):
            # Generate single surname variants
            single_surname_variants = self._generate_single_surname_variants(canonical)
            for variant in single_surname_variants:
                variants.append({
                    'str': variant,
                    'type': 'order-swap'
                })
        
        # Generate order swap (Given Family)
        if ', ' in canonical:
            family, given = canonical.split(', ', 1)
            swapped = f"{given} {family}"
            variants.append({
                'str': swapped,
                'type': 'order-swap'
            })
        
        # Add regional metadata
        entry['RegionCode'] = 'A2'
        entry['RegionFeatures'] = {
            'has_diacritics': self._has_diacritics(canonical),
            'has_particles': bool(particles_found),
            'is_dual_surname': self._is_dual_surname_pattern(canonical),
            'estimated_country': self._estimate_country(canonical)
        }
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate Western European names according to regional rules.
        
        - Check for valid Latin script with diacritics
        - Validate name structure and format
        - Ensure proper handling of particles
        - Check for regional consistency
        """
        canonical = entry.get('CanonicalLatin', '')
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin field")
        
        # Check for invalid whitespace characters
        if any(c in canonical for c in "\n\r\t\xa0"):
            raise RegionRuleError(f"Invalid whitespace characters in name: {canonical}")
        
        # Check basic format (Family, Given or Given Family)
        if not (', ' in canonical or ' ' in canonical):
            raise RegionRuleError("Invalid name format: must contain family and given names")
        
        # Validate character set (Latin script + diacritics)
        valid_chars = set()
        valid_chars.update('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        valid_chars.update(self.diacritic_chars)
        valid_chars.update(' ,-\'.')
        
        invalid_chars = set(canonical) - valid_chars
        if invalid_chars:
            raise RegionRuleError(f"Invalid characters in name: {', '.join(invalid_chars)}")
        
        # Check for overly long names (likely errors)
        if len(canonical) > 100:
            raise RegionRuleError("Name too long (>100 characters)")
        
        # Validate particle usage
        particles_in_name = self._extract_particles(canonical)
        for particle in particles_in_name:
            if particle.lower() not in self.particles:
                self.logger.warning(f"Unknown particle '{particle}' in name: {canonical}")
        
        # Check for consistent diacritic usage
        if self._has_inconsistent_diacritics(canonical):
            self.logger.warning(f"Inconsistent diacritic usage in name: {canonical}")
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate sort key for Western European names.
        
        - Sort by family name first
        - Handle particles correctly in sorting
        - Ignore diacritics for sorting purposes
        """
        canonical = entry.get('CanonicalLatin', '')
        if not canonical:
            return ''
        
        # Extract family and given names
        if ', ' in canonical:
            family, given = canonical.split(', ', 1)
        else:
            # Assume last word is family name
            parts = canonical.split()
            if len(parts) >= 2:
                family = parts[-1]
                given = ' '.join(parts[:-1])
            else:
                family = canonical
                given = ''
        
        # Remove particles from family name for sorting
        family_for_sort = self._remove_particles(family)
        
        # Remove diacritics for consistent sorting
        family_sort = self._remove_diacritics(family_for_sort).upper()
        given_sort = self._remove_diacritics(given).upper()
        
        return f"{family_sort}, {given_sort}"
    
    def _remove_diacritics(self, text: str) -> str:
        """Remove diacritics from text, keeping base letters."""
        # Decompose characters and remove combining marks
        normalized = unicodedata.normalize('NFD', text)
        ascii_text = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return ascii_text
    
    def _extract_particles(self, name: str) -> List[str]:
        """Extract particles from name."""
        words = name.split()
        particles_found = []
        
        for word in words:
            if word.lower().rstrip(',') in self.particles:
                particles_found.append(word.rstrip(','))
        
        return particles_found
    
    def _remove_particles(self, name: str) -> str:
        """Remove particles from name."""
        words = name.split()
        filtered_words = []
        
        for word in words:
            if word.lower().rstrip(',') not in self.particles:
                filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    def _has_diacritics(self, text: str) -> bool:
        """Check if text contains diacritical marks."""
        return any(c in self.diacritic_chars for c in text)
    
    def _is_dual_surname_pattern(self, name: str) -> bool:
        """Check if name follows Iberian dual surname pattern."""
        # Simple heuristic: if in "Family, Given" format and family has 2+ parts
        if ', ' in name:
            family, _ = name.split(', ', 1)
            family_parts = family.split()
            return len(family_parts) >= 2
        return False
    
    def _generate_single_surname_variants(self, name: str) -> List[str]:
        """Generate variants with single surname from dual surname."""
        if not ', ' in name:
            return []
        
        family, given = name.split(', ', 1)
        family_parts = family.split()
        
        if len(family_parts) < 2:
            return []
        
        variants = []
        # First surname only
        variants.append(f"{family_parts[0]}, {given}")
        # Last surname only  
        variants.append(f"{family_parts[-1]}, {given}")
        
        return variants
    
    def _estimate_country(self, name: str) -> Optional[str]:
        """Estimate likely country based on name characteristics."""
        name_lower = name.lower()
        
        # Spanish indicators
        if any(c in name_lower for c in 'ñáéíóúü') and self._is_dual_surname_pattern(name):
            return 'ES'
        
        # Portuguese indicators
        if any(c in name_lower for c in 'ãàâáçéêíóôõúü') and self._is_dual_surname_pattern(name):
            return 'PT'
        
        # French indicators
        if any(c in name_lower for c in 'àâäéèêëïîôöùûüÿç') or any(p in name_lower for p in ['de ', 'du ', 'des ', 'le ', 'la ']):
            return 'FR'
        
        # German indicators
        if any(c in name_lower for c in 'äöüß') or any(p in name_lower for p in ['von ', 'van ', 'der ', 'den ']):
            return 'DE'
        
        # Italian indicators
        if any(p in name_lower for p in ['di ', 'da ', 'del ', 'della ']) or any(c in name_lower for c in 'àáéèíìîóòúù'):
            return 'IT'
        
        # Dutch indicators
        if any(p in name_lower for p in ['van ', 'der ', 'den ', 'de ', 'het ', 'ten ', 'ter ', 'te ']):
            return 'NL'
        
        return None
    
    def _has_inconsistent_diacritics(self, name: str) -> bool:
        """Check for inconsistent use of diacritics (basic heuristic)."""
        # This is a simple check - could be enhanced with more sophisticated rules
        ascii_version = self._remove_diacritics(name)
        return len(name) != len(ascii_version) and not self._has_diacritics(name)