#!/usr/bin/env python3
"""
Tests for enhanced quality gates
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.quality_gates import (
    EnhancedQualityGates,
    ValidationResult,
    SchemaValidator,
    RoundtripValidator,
    CoherenceValidator,
    DuplicateDetector,
    PerformanceMonitor,
    CompletenessChecker,
    ConsistencyVerifier,
    AuthorityValidator,
)


class TestSchemaValidator:
    """Test schema validation gate"""

    @pytest.mark.asyncio
    async def test_valid_entry(self):
        """Test validation of a valid entry"""
        validator = SchemaValidator()

        entry = {
            "CanonicalLatin": "Smith, John",
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",  # 22 chars
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.95,
        }

        result = await validator.validate(entry)
        assert result.passed is True
        assert result.score == 1.0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test validation with missing fields"""
        validator = SchemaValidator()

        entry = {
            "CanonicalLatin": "Smith, John",
            # Missing GlobalID, DetectedRegion, UpdatedAt, Confidence
        }

        result = await validator.validate(entry)
        assert result.passed is False
        assert result.score < 1.0
        assert len(result.errors) > 0
        assert "Missing required field" in result.errors[0]

    @pytest.mark.asyncio
    async def test_invalid_globalid(self):
        """Test invalid GlobalID format"""
        validator = SchemaValidator()

        entry = {
            "CanonicalLatin": "Smith, John",
            "GlobalID": "invalid-id",  # Should be 22 char Base32
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.95,
        }

        result = await validator.validate(entry)
        assert result.passed is False
        assert "Invalid GlobalID format" in str(result.errors)

    @pytest.mark.asyncio
    async def test_confidence_out_of_range(self):
        """Test confidence value validation"""
        validator = SchemaValidator()

        entry = {
            "CanonicalLatin": "Smith, John",
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 1.5,  # Out of range
        }

        result = await validator.validate(entry)
        assert result.passed is False
        assert "Confidence out of range" in str(result.errors)


class TestRoundtripValidator:
    """Test roundtrip validation gate"""

    @pytest.mark.asyncio
    async def test_latin_only_entry(self):
        """Test entry with only Latin script"""
        validator = RoundtripValidator()

        entry = {
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
        }  # Same as Latin

        result = await validator.validate(entry)
        assert result.passed is True
        assert result.score >= 0.9

    @pytest.mark.asyncio
    async def test_with_native_script(self):
        """Test entry with native script"""
        validator = RoundtripValidator()

        entry = {
            "CanonicalLatin": "Li Ming",
            "CanonicalNative": "李明",
            "RegionalExtras": {"transliteration": "Li Ming"},
        }

        result = await validator.validate(entry)
        assert result.passed is True
        assert result.details["has_native_script"] is True

    @pytest.mark.asyncio
    async def test_with_roundtrip_variant(self):
        """Test entry with roundtrip variant"""
        validator = RoundtripValidator()

        entry = {
            "CanonicalLatin": "Kim Jung-un",
            "CanonicalNative": "김정은",
            "Variants": {"Synthesised": [{"str": "Kim Jong-un", "type": "roundtrip"}]},
        }

        result = await validator.validate(entry)
        assert result.passed is True
        assert result.score == 1.0


class TestCoherenceValidator:
    """Test coherence validation gate"""

    @pytest.mark.asyncio
    async def test_coherent_entry(self):
        """Test fully coherent entry"""
        validator = CoherenceValidator()

        entry = {
            "DetectedRegion": "A1",
            "LanguageOfPublication": ["eng"],
            "CountryCodes": ["US"],
            "Confidence": 0.95,
            "GraphQualityGates": {"graph_coherence_score": 0.92},
        }

        result = await validator.validate(entry)
        assert result.passed is True
        assert result.score >= 0.9

    @pytest.mark.asyncio
    async def test_language_mismatch(self):
        """Test language-region mismatch"""
        validator = CoherenceValidator()

        entry = {
            "DetectedRegion": "E4",  # Korea
            "LanguageOfPublication": ["eng"],  # Should be kor
            "CountryCodes": ["KR"],
        }

        result = await validator.validate(entry)
        assert len(result.warnings) > 0
        assert "unexpected for region" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_confidence_discrepancy(self):
        """Test confidence-graph score discrepancy"""
        validator = CoherenceValidator()

        entry = {
            "Confidence": 0.95,
            "GraphQualityGates": {"graph_coherence_score": 0.55},  # Large discrepancy
        }

        result = await validator.validate(entry)
        assert len(result.warnings) > 0
        assert "discrepancy" in result.warnings[0].lower()


class TestDuplicateDetector:
    """Test duplicate detection gate"""

    @pytest.mark.asyncio
    async def test_unique_entries(self):
        """Test unique entries"""
        detector = DuplicateDetector()

        entry1 = {
            "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA",
            "CanonicalLatin": "Smith, John",
            "DetectedRegion": "A1",
        }

        entry2 = {
            "GlobalID": "BBBBBBBBBBBBBBBBBBBBBB",
            "CanonicalLatin": "Jones, Mary",
            "DetectedRegion": "A1",
        }

        result1 = await detector.validate(entry1)
        assert result1.passed is True

        result2 = await detector.validate(entry2)
        assert result2.passed is True

    @pytest.mark.asyncio
    async def test_duplicate_detection(self):
        """Test duplicate entry detection"""
        detector = DuplicateDetector()

        entry1 = {
            "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA",
            "CanonicalLatin": "Smith, John William",
            "DetectedRegion": "A1",
            "CountryCodes": ["US"],
        }

        # Nearly identical entry
        entry2 = {
            "GlobalID": "BBBBBBBBBBBBBBBBBBBBBB",
            "CanonicalLatin": "Smith, John William",
            "DetectedRegion": "A1",
            "CountryCodes": ["US"],
        }

        result1 = await detector.validate(entry1)
        assert result1.passed is True

        result2 = await detector.validate(entry2)
        # Should detect as potential duplicate
        assert len(result2.warnings) > 0


