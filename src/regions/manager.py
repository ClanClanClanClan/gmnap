"""
Region detection and management for GMNAP.
Implements the region detection strategy from specs v6.
"""

import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fasttext

from src.core.unicode_handler import UnicodeNormalizer
from .base import (REGION_CODES, TERRITORY_TO_REGION,
                              RegionRuleError, RegionSpec,
                              get_region_for_territory)

logger = logging.getLogger(__name__)


@dataclass
class RegionDetectionResult:
    """Result of region detection."""
    region_code: str
    confidence: float
    detection_method: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RegionManager:
    """
    Manages region detection and routing.
    
    Implements the detection strategy from specs v6:
    1. Script Analysis
    2. Language Detection
    3. Affiliation Hints
    4. DOI Prefix
    5. Diaspora Overlay
    """
    
    def __init__(self, config_dir: Path = Path("./config")):
        self.config_dir = config_dir
        self._regions: Dict[str, RegionSpec] = {}
        self._unicode_normalizer = UnicodeNormalizer()
        self._lang_detector = None
        self._diaspora_config = {}
        self._doi_prefix_map = {}
        self._initialize()
    
    def _initialize(self):
        """Initialize region manager components."""
        # Load language detector
        self._load_language_detector()
        
        # Load diaspora configuration
        self._load_diaspora_config()
        
        # Load DOI prefix mappings
        self._load_doi_prefix_map()
        
        # Initialize script to region mappings
        self._init_script_mappings()
    
    def _load_language_detector(self):
        """Load FastText language detection model."""
        try:
            # Try config directory first
            model_path = self.config_dir / "lid.176.bin"
            
            # Fallback to global cache directory for tests
            if not model_path.exists():
                global_model_path = Path("cache/config/lid.176.bin")
                if global_model_path.exists():
                    model_path = global_model_path
            
            if model_path.exists():
                self._lang_detector = fasttext.load_model(str(model_path))
                logger.info(f"Loaded FastText language detector from {model_path}")
            else:
                logger.warning(f"FastText model not found at {model_path}")
        except Exception as e:
            logger.error(f"Failed to load language detector: {e}")
    
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
            "10.1126": "US",  # Science (US)
            "10.1073": "US",  # PNAS (US)
            "10.1103": "US",  # APS (US)
            "10.1088": "GB",  # IOP (UK)
            "10.1002": "US",  # Wiley (US)
            "10.1080": "GB",  # Taylor & Francis (UK)
            "10.1093": "GB",  # Oxford (UK)
            "10.1017": "GB",  # Cambridge (UK)
            "10.1109": "US",  # IEEE (US)
            "10.1145": "US",  # ACM (US)
            "10.1137": "US",  # SIAM (US)
            "10.1090": "US",  # AMS (US)
            "10.1112": "GB",  # LMS (UK)
            "10.1515": "DE",  # De Gruyter (Germany)
            "10.1007/s": "DE",  # Springer journals
            "10.4171": "CH",  # EMS (Switzerland)
        }
    
    def _init_script_mappings(self):
        """Initialize Unicode script to region mappings."""
        self._script_to_regions = {
            "Latin": ["A1", "A2", "A3", "A4", "A5", "B2", "F1", "F2", "F4", "G1", "R0"],
            "Cyrillic": ["B1", "B2", "C1", "C2"],
            "Greek": ["B3"],
            "Arabic": ["C2", "C3", "C4", "C5", "D4"],
            "Hebrew": ["C6"],
            "Armenian": ["C7"],
            "Georgian": ["C8"],
            "Devanagari": ["D1"],
            "Tamil": ["D2"],
            "Bengali": ["D3"],
            "Sinhala": ["D5"],
            "CJK": ["E1", "E2", "E3", "E4"],
            "Hangul": ["E4"],
            "Kana": ["E3"],
            "Thai": ["E6"],
            "Khmer": ["E6"],
            "Lao": ["E6"],
            "Myanmar": ["E6"],
            "Ethiopic": ["F3"],
        }
    
    def register_region(self, region: RegionSpec) -> None:
        """Register a region specification."""
        self._regions[region.code] = region
        logger.info(f"Registered region {region.code}: {REGION_CODES.get(region.code)}")
    
    def get_region(self, code: str) -> Optional[RegionSpec]:
        """Get region specification by code."""
        return self._regions.get(code)
    
    def detect_region(self, entry: Dict[str, Any]) -> RegionDetectionResult:
        """
        Detect region for an entry using multi-stage detection.
        
        Tie-breaker order: script > affiliation > DOI prefix > lang-ID score
        """
        candidates = []
        
        # 1. Script Analysis
        script_result = self._detect_by_script(entry)
        if script_result:
            candidates.append(script_result)
        
        # 2. Language Detection
        if self._lang_detector:
            lang_result = self._detect_by_language(entry)
            if lang_result:
                candidates.append(lang_result)
        
        # 3. Affiliation Hints
        affiliation_result = self._detect_by_affiliation(entry)
        if affiliation_result:
            candidates.append(affiliation_result)
        
        # 4. DOI Prefix
        doi_result = self._detect_by_doi(entry)
        if doi_result:
            candidates.append(doi_result)
        
        # 5. Apply diaspora overlay
        candidates = self._apply_diaspora_overlay(entry, candidates)
        
        # Select best candidate
        if not candidates:
            return RegionDetectionResult(
                region_code="Z0",
                confidence=0.0,
                detection_method="quarantine",
                metadata={"reason": "No detection method succeeded"}
            )
        
        # Sort by confidence and tie-breaker priority
        priority_order = ["script", "affiliation", "doi", "language"]
        candidates.sort(
            key=lambda x: (
                x.confidence,
                -priority_order.index(x.detection_method)
            ),
            reverse=True
        )
        
        result = candidates[0]
        
        # Check confidence threshold
        if result.confidence < 0.5:
            return RegionDetectionResult(
                region_code="Z0",
                confidence=result.confidence,
                detection_method="quarantine",
                metadata={"reason": f"Low confidence: {result.confidence}"}
            )
        
        return result
    
    def _detect_by_script(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region by Unicode script analysis."""
        # Get canonical name
        name = entry.get("CanonicalNative") or entry.get("CanonicalLatin", "")
        if not name:
            return None
        
        # Detect primary script
        script_info = self._unicode_normalizer.get_script_info(name)
        if not script_info:
            return None
        
        # Find dominant script
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
                        return RegionDetectionResult(
                            region_code=best_region,
                            confidence=count / total_chars,
                            detection_method="script",
                            metadata={"script": script, "script_ratio": count / total_chars}
                        )
        
        return None
    
    def _select_best_region_from_script(self, entry: Dict[str, Any], possible_regions: List[str]) -> Optional[str]:
        """Select best region from script matches using country code."""
        # Get country code
        country_codes = entry.get("CountryCodes", [])
        if not country_codes:
            return possible_regions[0]  # Fallback to first region
        
        country = country_codes[0]
        
        # Check if country directly maps to one of the possible regions
        expected_region = get_region_for_territory(country)
        if expected_region in possible_regions:
            return expected_region
        
        # Fallback to first region
        return possible_regions[0]
    
    def _detect_by_language(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region by language identification."""
        if not self._lang_detector:
            return None
        
        # Get text for detection
        text = entry.get("CanonicalLatin", "")
        if len(text) < 10:  # Too short for reliable detection
            return None
        
        # Detect language
        predictions = self._lang_detector.predict(text, k=3)
        languages = [lang.replace("__label__", "") for lang in predictions[0]]
        scores = predictions[1]
        
        # Map language to region
        lang_to_region = {
            "en": "A1", "es": "G1", "pt": "A2", "fr": "A2", "de": "A2",
            "it": "A2", "nl": "A2", "sv": "A3", "no": "A3", "da": "A3",
            "fi": "A3", "is": "A3", "ru": "B1", "uk": "B1", "be": "B1",
            "pl": "B2", "cs": "B2", "sk": "B2", "hr": "B2", "sr": "B2",
            "bg": "B2", "el": "B3", "tr": "C1", "az": "C1", "uz": "C1",
            "kk": "C1", "fa": "C2", "ar": "C3", "he": "C6", "hy": "C7",
            "ka": "C8", "hi": "D1", "ur": "D4", "bn": "D3", "ta": "D2",
            "si": "D5", "zh": "E1", "ja": "E3", "ko": "E4", "vi": "E5",
            "th": "E6", "km": "E6", "lo": "E6", "id": "E7", "ms": "E7",
            "tl": "E7", "am": "F3", "sw": "F2", "yo": "F2", "ha": "F2",
        }
        
        for lang, score in zip(languages, scores):
            if lang in lang_to_region and score > 0.5:
                return RegionDetectionResult(
                    region_code=lang_to_region[lang],
                    confidence=float(score),
                    detection_method="language",
                    metadata={"language": lang, "score": float(score)}
                )
        
        return None
    
    def _detect_by_affiliation(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region by affiliation/institution."""
        # Check country code first
        country = entry.get("CountryCodes", [])
        if country and isinstance(country, list) and country[0]:
            region = get_region_for_territory(country[0])
            if region != "R0":
                return RegionDetectionResult(
                    region_code=region,
                    confidence=0.9,
                    detection_method="affiliation",
                    metadata={"country": country[0]}
                )
        
        # Check affiliation timeline
        timeline = entry.get("AffiliationTimeline", [])
        if timeline:
            # Use most recent affiliation
            current = [aff for aff in timeline if aff.get("to") is None]
            if current:
                country = current[0].get("country")
                if country:
                    region = get_region_for_territory(country)
                    if region != "R0":
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.85,
                            detection_method="affiliation",
                            metadata={"country": country, "source": "timeline"}
                        )
        
        return None
    
    def _detect_by_doi(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region by DOI prefix."""
        # Look for DOI in variants or identifiers
        doi = None
        
        # Check variants
        for variant in entry.get("Variants", {}).get("Observed", []):
            source = variant.get("source", "")
            if "doi" in source.lower():
                # Extract DOI from source
                import re
                doi_match = re.search(r'10\.\d{4,}(?:\.\d+)?/[-._;()/:\w]+', source)
                if doi_match:
                    doi = doi_match.group()
                    break
        
        if not doi:
            return None
        
        # Match DOI prefix
        for prefix, country in sorted(self._doi_prefix_map.items(), key=lambda x: len(x[0]), reverse=True):
            if doi.startswith(prefix):
                region = get_region_for_territory(country)
                if region != "R0":
                    return RegionDetectionResult(
                        region_code=region,
                        confidence=0.7,
                        detection_method="doi",
                        metadata={"doi_prefix": prefix, "country": country}
                    )
        
        return None
    
    def _apply_diaspora_overlay(
        self, 
        entry: Dict[str, Any], 
        candidates: List[RegionDetectionResult]
    ) -> List[RegionDetectionResult]:
        """Apply diaspora overlay rules."""
        # Get birth year
        birth_year = entry.get("BirthYear")
        if not birth_year or not isinstance(birth_year, int):
            return candidates
        
        # Check diaspora mappings
        for candidate in candidates:
            country = candidate.metadata.get("country")
            if country and country in self._diaspora_config:
                rules = self._diaspora_config[country]
                for rule in rules:
                    date_range = rule.get("range", "")
                    if self._year_in_range(birth_year, date_range):
                        # Update region
                        candidate.region_code = rule["region"]
                        candidate.metadata["diaspora_applied"] = True
                        break
        
        return candidates
    
    def _year_in_range(self, year: int, range_str: str) -> bool:
        """Check if year is in range string (e.g., "1950-1980", "-2015", "2016-")."""
        if not range_str:
            return False
        
        parts = range_str.split("-")
        if len(parts) == 2:
            start = int(parts[0]) if parts[0] else float('-inf')
            end = int(parts[1]) if parts[1] else float('inf')
            return start <= year <= end
        
        return False
    
    def process_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an entry through region detection and apply regional rules.
        
        Args:
            entry: Entry to process
            
        Returns:
            Processed entry with region code
            
        Raises:
            RegionRuleError: If regional processing fails
        """
        # Detect region
        detection = self.detect_region(entry)
        entry["_region"] = detection.region_code
        entry["_region_confidence"] = detection.confidence
        entry["_region_detection"] = detection.metadata
        
        # Get region processor
        region = self.get_region(detection.region_code)
        if not region:
            if detection.region_code == "Z0":
                # Quarantine - minimal processing
                return entry
            else:
                raise ValueError(f"No processor for region {detection.region_code}")
        
        # Apply regional processing
        try:
            region.clean(entry)
            region.augment(entry)
            region.validate(entry)
            
            # Generate order key
            entry["_order_key"] = region.order_key(entry)
            
        except RegionRuleError as e:
            # Route to quarantine on failure
            logger.warning(f"Region processing failed for {entry.get('GlobalID')}: {e}")
            entry["_region"] = "Z0"
            entry["_region_error"] = str(e)
        
        return entry