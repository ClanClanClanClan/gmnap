"""
D1 - Hindi Belt region implementation.

Covers: Hindi-speaking states of India (UP, MP, Bihar, Rajasthan, Haryana, Delhi, Uttarakhand, Jharkhand, Chhattisgarh).
Features: Devanagari script, patronymic patterns, caste surnames, Sanskrit influences.
Population: ~450M (12% of global mathematicians)
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from src.regions.base import RegionRuleError, RegionSpec


class D1_HindiBelt(RegionSpec):
    """
    Hindi Belt region (D1).
    
    Handles Hindi-speaking regions with complex naming patterns:
    - Devanagari and Latin scripts
    - Patronymic naming (father's name + son/daughter)
    - Traditional surnames (family/caste names)
    - Sanskrit compound names
    - Regional variations (Punjabi influences, Rajasthani patterns)
    """
    
    def __init__(self):
        super().__init__(
            code="D1",
            yaml_files=["d1_hindi_belt.yaml"],
            scripts=["Devanagari", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["IAST", "ISO 15919", "Hunterian"]
        )
        
        # Common Hindi titles and honorifics
        self.titles = {
            # Traditional titles
            "श्री", "श्रीमती", "कुमारी", "बाबू", "जी",
            # Modern titles
            "डॉ", "डॉक्टर", "प्रोफेसर", "आचार्य",
            # Religious titles
            "पंडित", "उपाध्याय", "शास्त्री", "महर्षि",
            # Latin equivalents
            "Shri", "Smt", "Kumari", "Babu", "Ji",
            "Dr", "Prof", "Acharya", "Pandit", "Upadhyay", "Shastri"
        }
        
        # Common patronymic patterns
        self.patronymic_patterns = {
            # Son of patterns
            "पुत्र", "कुमार", "सिंह", "राज", "प्रसाद", "शंकर", "दास",
            # Daughter of patterns  
            "पुत्री", "कुमारी", "देवी", "बाला", "माता",
            # Latin equivalents
            "Kumar", "Singh", "Raj", "Prasad", "Shankar", "Das",
            "Kumari", "Devi", "Bala", "Mata"
        }
        
        # Common Hindi/Sanskrit surnames by region
        self.regional_surnames = {
            # UP/Bihar patterns
            "uttar_pradesh": {
                "यादव", "गुप्ता", "शर्मा", "वर्मा", "तिवारी", "पाण्डेय", "मिश्रा",
                "Yadav", "Gupta", "Sharma", "Verma", "Tiwari", "Pandey", "Mishra"
            },
            # Rajasthani patterns
            "rajasthan": {
                "शेखावत", "राठौड़", "चौहान", "गुर्जर", "जाट", "अग्रवाल",
                "Shekhawat", "Rathore", "Chauhan", "Gurjar", "Jat", "Agarwal"
            },
            # Punjabi influences
            "punjabi_belt": {
                "सिंह", "कौर", "चौधरी", "सिद्धू", "गिल", "ढिल्लों",
                "Singh", "Kaur", "Chaudhary", "Sidhu", "Gill", "Dhillon"
            }
        }
        
        # Devanagari character patterns
        self.devanagari_range = re.compile(r'[\u0900-\u097F]+')
        self.devanagari_vowels = "अआइईउऊएऐओऔ"
        self.devanagari_consonants = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
        
    def detect_region(self, name: str, country: str = "", **context) -> float:
        """
        Detect if a name belongs to Hindi Belt region.
        
        Args:
            name: The name to analyze
            country: Country code (IN for India)
            context: Additional context (state, language, etc.)
            
        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 0.0
        
        # Strong country indicator
        if country.upper() in ["IN", "IND"]:
            confidence += 0.3
        
        # Check for Devanagari script
        if self.devanagari_range.search(name):
            confidence += 0.4
            
            # Bonus for proper Devanagari patterns
            if self._has_valid_devanagari_structure(name):
                confidence += 0.2
        
        # Check for Hindi Belt surnames
        name_parts = self._split_name(name)
        for part in name_parts:
            if self._is_hindi_belt_surname(part):
                confidence += 0.3
                break
        
        # Check for patronymic patterns
        if self._has_patronymic_pattern(name):
            confidence += 0.2
        
        # Check for Sanskrit compound patterns
        if self._has_sanskrit_compound(name):
            confidence += 0.1
        
        # Regional context boost
        state = context.get("state", "").lower()
        if state in ["up", "uttar pradesh", "bihar", "mp", "madhya pradesh", 
                    "rajasthan", "haryana", "delhi", "uttarakhand", "jharkhand", "chhattisgarh"]:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def process_name(self, canonical_name: str, **kwargs) -> Dict[str, Any]:
        """
        Process Hindi Belt name into structured components.
        
        Args:
            canonical_name: The canonical name to process
            **kwargs: Additional processing context
            
        Returns:
            Dictionary with processed name components
        """
        try:
            # Clean and normalize
            clean_name = self._clean_name(canonical_name)
            
            # Split into components
            components = self._extract_name_components(clean_name)
            
            # Generate variants
            variants = self._generate_name_variants(components)
            
            # Extract regional features
            regional_extras = self._extract_regional_features(components)
            
            return {
                "processed_name": self._reconstruct_canonical_name(components),
                "name_components": components,
                "variants": variants,
                "regional_extras": regional_extras,
                "confidence": self.detect_region(canonical_name, **kwargs)
            }
            
        except Exception as e:
            raise RegionRuleError(f"D1 processing failed: {e}")
    
    def _clean_name(self, name: str) -> str:
        """Clean and normalize Hindi name."""
        # Remove titles
        clean = name
        for title in self.titles:
            # Remove both at start and end
            clean = re.sub(rf'^{re.escape(title)}\s+', '', clean, flags=re.IGNORECASE)
            clean = re.sub(rf'\s+{re.escape(title)}$', '', clean, flags=re.IGNORECASE)
        
        # Normalize Unicode (NFC for consistency)
        clean = unicodedata.normalize('NFC', clean)
        
        # Clean extra whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        return clean
    
    def _split_name(self, name: str) -> List[str]:
        """Split name into logical components."""
        # Handle both Devanagari and Latin scripts
        parts = []
        
        # Split on whitespace and common separators
        raw_parts = re.split(r'[\s,]+', name)
        
        for part in raw_parts:
            if part.strip():
                parts.append(part.strip())
        
        return parts
    
    def _extract_name_components(self, name: str) -> Dict[str, str]:
        """Extract structured name components."""
        parts = self._split_name(name)
        
        components = {
            "given_name": "",
            "middle_name": "",
            "family_name": "",
            "patronymic": "",
            "script": "mixed" if self.devanagari_range.search(name) else "latin"
        }
        
        if len(parts) >= 2:
            # Most common pattern: Given [Middle] Family
            components["given_name"] = parts[0]
            components["family_name"] = parts[-1]
            
            if len(parts) == 3:
                components["middle_name"] = parts[1]
            elif len(parts) > 3:
                components["middle_name"] = " ".join(parts[1:-1])
            
            # Check if middle name is patronymic
            if components["middle_name"] and self._is_patronymic(components["middle_name"]):
                components["patronymic"] = components["middle_name"]
                components["middle_name"] = ""
                
        elif len(parts) == 1:
            # Mononym - common in traditional contexts
            components["given_name"] = parts[0]
        
        return components
    
    def _generate_name_variants(self, components: Dict[str, str]) -> List[Dict[str, str]]:
        """Generate name variants for search and matching."""
        variants = []
        
        given = components.get("given_name", "")
        middle = components.get("middle_name", "")
        family = components.get("family_name", "")
        patronymic = components.get("patronymic", "")
        
        # Standard formats
        if given and family:
            variants.extend([
                {"str": f"{given} {family}", "type": "standard"},
                {"str": f"{family}, {given}", "type": "reversed"},
                {"str": f"{family} {given}", "type": "family_first"}
            ])
        
        # With middle name/patronymic
        if middle:
            variants.extend([
                {"str": f"{given} {middle} {family}", "type": "full"},
                {"str": f"{family}, {given} {middle}", "type": "full_reversed"}
            ])
        
        if patronymic:
            variants.extend([
                {"str": f"{given} {patronymic} {family}", "type": "patronymic"},
                {"str": f"{given} s/o {patronymic}", "type": "son_of"}
            ])
        
        # Script variants (if mixed script)
        if components.get("script") == "mixed":
            # Generate transliteration variants
            for variant in variants[:]:  # Copy to avoid modifying during iteration
                if self.devanagari_range.search(variant["str"]):
                    # Add transliterated version
                    transliterated = self._transliterate_to_latin(variant["str"])
                    if transliterated:
                        variants.append({
                            "str": transliterated,
                            "type": variant["type"] + "_transliterated"
                        })
        
        return variants
    
    def _extract_regional_features(self, components: Dict[str, str]) -> Dict[str, Any]:
        """Extract Hindi Belt specific features."""
        features = {
            "script_type": components.get("script", "latin"),
            "patronymic_present": bool(components.get("patronymic")),
            "surname_type": "",
            "regional_markers": [],
            "caste_indicators": [],
            "language_hints": []
        }
        
        family_name = components.get("family_name", "")
        
        # Classify surname type
        if family_name:
            if family_name in self.regional_surnames["uttar_pradesh"]:
                features["surname_type"] = "brahmin_kayastha"
                features["regional_markers"].append("UP/Bihar")
            elif family_name in self.regional_surnames["rajasthan"]:
                features["surname_type"] = "rajput_marwari"
                features["regional_markers"].append("Rajasthan")
            elif family_name in self.regional_surnames["punjabi_belt"]:
                features["surname_type"] = "punjabi_influence"
                features["regional_markers"].append("Punjab_influence")
        
        # Check for Sanskrit roots
        if self._has_sanskrit_compound(components.get("given_name", "")):
            features["language_hints"].append("sanskrit_roots")
        
        return features
    
    def _has_valid_devanagari_structure(self, text: str) -> bool:
        """Check if Devanagari text has valid structure."""
        if not self.devanagari_range.search(text):
            return False
        
        # Basic validation - contains vowels and consonants
        has_vowels = any(c in text for c in self.devanagari_vowels)
        has_consonants = any(c in text for c in self.devanagari_consonants)
        
        return has_vowels and has_consonants
    
    def _is_hindi_belt_surname(self, name: str) -> bool:
        """Check if name is a common Hindi Belt surname."""
        for region_surnames in self.regional_surnames.values():
            if name in region_surnames:
                return True
        return False
    
    def _has_patronymic_pattern(self, name: str) -> bool:
        """Check for patronymic naming patterns."""
        parts = self._split_name(name)
        for part in parts:
            if part in self.patronymic_patterns:
                return True
        return False
    
    def _is_patronymic(self, name: str) -> bool:
        """Check if a name component is a patronymic."""
        return name in self.patronymic_patterns
    
    def _has_sanskrit_compound(self, name: str) -> bool:
        """Check for Sanskrit compound name patterns."""
        # Simple heuristic for Sanskrit compounds
        sanskrit_elements = {
            # Common Sanskrit roots
            "राम", "कृष्ण", "विष्णु", "शिव", "देव", "चंद्र", "सूर्य", "प्रकाश",
            "Ram", "Krishna", "Vishnu", "Shiv", "Dev", "Chandra", "Surya", "Prakash",
            "अनिल", "सुनील", "दिनेश", "राजेश", "महेश", "उमेश",
            "Anil", "Sunil", "Dinesh", "Rajesh", "Mahesh", "Umesh"
        }
        
        return any(element in name for element in sanskrit_elements)
    
    def _transliterate_to_latin(self, devanagari_text: str) -> Optional[str]:
        """Simple transliteration from Devanagari to Latin."""
        # Basic mapping for common characters
        transliteration_map = {
            'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ii', 'उ': 'u', 'ऊ': 'uu',
            'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
            'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
            'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
            'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
            'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
            'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
            'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
            'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h'
        }
        
        result = ""
        for char in devanagari_text:
            if char in transliteration_map:
                result += transliteration_map[char]
            else:
                result += char
        
        return result if result else None
    
    def _reconstruct_canonical_name(self, components: Dict[str, str]) -> str:
        """Reconstruct canonical name from components."""
        parts = []
        
        if components.get("given_name"):
            parts.append(components["given_name"])
        
        if components.get("middle_name"):
            parts.append(components["middle_name"])
        elif components.get("patronymic"):
            parts.append(components["patronymic"])
        
        if components.get("family_name"):
            parts.append(components["family_name"])
        
        return " ".join(parts)
    
    # Abstract method implementations
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to D1 Hindi Belt rules."""
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
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with D1-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return
        
        # Process name and get components
        result = self.process_name(canonical, country=entry.get("CountryCodes", [""])[0])
        
        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        
        # Add Hindi Belt specific data
        entry["RegionalExtras"].update(result.get("regional_extras", {}))
        entry["RegionalExtras"]["name_components"] = result.get("name_components", {})
        
        # Add variants if generated
        if result.get("variants"):
            if "Variants" not in entry:
                entry["Variants"] = {"Synthesised": []}
            elif "Synthesised" not in entry["Variants"]:
                entry["Variants"]["Synthesised"] = []
            
            entry["Variants"]["Synthesised"].extend(result["variants"])
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to D1 Hindi Belt rules."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")
        
        # Check for valid script combinations
        has_devanagari = self.devanagari_range.search(canonical)
        has_latin = bool(re.search(r'[a-zA-Z]', canonical))
        
        if has_devanagari and has_latin:
            # Mixed script - validate both parts are meaningful
            if not self._has_valid_devanagari_structure(canonical):
                raise RegionRuleError("Invalid Devanagari structure in mixed script name")
        
        # Check for regional appropriateness
        if entry.get("CountryCodes"):
            country = entry["CountryCodes"][0]
            if country == "IN":
                confidence = self.detect_region(canonical, country)
                if confidence < 0.3:
                    raise RegionRuleError(f"Name doesn't match Hindi Belt patterns (confidence: {confidence:.2f})")
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for Hindi names."""
        components = entry.get("RegionalExtras", {}).get("name_components", {})
        
        # Primary sort by family name, secondary by given name
        family = components.get("family_name", "")
        given = components.get("given_name", "")
        
        # For mixed scripts, transliterate Devanagari to Latin for consistent sorting
        if self.devanagari_range.search(family):
            family_key = self._transliterate_to_latin(family) or family
        else:
            family_key = family
        
        if self.devanagari_range.search(given):
            given_key = self._transliterate_to_latin(given) or given
        else:
            given_key = given
        
        # Normalize to lowercase for case-insensitive sorting
        family_key = family_key.lower()
        given_key = given_key.lower()
        
        # Create sort key: "family|given" 
        sort_key = f"{family_key}|{given_key}"
        
        # Remove diacritics for better sorting
        import unicodedata
        sort_key = ''.join(c for c in unicodedata.normalize('NFD', sort_key) 
                          if unicodedata.category(c) != 'Mn')
        
        return sort_key