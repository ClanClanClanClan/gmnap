"""
Enhanced Quality Gates for GMNAP V7
Implements comprehensive validation with 8 quality gates
"""

import re
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import logging
from abc import ABC, abstractmethod


@dataclass
class ValidationResult:
    """Result of a validation check"""

    passed: bool
    score: float  # 0.0 to 1.0
    gate_name: str
    details: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


class QualityGate(ABC):
    """Abstract base class for quality gates"""

    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Validate an entry"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Gate name"""
        pass


class SchemaValidator(QualityGate):
    """Validates entries against V7 JSON schema"""

    @property
    def name(self) -> str:
        return "schema_validation"

    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Validate against V7 schema requirements"""
        errors = []
        warnings = []

        # Required fields per V7 spec
        required_fields = [
            "CanonicalLatin",
            "GlobalID",
            "DetectedRegion",
            "UpdatedAt",
            "Confidence",
        ]

        # Check required fields
        missing_fields = []
        for field in required_fields:
            if field not in entry or entry[field] is None:
                missing_fields.append(field)
                errors.append(f"Missing required field: {field}")

        # Validate GlobalID format (22-char Base32)
        if "GlobalID" in entry and entry["GlobalID"]:
            gid = entry["GlobalID"]
            if not re.match(r"^[A-Z2-7]{22}$", gid):
                errors.append(f"Invalid GlobalID format: {gid}")

        # Validate UpdatedAt format
        if "UpdatedAt" in entry and entry["UpdatedAt"]:
            try:
                datetime.fromisoformat(entry["UpdatedAt"].replace("Z", "+00:00"))
            except:
                errors.append(f"Invalid UpdatedAt format: {entry['UpdatedAt']}")

        # Validate Confidence range
        if "Confidence" in entry and entry["Confidence"] is not None:
            conf = entry["Confidence"]
            if not (0.0 <= conf <= 1.0):
                errors.append(f"Confidence out of range: {conf}")

        # Calculate score
        total_checks = len(required_fields) + 3  # fields + format checks
        passed_checks = total_checks - len(errors)
        score = passed_checks / total_checks

        return ValidationResult(
            passed=len(errors) == 0,
            score=score,
            gate_name=self.name,
            details={
                "missing_fields": missing_fields,
                "total_fields": len(required_fields),
                "format_valid": len(errors) - len(missing_fields) == 0,
            },
            errors=errors,
            warnings=warnings,
        )


class RoundtripValidator(QualityGate):
    """Validates name roundtrip consistency"""

    @property
    def name(self) -> str:
        return "roundtrip_validation"

    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Check if names can roundtrip correctly"""
        errors = []
        warnings = []

        canonical_latin = entry.get("CanonicalLatin", "")
        canonical_native = entry.get("CanonicalNative", "")

        if not canonical_latin:
            errors.append("Missing CanonicalLatin for roundtrip check")
            return ValidationResult(
                passed=False,
                score=0.0,
                gate_name=self.name,
                details={"roundtrip_possible": False},
                errors=errors,
                warnings=warnings,
            )

        # Check if native script exists and differs from Latin
        has_native = canonical_native and canonical_native != canonical_latin

        # For entries with native scripts, check consistency
        roundtrip_score = 1.0
        if has_native:
            # Check if we have transliteration info
            if "RegionalExtras" in entry:
                extras = entry["RegionalExtras"]
                if "transliteration" in extras:
                    # Verify transliteration matches
                    transliterated = extras["transliteration"]
                    if transliterated.lower() != canonical_latin.lower():
                        roundtrip_score = 0.8
                        warnings.append("Transliteration mismatch detected")

        # Check variant consistency
        if "Variants" in entry:
            variants = entry["Variants"]
            if "Synthesised" in variants:
                for variant in variants["Synthesised"]:
                    if variant.get("type") == "roundtrip":
                        # Found roundtrip variant, good
                        roundtrip_score = min(roundtrip_score + 0.1, 1.0)

        return ValidationResult(
            passed=roundtrip_score >= self.threshold,
            score=roundtrip_score,
            gate_name=self.name,
            details={"has_native_script": has_native, "roundtrip_possible": roundtrip_score >= 0.9},
            errors=errors,
            warnings=warnings,
        )