class TestCompletenessChecker:
    """Test completeness checking gate"""

    @pytest.mark.asyncio
    async def test_complete_entry(self):
        """Test fully complete entry"""
        checker = CompletenessChecker()

        entry = {
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "LanguageOfPublication": ["eng"],
            "FamilyNameType": "patronymic",
            "Gender": "male",
            "CountryCodes": ["US"],
            "Confidence": 0.95,
            "Historic": False,
            "GDPR_DATA": False,
            "RegionalExtras": {"region_confidence": 0.95},
            "GraphQualityGates": {"score": 0.9},
            "Variants": {"Observed": []},
        }

        result = await checker.validate(entry)
        assert result.passed is True
        assert result.score > 0.9
        assert result.details["completeness_percentage"] > 90

    @pytest.mark.asyncio
    async def test_minimal_entry(self):
        """Test minimal entry"""
        checker = CompletenessChecker(threshold=0.3)  # Lower threshold for minimal

        entry = {
            "CanonicalLatin": "Smith, John",
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.95,
        }

        result = await checker.validate(entry)
        # Should pass with required fields but lower score
        assert result.passed is True
        assert result.score < 0.6
        assert result.score > 0.3  # Should be above minimal threshold


class TestConsistencyVerifier:
    """Test consistency verification gate"""

    @pytest.mark.asyncio
    async def test_consistent_entry(self):
        """Test internally consistent entry"""
        verifier = ConsistencyVerifier()

        entry = {
            "CanonicalLatin": "Smith Jones",  # Proper capitalization
            "Confidence": 0.95,
            "UpdatedAt": datetime.now().isoformat(),
            "Variants": {"Observed": [{"str": "Smith, J."}, {"str": "S. Jones"}]},
        }

        result = await verifier.validate(entry)
        assert result.passed is True
        assert result.score >= 0.9

    @pytest.mark.asyncio
    async def test_future_date(self):
        """Test future date detection"""
        verifier = ConsistencyVerifier()

        future_date = datetime.now() + timedelta(days=1)
        entry = {"UpdatedAt": future_date.isoformat()}

        result = await verifier.validate(entry)
        assert result.passed is False
        assert "future" in str(result.errors).lower()

    @pytest.mark.asyncio
    async def test_duplicate_variants(self):
        """Test duplicate variant detection"""
        verifier = ConsistencyVerifier()

        entry = {
            "Variants": {
                "Observed": [{"str": "Smith, J."}, {"str": "Smith, J."}]
            }  # Duplicate
        }

        result = await verifier.validate(entry)
        assert len(result.warnings) > 0
        assert "Duplicate variant" in result.warnings[0]


class TestAuthorityValidator:
    """Test authority validation gate"""

    @pytest.mark.asyncio
    async def test_with_authority_data(self):
        """Test entry with authority data"""
        validator = AuthorityValidator()

        entry = {
            "authority_data": {
                "ORCID": {
                    "confidence": 0.95,
                    "orcid": "0000-0002-1234-5678",
                    "publications": 42,
                },
                "Crossref": {"confidence": 0.88, "affiliations": ["MIT", "Harvard"]},
            }
        }

        result = await validator.validate(entry)
        assert result.passed is True
        assert result.score > 0.8
        assert result.details["has_authority_data"] is True
        assert result.details["source_count"] == 2

    @pytest.mark.asyncio
    async def test_no_authority_data(self):
        """Test entry without authority data"""
        validator = AuthorityValidator()

        entry = {}

        result = await validator.validate(entry)
        # Should pass with neutral score
        assert result.passed is True
        assert result.score == 0.5
        assert len(result.warnings) > 0


class TestEnhancedQualityGates:
    """Test the full quality gate system"""

    @pytest.mark.asyncio
    async def test_validate_entry(self):
        """Test full validation of an entry"""
        gates = EnhancedQualityGates()

        entry = {
            "CanonicalLatin": "Smith, John William",
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.95,
            "LanguageOfPublication": ["eng"],
            "CountryCodes": ["US"],
        }

        result = await gates.validate_entry(entry)

        assert "passed" in result
        assert "score" in result
        assert "gates" in result
        assert "summary" in result

        # Check all gates were run
        assert len(result["gates"]) == 8
        assert result["summary"]["gates_run"] == 8

    @pytest.mark.asyncio
    async def test_validate_batch(self):
        """Test batch validation"""
        gates = EnhancedQualityGates()

        entries = [
            {
                "CanonicalLatin": "Smith, John",
                "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA",
                "DetectedRegion": "A1",
                "UpdatedAt": datetime.now().isoformat(),
                "Confidence": 0.95,
            },
            {
                "CanonicalLatin": "李明",
                "GlobalID": "BBBBBBBBBBBBBBBBBBBBBB",
                "DetectedRegion": "E1",
                "UpdatedAt": datetime.now().isoformat(),
                "Confidence": 0.92,
            },
            {
                "CanonicalLatin": "Invalid Entry"
                # Missing required fields
            },
        ]

        result = await gates.validate_batch(entries)

        assert "batch_results" in result
        assert "summary" in result
        assert result["summary"]["total_entries"] == 3
        assert result["summary"]["failed_entries"] >= 1  # At least the invalid entry


def main():
    """Run all tests"""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()
