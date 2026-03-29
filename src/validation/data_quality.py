"""
Data quality validation rules for GMNAP.
Ensures data completeness, consistency, and accuracy.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """
    Validates data quality aspects of GMNAP entries.

    Focuses on:
    - Completeness: Required fields are present and meaningful
    - Consistency: Data is internally consistent
    - Accuracy: Data follows expected patterns and ranges
    - Duplication: Detects potential duplicate entries
    - Temporal validity: Dates and timelines make sense
    """

    def __init__(self):
        self.current_year = datetime.now().year

        # Define completeness requirements
        self.required_fields = {"GlobalID", "CanonicalLatin", "Confidence"}

        self.highly_recommended_fields = {
            "BirthYear",
            "PrimaryMSC",
            "CountryCodes",
            "AuthorityIDs",
            "LanguageOfPublication",
        }

        # Common name patterns that might indicate issues
        self.suspicious_patterns = [
            r"^test",
            r"^example",
            r"^unknown",
            r"^anonymous",
            r"^user\d+",
            r"^temp",
            r"^placeholder",
            r"^\d+$",  # Just numbers
            r"^[A-Z]{1,2}$",  # Just initials
        ]

        # Valid MSC top-level categories
        self.valid_msc_categories = {
            "00",
            "01",
            "03",
            "05",
            "06",
            "08",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
            "20",
            "22",
            "26",
            "28",
            "30",
            "31",
            "32",
            "33",
            "34",
            "35",
            "37",
            "39",
            "40",
            "41",
            "42",
            "43",
            "44",
            "45",
            "46",
            "47",
            "49",
            "51",
            "52",
            "53",
            "54",
            "55",
            "57",
            "58",
            "60",
            "62",
            "65",
            "68",
            "70",
            "74",
            "76",
            "78",
            "80",
            "81",
            "82",
            "83",
            "85",
            "86",
            "90",
            "91",
            "92",
            "93",
            "94",
            "97",
        }

    def validate_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data quality of a single entry.

        Args:
            entry: Entry to validate

        Returns:
            Dictionary with validation results:
            - is_valid: Overall validity
            - completeness_score: 0-100 score
            - errors: List of error messages
            - warnings: List of warning messages
            - suggestions: List of improvement suggestions
        """
        result = {
            "is_valid": True,
            "completeness_score": 100,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Check completeness
        self._check_completeness(entry, result)

        # Check consistency
        self._check_consistency(entry, result)

        # Check accuracy
        self._check_accuracy(entry, result)

        # Check temporal validity
        self._check_temporal_validity(entry, result)

        # Check for suspicious patterns
        self._check_suspicious_patterns(entry, result)

        # Check authority ID quality
        self._check_authority_ids(entry, result)

        # Check MSC codes
        self._check_msc_codes(entry, result)

        # Check affiliations
        self._check_affiliations(entry, result)

        # Calculate final validity
        result["is_valid"] = len(result["errors"]) == 0

        return result

    def _check_completeness(self, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Check data completeness."""
        # Required fields
        missing_required = []
        for field in self.required_fields:
            if field not in entry or not entry[field]:
                missing_required.append(field)
                result["errors"].append(f"Missing required field: {field}")

        # Highly recommended fields
        missing_recommended = []
        for field in self.highly_recommended_fields:
            if field not in entry or not entry[field]:
                missing_recommended.append(field)

        if missing_recommended:
            result["warnings"].append(
                f"Missing recommended fields: {', '.join(missing_recommended)}"
            )
            result["suggestions"].append("Consider adding: " + ", ".join(missing_recommended))

        # Calculate completeness score
        total_fields = len(self.required_fields) + len(self.highly_recommended_fields)
        missing_count = len(missing_required) + (len(missing_recommended) * 0.5)
        result["completeness_score"] = int(100 * (1 - missing_count / total_fields))

        # Check for meaningful content
        canonical = entry.get("CanonicalLatin", "")
        if canonical and len(canonical.strip()) < 3:
            result["errors"].append("CanonicalLatin too short to be meaningful")

        # Check for empty collections
        if "PrimaryMSC" in entry and isinstance(entry["PrimaryMSC"], list):
            if len(entry["PrimaryMSC"]) == 0:
                result["warnings"].append("PrimaryMSC is empty list")

    def _check_consistency(self, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Check internal consistency."""
        # Check name consistency
        canonical = entry.get("CanonicalLatin", "")

        # Check if CanonicalNative exists for non-Latin scripts
        if "RegionCode" in entry:
            region = entry["RegionCode"]
            # Regions that should have CanonicalNative
            native_regions = [
                "B1",
                "B2",
                "C1",
                "C2",
                "C3",
                "C4",
                "C5",
                "D1",
                "D2",
                "D3",
                "D4",
                "E1",
                "E2",
                "E3",
                "E4",
            ]
            if region in native_regions and not entry.get("CanonicalNative"):
                result["warnings"].append(f"Region {region} should have CanonicalNative")

        # Check variant consistency
        variants = entry.get("Variants", {})
        if variants:
            # Check for duplicates
            all_variants = []
            for variant_type, variant_list in variants.items():
                if isinstance(variant_list, list):
                    all_variants.extend(v.get("name", "") for v in variant_list)

            variant_counts = Counter(all_variants)
            duplicates = [v for v, count in variant_counts.items() if count > 1]
            if duplicates:
                result["warnings"].append(f"Duplicate variants detected: {', '.join(duplicates)}")

        # Check confidence score consistency
        confidence = entry.get("Confidence", 0)
        auth_ids = entry.get("AuthorityIDs", {})

        # High confidence should have authority IDs
        if confidence >= 80 and not auth_ids:
            result["warnings"].append("High confidence (≥80) but no authority IDs")
            result["suggestions"].append("Consider adding authority IDs or reducing confidence")

        # Low confidence with many authority IDs is suspicious
        if confidence < 50 and len(auth_ids) > 3:
            result["warnings"].append(
                f"Low confidence ({confidence}) but {len(auth_ids)} authority IDs"
            )

    def _check_accuracy(self, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Check data accuracy and patterns."""
        # Check country codes
        country_codes = entry.get("CountryCodes", [])
        for code in country_codes:
            if not (isinstance(code, str) and len(code) == 2 and code.isupper()):
                result["errors"].append(f"Invalid country code format: {code}")

        # Check language codes
        languages = entry.get("LanguageOfPublication", [])
        for lang in languages:
            if not (isinstance(lang, str) and 2 <= len(lang) <= 3 and lang.islower()):
                result["errors"].append(f"Invalid language code format: {lang}")

        # Check for reasonable number of languages
        if len(languages) > 10:
            result["warnings"].append(f"Unusually high number of languages: {len(languages)}")

        # Check email format if present
        email = entry.get("Email")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            result["errors"].append(f"Invalid email format: {email}")

        # Check URL format if present
        homepage = entry.get("Homepage")
        if homepage and not re.match(r"^https?://[^\s]+$", homepage):
            result["warnings"].append(f"Invalid or non-HTTPS URL: {homepage}")

    def _check_temporal_validity(self, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Check temporal data validity."""
        birth_year = entry.get("BirthYear")
        death_year = entry.get("DeathYear")

        # Parse years
        birth_num = self._parse_year(birth_year)
        death_num = self._parse_year(death_year)

        if birth_num is not None:
            # Check reasonable birth year
            if birth_num > self.current_year:
                result["errors"].append(f"Birth year in future: {birth_year}")
            elif birth_num < 1800:
                result["warnings"].append(f"Very old birth year: {birth_year}")
            elif birth_num > self.current_year - 18:
                result["warnings"].append(f"Person younger than 18: born {birth_year}")

        if death_num is not None:
            # Check reasonable death year
            if death_num > self.current_year:
                result["errors"].append(f"Death year in future: {death_year}")

            # Check lifespan
            if birth_num is not None:
                lifespan = death_num - birth_num
                if lifespan < 0:
                    result["errors"].append(f"Death before birth: {birth_year} - {death_year}")
                elif lifespan < 20:
                    result["warnings"].append(f"Very short lifespan: {lifespan} years")
                elif lifespan > 110:
                    result["warnings"].append(f"Unusually long lifespan: {lifespan} years")

        # Check affiliation timeline
        timeline = entry.get("AffiliationTimeline", [])
        if timeline:
            # Check chronological order
            prev_year = None
            for i, affiliation in enumerate(timeline):
                from_year = affiliation.get("from")
                to_year = affiliation.get("to")

                if from_year is not None and to_year is not None:
                    if to_year < from_year:
                        result["errors"].append(f"Affiliation {i}: 'to' before 'from'")

                if prev_year is not None and from_year is not None:
                    if from_year < prev_year:
                        result["warnings"].append("Affiliation timeline not in chronological order")

                if to_year is not None:
                    prev_year = to_year
                elif from_year is not None:
                    prev_year = from_year

        # Check name events chronology
        name_events = entry.get("NameEvents", [])
        if len(name_events) > 1:
            years = [event.get("year") for event in name_events if event.get("year")]
            if years != sorted(years):
                result["errors"].append("NameEvents not in chronological order")

    def _check_suspicious_patterns(self, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Check for suspicious or test data patterns."""
        canonical = entry.get("CanonicalLatin", "").lower()

        for pattern in self.suspicious_patterns:
            if re.match(pattern, canonical):
                result["warnings"].append(f"Suspicious name pattern: matches '{pattern}'")
                result["suggestions"].append("Verify this is not test/placeholder data")

        # Check for keyboard mashing
        if re.search(r"([a-z])\1{4,}", canonical):
            result["warnings"].append("Repeated characters detected (possible keyboard mashing)")

        # Check for very generic names
        generic_names = ["smith", "jones", "wang", "li", "zhang", "chen"]
        name_parts = canonical.split()
        if len(name_parts) == 1 and name_parts[0] in generic_names:
            result["warnings"].append("Single generic name - may need more identification")

    def _check_authority_ids(self, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Check authority ID quality."""
        auth_ids = entry.get("AuthorityIDs", {})

        if not auth_ids:
            return

        # Check for suspicious patterns in IDs
        for service, value in auth_ids.items():
            if isinstance(value, str):
                # Check for placeholder IDs
                if value in ["0", "000", "test", "temp", "unknown"]:
                    result["warnings"].append(f"{service} ID looks like placeholder: {value}")

                # Service-specific checks
                if service == "ORCID":
                    # ORCID format: XXXX-XXXX-XXXX-XXXX where last char can be X
                    if not re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", value):
                        result["errors"].append(f"Invalid ORCID format: {value}")

                elif service == "zbMATH":
                    if not re.match(r"^[a-z-]+\.[a-z-]+(\.[a-z-]+)?$", value):
                        result["warnings"].append(f"Unusual zbMATH format: {value}")

            elif isinstance(value, dict):
                # Check for license on proprietary sources
                if service in ["Scopus", "WoS", "Dimensions"]:
                    if "license" not in value:
                        result["errors"].append(f"{service} missing required license field")

    def _check_msc_codes(self, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Check MSC code validity."""
        msc_codes = entry.get("PrimaryMSC", [])

        if not msc_codes:
            return

        seen_codes = set()
        for msc in msc_codes:
            code = msc.get("code", "")
            source = msc.get("source", "")

            # Check format
            if not re.match(r"^\d{2}[A-Z]\d{2}$", code):
                result["errors"].append(f"Invalid MSC format: {code}")
                continue

            # Check category
            category = code[:2]
            if category not in self.valid_msc_categories:
                result["warnings"].append(f"Unknown MSC category: {category}")

            # Check source
            if not source:
                result["errors"].append(f"MSC code {code} missing source")
            elif source not in ["zbMATH", "MathSciNet", "OpenAlex", "manual"]:
                result["warnings"].append(f"Unusual MSC source: {source}")

            # Check duplicates
            if code in seen_codes:
                result["warnings"].append(f"Duplicate MSC code: {code}")
            seen_codes.add(code)

        # Check for too many codes
        if len(msc_codes) > 10:
            result["warnings"].append(f"Unusually high number of MSC codes: {len(msc_codes)}")
            result["suggestions"].append("Consider keeping only primary research areas")

    def _check_affiliations(self, entry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Check affiliation data quality."""
        timeline = entry.get("AffiliationTimeline", [])

        if not timeline:
            # Check if we have birth year but no affiliations
            if entry.get("BirthYear"):
                birth_num = self._parse_year(entry["BirthYear"])
                if birth_num and birth_num < self.current_year - 25:
                    result["suggestions"].append("Consider adding affiliation information")
            return

        # Check for gaps in timeline
        sorted_timeline = sorted(timeline, key=lambda x: x.get("from", 0))

        for i in range(len(sorted_timeline) - 1):
            current = sorted_timeline[i]
            next_aff = sorted_timeline[i + 1]

            current_to = current.get("to")
            next_from = next_aff.get("from")

            if current_to and next_from:
                gap = next_from - current_to
                if gap > 5:
                    result["warnings"].append(f"Large gap in affiliation timeline: {gap} years")

        # Check institution names
        for i, aff in enumerate(timeline):
            inst = aff.get("institution", "")
            if inst and len(inst) < 3:
                result["errors"].append(f"Institution name too short in affiliation {i}")

            # Check for test institutions
            if re.search(r"test|temp|example", inst, re.I):
                result["warnings"].append(f"Suspicious institution name: {inst}")

    def _parse_year(self, year_value) -> Optional[int]:
        """Parse year from various formats."""
        if isinstance(year_value, int):
            return year_value

        if isinstance(year_value, str):
            # Handle formats like "1970s", "c1150", "-500"
            if year_value.endswith("s"):
                return int(year_value[:-1])
            elif year_value.startswith("c"):
                return int(year_value[1:])
            else:
                try:
                    return int(year_value)
                except ValueError:
                    return None

        return None

    def check_duplicate_potential(self, entry1: Dict[str, Any], entry2: Dict[str, Any]) -> float:
        """
        Check if two entries might be duplicates.

        Args:
            entry1: First entry
            entry2: Second entry

        Returns:
            Similarity score (0-1, higher means more likely duplicate)
        """
        score = 0.0

        # Check name similarity
        name1 = entry1.get("CanonicalLatin", "").lower()
        name2 = entry2.get("CanonicalLatin", "").lower()

        if name1 == name2:
            score += 0.4
        elif self._fuzzy_match(name1, name2) > 0.8:
            score += 0.3

        # Check birth year
        birth1 = self._parse_year(entry1.get("BirthYear"))
        birth2 = self._parse_year(entry2.get("BirthYear"))

        if birth1 and birth2:
            if birth1 == birth2:
                score += 0.2
            elif abs(birth1 - birth2) <= 2:
                score += 0.1

        # Check authority ID overlap
        auth1 = set(entry1.get("AuthorityIDs", {}).keys())
        auth2 = set(entry2.get("AuthorityIDs", {}).keys())

        if auth1 and auth2:
            overlap = len(auth1 & auth2) / len(auth1 | auth2)
            score += overlap * 0.3

        # Check country overlap
        countries1 = set(entry1.get("CountryCodes", []))
        countries2 = set(entry2.get("CountryCodes", []))

        if countries1 and countries2 and countries1 & countries2:
            score += 0.1

        return min(score, 1.0)

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Simple fuzzy string matching."""
        # Levenshtein distance normalized by max length
        if not s1 or not s2:
            return 0.0

        # Simple character-based similarity
        longer = s1 if len(s1) > len(s2) else s2
        shorter = s2 if len(s1) > len(s2) else s1

        if len(longer) == 0:
            return 1.0

        # Count matching characters
        matches = sum(1 for c in shorter if c in longer)
        return matches / len(longer)

    def generate_quality_report(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a quality report for a collection of entries.

        Args:
            entries: List of entries to analyze

        Returns:
            Quality report with statistics and recommendations
        """
        report = {
            "total_entries": len(entries),
            "valid_entries": 0,
            "average_completeness": 0,
            "common_errors": Counter(),
            "common_warnings": Counter(),
            "field_coverage": {},
            "recommendations": [],
        }

        completeness_scores = []

        for entry in entries:
            result = self.validate_entry(entry)

            if result["is_valid"]:
                report["valid_entries"] += 1

            completeness_scores.append(result["completeness_score"])

            # Count errors and warnings
            for error in result["errors"]:
                report["common_errors"][error] += 1

            for warning in result["warnings"]:
                report["common_warnings"][warning] += 1

        # Calculate statistics
        if completeness_scores:
            report["average_completeness"] = sum(completeness_scores) / len(completeness_scores)

        # Field coverage analysis
        all_fields = set()
        for entry in entries:
            all_fields.update(entry.keys())

        for field in all_fields:
            count = sum(1 for e in entries if field in e and e[field])
            report["field_coverage"][field] = {
                "count": count,
                "percentage": (count / len(entries)) * 100,
            }

        # Generate recommendations
        if report["average_completeness"] < 80:
            report["recommendations"].append(
                "Focus on improving data completeness - many entries missing key fields"
            )

        most_common_error = report["common_errors"].most_common(1)
        if most_common_error:
            error, count = most_common_error[0]
            if count > len(entries) * 0.1:
                report["recommendations"].append(
                    f"Address systematic issue: '{error}' affects {count} entries"
                )

        return report


# Global instance
data_quality_validator = DataQualityValidator()