class CoherenceValidator(QualityGate):
    """Validates cross-field coherence"""

    @property
    def name(self) -> str:
        return "coherence_validation"

    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Check cross-field consistency"""
        errors = []
        warnings = []
        coherence_checks = []

        # Check region-language coherence
        region = entry.get("DetectedRegion", "")
        languages = entry.get("LanguageOfPublication", [])

        region_language_map = {
            "A1": ["eng"],
            "A2": ["eng", "fra", "deu", "spa", "ita", "por", "nld"],
            "B1": ["rus", "ukr", "bel"],
            "B2": ["hrv", "srp", "slv", "ces", "pol"],
            "C1": ["tur", "aze", "kaz"],
            "C2": ["fas", "tgk"],
            "C3": ["ara", "heb"],
            "C4": ["ara"],
            "D1": ["hin", "urd"],
            "E1": ["zho", "cmn"],
            "E3": ["jpn"],
            "E4": ["kor"],
            "E5": ["vie"],
        }

        if region in region_language_map:
            expected_langs = region_language_map[region]
            if languages and not any(lang in expected_langs for lang in languages):
                warnings.append(f"Language {languages} unexpected for region {region}")
                coherence_checks.append(False)
            else:
                coherence_checks.append(True)

        # Check country-region coherence
        countries = entry.get("CountryCodes", [])
        region_country_map = {
            "A1": ["US", "GB", "CA", "AU", "NZ"],
            "A2": ["FR", "DE", "ES", "IT", "PT", "NL", "BE"],
            "B1": ["RU", "UA", "BY"],
            "E1": ["CN"],
            "E3": ["JP"],
            "E4": ["KR", "KP"],
        }

        if region in region_country_map and countries:
            expected_countries = region_country_map[region]
            if not any(country in expected_countries for country in countries):
                warnings.append(f"Country {countries} unexpected for region {region}")
                coherence_checks.append(False)
            else:
                coherence_checks.append(True)

        # Check confidence-quality coherence
        confidence = entry.get("Confidence", 0)
        quality_gates = entry.get("GraphQualityGates", {})
        graph_score = quality_gates.get("graph_coherence_score", 0)

        if abs(confidence - graph_score) > 0.3:
            warnings.append(
                f"Large discrepancy between confidence ({confidence}) and graph score ({graph_score})"
            )
            coherence_checks.append(False)
        else:
            coherence_checks.append(True)

        # Calculate score
        if coherence_checks:
            score = sum(coherence_checks) / len(coherence_checks)
        else:
            score = 1.0  # No checks performed, assume coherent

        return ValidationResult(
            passed=score >= self.threshold,
            score=score,
            gate_name=self.name,
            details={
                "checks_performed": len(coherence_checks),
                "checks_passed": sum(coherence_checks),
            },
            errors=errors,
            warnings=warnings,
        )


class DuplicateDetector(QualityGate):
    """Detects potential duplicate entries"""

    def __init__(self, threshold: float = 0.85):
        super().__init__(threshold)
        self.seen_entries = {}  # Cache for duplicate detection

    @property
    def name(self) -> str:
        return "duplicate_detection"

    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Check for duplicate entries"""
        errors = []
        warnings = []

        # Generate fingerprint
        fingerprint = self._generate_fingerprint(entry)

        # Check against seen entries
        is_duplicate = False
        similarity_scores = []

        for seen_fp, seen_entry in self.seen_entries.items():
            similarity = self._calculate_similarity(fingerprint, seen_fp)
            similarity_scores.append(similarity)

            if similarity >= self.threshold:
                is_duplicate = True
                warnings.append(f"Potential duplicate of {seen_entry['GlobalID']}")

        # Add to cache
        self.seen_entries[fingerprint] = {
            "GlobalID": entry.get("GlobalID", ""),
            "CanonicalLatin": entry.get("CanonicalLatin", ""),
        }

        # Calculate score (inverse of max similarity)
        max_similarity = max(similarity_scores) if similarity_scores else 0.0
        score = 1.0 - max_similarity

        return ValidationResult(
            passed=not is_duplicate,
            score=score,
            gate_name=self.name,
            details={
                "is_duplicate": is_duplicate,
                "max_similarity": max_similarity,
                "comparisons": len(similarity_scores),
            },
            errors=errors,
            warnings=warnings,
        )

    def _generate_fingerprint(self, entry: Dict[str, Any]) -> str:
        """Generate a fingerprint for duplicate detection"""
        # Normalize and combine key fields
        name = entry.get("CanonicalLatin", "").lower().strip()
        name = re.sub(r"[^a-z0-9]", "", name)

        region = entry.get("DetectedRegion", "")
        countries = "".join(sorted(entry.get("CountryCodes", [])))

        return f"{name}_{region}_{countries}"

    def _calculate_similarity(self, fp1: str, fp2: str) -> float:
        """Calculate similarity between two fingerprints"""
        if fp1 == fp2:
            return 1.0

        # Simple character-based similarity
        common = sum(1 for c1, c2 in zip(fp1, fp2) if c1 == c2)
        max_len = max(len(fp1), len(fp2))

        return common / max_len if max_len > 0 else 0.0


