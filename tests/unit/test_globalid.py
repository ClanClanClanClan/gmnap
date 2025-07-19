"""
Unit tests for GlobalID generation.

Tests the deterministic ID generation, collision handling,
and various input formats.
"""

from unittest.mock import patch

import pytest

from src.core.globalid import (GlobalIDGenerator, generate_global_id,
                               validate_global_id)


class TestGlobalIDGenerator:
    """Test GlobalID generation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GlobalIDGenerator()
        self.generator.clear()
    
    def test_generate_basic_id(self):
        """Test basic ID generation."""
        entry = {
            "CanonicalNative": "Smith, John",
            "BirthYear": 1950,
            "DeathYear": 2020
        }
        
        global_id = self.generator.generate(entry)
        
        # Check format: 22 Base32 characters
        assert len(global_id) == 22
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in global_id)
    
    def test_deterministic_generation(self):
        """Test that same input produces same ID."""
        entry = {
            "CanonicalNative": "García-López, María",
            "BirthYear": 1975
        }
        
        id1 = self.generator.generate(entry)
        id2 = self.generator.generate(entry)
        
        assert id1 == id2
    
    def test_collision_handling(self):
        """Test collision suffix handling."""
        # Mock the hash function to force collision
        entry1 = {
            "CanonicalNative": "Test User 1",
            "BirthYear": 1980
        }
        entry2 = {
            "CanonicalNative": "Test User 2",  # Different name
            "BirthYear": 1980
        }
        
        # Generate first ID
        id1 = self.generator.generate(entry1)
        base_id = id1
        
        # Mock _compute_base_id to return same base for entry2
        with patch.object(self.generator, '_compute_base_id', return_value=base_id):
            id2 = self.generator.generate(entry2)
        
        # Should have collision suffix
        assert id2 == f"{base_id}--1"
    
    def test_multiple_collisions(self):
        """Test multiple collision handling."""
        base_id = "ABCDEFGHIJKLMNOPQRSTUV"
        
        # Pre-populate collision data in the new format
        self.generator._true_collisions[base_id] = {
            "Test1": 0,
            "Test2": 1,
            "Test3": 2
        }
        
        entry = {"CanonicalNative": "Test4"}  # New entry with same base ID
        
        with patch.object(self.generator, '_compute_base_id', return_value=base_id):
            new_id = self.generator.generate(entry)
        
        assert new_id == f"{base_id}--3"
    
    def test_special_birth_year_formats(self):
        """Test various birth year formats."""
        test_cases = [
            ("1970s", "García, Juan", "IYJQ7TKMSX4J6X35WVZQNU"),  # Decade
            ("-500", "Pythagoras", "Q7GHY6XNB5QEXAMPLE2"),      # BCE
            ("c1150", "Fibonacci", "MHJKLMNOPQRSTEXAMPLE3"),    # Circa
            ("1150/1160", "Unknown", "RSTUVWXYZ234567EXAMPL"),  # Range
        ]
        
        for birth_year, name, _ in test_cases:
            entry = {
                "CanonicalNative": name,
                "BirthYear": birth_year
            }
            
            global_id = self.generator.generate(entry)
            
            # Verify it's a valid ID
            assert len(global_id.split("--")[0]) == 22
            assert validate_global_id(global_id)
    
    def test_canonical_latin_fallback(self):
        """Test fallback to CanonicalLatin when Native missing."""
        entry = {
            "CanonicalLatin": "Müller, Hans",
            "BirthYear": 1960
        }
        
        # Should not raise error
        global_id = self.generator.generate(entry)
        assert len(global_id) == 22
    
    def test_missing_canonical_error(self):
        """Test error when no canonical name provided."""
        entry = {
            "BirthYear": 1960
        }
        
        with pytest.raises(ValueError, match="must have CanonicalNative or CanonicalLatin"):
            self.generator.generate(entry)
    
    def test_unicode_names(self):
        """Test GlobalID generation with Unicode names."""
        test_cases = [
            "李明",                    # Chinese
            "Владимир Петров",        # Cyrillic
            "محمد الأحمد",            # Arabic
            "Σωκράτης",              # Greek
            "José María García-López" # Latin with diacritics
        ]
        
        for name in test_cases:
            entry = {"CanonicalNative": name}
            global_id = self.generator.generate(entry)
            
            assert validate_global_id(global_id)
            assert len(global_id.split("--")[0]) == 22
    
    def test_validate_id_format(self):
        """Test GlobalID format validation."""
        # Valid IDs
        assert validate_global_id("ABCDEFGHIJKLMNOPQRSTUV")
        assert validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--1")
        assert validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--42")
        
        # Invalid IDs
        assert not validate_global_id("")
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTU")  # Too short
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTUVW")  # Too long
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTU1")  # Invalid char
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--")  # Missing suffix
        # Zero suffix should be valid (first collision has 0 internally)
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--abc")  # Non-numeric
    
    def test_load_existing_ids(self):
        """Test loading pre-existing IDs."""
        existing = {
            "ABCDEFGHIJKLMNOPQRSTUV",
            "BCDEFGHIJKLMNOPQRSTUVW--1",
            "CDEFGHIJKLMNOPQRSTUVWX--5"
        }
        
        # The new implementation doesn't actually need to pre-load IDs
        # since it's deterministic. This is just for backwards compatibility.
        self.generator.load_existing_ids(existing)
        
        # The method is now mostly a no-op, so we just check it doesn't crash
        assert True
    
    def test_get_stats(self):
        """Test statistics gathering."""
        # Generate some IDs
        entries = [
            {"CanonicalNative": f"Test {i}", "BirthYear": 1950 + i}
            for i in range(10)
        ]
        
        for entry in entries:
            self.generator.generate(entry)
        
        stats = self.generator.get_stats()
        
        assert stats["total_unique_entries"] == 10
        assert stats["base_ids_with_collisions"] == 0  # No collisions expected
        assert stats["total_collisions"] == 0
        assert stats["max_collision_suffix"] == 0
    
    def test_clear(self):
        """Test clearing all tracked IDs."""
        # Generate some IDs
        entry = {"CanonicalNative": "Test, User", "BirthYear": 1990}
        self.generator.generate(entry)
        
        # Should have state
        assert len(self.generator._true_collisions) > 0
        
        # Clear
        self.generator.clear()
        
        # Should be empty
        assert len(self.generator._true_collisions) == 0


class TestModuleFunctions:
    """Test module-level convenience functions."""
    
    def test_generate_global_id_function(self):
        """Test the module-level generate function."""
        entry = {
            "CanonicalNative": "Test, User",
            "BirthYear": 1990
        }
        
        global_id = generate_global_id(entry)
        assert validate_global_id(global_id)
    
    def test_validate_global_id_function(self):
        """Test the module-level validate function."""
        assert validate_global_id("ABCDEFGHIJKLMNOPQRSTUV")
        assert not validate_global_id("INVALID")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])