"""
A3 - Nordic-Baltic region implementation.

Covers: DK, NO, SE, FI, IS, FO, AX (Nordic) + EE, LV, LT (Baltic).
Features: Icelandic patronymic system, Scandinavian particles, Baltic surname patterns,
          Latin with extensive diacritics.
"""

import re
from typing import Any, Dict, List, Optional

from ...base import RegionRuleError, RegionSpec


class A3NordicBalticProcessor(RegionSpec):
    """
    Nordic-Baltic region (A3).
    
    Handles Nordic and Baltic naming conventions:
    - Icelandic patronymic system (-dóttir, -son)
    - Scandinavian noble particles (af, av, von, zu)
    - Baltic surname endings (-as, -is, -us, -ė, -ienė)
    - Extensive use of diacritics (å, ä, ö, æ, ø, ū, č, š, ž)
    - Standard "Family, Given" order (except Iceland: often just given + patronymic)
    """
    
    def __init__(self):
        super().__init__(
            code="A3",
            yaml_files=["a3_nordic_baltic.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",  # Iceland uses patronymic
            romanisation_standards=[]
        )
        
        # Nordic/Baltic specific characters
        self.nordic_chars = set("åäöæøÅÄÖÆØáéíóúýÁÉÍÓÚÝðÐþÞ")  # Including Icelandic
        self.baltic_chars = set("ąčęėįšųūžĄČĘĖĮŠŲŪŽõÕāēīūĀĒĪŪļķņģĻĶŅĢ")  # Including Latvian
        self.allowed_chars = self.nordic_chars | self.baltic_chars
        
        # Icelandic patronymic suffixes (Rule 8)
        self.patronymic_suffixes = {
            # Male
            "son": "son",
            "sson": "son",  # Swedish variant
            "sen": "son",   # Danish/Norwegian variant
            "søn": "son",   # Danish variant
            "poika": "son", # Finnish (rare)
            # Female
            "dóttir": "daughter",
            "dotter": "daughter",  # Swedish
            "datter": "daughter",  # Norwegian
            "dottir": "daughter",  # ASCII variant
            "tytär": "daughter",   # Finnish (rare)
        }
        
        # Scandinavian noble particles
        self.scandinavian_particles = {
            "af", "av",           # Swedish/Norwegian "of"
            "von", "von der",     # German influence
            "zu",                 # German "to/at"
            "de", "de la",        # French influence
            "den",                # "the" (Norwegian/Danish)
            "der",                # "the" (German influence)
        }
        
        # Baltic surname endings
        self.baltic_male_endings = {"as", "is", "us", "ys", "ius"}
        self.baltic_female_endings = {"ė", "ienė", "ytė", "utė", "aitė", "iūtė"}
        
        # Common Nordic first names (for pattern recognition)
        self.common_nordic_first = {
            # Swedish
            "Erik", "Karl", "Johan", "Anders", "Per", "Lars", "Nils", "Olof",
            "Anna", "Maria", "Kristina", "Karin", "Eva", "Birgitta",
            # Norwegian
            "Ole", "Bjørn", "Knut", "Svein", "Arne", "Morten",
            "Ingrid", "Astrid", "Solveig", "Ragnhild",
            # Danish
            "Jens", "Peter", "Hans", "Christian", "Søren", "Niels",
            "Mette", "Anne", "Hanne", "Kirsten",
            # Icelandic
            "Magnús", "Guðmundur", "Jón", "Ólafur", "Þór", "Sigurður",
            "Guðrún", "Sigríður", "Helga", "Margrét",
            # Finnish
            "Matti", "Jukka", "Kari", "Antti", "Mikko", "Jussi",
            "Marja", "Anneli", "Päivi", "Ritva",
            # Estonian
            "Toomas", "Andres", "Mart", "Jaan", "Peeter",
            "Mari", "Kadri", "Piret", "Tiina",
            # Latvian
            "Jānis", "Andris", "Mārtiņš", "Juris", "Pēteris",
            "Inese", "Liga", "Dace", "Ilze",
            # Lithuanian
            "Jonas", "Petras", "Antanas", "Juozas", "Kazys",
            "Ona", "Marija", "Janina", "Elena"
        }
        
        # Common Baltic surnames (for pattern recognition)
        self.common_baltic_surnames = {
            # Lithuanian
            "Kazlauskas", "Petrauskas", "Stankevičius", "Jankauskas", "Žukauskas",
            # Latvian  
            "Bērziņš", "Kalniņš", "Ozoliņš", "Liepiņš", "Vilks",
            # Estonian
            "Tamm", "Saar", "Mägi", "Kask", "Kukk"
        }
        
        # Common titles
        self.titles = {
            "Dr", "Dr.", "Prof", "Prof.", "Professor",
            "Hr", "Hr.", "Fru", "Frk", "Frk.",  # Scandinavian
            "Härra", "Proua", "Preili",         # Estonian
            "Ponas", "Ponia", "Panelė",         # Lithuanian
            "Kungs", "Kundze", "Jaunkundze"     # Latvian
        }
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to A3 rules."""
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
        # Input validation - ensure it's a string
        if not isinstance(name, str):
            raise RegionRuleError(f"Name must be string, not {type(name).__name__}")
        
        if not name:
            return name
        
        # Security: filter out dangerous control characters (except safe whitespace)
        if any(ord(c) < 32 and c not in '\t\n\r ' for c in name):
            raise RegionRuleError("Name contains dangerous control characters")
        
        # Remove titles
        name = self._remove_titles(name)
        
        # Normalize whitespace
        name = " ".join(name.split())
        
        # Normalize punctuation (but preserve hyphens in names like "Anna-Liisa")
        name = re.sub(r'\s*,\s*', ', ', name)
        
        return name.strip()
    
    def _remove_titles(self, text: str) -> str:
        """Remove titles from beginning of name."""
        if not text:
            return text
        
        words = text.split()
        while words and words[0] in self.titles:
            words.pop(0)
        
        return " ".join(words)
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with A3-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return
        
        # Extract components
        components = self._extract_components(canonical)
        
        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        
        entry["RegionalExtras"].update(components)
        
        # Rule 8: Icelandic Patronymic – FamilyNameType=patronymic; excluded from collisions
        if components.get("is_patronymic"):
            entry["FamilyNameType"] = "patronymic"
            # Store additional patronymic metadata for V7 compliance
            entry["RegionalExtras"]["patronymic_excluded_from_collisions"] = True
            entry["RegionalExtras"]["patronymic_cultural_context"] = "icelandic"
        
        # Generate synthesized variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []
        
        # Add ASCII variant
        ascii_variant = self._generate_ascii_variant(canonical)
        if ascii_variant != canonical:
            entry["Variants"]["Synthesised"].append({
                "str": ascii_variant,
                "type": "ascii-lossy"
            })
        
        # Add particle-drop variant for nobles
        if components.get("particle"):
            particle_drop = self._generate_particle_drop_variant(canonical, components)
            if particle_drop and particle_drop != canonical:
                entry["Variants"]["Synthesised"].append({
                    "str": particle_drop,
                    "type": "particle-drop"
                })
    
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components with Nordic-Baltic specific handling."""
        components = {}
        
        # Check if it's Icelandic patronymic format
        is_icelandic_pattern = self._detect_icelandic_pattern(name)
        
        if "," in name:
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Handle different formats
            if is_icelandic_pattern:
                # Icelandic often uses "Given Patronymic" without comma
                words = name.split()
                if len(words) >= 2:
                    # Check if last word is patronymic
                    last_word = words[-1]
                    if self._is_patronymic(last_word):
                        given = " ".join(words[:-1])
                        family = last_word
                        components["is_patronymic"] = True
                    else:
                        given = " ".join(words[:-1])
                        family = words[-1]
                else:
                    given = ""
                    family = name
            else:
                # Standard "Given Family" format
                words = name.split()
                if len(words) >= 2:
                    given = " ".join(words[:-1])
                    family = words[-1]
                else:
                    given = ""
                    family = name
        
        components["family_name"] = family
        components["given_name"] = given
        
        # Check for patronymic
        if self._is_patronymic(family):
            components["is_patronymic"] = True
            # Extract the root name
            for suffix, meaning in self.patronymic_suffixes.items():
                if family.endswith(suffix):
                    components["patronymic_root"] = family[:-len(suffix)]
                    components["patronymic_type"] = meaning
                    break
        
        # Check for particles in family name
        family_words = family.split()
        if len(family_words) > 1:
            particles_found = []
            main_surname = []
            
            for word in family_words:
                if word.lower() in self.scandinavian_particles:
                    particles_found.append(word)
                else:
                    main_surname.append(word)
            
            if particles_found:
                components["particle"] = " ".join(particles_found)
                components["main_surname"] = " ".join(main_surname)
        
        # Check for Baltic gendered endings
        if self._has_baltic_ending(family):
            # Check endings in order of length (longest first) to avoid substring matches
            for ending in sorted(self.baltic_female_endings, key=len, reverse=True):
                if family.endswith(ending):
                    components["gender_inflected"] = True
                    components["gender"] = "female"
                    # Also store the male form
                    if ending == "ienė":
                        components["male_form"] = family[:-4] + "is"
                    elif ending in ["ytė", "utė", "aitė", "iūtė"]:
                        components["male_form"] = family[:-3] + "us"
                    break
        
        return components
    
    def _detect_icelandic_pattern(self, name: str) -> bool:
        """Detect if name follows Icelandic pattern."""
        words = name.split()
        if not words:
            return False
        
        # Check if last word is patronymic
        if self._is_patronymic(words[-1]):
            return True
        
        # Check if any word is a common Icelandic first name
        icelandic_names = {"Magnús", "Guðmundur", "Jón", "Ólafur", "Þór", 
                          "Sigurður", "Guðrún", "Sigríður", "Helga", "Margrét"}
        return any(word in icelandic_names for word in words)
    
    def _is_patronymic(self, name: str) -> bool:
        """Check if name is a patronymic."""
        name_lower = name.lower()
        
        # Check for Icelandic-specific endings first (more reliable)
        icelandic_endings = ["dóttir", "dottir", "datter"]
        if any(name_lower.endswith(ending) for ending in icelandic_endings):
            return True
        
        # For -son/-sen endings, be more strict to avoid false positives
        if name_lower.endswith("son") or name_lower.endswith("sen"):
            # Common non-patronymic surnames (false positives)
            common_surnames = ["johnson", "jackson", "wilson", "anderson", "andersen", 
                             "thompson", "olsen", "jensen", "larsen", "nielsen"]
            if name_lower in common_surnames:
                return False
            
            # If it contains Icelandic characters, likely patronymic
            if any(c in name for c in "áéíóúýþðæöÁÉÍÓÚÝÞÐÆÖ"):
                return True
            
            # If it starts with typical Icelandic/Nordic given name roots
            icelandic_roots = ["magnús", "guðmund", "ólaf", "sigurð", "björn", "erik"]
            name_root = name_lower[:-3]  # Remove -son
            if any(name_root.startswith(root) for root in icelandic_roots):
                return True
            
            # Default to false for ambiguous cases
            return False
        
        return any(name_lower.endswith(suffix) for suffix in self.patronymic_suffixes.keys())
    
    def _has_baltic_ending(self, name: str) -> bool:
        """Check if name has Baltic gendered ending."""
        return (any(name.endswith(ending) for ending in self.baltic_male_endings) or
                any(name.endswith(ending) for ending in self.baltic_female_endings))
    
    def _generate_ascii_variant(self, name: str) -> str:
        """Generate ASCII variant with proper substitutions."""
        # Nordic/Baltic specific character mappings
        replacements = {
            'å': 'a', 'Å': 'A',
            'ä': 'a', 'Ä': 'A',  # Swedish/Finnish
            'ö': 'o', 'Ö': 'O',  # Swedish/Finnish
            'æ': 'ae', 'Æ': 'AE',  # Danish/Norwegian/Icelandic
            'ø': 'o', 'Ø': 'O',    # Danish/Norwegian
            'ð': 'd', 'Ð': 'D',    # Icelandic eth
            'þ': 'th', 'Þ': 'TH',  # Icelandic thorn
            'õ': 'o', 'Õ': 'O',    # Estonian
            'ü': 'u', 'Ü': 'U',    # Estonian/German influence
            'ą': 'a', 'Ą': 'A',    # Lithuanian
            'č': 'c', 'Č': 'C',    # Baltic
            'ę': 'e', 'Ę': 'E',    # Lithuanian
            'ė': 'e', 'Ė': 'E',    # Lithuanian
            'į': 'i', 'Į': 'I',    # Lithuanian
            'š': 's', 'Š': 'S',    # Baltic
            'ų': 'u', 'Ų': 'U',    # Lithuanian
            'ū': 'u', 'Ū': 'U',    # Baltic
            'ž': 'z', 'Ž': 'Z',    # Baltic
            'ņ': 'n', 'Ņ': 'N',    # Latvian
            'ļ': 'l', 'Ļ': 'L',    # Latvian
            'ķ': 'k', 'Ķ': 'K',    # Latvian
            'ģ': 'g', 'Ģ': 'G',    # Latvian
        }
        
        result = name
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)
        
        # Final ASCII normalization
        import unicodedata
        result = unicodedata.normalize('NFKD', result)
        result = result.encode('ascii', 'ignore').decode('ascii')
        
        return result
    
    def _generate_particle_drop_variant(self, name: str, components: Dict[str, Any]) -> Optional[str]:
        """Generate variant without noble particle."""
        particle = components.get("particle")
        if not particle:
            return None
        
        main_surname = components.get("main_surname", "")
        given = components.get("given_name", "")
        
        if main_surname and given:
            return f"{main_surname}, {given}"
        elif main_surname:
            return main_surname
        
        return None
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to A3 rules."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")
        
        # Check for valid characters
        if not self._is_valid_nordic_baltic_name(canonical):
            invalid_chars = set(canonical) - set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ,.-'") - self.allowed_chars
            if invalid_chars:
                raise RegionRuleError(f"Invalid characters in name: {invalid_chars}")
        
        # Validate structure
        components = entry.get("RegionalExtras", {})
        
        # Special validation for Icelandic patronymics
        if components.get("is_patronymic"):
            family = components.get("family_name", "")
            if not self._is_patronymic(family):
                raise RegionRuleError(f"Marked as patronymic but doesn't match pattern: {family}")
            
            # Excluded from surname collision stats (Rule 8)
            if "FamilyNameType" not in entry:
                raise RegionRuleError("Patronymic must have FamilyNameType set")
        
        # Validate Baltic gendered endings consistency
        if components.get("gender_inflected"):
            family = components.get("family_name", "")
            gender = components.get("gender")
            
            if gender == "female" and not any(family.endswith(e) for e in self.baltic_female_endings):
                raise RegionRuleError(f"Gender mismatch: marked female but no female ending: {family}")
    
    def _is_valid_nordic_baltic_name(self, name: str) -> bool:
        """Check if name contains valid Nordic-Baltic characters."""
        # Allow basic Latin, Nordic/Baltic special characters, numbers, and common punctuation
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ,.-'")
        allowed.update(self.allowed_chars)
        allowed.update("ðÐþÞ")  # Icelandic special
        
        return all(c in allowed for c in name)
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})
        
        # Get family and given names
        family = components.get("family_name", "")
        given = components.get("given_name", "")
        
        # Special handling for patronymics (Rule 8)
        if components.get("is_patronymic"):
            # Sort by given name primarily for Icelandic names
            # This is cultural - Icelandic phone books sort by first name
            sort_key = f"{given} {family}"
        else:
            # Standard family, given sorting
            # Use main surname if particle exists
            main_surname = components.get("main_surname", family)
            sort_key = f"{main_surname}, {given}"
        
        # Convert to sort form - handle Nordic/Baltic characters
        sort_key = self._normalize_for_sorting(sort_key)
        
        # Ensure determinism
        return " ".join(sort_key.split()).upper()
    
    def _normalize_for_sorting(self, text: str) -> str:
        """Normalize text for sorting with Nordic-Baltic rules."""
        # In Nordic countries, å/Å sorts after z
        # ä/Ä and ö/Ö also sort after z in Swedish/Finnish
        # æ/Æ, ø/Ø, å/Å sort after z in Danish/Norwegian
        
        # For simplicity, we'll use a mapping approach
        # This ensures consistent sorting across the region
        replacements = {
            'å': 'zzza', 'Å': 'ZZZA',  # After Z
            'ä': 'zzzb', 'Ä': 'ZZZB',  # After å
            'ö': 'zzzc', 'Ö': 'ZZZC',  # After ä
            'æ': 'zzzd', 'Æ': 'ZZZD',  # After ö
            'ø': 'zzze', 'Ø': 'ZZZE',  # After æ
            # Baltic characters sort normally within their alphabets
            'č': 'cz', 'Č': 'CZ',
            'š': 'sz', 'Š': 'SZ', 
            'ž': 'zz', 'Ž': 'ZZ',
        }
        
        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)
        
        # Remove punctuation for sorting
        result = re.sub(r'[^\w\s]', '', result)
        
        return result