class PerformanceMonitor(QualityGate):
    """Monitors processing performance"""

    @property
    def name(self) -> str:
        return "performance_monitoring"

    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Check processing performance"""
        errors = []
        warnings = []

        # Check if timing metadata exists
        if "_timing" in entry:
            timings = entry["_timing"]
            total_time = timings.get("total_ms", 0)

            # Thresholds in milliseconds
            if total_time > 1000:
                errors.append(f"Processing too slow: {total_time}ms")
            elif total_time > 500:
                warnings.append(f"Processing slower than target: {total_time}ms")

            score = max(0, 1.0 - (total_time / 1000))
        else:
            # No timing data, assume good performance
            score = 1.0

        return ValidationResult(
            passed=len(errors) == 0,
            score=score,
            gate_name=self.name,
            details={
                "has_timing_data": "_timing" in entry,
                "processing_time_ms": entry.get("_timing", {}).get("total_ms", 0),
            },
            errors=errors,
            warnings=warnings,
        )


class CompletenessChecker(QualityGate):
    """Checks entry completeness"""

    @property
    def name(self) -> str:
        return "completeness_check"

    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Check if entry has all recommended fields"""
        errors = []
        warnings = []

        # V7 recommended fields
        recommended_fields = {
            "CanonicalLatin": 1.0,  # Required
            "CanonicalNative": 0.8,
            "GlobalID": 1.0,  # Required
            "DetectedRegion": 1.0,  # Required
            "UpdatedAt": 1.0,  # Required
            "LanguageOfPublication": 0.9,
            "FamilyNameType": 0.7,
            "Gender": 0.6,
            "CountryCodes": 0.9,
            "Confidence": 1.0,  # Required
            "Historic": 0.5,
            "GDPR_DATA": 0.8,
            "RegionalExtras": 0.8,
            "GraphQualityGates": 0.7,
            "Variants": 0.9,
        }

        # Calculate completeness
        total_weight = sum(recommended_fields.values())
        completed_weight = 0.0
        missing_important = []

        for field, weight in recommended_fields.items():
            if field in entry and entry[field] is not None:
                # Check if field has meaningful content
                value = entry[field]
                if isinstance(value, str) and value.strip():
                    completed_weight += weight
                elif isinstance(value, (list, dict)) and value:
                    completed_weight += weight
                elif isinstance(value, (int, float, bool)):
                    completed_weight += weight
                else:
                    if weight >= 0.8:
                        missing_important.append(field)
            else:
                if weight >= 0.8:
                    missing_important.append(field)
                    if weight == 1.0:
                        errors.append(f"Missing required field: {field}")
                    else:
                        warnings.append(f"Missing important field: {field}")

        score = completed_weight / total_weight

        return ValidationResult(
            passed=len(errors) == 0 and score >= self.threshold,
            score=score,
            gate_name=self.name,
            details={
                "completeness_percentage": score * 100,
                "missing_important_fields": missing_important,
                "total_fields": len(recommended_fields),
            },
            errors=errors,
            warnings=warnings,
        )


