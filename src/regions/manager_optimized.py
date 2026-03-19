"""
Optimized Region detection and management for GMNAP.
Performance improvements:
1. Singleton pattern for FastText model loading
2. Lazy loading of regions only when needed
3. Cache region detection results
4. Only load regions that are actually implemented
"""

import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache

try:
    import fasttext
except ImportError:
    fasttext = None  # type: ignore[assignment]

from src.core.unicode_handler import UnicodeNormalizer
from .base import (REGION_CODES, TERRITORY_TO_REGION,
                              RegionRuleError, RegionSpec,
                              get_region_for_territory)

logger = logging.getLogger(__name__)

# Region overlay map from spec §2a — sub-national/contextual overrides
# These override the standard TERRITORY_TO_REGION mapping for specific contexts
_REGION_OVERLAY_MAP = {
    "CH-FR": "A2",     # French-speaking Switzerland → Western Europe
    "RU-NC": "C9",     # North Caucasus Russia → Caucasus-Turkic
    "AZ-IR": "C9",     # Iranian Azerbaijan → Caucasus-Turkic
    "IN-HN": "D1",     # Hindi Belt India → South Asia Hindi
    "IN-SOUTH": "D2",  # Southern India → South Asia Dravidian
    "IN-WB": "D3",     # West Bengal India → South Asia Bengali
    "LK-TA": "D2",     # Tamil Sri Lanka → South Asia Dravidian
    "LK-SI": "D5",     # Sinhala Sri Lanka → Sinhala
    "TR-TRP": "D3",    # Tripura (Turkey context) → Bengali
    "AS-ASM": "D3",    # Assam → Bengali
}


# Singleton for FastText model to prevent multiple loads
_fasttext_model = None
_fasttext_load_attempted = False


def get_fasttext_model(config_dir: Path = Path("./config")):
    """Get or load the FastText model (singleton pattern)."""
    global _fasttext_model, _fasttext_load_attempted
    
    if _fasttext_model is not None:
        return _fasttext_model
        
    if _fasttext_load_attempted:
        # Already tried and failed, don't try again
        return None
    
    _fasttext_load_attempted = True
    
    try:
        # Try config directory first
        model_path = config_dir / "lid.176.bin"
        
        # Fallback to global cache directory for tests
        if not model_path.exists():
            global_model_path = Path("cache/config/lid.176.bin")
            if global_model_path.exists():
                model_path = global_model_path
        
        if model_path.exists() and fasttext is not None:
            _fasttext_model = fasttext.load_model(str(model_path))
            logger.info(f"Loaded FastText language detector from {model_path}")
            return _fasttext_model
        else:
            logger.warning(f"FastText model not found at {model_path}")
            return None
    except Exception as e:
        logger.error(f"Failed to load language detector: {e}")
        return None


