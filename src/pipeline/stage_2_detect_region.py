"""
GMNAP v7.0 Pipeline Stage 2: Regional Detection
Detects appropriate regional processors for incoming data.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.errors import RegionalDetectionError
from ..core.romanization_detector import RomanizationDetector
from ..regions.manager import RegionManager


class DetectRegionStage:
    """Stage 2: Regional detection and processor assignment"""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize regional detection stage"""
        self.config_path = config_path or Path("./config")
        self.region_manager = RegionManager(self.config_path)
        self.romanization_detector = RomanizationDetector()
        self.confidence_threshold = 0.7  # Default confidence threshold

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect appropriate regional processors for each record

        Args:
            context: Pipeline execution context with raw data

        Returns:
            Updated context with regional assignments
        """
        try:
            raw_data = context.get("raw_data", [])
            config = context.get("config", {})

            # Update confidence threshold from config
            regional_config = config.get("regions", {})
            self.confidence_threshold = regional_config.get("detection_threshold", 0.7)

            # Detect regions for each record
            regional_assignments = []
            detection_stats = {
                "total_records": len(raw_data),
                "detected_regions": {},
                "unassigned_records": 0,
                "multi_region_records": 0,
            }

            for i, record in enumerate(raw_data):
                try:
                    assignments = self._detect_regions_for_record(record)

                    if not assignments:
                        detection_stats["unassigned_records"] += 1
                        # Assign to residual processor
                        assignments = [("R0", 0.5, "residual_fallback")]
                    elif len(assignments) > 1:
                        detection_stats["multi_region_records"] += 1

                    # Update statistics
                    for region_code, confidence, method in assignments:
                        if region_code not in detection_stats["detected_regions"]:
                            detection_stats["detected_regions"][region_code] = 0
                        detection_stats["detected_regions"][region_code] += 1

                    regional_assignments.append(
                        {
                            "record_index": i,
                            "record_id": record.get("GlobalID", f"record_{i}"),
                            "assignments": assignments,
                            "primary_region": (
                                assignments[0][0] if assignments else "R0"
                            ),
                        }
                    )

                except Exception as e:
                    logger.warning(
                        f"Regional detection failed for record {i}: {str(e)}"
                    )
                    # Fallback to residual processor
                    regional_assignments.append(
                        {
                            "record_index": i,
                            "record_id": record.get("GlobalID", f"record_{i}"),
                            "assignments": [("R0", 0.3, "error_fallback")],
                            "primary_region": "R0",
                        }
                    )
                    detection_stats["unassigned_records"] += 1

            # Update context
            context["regional_assignments"] = regional_assignments
            context["detection_statistics"] = detection_stats
            context["stage_2_completed"] = True

            return context

        except Exception as e:
            raise RegionalDetectionError(f"Stage 2 regional detection failed: {str(e)}")

    def _detect_regions_for_record(
        self, record: Dict[str, Any]
    ) -> List[Tuple[str, float, str]]:
        """
        Detect appropriate regions for a single record

        Returns:
            List of tuples: (region_code, confidence, detection_method)
        """
        assignments = []

        # Extract name components
        canonical_latin = record.get("CanonicalLatin", "")
        canonical_native = record.get("CanonicalNative", "")

        # Method 1: Script-based detection from native field
        if canonical_native:
            script_assignments = self._detect_by_script(canonical_native)
            assignments.extend(script_assignments)

        # Method 2: Language detection from Latin field
        if canonical_latin:
            language_assignments = self._detect_by_language(canonical_latin)
            assignments.extend(language_assignments)

        # Method 3: Pattern-based detection
        pattern_assignments = self._detect_by_patterns(record)
        assignments.extend(pattern_assignments)

        # Method 4: Contextual detection (institution, location, etc.)
        context_assignments = self._detect_by_context(record)
        assignments.extend(context_assignments)

        # Sort by confidence and remove duplicates
        assignments = self._deduplicate_assignments(assignments)

        # Filter by confidence threshold
        filtered_assignments = [
            (region, conf, method)
            for region, conf, method in assignments
            if conf >= self.confidence_threshold
        ]

        return filtered_assignments[:3]  # Return top 3 assignments

    def _detect_by_script(self, text: str) -> List[Tuple[str, float, str]]:
        """Detect region based on script/writing system"""
        assignments = []

        # Analyze character ranges to determine script
        script_scores = self._analyze_script_composition(text)

        for script, score in script_scores.items():
            if score > 0.5:  # Minimum script presence threshold
                region_mappings = self._get_script_to_region_mappings()
                if script in region_mappings:
                    for region_code, confidence_multiplier in region_mappings[script]:
                        final_confidence = score * confidence_multiplier
                        assignments.append(
                            (region_code, final_confidence, f"script_{script}")
                        )

        return assignments

    def _detect_by_language(self, text: str) -> List[Tuple[str, float, str]]:
        """Detect region based on language detection"""
        assignments = []

        try:
            # Use fastText or similar for language detection
            detected_languages = self._detect_languages(text)

            for lang_code, confidence in detected_languages:
                region_mappings = self._get_language_to_region_mappings()
                if lang_code in region_mappings:
                    for region_code, multiplier in region_mappings[lang_code]:
                        final_confidence = confidence * multiplier
                        assignments.append(
                            (region_code, final_confidence, f"language_{lang_code}")
                        )

        except Exception as e:
            print(f"Language detection failed: {str(e)}")

        return assignments

    def _detect_by_patterns(
        self, record: Dict[str, Any]
    ) -> List[Tuple[str, float, str]]:
        """Detect region based on name patterns and structure"""
        assignments = []

        canonical_latin = record.get("CanonicalLatin", "")

        if not canonical_latin:
            return assignments

        # Pattern-based heuristics
        patterns = {
            # Western patterns
            "surname_first": r"^[A-Z][a-z]+,\s+[A-Z][a-z]+",  # "Smith, John"
            "particle_names": r"\b(van|von|de|del|della|du|da|le|la)\b",  # European particles
            "hyphenated_surnames": r"[A-Z][a-z]+-[A-Z][a-z]+",  # "Smith-Jones"
            # Asian patterns
            "cjk_romanization": r"^[A-Z][a-z]+\s+[A-Z][a-z]+$",  # Simple romanization
            "korean_patterns": r"\b(Kim|Park|Lee|Choi|Jung|Kang|Cho|Yoon|Jang|Lim)\b",
            "chinese_patterns": r"\b(Wang|Zhang|Li|Liu|Chen|Yang|Huang|Zhao|Wu|Zhou)\b",
            "japanese_patterns": r"\b(Tanaka|Suzuki|Takahashi|Watanabe|Ito|Yamamoto|Nakamura)\b",
            # Other patterns
            "arabic_patterns": r"\b(Al|El|Ibn|Abu)\b",
            "slavic_patterns": r"(ovich|ovic|enko|sky|ski|czyk|wicz)$",
        }

        import re

        for pattern_name, pattern in patterns.items():
            if re.search(pattern, canonical_latin, re.IGNORECASE):
                region_confidence = self._pattern_to_region_confidence(pattern_name)
                assignments.extend(region_confidence)

        return assignments

    def _detect_by_context(
        self, record: Dict[str, Any]
    ) -> List[Tuple[str, float, str]]:
        """Detect region based on contextual information"""
        assignments = []

        # Institution-based detection
        institution = record.get("Institution", "")
        if institution:
            institution_regions = self._detect_institution_region(institution)
            assignments.extend(institution_regions)

        # Location-based detection
        location_fields = ["Country", "City", "Location", "Address"]
        for field in location_fields:
            if field in record:
                location_regions = self._detect_location_region(record[field])
                assignments.extend(location_regions)

        # Subject/field-based hints
        subject = record.get("Subject", "")
        if subject:
            subject_regions = self._detect_subject_region(subject)
            assignments.extend(subject_regions)

        return assignments

    def _analyze_script_composition(self, text: str) -> Dict[str, float]:
        """Analyze the script composition of text"""
        if not text:
            return {}

        script_counts = {
            "latin": 0,
            "cyrillic": 0,
            "arabic": 0,
            "hebrew": 0,
            "han": 0,  # Chinese/Japanese/Korean ideographs
            "hiragana": 0,
            "katakana": 0,
            "hangul": 0,
            "devanagari": 0,
            "thai": 0,
            "other": 0,
        }

        for char in text:
            code = ord(char)

            if 0x0041 <= code <= 0x007A or 0x00C0 <= code <= 0x024F:  # Latin
                script_counts["latin"] += 1
            elif 0x0400 <= code <= 0x04FF:  # Cyrillic
                script_counts["cyrillic"] += 1
            elif 0x0600 <= code <= 0x06FF:  # Arabic
                script_counts["arabic"] += 1
            elif 0x0590 <= code <= 0x05FF:  # Hebrew
                script_counts["hebrew"] += 1
            elif 0x4E00 <= code <= 0x9FFF:  # CJK Ideographs
                script_counts["han"] += 1
            elif 0x3040 <= code <= 0x309F:  # Hiragana
                script_counts["hiragana"] += 1
            elif 0x30A0 <= code <= 0x30FF:  # Katakana
                script_counts["katakana"] += 1
            elif 0xAC00 <= code <= 0xD7AF:  # Hangul
                script_counts["hangul"] += 1
            elif 0x0900 <= code <= 0x097F:  # Devanagari
                script_counts["devanagari"] += 1
            elif 0x0E00 <= code <= 0x0E7F:  # Thai
                script_counts["thai"] += 1
            else:
                script_counts["other"] += 1

        total_chars = len(text)
        script_ratios = {
            script: count / total_chars for script, count in script_counts.items()
        }

        return script_ratios

    def _get_script_to_region_mappings(self) -> Dict[str, List[Tuple[str, float]]]:
        """Get mapping from scripts to regions with confidence multipliers"""
        return {
            "han": [("E1", 0.9), ("E2", 0.8), ("E3", 0.7)],
            "hangul": [("E4", 0.95)],
            "hiragana": [("E3", 0.95)],
            "katakana": [("E3", 0.9)],
            "cyrillic": [("B1", 0.9), ("B2", 0.8)],
            "arabic": [("C3", 0.8), ("C4", 0.8), ("C5", 0.8)],
            "hebrew": [("C6", 0.95)],
            "devanagari": [("D1", 0.9), ("D3", 0.7)],
            "thai": [("E6", 0.95)],
            "latin": [
                ("A1", 0.6),
                ("A2", 0.6),
                ("G1", 0.5),
            ],  # Lower confidence for Latin
        }

    def _get_language_to_region_mappings(self) -> Dict[str, List[Tuple[str, float]]]:
        """Get mapping from languages to regions"""
        return {
            "en": [("A1", 0.8), ("A4", 0.6), ("A5", 0.6), ("F2", 0.5)],
            "zh": [("E1", 0.9), ("E2", 0.8)],
            "ja": [("E3", 0.95)],
            "ko": [("E4", 0.95)],
            "ru": [("B1", 0.9)],
            "ar": [("C3", 0.8), ("C4", 0.8), ("C5", 0.8)],
            "he": [("C6", 0.95)],
            "hi": [("D1", 0.9)],
            "bn": [("D3", 0.9)],
            "th": [("E6", 0.9)],
            "vi": [("E5", 0.9)],
            "es": [("G1", 0.8)],
            "pt": [("G1", 0.7)],
            "fr": [("A2", 0.7), ("F1", 0.6)],
            "de": [("A2", 0.8)],
            "it": [("A2", 0.7)],
        }

    def _pattern_to_region_confidence(
        self, pattern_name: str
    ) -> List[Tuple[str, float, str]]:
        """Convert pattern matches to region confidence scores"""
        pattern_mappings = {
            "surname_first": [("A1", 0.7, "pattern_surname_first")],
            "particle_names": [("A2", 0.8, "pattern_particles")],
            "hyphenated_surnames": [
                ("A1", 0.6, "pattern_hyphenated"),
                ("A2", 0.5, "pattern_hyphenated"),
            ],
            "korean_patterns": [("E4", 0.8, "pattern_korean_surname")],
            "chinese_patterns": [
                ("E1", 0.7, "pattern_chinese_surname"),
                ("E2", 0.6, "pattern_chinese_surname"),
            ],
            "japanese_patterns": [("E3", 0.8, "pattern_japanese_surname")],
            "arabic_patterns": [
                ("C3", 0.7, "pattern_arabic"),
                ("C4", 0.7, "pattern_arabic"),
            ],
            "slavic_patterns": [
                ("B1", 0.7, "pattern_slavic"),
                ("B2", 0.7, "pattern_slavic"),
            ],
        }

        return pattern_mappings.get(pattern_name, [])

    def _detect_languages(self, text: str) -> List[Tuple[str, float]]:
        """Detect languages in text using fastText or similar"""
        # Placeholder implementation - in real implementation would use fastText
        # For now, return simple heuristics

        detected = []

        # Simple character-based heuristics
        if any(0x4E00 <= ord(c) <= 0x9FFF for c in text):
            detected.append(("zh", 0.8))
        elif any(0xAC00 <= ord(c) <= 0xD7AF for c in text):
            detected.append(("ko", 0.9))
        elif any(0x3040 <= ord(c) <= 0x309F for c in text):
            detected.append(("ja", 0.9))
        elif any(0x0400 <= ord(c) <= 0x04FF for c in text):
            detected.append(("ru", 0.8))
        elif any(0x0600 <= ord(c) <= 0x06FF for c in text):
            detected.append(("ar", 0.8))
        else:
            # Default to English for Latin script
            detected.append(("en", 0.6))

        return detected

    def _detect_institution_region(
        self, institution: str
    ) -> List[Tuple[str, float, str]]:
        """Detect region based on institution name"""
        assignments = []

        # University/institution keywords by region
        institution_keywords = {
            "A1": ["university", "college", "institute", "MIT", "Harvard", "Stanford"],
            "A2": ["université", "universität", "università", "universidad"],
            "E1": ["大学", "university", "学院"],
            "E3": ["大学", "だいがく", "university"],
            "E4": ["대학교", "university", "대학"],
        }

        institution_lower = institution.lower()

        for region, keywords in institution_keywords.items():
            for keyword in keywords:
                if keyword.lower() in institution_lower:
                    assignments.append((region, 0.6, f"institution_{keyword}"))
                    break

        return assignments

    def _detect_location_region(self, location: str) -> List[Tuple[str, float, str]]:
        """Detect region based on location information"""
        assignments = []

        # Country/location mappings
        location_mappings = {
            "A1": [
                "usa",
                "united states",
                "canada",
                "australia",
                "new zealand",
                "uk",
                "britain",
            ],
            "A2": ["germany", "france", "italy", "spain", "netherlands", "belgium"],
            "E1": ["china", "prc", "mainland china"],
            "E2": ["taiwan", "hong kong", "singapore"],
            "E3": ["japan"],
            "E4": ["korea", "south korea", "north korea"],
            "G1": ["brazil", "mexico", "argentina", "chile", "colombia"],
        }

        location_lower = location.lower()

        for region, locations in location_mappings.items():
            for loc in locations:
                if loc in location_lower:
                    assignments.append((region, 0.8, f"location_{loc}"))
                    break

        return assignments

    def _detect_subject_region(self, subject: str) -> List[Tuple[str, float, str]]:
        """Detect region based on subject/field hints"""
        # This is a lower-confidence method
        assignments = []

        subject_lower = subject.lower()

        # Some fields might have regional tendencies
        if "chinese" in subject_lower or "mandarin" in subject_lower:
            assignments.append(("E1", 0.4, "subject_chinese"))
        elif "japanese" in subject_lower:
            assignments.append(("E3", 0.4, "subject_japanese"))
        elif "korean" in subject_lower:
            assignments.append(("E4", 0.4, "subject_korean"))

        return assignments

    def _deduplicate_assignments(
        self, assignments: List[Tuple[str, float, str]]
    ) -> List[Tuple[str, float, str]]:
        """Remove duplicate region assignments, keeping highest confidence"""
        region_best = {}

        for region, confidence, method in assignments:
            if region not in region_best or confidence > region_best[region][0]:
                region_best[region] = (confidence, method)

        # Convert back to list and sort by confidence
        result = [
            (region, conf, method) for region, (conf, method) in region_best.items()
        ]
        result.sort(key=lambda x: x[1], reverse=True)

        return result