class ConsistencyVerifier(QualityGate):
    """Verifies internal consistency of entries"""

    @property
    def name(self) -> str:
        return "consistency_verification"

    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Verify internal consistency"""
        errors = []
        warnings = []
        consistency_checks = []

        # Check name consistency
        canonical_latin = entry.get("CanonicalLatin", "")
        if canonical_latin:
            # Check for consistent capitalization
            words = canonical_latin.split()
            for word in words:
                if word and not (word[0].isupper() or word.islower()):
                    warnings.append(f"Inconsistent capitalization in: {word}")
                    consistency_checks.append(False)
                else:
                    consistency_checks.append(True)

        # Check variant consistency
        if "Variants" in entry:
            variants = entry["Variants"]
            seen_variants = set()

            for variant_type in ["Observed", "Synthesised"]:
                if variant_type in variants:
                    for variant in variants[variant_type]:
                        var_str = variant.get("str", "")
                        if var_str in seen_variants:
                            warnings.append(f"Duplicate variant: {var_str}")
                            consistency_checks.append(False)
                        else:
                            seen_variants.add(var_str)
                            consistency_checks.append(True)

        # Check date consistency
        if "UpdatedAt" in entry:
            try:
                updated = datetime.fromisoformat(entry["UpdatedAt"].replace("Z", "+00:00"))
                if updated > datetime.now():
                    errors.append("UpdatedAt is in the future")
                    consistency_checks.append(False)
                else:
                    consistency_checks.append(True)
            except:
                pass

        # Check numeric consistency
        confidence = entry.get("Confidence", 0)
        if not (0.0 <= confidence <= 1.0):
            errors.append(f"Invalid confidence value: {confidence}")
            consistency_checks.append(False)
        else:
            consistency_checks.append(True)

        # Calculate score
        if consistency_checks:
            score = sum(consistency_checks) / len(consistency_checks)
        else:
            score = 1.0

        return ValidationResult(
            passed=len(errors) == 0 and score >= self.threshold,
            score=score,
            gate_name=self.name,
            details={
                "checks_performed": len(consistency_checks),
                "checks_passed": sum(consistency_checks),
                "consistency_rate": score,
            },
            errors=errors,
            warnings=warnings,
        )


class AuthorityValidator(QualityGate):
    """Validates authority data quality"""

    @property
    def name(self) -> str:
        return "authority_validation"

    async def validate(self, entry: Dict[str, Any]) -> ValidationResult:
        """Validate authority enrichment data"""
        errors = []
        warnings = []

        authority_data = entry.get("authority_data", {})

        if not authority_data:
            # No authority data
            score = 0.5  # Neutral score if no data
            warnings.append("No authority data present")
        else:
            # Check authority data quality
            valid_sources = 0
            total_sources = 0
            min_confidence = 1.0

            for source, data in authority_data.items():
                total_sources += 1

                # Check if data has required fields
                if isinstance(data, dict):
                    if "confidence" in data:
                        conf = data["confidence"]
                        if 0.0 <= conf <= 1.0:
                            valid_sources += 1
                            min_confidence = min(min_confidence, conf)
                        else:
                            errors.append(f"Invalid confidence from {source}: {conf}")

                    # Check for meaningful data
                    if any(key in data for key in ["orcid", "publications", "affiliations"]):
                        valid_sources += 0.5  # Bonus for rich data

            if total_sources > 0:
                score = min(1.0, (valid_sources / total_sources) * min_confidence)
            else:
                score = 0.5

        return ValidationResult(
            passed=len(errors) == 0
            and score >= self.threshold * 0.5,  # Lower threshold for authority
            score=score,
            gate_name=self.name,
            details={
                "has_authority_data": bool(authority_data),
                "source_count": len(authority_data),
                "data_quality_score": score,
            },
            errors=errors,
            warnings=warnings,
        )


class EnhancedQualityGates:
    """Enhanced quality gate system with 8 validators"""

    def __init__(self):
        self.gates = {
            "schema": SchemaValidator(),
            "roundtrip": RoundtripValidator(),
            "coherence": CoherenceValidator(),
            "duplicate": DuplicateDetector(),
            "performance": PerformanceMonitor(),
            "completeness": CompletenessChecker(),
            "consistency": ConsistencyVerifier(),
            "authority": AuthorityValidator(),
        }
        self.logger = logging.getLogger(__name__)

    async def validate_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Run all quality gates on an entry"""
        results = {}
        all_errors = []
        all_warnings = []
        total_score = 0.0

        for gate_name, gate in self.gates.items():
            try:
                result = await gate.validate(entry)
                results[gate_name] = {
                    "passed": result.passed,
                    "score": result.score,
                    "details": result.details,
                    "errors": result.errors,
                    "warnings": result.warnings,
                }

                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
                total_score += result.score

            except Exception as e:
                self.logger.error(f"Gate {gate_name} failed: {e}")
                results[gate_name] = {"passed": False, "score": 0.0, "error": str(e)}

        # Overall validation result
        num_gates = len(self.gates)
        avg_score = total_score / num_gates if num_gates > 0 else 0.0
        all_passed = all(r.get("passed", False) for r in results.values())

        return {
            "passed": all_passed,
            "score": avg_score,
            "gates": results,
            "errors": all_errors,
            "warnings": all_warnings,
            "summary": {
                "gates_run": num_gates,
                "gates_passed": sum(1 for r in results.values() if r.get("passed", False)),
                "average_score": avg_score,
                "error_count": len(all_errors),
                "warning_count": len(all_warnings),
            },
        }

    async def validate_batch(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a batch of entries"""
        results = []

        for entry in entries:
            result = await self.validate_entry(entry)
            results.append({"GlobalID": entry.get("GlobalID", ""), "validation": result})

        # Calculate batch statistics
        total_entries = len(entries)
        passed_entries = sum(1 for r in results if r["validation"]["passed"])
        avg_score = (
            sum(r["validation"]["score"] for r in results) / total_entries
            if total_entries > 0
            else 0.0
        )

        return {
            "batch_results": results,
            "summary": {
                "total_entries": total_entries,
                "passed_entries": passed_entries,
                "failed_entries": total_entries - passed_entries,
                "validation_rate": (
                    (passed_entries / total_entries * 100) if total_entries > 0 else 0
                ),
                "average_score": avg_score,
            },
        }
