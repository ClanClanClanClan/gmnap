"""
Unit tests for A1 (Core Anglo-Sphere) region implementation.

Tests name cleaning, augmentation, validation, and order key generation
for English-speaking regions.
"""

import pytest

from src.regions.a_groups.a1_anglo_sphere import A1_AngloSphere
from src.regions.base import RegionRuleError


class TestA1AngloSphere:
    """Test A1 region processing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.region = A1_AngloSphere()

    def test_region_metadata(self):
        """Test region configuration."""
        assert self.region.code == "A1"
        assert self.region.canonical_order == "Family, Given"
        assert "Latin" in self.region.scripts
        assert not self.region.mixed_scripts

    def test_title_removal(self):
        """Test removal of academic and social titles."""
        test_cases = [
            ("Dr. Smith, John", "Smith, John"),
            ("Prof. Johnson, Mary", "Johnson, Mary"),
            ("Mr. Brown, Robert", "Brown, Robert"),
            ("Dame Williams, Sarah", "Williams, Sarah"),
            ("Rev. Davis, Michael", "Davis, Michael"),
            ("Col. Wilson, James", "Wilson, James"),
        ]

        for input_name, expected in test_cases:
            entry = {"CanonicalLatin": input_name}
            self.region.clean(entry)
            assert entry["CanonicalLatin"] == expected

    def test_generational_suffix_removal(self):
        """Test removal of generational suffixes."""
        test_cases = [
            ("Smith, John Jr.", "Smith, John"),
            ("Johnson, Robert Sr.", "Johnson, Robert"),
            ("Brown, William III", "Brown, William"),
            ("Davis, Michael Jr", "Davis, Michael"),
            ("Wilson, James Esq.", "Wilson, James"),
            ("Miller, David PhD", "Miller, David"),
        ]

        for input_name, expected in test_cases:
            entry = {"CanonicalLatin": input_name}
            self.region.clean(entry)
            assert entry["CanonicalLatin"] == expected

    def test_punctuation_normalization(self):
        """Test punctuation normalization."""
        test_cases = [
            ("Smith,John", "Smith, John"),  # Add space after comma
            ("Smith, J.C.", "Smith, J. C."),  # Space after initials
            ("Smith, J C", "Smith, J. C."),  # Add periods to initials
            ("Smith , John", "Smith, John"),  # Remove extra spaces
            ("Smith,  John  ", "Smith, John"),  # Multiple spaces
        ]

        for input_name, expected in test_cases:
            entry = {"CanonicalLatin": input_name}
            self.region.clean(entry)
            assert entry["CanonicalLatin"] == expected

    def test_component_extraction(self):
        """Test name component extraction."""
        entry = {"CanonicalLatin": "Smith, John Charles"}
        self.region.augment(entry)

        extras = entry.get("RegionalExtras", {})
        assert extras["family_name"] == "Smith"
        assert extras["given_name"] == "John Charles"
        assert extras["first_name"] == "John"
        assert "middle_names" in extras or "middle_initials" in extras

    def test_middle_initial_extraction(self):
        """Test middle initial extraction."""
        test_cases = [
            ("Smith, John C.", {"first_name": "John", "middle_initials": ["C."]}),
            ("Smith, J. C.", {"first_name": "J.", "middle_initials": ["C."]}),
            (
                "Smith, John Charles",
                {"first_name": "John", "middle_names": ["Charles"]},
            ),
            ("Smith, J. C. D.", {"first_name": "J.", "middle_initials": ["C.", "D."]}),
        ]

        for name, expected in test_cases:
            entry = {"CanonicalLatin": name}
            self.region.augment(entry)
            extras = entry.get("RegionalExtras", {})

            for key, value in expected.items():
                assert extras.get(key) == value

    def test_particle_detection(self):
        """Test particle detection in family names."""
        test_cases = [
            (
                "van der Berg, Johannes",
                {"particles": ["van", "der"], "main_surname": "Berg"},
            ),
            ("de la Cruz, Maria", {"particles": ["de", "la"], "main_surname": "Cruz"}),
            ("O'Connor, Patrick", {}),  # Apostrophe not a particle
            ("MacDonald, Andrew", {}),  # Prefix not a particle
        ]

        for name, expected in test_cases:
            entry = {"CanonicalLatin": name}
            self.region.augment(entry)
            extras = entry.get("RegionalExtras", {})

            for key, value in expected.items():
                assert extras.get(key) == value

    def test_variant_generation(self):
        """Test synthesis of name variants."""
        entry = {"CanonicalLatin": "Smith, John C."}
        self.region.augment(entry)

        variants = entry.get("Variants", {}).get("Synthesised", [])

        # Should have at least collapsed initial variant
        collapsed = [v for v in variants if v.get("type") == "initial-collapse"]
        assert len(collapsed) > 0

        # Should have ASCII variant if needed
        [v for v in variants if v.get("type") == "ascii-lossy"]
        # May or may not have ASCII variant for this name

    def test_ascii_variant_generation(self):
        """Test ASCII variant generation for names with diacritics."""
        entry = {"CanonicalLatin": "García, José"}
        self.region.augment(entry)

        variants = entry.get("Variants", {}).get("Synthesised", [])
        ascii_variants = [v for v in variants if v.get("type") == "ascii-lossy"]

        assert len(ascii_variants) > 0
        assert ascii_variants[0]["str"] == "Garcia, Jose"

    def test_validation_success(self):
        """Test successful validation."""
        entry = {
            "CanonicalLatin": "Smith, John",
            "RegionalExtras": {"family_name": "Smith", "given_name": "John"},
        }

        # Should not raise exception
        self.region.validate(entry)

    def test_validation_missing_canonical(self):
        """Test validation failure for missing canonical name."""
        entry = {}

        with pytest.raises(RegionRuleError, match="Missing CanonicalLatin"):
            self.region.validate(entry)

    def test_validation_invalid_characters(self):
        """Test validation of character sets."""
        # Invalid characters for A1
        entry = {"CanonicalLatin": "Smith, 张三"}  # Chinese characters

        with pytest.raises(RegionRuleError, match="Invalid characters"):
            self.region.validate(entry)

    def test_validation_comma_format(self):
        """Test validation of comma usage."""
        invalid_entries = [
            {"CanonicalLatin": "Smith, John, Jr."},  # Too many commas
            {"CanonicalLatin": "Smith, "},  # Empty after comma
            {"CanonicalLatin": ", John"},  # Empty before comma
        ]

        for entry in invalid_entries:
            with pytest.raises(RegionRuleError):
                self.region.validate(entry)

    def test_validation_family_name_length(self):
        """Test family name minimum length."""
        entry = {
            "CanonicalLatin": "Smith, John",
            "RegionalExtras": {"family_name": "S", "given_name": "John"},  # Too short
        }

        with pytest.raises(RegionRuleError, match="Family name too short"):
            self.region.validate(entry)

    def test_validation_given_name_format(self):
        """Test given name format validation."""
        entry = {
            "CanonicalLatin": "Smith, John123",  # Invalid characters
            "RegionalExtras": {"family_name": "Smith", "given_name": "John123"},
        }

        with pytest.raises(RegionRuleError, match="Invalid given name format"):
            self.region.validate(entry)

    def test_order_key_generation(self):
        """Test deterministic order key generation."""
        entry = {
            "CanonicalLatin": "Smith, John",
            "RegionalExtras": {"family_name": "Smith", "given_name": "John"},
        }

        key1 = self.region.order_key(entry)
        key2 = self.region.order_key(entry)

        # Should be deterministic
        assert key1 == key2
        assert key1 == "SMITH, JOHN"

    def test_order_key_with_particles(self):
        """Test order key with particles."""
        entry = {
            "CanonicalLatin": "van der Berg, Johannes",
            "RegionalExtras": {
                "family_name": "van der Berg",
                "given_name": "Johannes",
                "particles": ["van", "der"],
                "main_surname": "Berg",
            },
        }

        key = self.region.order_key(entry)

        # Should sort by main surname, ignoring particles
        assert key == "BERG, JOHANNES"

    def test_order_key_punctuation_removal(self):
        """Test punctuation removal in order keys."""
        entry = {
            "CanonicalLatin": "O'Connor, Mary-Jane",
            "RegionalExtras": {"family_name": "O'Connor", "given_name": "Mary-Jane"},
        }

        key = self.region.order_key(entry)

        # Should remove punctuation for sorting
        assert key == "OCONNOR, MARYJANE"

    def test_order_key_whitespace_normalization(self):
        """Test whitespace normalization in order keys."""
        entry = {
            "CanonicalLatin": "Smith,  John   Charles",
            "RegionalExtras": {"family_name": "Smith", "given_name": "John   Charles"},
        }

        key = self.region.order_key(entry)

        # Should normalize whitespace
        assert key == "SMITH, JOHN CHARLES"

    def test_extended_latin_acceptance(self):
        """Test acceptance of extended Latin characters."""
        entry = {"CanonicalLatin": "García, José"}

        # Should not raise exception for Latin-1 supplement
        self.region.validate(entry)

    def test_full_processing_pipeline(self):
        """Test complete processing pipeline."""
        entry = {
            "CanonicalLatin": "Dr. Smith, John C. Jr.",
            "Variants": {"Observed": [], "Synthesised": []},
        }

        # Clean
        self.region.clean(entry)
        assert entry["CanonicalLatin"] == "Smith, John C."

        # Augment
        self.region.augment(entry)
        assert "RegionalExtras" in entry
        assert entry["RegionalExtras"]["family_name"] == "Smith"
        assert entry["RegionalExtras"]["given_name"] == "John C."

        # Validate
        self.region.validate(entry)  # Should not raise

        # Order key
        key = self.region.order_key(entry)
        assert key == "SMITH, JOHN C"

    def test_edge_cases(self):
        """Test edge cases and unusual inputs."""
        edge_cases = [
            "",  # Empty string
            "Smith",  # No comma
            "Smith, ",  # Empty given name
            ", John",  # Empty family name
            "Smith, John, Mary",  # Multiple commas
            "Smith-Jones, Mary-Anne",  # Hyphenated names
            "O'Malley, Seán",  # Irish names
            "St. John, Mary",  # Compound family name
        ]

        for name in edge_cases:
            entry = {"CanonicalLatin": name}

            try:
                self.region.clean(entry)
                self.region.augment(entry)
                self.region.validate(entry)
                self.region.order_key(entry)
            except RegionRuleError:
                # Some edge cases should fail validation
                pass
            except Exception as e:
                pytest.fail(f"Unexpected error for '{name}': {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