@dataclass
class RegionDetectionResult:
    """Result of region detection."""
    region_code: str
    confidence: float
    detection_method: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RegionManager:
    """
    Optimized region detection and routing manager.
    
    Key optimizations:
    1. Singleton FastText model loading
    2. Lazy region loading
    3. Detection result caching
    4. Only load actually implemented regions
    """
    
    # List of actually implemented regions (not just architecturally defined)
    IMPLEMENTED_REGIONS = {
        # A Groups - Western sphere
        "A1", "A2", "A3", "A4", "A5",
        # B Groups - Slavic/Central Europe
        "B1", "B2", "B3",
        # C Groups - Middle East/Caucasus
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9",
        # D Groups - South Asia
        "D1", "D2", "D3", "D4", "D5",
        # E Groups - East Asia
        "E1", "E2", "E3", "E4", "E5", "E6", "E7",
        # F Groups - Sub-Saharan Africa
        "F1", "F2", "F3", "F4",
        # G Groups - Latin America
        "G1",
        # Special
        "H1", "R0", "Z0",
    }
    
    def __init__(self, config_dir: Path = Path("./config")):
        self.config_dir = config_dir
        self._regions: Dict[str, RegionSpec] = {}
        self._unicode_normalizer = UnicodeNormalizer()
        self._lang_detector = None
        self._diaspora_config = {}
        self._doi_prefix_map = {}
        self._regions_loaded = False
        self._detection_cache = {}  # Cache detection results
        self._initialize_core()
    
    def _initialize_core(self):
        """Initialize only core components (not regions)."""
        # Get shared FastText model
        self._lang_detector = get_fasttext_model(self.config_dir)
        
        # Load diaspora configuration
        self._load_diaspora_config()
        
        # Load DOI prefix mappings
        self._load_doi_prefix_map()
        
        # Initialize script to region mappings (only implemented regions)
        self._init_script_mappings()
        
        # Initialize surname pattern databases
        self._init_surname_patterns()
    
    def _load_diaspora_config(self):
        """Load diaspora overlay configuration."""
        diaspora_path = self.config_dir / "diaspora.yaml"
        if diaspora_path.exists():
            import yaml
            with open(diaspora_path) as f:
                self._diaspora_config = yaml.safe_load(f) or {}
            logger.info(f"Loaded diaspora config with {len(self._diaspora_config)} entries")
    
    def _load_doi_prefix_map(self):
        """Load DOI prefix to country mappings."""
        # Common DOI prefixes and their associated countries
        self._doi_prefix_map = {
            "10.1007": "DE",  # Springer (Germany)
            "10.1016": "NL",  # Elsevier (Netherlands)
            "10.1038": "GB",  # Nature (UK)
            "10.1126": "US",  # Science (USA)
            "10.1002": "US",  # Wiley (USA)
            "10.1021": "US",  # ACS (USA)
            "10.1088": "GB",  # IOP (UK)
            "10.1103": "US",  # APS (USA)
            "10.1109": "US",  # IEEE (USA)
            "10.1145": "US",  # ACM (USA)
            "10.1137": "US",  # SIAM (USA)
            "10.1090": "US",  # AMS (USA)
            "10.1063": "US",  # AIP (USA)
            "10.1093": "GB",  # Oxford (UK)
            "10.1017": "GB",  # Cambridge (UK)
            "10.3390": "CH",  # MDPI (Switzerland)
            "10.1080": "GB",  # Taylor & Francis (UK)
            "10.1111": "GB",  # Blackwell (UK)
            "10.1155": "US",  # Hindawi (USA/Egypt)
            "10.1371": "US",  # PLOS (USA)
            "10.4171": "CH",  # EMS (Switzerland)
        }
    
    def _init_script_mappings(self):
        """Initialize Unicode script to region mappings (only implemented regions)."""
        # Only map to regions that are actually implemented
        self._script_to_regions = {
            "Latin": [r for r in ["A1", "A2", "A3", "A4", "A5", "B2", "G1", "F1", "F2", "F4", "R0"] if r in self.IMPLEMENTED_REGIONS],
            "Cyrillic": [r for r in ["B1", "B2", "C9"] if r in self.IMPLEMENTED_REGIONS],
            "Greek": [r for r in ["B3"] if r in self.IMPLEMENTED_REGIONS],
            "Arabic": [r for r in ["C2", "C3", "C4", "C5", "D4"] if r in self.IMPLEMENTED_REGIONS],
            "Hebrew": [r for r in ["C6"] if r in self.IMPLEMENTED_REGIONS],
            "Devanagari": [r for r in ["D1"] if r in self.IMPLEMENTED_REGIONS],
            "Bengali": [r for r in ["D3"] if r in self.IMPLEMENTED_REGIONS],
            "Tamil": [r for r in ["D2"] if r in self.IMPLEMENTED_REGIONS],
            "Telugu": [r for r in ["D2"] if r in self.IMPLEMENTED_REGIONS],
            "Sinhala": [r for r in ["D5"] if r in self.IMPLEMENTED_REGIONS],
            "Thai": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Myanmar": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Georgian": [r for r in ["C8"] if r in self.IMPLEMENTED_REGIONS],
            "Armenian": [r for r in ["C7"] if r in self.IMPLEMENTED_REGIONS],
            "CJK": [r for r in ["E1", "E2", "E3"] if r in self.IMPLEMENTED_REGIONS],
            "Hangul": [r for r in ["E4"] if r in self.IMPLEMENTED_REGIONS],
            "Ethiopic": [r for r in ["F3"] if r in self.IMPLEMENTED_REGIONS],
        }
    
    def _ensure_regions_loaded(self):
        """Lazy load regions only when needed."""
        if not self._regions_loaded:
            self._load_regions()
            self._regions_loaded = True
    
    def register_region(self, region: RegionSpec) -> None:
        """Register a region specification."""
        # Only register if it's in the implemented list
        if region.code in self.IMPLEMENTED_REGIONS:
            self._regions[region.code] = region
            logger.info(f"Registered region {region.code}: {REGION_CODES.get(region.code)}")
        else:
            logger.debug(f"Skipping unimplemented region {region.code}")
    
    def get_region(self, code: str) -> Optional[RegionSpec]:
        """Get region specification by code."""
        self._ensure_regions_loaded()
        return self._regions.get(code)
    
    def detect_region(self, entry: Dict[str, Any]) -> RegionDetectionResult:
        """
        Detect region for an entry using multi-stage detection.
        
        Args:
            entry: Dictionary containing entry data
        """
        # Ensure regions are loaded
        self._ensure_regions_loaded()
        
        # Create cache key from entry data
        cache_key = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        
        # Check cache
        if cache_key in self._detection_cache:
            return self._detection_cache[cache_key]
        
        # Detect region
        result = self._detect_region_uncached(entry)
        
        # Cache result
        if cache_key:
            self._detection_cache[cache_key] = result
        
        return result
    
    def _detect_region_uncached(self, entry: Dict[str, Any]) -> RegionDetectionResult:
        """
        Detect region for an entry using V7-compliant multi-stage detection.
        
        V7 Strategy (MUST follow this order):
        1. Script Analysis
        2. ICU (Unicode normalization and script detection)
        3. FastText (language detection)
        4. Affiliation Hints
        5. DOI Prefix  
        6. Diaspora Overlay
        """
        # V7 Stage 0: Region overlay map (spec §2a sub-national overrides)
        # Runs first when CountryCodes + institution keywords provide strong signal
        country_codes = entry.get("CountryCodes", [])
        if country_codes:
            overlay_result = self._detect_by_overlay(entry, country_codes)
            if overlay_result:
                return overlay_result

        # V7 Stage 1: Script Analysis (highest priority)
        result = self._detect_by_script(entry)
        if result and result.confidence >= 0.9:
            return result

        # V7 Stage 2: ICU processing
        result = self._detect_by_icu(entry)
        if result and result.confidence >= 0.85:
            return result
        
        # V7 Stage 3: FastText language detection
        if self._lang_detector:
            result = self._detect_by_language(entry)
            if result and result.confidence >= 0.7:
                return result
        
        # Affiliation hints
        result = self._detect_by_affiliation(entry)
        if result:
            return result
        
        # DOI prefix
        result = self._detect_by_doi(entry)
        if result:
            return result
        
        # Diaspora overlay
        result = self._detect_by_diaspora(entry)
        if result:
            return result
        
        # Fallback based on country code
        if country_codes:
            region = get_region_for_territory(country_codes[0])
            # Only return if it's an implemented region
            if region in self.IMPLEMENTED_REGIONS:
                return RegionDetectionResult(
                    region_code=region,
                    confidence=0.3,
                    detection_method="country-fallback",
                    metadata={"country": country_codes[0]}
                )
        
        # Default fallback - but only if A1 is implemented
        if "A1" in self.IMPLEMENTED_REGIONS:
            return RegionDetectionResult(
                region_code="A1",
                confidence=0.1,
                detection_method="default-fallback",
                metadata={}
            )
        else:
            # No implemented regions available - should not happen
            return RegionDetectionResult(
                region_code="Z0",
                confidence=0.0,
                detection_method="no-regions",
                metadata={}
            )
    
    def _detect_by_script(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region based on Unicode script analysis."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return None
        
        # Normalize and analyze scripts
        normalized = self._unicode_normalizer.normalize(canonical)
        script_info = self._analyze_scripts(normalized)
        
        # Count total alphabetic characters
        total_chars = sum(script_info.values())
        if total_chars == 0:
            return None
        
        for script, count in sorted(script_info.items(), key=lambda x: x[1], reverse=True):
            if count / total_chars >= 0.5:  # At least 50% of characters
                possible_regions = self._script_to_regions.get(script, [])
                if possible_regions:
                    # Use country code to select best region from script matches
                    best_region = self._select_best_region_from_script(entry, possible_regions)
                    if best_region:
                        # Lower confidence for generic scripts like Latin
                        confidence = 0.7 if script == "Latin" else count / total_chars
                        return RegionDetectionResult(
                            region_code=best_region,
                            confidence=confidence,
                            detection_method="script",
                            metadata={"script": script, "script_ratio": count / total_chars}
                        )
        
        return None
    
    def _detect_by_icu(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """V7 Stage 2: ICU processing - Unicode normalization and script detection."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return None
        
        # ICU normalization - apply NFC→NFKD→fold→NFC chain
        try:
            # Normalize using Unicode handler
            normalized = self._unicode_normalizer.normalize(canonical)
            
            # Analyze normalized text for enhanced script detection
            script_info = self._analyze_scripts(normalized)
            total_chars = sum(script_info.values())
            
            if total_chars == 0:
                return None
            
            # ICU-enhanced script detection with higher confidence
            for script, count in sorted(script_info.items(), key=lambda x: x[1], reverse=True):
                if count / total_chars >= 0.6:  # Higher threshold for ICU stage
                    possible_regions = self._script_to_regions.get(script, [])
                    if possible_regions:
                        best_region = self._select_best_region_from_script(entry, possible_regions)
                        if best_region:
                            confidence = min(0.9, count / total_chars + 0.1)  # ICU boost
                            return RegionDetectionResult(
                                region_code=best_region,
                                confidence=confidence,
                                detection_method="icu-script",
                                metadata={"script": script, "normalized": normalized, "script_ratio": count / total_chars}
                            )
        except Exception as e:
            logger.debug(f"ICU processing failed: {e}")
        
        return None
    
    def _select_best_region_from_script(self, entry: Dict[str, Any], possible_regions: List[str]) -> Optional[str]:
        """Select best region from script matches using surname patterns and country codes."""
        # Get country code
        country_codes = entry.get("CountryCodes", [])
        if country_codes:
            country = country_codes[0]
            # Check if country directly maps to one of the possible regions
            expected_region = get_region_for_territory(country)
            if expected_region in possible_regions and expected_region in self.IMPLEMENTED_REGIONS:
                return expected_region
        
        # Use surname pattern detection for Latin script regions
        name = entry.get("CanonicalLatin", "")
        if name and "Latin" in [script for script, regions in self._script_to_regions.items() if any(r in possible_regions for r in regions)]:
            surname_region = self._detect_by_surname_patterns(name, possible_regions)
            if surname_region and surname_region in self.IMPLEMENTED_REGIONS:
                return surname_region
        
        # Fallback to first implemented region
        for region in possible_regions:
            if region in self.IMPLEMENTED_REGIONS:
                return region
        
        return None
    
    def _detect_by_surname(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region using direct surname pattern matching."""
        name = entry.get("CanonicalLatin", "")
        if not name:
            return None
        
        # Extract surname from "Family, Given" format
        if "," in name:
            family_name = name.split(",")[0].strip().lower()
        else:
            # Try "Given Family" format
            parts = name.strip().split()
            if len(parts) >= 2:
                family_name = parts[-1].lower()
            else:
                return None
        
        # Clean surname for matching
        family_name = self._clean_surname_for_matching(family_name)
        
        # Score each region based on surname matches
        best_match = None
        best_score = 0
        
        for region_code, surnames in self.surname_patterns.items():
            # Only check implemented regions
            if region_code not in self.IMPLEMENTED_REGIONS:
                continue
                
            score = 0
            
            # Direct match
            if family_name in surnames:
                score = 10
            else:
                # Partial match scoring
                for surname in surnames:
                    if family_name.startswith(surname) or surname.startswith(family_name):
                        score = max(score, 7)
                    elif surname in family_name or family_name in surname:
                        score = max(score, 5)
            
            if score > best_score:
                best_score = score
                best_match = region_code
        
        if best_match and best_score >= 5:
            confidence = 0.95 if best_score >= 10 else 0.85
            return RegionDetectionResult(
                region_code=best_match,
                confidence=confidence,
                detection_method="surname",
                metadata={"surname": family_name, "score": best_score}
            )
        
        return None
    
    def _detect_by_language(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region based on language identification."""
        if not self._lang_detector:
            return None
        
        text = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not text or len(text) < 10:  # Need reasonable text length
            return None
        
        try:
            # FastText returns ((label,), (confidence,))
            predictions = self._lang_detector.predict(text, k=3)
            
            # Map language codes to regions (only implemented ones)
            lang_to_region = {
                "en": "A1", "es": "G1", "pt": "G1", "fr": "A2", "de": "A2",
                "it": "A2", "nl": "A2", "ru": "B1", "uk": "B1", "pl": "B2",
                "cs": "B2", "sk": "B2", "hr": "B2", "sr": "B2", "sl": "B2",
                "ar": "C3", "fa": "C2", "tr": "C1", "he": "C6", "hi": "D1",
                "ur": "D4", "bn": "D3", "ta": "D2", "te": "D2", "si": "D5",
                "zh": "E1", "ja": "E3", "ko": "E4", "vi": "E5", "th": "E6",
                "id": "E7", "ms": "E7", "tl": "E7", "sw": "F1", "am": "F3",
            }
            
            for (lang_label,), (conf,) in zip(predictions[0], predictions[1]):
                lang_code = lang_label.replace("__label__", "")
                region = lang_to_region.get(lang_code)
                if region and region in self.IMPLEMENTED_REGIONS and conf > 0.5:
                    return RegionDetectionResult(
                        region_code=region,
                        confidence=min(conf, 0.9),  # Cap confidence
                        detection_method="language",
                        metadata={"language": lang_code, "lang_confidence": conf}
                    )
        except Exception as e:
            logger.debug(f"Language detection failed: {e}")
        
        return None
    
    def _detect_by_affiliation(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region based on affiliation information."""
        affiliations = entry.get("Affiliations", [])
        if not affiliations:
            return None
        
        # Extract country from affiliation
        # This is a simplified version - real implementation would be more sophisticated
        for affiliation in affiliations:
            if isinstance(affiliation, dict):
                country = affiliation.get("country")
                if country:
                    region = get_region_for_territory(country)
                    if region and region in self.IMPLEMENTED_REGIONS:
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.8,
                            detection_method="affiliation",
                            metadata={"country": country, "affiliation": affiliation.get("name")}
                        )
        
        return None
    
    def _detect_by_doi(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region based on DOI prefix."""
        dois = entry.get("DOIs", [])
        if not dois:
            return None
        
        for doi in dois:
            # Extract prefix (e.g., "10.1007" from "10.1007/s00220-021-04123-0")
            if "/" in doi:
                prefix = doi.split("/")[0]
                country = self._doi_prefix_map.get(prefix)
                if country:
                    region = get_region_for_territory(country)
                    if region and region in self.IMPLEMENTED_REGIONS:
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.6,
                            detection_method="doi",
                            metadata={"doi_prefix": prefix, "country": country}
                        )
        
        return None
    
    def _detect_by_overlay(self, entry: Dict[str, Any],
                           country_codes: List[str]) -> Optional[RegionDetectionResult]:
        """
        Detect region using the spec §2a region overlay map.

        Checks sub-national context clues (institution, affiliation) to build
        composite keys like 'IN-HN', 'LK-TA' etc. for overlay lookup.
        """
        inst_raw = entry.get("Institution", "") or entry.get("Affiliation", "")
        institution = " ".join(inst_raw) if isinstance(inst_raw, list) else (inst_raw or "")
        institution_country = entry.get("InstitutionCountry", "")

        for country in country_codes:
            # Build candidate overlay keys from available context
            candidates = []

            # Check institution-based sub-national hints
            if country == "IN":
                inst_lower = institution.lower()
                if any(w in inst_lower for w in ["chennai", "madras", "bengaluru",
                                                  "bangalore", "hyderabad", "kerala",
                                                  "tamil", "karnataka", "andhra"]):
                    candidates.append("IN-SOUTH")
                elif any(w in inst_lower for w in ["kolkata", "calcutta", "bengal",
                                                    "jadavpur", "presidency"]):
                    candidates.append("IN-WB")
                else:
                    candidates.append("IN-HN")  # Hindi belt default for India
            elif country == "LK":
                inst_lower = institution.lower()
                if any(w in inst_lower for w in ["jaffna", "tamil", "batticaloa"]):
                    candidates.append("LK-TA")
                else:
                    candidates.append("LK-SI")
            elif country == "CH":
                inst_lower = institution.lower()
                if any(w in inst_lower for w in ["genève", "geneva", "lausanne",
                                                  "fribourg", "neuchâtel"]):
                    candidates.append("CH-FR")
            elif country == "RU":
                inst_lower = institution.lower()
                if any(w in inst_lower for w in ["dagestan", "chechnya", "ingushetia",
                                                  "kabardino", "ossetia", "caucasus"]):
                    candidates.append("RU-NC")
            elif country == "AZ":
                inst_lower = institution.lower()
                if any(w in inst_lower for w in ["tabriz", "iran", "urmia"]):
                    candidates.append("AZ-IR")

            # Look up each candidate in the overlay map
            for key in candidates:
                if key in _REGION_OVERLAY_MAP:
                    region = _REGION_OVERLAY_MAP[key]
                    if region in self.IMPLEMENTED_REGIONS:
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.5,
                            detection_method="region-overlay",
                            metadata={"overlay_key": key, "country": country}
                        )

        return None

    def _detect_by_diaspora(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """
        Detect region based on diaspora patterns.

        Uses config/diaspora.yaml to determine the correct region when a
        mathematician publishes from a country outside their home region.
        Checks CountryCodes against diaspora config date ranges.
        """
        countries = entry.get("CountryCodes", [])
        if not countries or not self._diaspora_config:
            return None

        # Get publication date context for range matching
        birth_year = entry.get("BirthYear")
        pub_year = None
        if isinstance(birth_year, int) and birth_year > 1900:
            # Estimate active publication period: birth + 25 to birth + 65
            pub_year = birth_year + 40  # approximate mid-career

        for country in countries:
            if country not in self._diaspora_config:
                continue

            ranges = self._diaspora_config[country]
            if not isinstance(ranges, list):
                continue

            for entry_range in ranges:
                if not isinstance(entry_range, dict):
                    continue

                region = entry_range.get("region")
                range_str = entry_range.get("range", "")

                if not region or region not in self.IMPLEMENTED_REGIONS:
                    continue

                # Check if publication year falls within range
                if self._year_in_range(pub_year, range_str):
                    return RegionDetectionResult(
                        region_code=region,
                        confidence=0.65,
                        detection_method="diaspora",
                        metadata={"country": country, "range": range_str}
                    )

        return None

    @staticmethod
    def _year_in_range(year: Optional[int], range_str: str) -> bool:
        """Check if a year falls within a diaspora range string.

        Range formats:
        - "" (empty) → always matches (default/unbounded)
        - "-2015" → matches year ≤ 2015
        - "2016-" → matches year ≥ 2016
        - "1980-2000" → matches 1980 ≤ year ≤ 2000
        """
        if not range_str:
            return True  # Empty range = always matches

        if year is None:
            return True  # No year info = assume match

        range_str = range_str.strip()
        if range_str.startswith("-"):
            # "-2015" → up to 2015
            try:
                end = int(range_str[1:])
                return year <= end
            except ValueError:
                return True
        elif range_str.endswith("-"):
            # "2016-" → from 2016 onward
            try:
                start = int(range_str[:-1])
                return year >= start
            except ValueError:
                return True
        elif "-" in range_str:
            # "1980-2000"
            parts = range_str.split("-")
            try:
                return int(parts[0]) <= year <= int(parts[1])
            except (ValueError, IndexError):
                return True

        return True
    
    def _analyze_scripts(self, text: str) -> Dict[str, int]:
        """Analyze Unicode scripts in text."""
        script_counts = {}
        
        for char in text:
            if char.isalpha():
                # Get Unicode script
                script = self._get_unicode_script(char)
                script_counts[script] = script_counts.get(script, 0) + 1
        
        return script_counts
    
    def _get_unicode_script(self, char: str) -> str:
        """Determine Unicode script of a character."""
        # Simplified script detection - real implementation would use unicodedata
        code = ord(char)
        
        # Basic Latin
        if 0x0041 <= code <= 0x007A:
            return "Latin"
        # Latin Extended
        elif 0x0100 <= code <= 0x024F:
            return "Latin"
        # Cyrillic
        elif 0x0400 <= code <= 0x04FF:
            return "Cyrillic"
        # Greek
        elif 0x0370 <= code <= 0x03FF:
            return "Greek"
        # Arabic
        elif 0x0600 <= code <= 0x06FF:
            return "Arabic"
        # Hebrew
        elif 0x0590 <= code <= 0x05FF:
            return "Hebrew"
        # Devanagari
        elif 0x0900 <= code <= 0x097F:
            return "Devanagari"
        # Bengali
        elif 0x0980 <= code <= 0x09FF:
            return "Bengali"
        # Tamil
        elif 0x0B80 <= code <= 0x0BFF:
            return "Tamil"
        # Telugu
        elif 0x0C00 <= code <= 0x0C7F:
            return "Telugu"
        # Sinhala
        elif 0x0D80 <= code <= 0x0DFF:
            return "Sinhala"
        # Thai
        elif 0x0E00 <= code <= 0x0E7F:
            return "Thai"
        # Myanmar
        elif 0x1000 <= code <= 0x109F:
            return "Myanmar"
        # Georgian
        elif 0x10A0 <= code <= 0x10FF:
            return "Georgian"
        # Hangul
        elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
            return "Hangul"
        # CJK
        elif 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            return "CJK"
        # Hiragana/Katakana
        elif 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:
            return "CJK"
        # Armenian
        elif 0x0530 <= code <= 0x058F:
            return "Armenian"
        # Ethiopic
        elif 0x1200 <= code <= 0x137F:
            return "Ethiopic"
        else:
            return "Unknown"
    
    def _init_surname_patterns(self):
        """Initialize surname pattern databases for implemented regions only."""
        self.surname_patterns = {}
        
        # Only add patterns for implemented regions
        if "A1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A1"] = {
                # Common Anglo surnames
                "smith", "johnson", "williams", "brown", "jones", "garcia", "miller", 
                "davis", "rodriguez", "martinez", "hernandez", "lopez", "gonzalez",
                "wilson", "anderson", "thomas", "taylor", "moore", "jackson", "martin",
                "lee", "perez", "thompson", "white", "harris", "sanchez", "clark",
                # Mathematician surnames
                "newton", "darwin", "maxwell", "faraday", "kelvin", "rayleigh", "hardy",
                "littlewood", "ramsey", "turing", "russell", "whitehead", "hamilton",
                "cayley", "sylvester", "boole", "de morgan", "babbage", "lovelace"
            }
        
        if "A2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A2"] = {
                # German
                "müller", "schmidt", "schneider", "fischer", "weber", "meyer", "wagner",
                "becker", "schulz", "hoffmann", "schäfer", "koch", "bauer", "richter",
                "gauss", "riemann", "hilbert", "weierstrass", "cantor", "dedekind",
                "kronecker", "kummer", "dirichlet", "jacobi", "weyl", "noether", "artin",
                "hasse", "hecke", "minkowski", "hurwitz", "landau", "siegel", "selberg",
                # French
                "bernard", "dubois", "thomas", "robert", "richard", "petit", "durand",
                "cauchy", "lagrange", "laplace", "fourier", "poisson", "hermite",
                "poincaré", "hadamard", "lebesgue", "borel", "cartan", "weil", "serre",
                "grothendieck", "deligne", "connes", "villani", "demailly",
                # Dutch
                "van der waals", "lorentz", "zeeman", "kamerlingh", "huygens",
                "stevin", "van der waerden", "brouwer", "de groot",
                # Belgian
                "deligne", "bourgain", "daubechies",
                # Austrian
                "schrödinger", "pauli", "mach", "boltzmann", "doppler", "gödel",
                # Swiss
                "euler", "bernoulli", "steiner",
                # Italian (Northern)
                "rossi", "ferrari", "russo", "bianchi", "romano", "colombo", "ricci",
                "fibonacci", "galilei", "torricelli", "volta", "avogadro", "fermi",
                "levi-civita", "ricci-curbastro", "betti", "cremona", "peano",
                "bombieri", "fubini", "vitali",
                # Hungarian
                "nagy", "kovács", "tóth", "szabó", "horváth", "varga", "kiss",
                "molnár", "németh", "farkas", "balogh", "papp", "takács", "juhász",
                "neumann", "wigner", "teller", "kármán", "pólya", "szegő",
                "riesz", "haar", "turán", "rényi", "lovász", "szemerédi", "babai",
                # Polish mathematicians
                "banach", "steinhaus", "mazur", "schauder", "kuratowski", "sierpiński",
                "tarski", "mostowski", "knaster", "borsuk", "ulam", "zygmund"
            }
        
        if "A3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A3"] = {
                # Swedish
                "andersson", "johansson", "karlsson", "nilsson", "eriksson", "larsson",
                "olsson", "persson", "svensson", "gustafsson", "pettersson", "jonsson",
                # Norwegian  
                "hansen", "johansen", "olsen", "larsen", "andersen", "pedersen",
                "nielsen", "kristiansen", "jensen", "carlsen", "lie", "abel",
                # Danish
                "nielsen", "jensen", "hansen", "pedersen", "andersen", "christensen",
                "larsen", "sørensen", "rasmussen", "jørgensen", "petersen", "madsen",
                # Icelandic (patronymic)
                "einarsson", "sigurdsson", "guðmundsson", "jónsson", "ólafsson",
                "magnusson", "þórsson", "ragnarsson", "björnsson", "stefánsson",
                # Finnish
                "virtanen", "korhonen", "mäkinen", "nieminen", "mäkelä", "hämäläinen",
                "laine", "heikkinen", "koskinen", "järvinen", "lehtonen", "saarinen",
                # Estonian  
                "tamm", "saar", "mägi", "kask", "kukk", "sepp", "kõiv", "rebane",
                "hunt", "roos", "vaher", "männik", "kadak", "kallas",
                # Latvian
                "bērziņš", "kalniņš", "ozoliņš", "liepiņš", "vilks", "priede",
                "krūmiņš", "jansons", "pētersons", "kļaviņš",
                # Lithuanian
                "kazlauskas", "petrauskas", "stankevičius", "jankauskas", "žukauskas",
                "butkus", "paulauskas", "gudauskas", "mockus", "rimkus",
                # Hungarian (mathematicians and common surnames)
                "erdős", "rényi", "turán", "kövári", "szekeres", "lovász", "szemerédi",
                "babai", "bollobás", "komlós", "rödl", "freud", "katona", "simonovits",
                "nagy", "kovács", "tóth", "szabó", "horváth", "varga", "kiss", "molnár"
            }
        
        if "B1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B1"] = {
                # Russian
                "ivanov", "smirnov", "kuznetsov", "popov", "sokolov", "lebedev",
                "kozlov", "novikov", "morozov", "petrov", "volkov", "solovyov",
                "vasilyev", "zaytsev", "pavlov", "semyonov", "golubev", "vinogradov",
                "chebyshev", "lobachevsky", "markov", "lyapunov", "kolmogorov",
                "khinchin", "alexandrov", "pontryagin", "shafarevich", "gel'fand",
                "arnol'd", "sinai", "novikov", "manin", "kirillov", "faddeev",
                # Ukrainian
                "shevchenko", "bondarenko", "kovalenko", "tkachenko", "kravchenko",
                "oliynyk", "kovalchuk", "shevchuk", "polishchuk", "bondarchuk"
            }
        
        if "B2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B2"] = {
                # Polish
                "nowak", "kowalski", "wiśniewski", "wójcik", "kowalczyk",
                "kamiński", "lewandowski", "zieliński", "szymański", "woźniak",
                "dąbrowski", "kozłowski", "jankowski", "mazur", "wojciechowski",
                "kwiatkowski", "krawczyk", "kaczmarek", "piotrowski", "grabowski",
                # Czech
                "novák", "svoboda", "novotný", "dvořák", "černý", "procházka",
                "krejčí", "čech", "bolzano",
                # Slovak
                "kováč", "horváth", "baláž", "szabó", "molnár", "lukáč", "kováčik",
                # Croatian
                "horvat", "kovačić", "babić", "marić", "jurić", "pavlović",
                "kovač", "božić", "mohorovičić",
                # Serbian
                "jovanović", "petrović", "nikolić", "marković", "đorđević",
                "stojanović", "milić", "milanković",
                # Slovenian
                "novak", "horvat", "krajnc", "kovač", "potočnik", "vidmar"
            }
        
        if "B3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B3"] = {
                # Ancient Greek mathematicians
                "euclid", "archimedes", "apollonius", "diophantus", "pappus", "ptolemy",
                "thales", "pythagoras", "eratosthenes", "hipparchus", "menelaus",
                # Modern Greek surnames
                "papadopoulos", "georgiou", "dimitriou", "ioannou", "constantinou", 
                "nikolaou", "christou", "michail", "stavros", "kostas", "yannis",
                "christodoulou", "papageorgiou", "hadjidakis", "chatzidakis",
                # Common patterns (-opoulos, -akis, -ou)
                "antonopoulos", "giannopoulos", "economopoulos", "theodoropoulos",
                "stefanakis", "nikolakis", "dimitrakis", "georgakis", "christakis",
                # Greek script versions (for mixed detection)
                "παπαδόπουλος", "γεωργίου", "δημητρίου", "ιωάννου", "κωνσταντίνου",
                "νικολάου", "χρήστου", "μιχαήλ", "σταύρος", "κώστας", "γιάννης"
            }
        
        if "C2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C2"] = {
                # Persian
                "ahmadi", "hosseini", "mohammadi", "rezaei", "karimi", "moradi",
                "ali", "rahimi", "rostami", "nazari", "safari", "hashemi",
                "khayyam", "tusi", "kashani", "biruni", "khwarizmi", "karaji",
                # Tajik
                "rahmonov", "safarov", "karimov", "nazarov", "rustamov"
            }
        
        if "C3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C3"] = {
                # Arabic (Levant/Egypt)
                "hassan", "hussein", "ahmad", "mahmoud", "ibrahim", "mohamed",
                "abdullah", "yousef", "khalil", "rahman", "hamza", "omar",
                "saleh", "saeed", "nasser", "jaber", "haddad", "khoury",
                "al-khwarizmi", "alhazen", "al-kindi", "al-battani", "al-biruni",
                "al-kashi", "al-tusi", "al-din", "al-jazari", "al-qalasadi",
                # Add more Arabic patterns without hyphen
                "muhammad", "khwarizmi", "alkhwarizmi", "jabir", "aljabir", "sina", 
                "farabi", "alfarabi",
            }
        
        if "C4" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C4"] = {
                # Gulf Arabic
                "al-rashid", "al-sabah", "al-thani", "al-nahyan", "al-maktoum",
                "al-khalifa", "al-said", "al-otaibi", "al-mutairi", "al-harbi",
                "al-ghamdi", "al-qahtani", "al-shammari", "al-anazi", "al-tamimi"
            }
        
        if "D1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["D1"] = {
                # Hindi Belt
                "sharma", "verma", "gupta", "kumar", "singh", "yadav", "mishra",
                "pandey", "patel", "tiwari", "jain", "agarwal", "mehta", "joshi",
                "chauhan", "gautam", "kaur", "malhotra", "kapoor", "chopra",
                "ramanujan", "bose", "chandrasekhar", "raman", "saha", "mahalanobis",
                "rao", "bhattacharya", "das", "sen", "mukherjee", "chatterjee"
            }
        
        if "E1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E1"] = {
                # Chinese (Mainland)
                "wang", "li", "zhang", "liu", "chen", "yang", "huang", "zhao",
                "zhou", "wu", "xu", "sun", "ma", "zhu", "hu", "guo", "he",
                "lin", "luo", "gao", "zheng", "liang", "xie", "song", "tang",
                "chern", "yau", "tao", "hua", "shen", "feng", "cao", "deng"
            }
        
        if "E3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E3"] = {
                # Japanese
                "sato", "suzuki", "takahashi", "tanaka", "watanabe", "ito",
                "yamamoto", "nakamura", "kobayashi", "kato", "yoshida", "yamada",
                "sasaki", "yamaguchi", "saito", "matsumoto", "inoue", "kimura",
                "hayashi", "shimizu", "yamazaki", "mori", "abe", "ikeda",
                "hashimoto", "yamashita", "ishikawa", "nakajima", "maeda", "fujita",
                "kiyoshi", "kunihiko", "shigefumi", "heisuke", "goro", "mikio"
            }
        
        if "G1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["G1"] = {
                # Spanish
                "garcía", "rodríguez", "gonzález", "fernández", "lópez", "martínez",
                "sánchez", "pérez", "gómez", "ruiz", "hernández", "jiménez",
                "díaz", "moreno", "muñoz", "álvarez", "romero", "navarro",
                "torres", "domínguez", "vázquez", "ramos", "castro", "ortiz",
                # Portuguese
                "silva", "santos", "oliveira", "souza", "rodrigues", "almeida",
                "nascimento", "lima", "araújo", "fernandes", "carvalho", "gomes",
                "martins", "rocha", "ribeiro", "alves", "monteiro", "mendes",
                "barros", "freitas", "barbosa", "pinto", "moreira", "cavalcanti",
                # Latin American
                "garcia", "rodriguez", "gonzalez", "fernandez", "lopez", "martinez",
                "sanchez", "perez", "gomez", "ruiz", "hernandez", "jimenez",
                "diaz", "moreno", "munoz", "alvarez", "romero", "navarro"
            }
        
        if "E4" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E4"] = {
                # Most common Korean surnames
                "kim", "lee", "park", "choi", "jung", "kang", "cho", "yoon", "jang", "lim",
                "han", "oh", "seo", "shin", "kwon", "hwang", "ahn", "song", "yoo", "hong",
                "jeon", "go", "moon", "yang", "baek", "heo", "nam", "sim", "won", "kwak",
                "son", "myung", "noh", "koo", "ryu", "jin", "ma", "cha", "yu", "do",
                "bae", "seok", "woo", "min", "gang", "ko", "goo", "tae", "pyo", "ha",
                # Mathematician surnames  
                "kim", "lee", "park", "choi", "cho", "kang", "moon", "seo", "han", "shin",
                "kwon", "jung", "oh", "yoon", "jang", "hwang", "song", "ahn", "lim", "hong",
                # Romanization variants
                "gim", "ri", "bak", "choe", "jeong", "gang", "jo", "yun", "jang", "im"
            }

        if "C1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C1"] = {
                "yılmaz", "kaya", "demir", "çelik", "şahin", "yıldız", "yıldırım",
                "öztürk", "aydın", "özdemir", "arslan", "doğan", "kılıç", "aslan",
                "erdoğan", "güneş", "kurt", "ateş", "polat", "koç"
            }

        if "C5" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C5"] = {
                "benali", "bensaid", "boumediene", "belkacem", "bouzid", "hammadi",
                "kaddour", "lahlou", "mansouri", "zeroual", "amrani", "berrada",
                "chaoui", "fekhar", "ghali", "hadj", "messaoud", "taleb"
            }

        if "E2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E2"] = {
                "chen", "lin", "huang", "chang", "li", "wang", "wu", "liu", "tsai", "yang",
                "hsu", "cheng", "ho", "tseng", "liao", "lai", "lu", "hung", "chung", "shih"
            }

        if "E5" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E5"] = {
                "nguyen", "tran", "le", "pham", "hoang", "huynh", "phan", "vu", "vo",
                "dang", "bui", "do", "ho", "ngo", "duong", "ly", "dao", "dinh", "lam"
            }

        if "D2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["D2"] = {
                "pillai", "nair", "menon", "reddy", "naidu", "rao", "iyer", "iyengar",
                "srinivasan", "krishnamurthy", "ramanathan", "subramaniam", "venkatesh"
            }

        if "D3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["D3"] = {
                "das", "dutta", "gupta", "roy", "sen", "bose", "ghosh", "banerjee",
                "chatterjee", "mukherjee", "chakraborty", "sarkar", "islam", "ahmed"
            }

        if "F2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["F2"] = {
                "okonkwo", "adeyemi", "osei", "mensah", "kamau", "mwangi", "adebayo",
                "owusu", "achebe", "emecheta", "soyinka", "ngugi", "odinga", "kenyatta"
            }

    def _detect_by_surname_patterns(self, name: str, possible_regions: List[str]) -> Optional[str]:
        """Detect region using surname pattern matching."""
        if not hasattr(self, 'surname_patterns'):
            return None
            
        # Extract surname from "Family, Given" format
        if "," in name:
            family_name = name.split(",")[0].strip().lower()
        else:
            # Try "Given Family" format
            parts = name.strip().split()
            if len(parts) >= 2:
                family_name = parts[-1].lower()
            else:
                return None
        
        # Clean surname for matching
        family_name = self._clean_surname_for_matching(family_name)
        
        # Score each possible region based on surname matches
        region_scores = {}
        
        for region in possible_regions:
            if region in self.surname_patterns and region in self.IMPLEMENTED_REGIONS:
                surnames = self.surname_patterns[region]
                
                # Direct match
                if family_name in surnames:
                    region_scores[region] = 10
                else:
                    # Partial match scoring
                    for surname in surnames:
                        if family_name.startswith(surname) or surname.startswith(family_name):
                            region_scores[region] = max(region_scores.get(region, 0), 7)
                        elif surname in family_name or family_name in surname:
                            region_scores[region] = max(region_scores.get(region, 0), 5)
        
        # Return region with highest score (minimum score of 5 to avoid false positives)
        if region_scores:
            best_region = max(region_scores.items(), key=lambda x: x[1])
            if best_region[1] >= 5:
                return best_region[0]
        
        return None
    
    def _clean_surname_for_matching(self, surname: str) -> str:
        """Clean surname by removing common particles and prefixes."""
        # Remove common particles (case insensitive)
        particles = {
            "de", "del", "della", "delle", "dello", "di", "da", "dal", "dalla",
            "du", "des", "le", "la", "les", "dos", "das", "do", "da",
            "von", "van", "der", "den", "het", "ten", "ter", "te",
            "zum", "zur", "am", "im", "zu", "auf", "unter",
            "al", "ibn", "abu", "bin", "ben", "bat",
            "o'", "mc", "mac", "fitz",
        }
        
        # Split on spaces and hyphens
        parts = surname.replace("-", " ").split()
        if len(parts) > 1:
            # Check if first part is a particle
            if parts[0].lower() in particles:
                return " ".join(parts[1:])
            # Check if it starts with particle patterns
            for particle in particles:
                if surname.startswith(particle.lower() + " "):
                    return surname[len(particle) + 1:]
        
        return surname
    
    def _load_regions(self):
        """Load and register only actually implemented region implementations."""
        import importlib
        
        # Only load regions that are actually implemented
        region_imports = {
            # A Groups
            "A1": ("src.regions.a_groups.a1_anglo_sphere", "A1_AngloSphere"),
            "A2": ("src.regions.a_groups.a2_western_europe", "A2_WesternEurope"),
            "A3": ("src.regions.a_groups.a3_nordic_baltic.processor", "A3NordicBalticProcessor"),
            "A4": ("src.regions.a_groups.a4_oceania.processor", "A4OceaniaProcessor"),
            "A5": ("src.regions.a_groups.a5_caribbean.processor", "A5CaribbeanProcessor"),
            # B Groups
            "B1": ("src.regions.b_groups.b1_east_slavic", "B1_EastSlavic"),
            "B2": ("src.regions.b_groups.b2_south_slavic_central", "B2_SouthSlavicCentral"),
            "B3": ("src.regions.b_groups.b3_greek.processor", "B3GreekProcessor"),
            # C Groups
            "C1": ("src.regions.c_groups.c1_turkic.processor", "C1TurkicProcessor"),
            "C2": ("src.regions.c_groups.c2_persian_tajik", "C2_PersianTajik"),
            "C3": ("src.regions.c_groups.c3_arabic_levant_nile", "C3_ArabicLevantNile"),
            "C4": ("src.regions.c_groups.c4_arabic_gulf", "C4_ArabicGulf"),
            "C5": ("src.regions.c_groups.c5_arabic_maghreb", "C5ArabicMaghreb"),
            "C6": ("src.regions.c_groups.c6_hebrew_diaspora", "C6HebrewDiaspora"),
            "C7": ("src.regions.c_groups.c7_armenian", "C7Armenian"),
            "C8": ("src.regions.c_groups.c8_georgian", "C8Georgian"),
            "C9": ("src.regions.c_groups.c9_caucasus_turkic", "C9CaucasusTurkic"),
            # D Groups
            "D1": ("src.regions.d_groups.d1_south_asia_hindi_belt", "D1_SouthAsiaHindiBelt"),
            "D2": ("src.regions.d_groups.d2_south_asia_dravidian", "D2SouthAsiaDravidian"),
            "D3": ("src.regions.d_groups.d3_south_asia_bengali", "D3SouthAsiaBengali"),
            "D4": ("src.regions.d_groups.d4_pakistan_urdu", "D4PakistanUrdu"),
            "D5": ("src.regions.d_groups.d5_sinhala", "D5Sinhala"),
            # E Groups
            "E1": ("src.regions.e_groups.e1_sinophone_mainland", "E1_SinophoneMainland"),
            "E2": ("src.regions.e_groups.e2_traditional_chinese", "E2TraditionalChineseProcessor"),
            "E3": ("src.regions.e_groups.e3_japan", "E3_Japan"),
            "E4": ("src.regions.e_groups.e4_korea.processor_lightweight", "E4KoreanProcessor"),
            "E5": ("src.regions.e_groups.e5_vietnam", "E5Vietnam"),
            "E6": ("src.regions.e_groups.e6_mainland_sea", "E6MainlandSEA"),
            "E7": ("src.regions.e_groups.e7_maritime_sea", "E7MaritimeSEA"),
            # F Groups
            "F1": ("src.regions.f_groups.f1_ssa_francophone", "F1SSAFrancophone"),
            "F2": ("src.regions.f_groups.f2_ssa_anglophone", "F2SSAAnglophone"),
            "F3": ("src.regions.f_groups.f3_horn_of_africa", "F3HornOfAfrica"),
            "F4": ("src.regions.f_groups.f4_lusophone_africa", "F4LusophoneAfrica"),
            # G Groups
            "G1": ("src.regions.g_groups.g1_latin_america", "G1_LatinAmerica"),
            # Special
            "H1": ("src.regions.special.h1_historical", "H1Historical"),
            "R0": ("src.regions.special.r0_residual_latin_ascii", "R0ResidualLatinASCII"),
            "Z0": ("src.regions.special.z0_quarantine", "Z0Quarantine"),
        }
        
        regions_loaded = 0
        
        for region_code in self.IMPLEMENTED_REGIONS:
            if region_code in region_imports:
                module_path, class_name = region_imports[region_code]
                try:
                    # Import the module
                    module = importlib.import_module(module_path)
                    
                    # Get the class
                    region_class = getattr(module, class_name)
                    
                    # Instantiate the region
                    region_instance = region_class()
                    
                    # Register the region
                    self.register_region(region_instance)
                    regions_loaded += 1
                    
                except (ImportError, AttributeError, Exception) as e:
                    logger.error(f"Could not load region {region_code} from {module_path}: {e}")
        
        logger.info(f"Loaded {regions_loaded} implemented regions successfully")