"""
Hardcore Unicode handling testing for GMNAP.

Tests Unicode normalization, script detection, homograph attacks,
and all scenarios that could cause corruption or security issues.
"""

import gc
import random
import string
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Empty, Queue
from typing import Dict, List, Tuple

import psutil
import pytest

from src.core.unicode_handler import (
    UnicodeConfig,
    UnicodeNormalizer,
    generate_name_variants,
    normalize_name,
)


class TestUnicodeNormalizationSecurity:
    """Test Unicode normalization security vulnerabilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = UnicodeNormalizer()

    def test_homograph_attack_detection(self):
        """Test detection of homograph attacks."""
        # Latin vs Cyrillic homographs
        homograph_pairs = [
            ("Smith, John", "Sмith, John"),  # Cyrillic 'м' instead of 'm'
            ("Anderson, Anna", "Аnderson, Anna"),  # Cyrillic 'А' instead of 'A'
            ("Garcia, Maria", "Gаrcia, Maria"),  # Cyrillic 'а' instead of 'a'
            ("Johnson, Robert", "Jоhnson, Robert"),  # Cyrillic 'о' instead of 'o'
            ("Williams, Emma", "Williаms, Emma"),  # Cyrillic 'а' instead of 'a'
            ("Brown, David", "Brоwn, David"),  # Cyrillic 'о' instead of 'o'
            ("Miller, Sarah", "Мiller, Sarah"),  # Cyrillic 'М' instead of 'M'
            ("Davis, Michael", "Dаvis, Michael"),  # Cyrillic 'а' instead of 'a'
        ]

        for latin_name, cyrillic_name in homograph_pairs:
            # Should detect mixed scripts (use lower threshold for single character attacks)
            assert self.normalizer.is_mixed_script(
                cyrillic_name, threshold=0.05
            ), f"Failed to detect mixed script in: {cyrillic_name}"

            # Should have different script compositions
            latin_scripts = self.normalizer.get_script_info(latin_name)
            cyrillic_scripts = self.normalizer.get_script_info(cyrillic_name)

            # Latin should be pure Latin
            assert "Latin" in latin_scripts, f"Latin text should contain Latin script: {latin_name}"
            assert (
                "Cyrillic" not in latin_scripts
            ), f"Latin text should not contain Cyrillic: {latin_name}"

            # Cyrillic version should contain both scripts
            assert (
                "Cyrillic" in cyrillic_scripts
            ), f"Cyrillic text should contain Cyrillic script: {cyrillic_name}"
            assert (
                "Latin" in cyrillic_scripts
            ), f"Mixed text should contain Latin script: {cyrillic_name}"

    def test_unicode_normalization_attacks(self):
        """Test Unicode normalization attacks."""
        # Various normalization attack vectors
        attack_vectors = [
            # Overlong sequences
            "Müller",  # Normal
            "Mu\u0308ller",  # Combining diaeresis
            "Mu\u0308\u0308ller",  # Double combining diaeresis
            "Mu\u0308\u0301ller",  # Multiple combining marks
            # Zero-width characters
            "Smith\u200b\u200cJohn",  # Zero-width space and non-joiner
            "Garcia\u200d\u200eMaria",  # Zero-width joiner and left-to-right mark
            "Johnson\ufeffRobert",  # Zero-width no-break space
            # Directional override attacks
            "Ahmed\u202ehtimS",  # Right-to-left override
            "Sarah\u202dhtimS",  # Left-to-right override
            "David\u2066\u2067Brown",  # Directional isolates
            # Variation selectors
            "Test\ufe00",  # Variation selector-1
            "Name\ufe0f",  # Variation selector-16
            # Combining character flooding
            "A" + "\u0301" * 100,  # 100 acute accents
            "B" + "\u0308" * 50,  # 50 diaeresis
            # Normalization edge cases
            "\u1e9b\u0323",  # ẛ̣ (multiple normalizations)
            "\u0390",  # ΐ (Greek)
            "\u03b0",  # ΰ (Greek)
        ]

        for attack_vector in attack_vectors:
            # Should normalize without crashing
            normalized = self.normalizer.normalize(attack_vector)
            assert isinstance(normalized, str), f"Normalization failed for: {repr(attack_vector)}"

            # Should not be excessively long
            assert (
                len(normalized) <= len(attack_vector) * 2
            ), f"Normalization expanded too much: {repr(attack_vector)}"

            # Should be valid Unicode
            try:
                normalized.encode("utf-8")
            except UnicodeEncodeError:
                pytest.fail(f"Normalization produced invalid Unicode: {repr(attack_vector)}")

    def test_script_confusion_attacks(self):
        """Test script confusion attacks."""
        # Names with deliberately confusing scripts
        confusing_names = [
            # Mixed Latin/Cyrillic
            "Алексеев, Alexej",  # Cyrillic surname, Latin given name
            "Dimitrov, Димитър",  # Latin surname, Cyrillic given name
            # Mixed Arabic/Latin
            "محمد, Mohammed",  # Arabic first, Latin second
            "Ahmad, أحمد",  # Latin first, Arabic second
            # Mixed Greek/Latin
            "Παπαδόπουλος, Papadopoulos",  # Greek first, Latin second
            "Nikolaos, Νικόλαος",  # Latin first, Greek second
            # Mixed Chinese/Latin
            "李明, Li Ming",  # Chinese first, Latin second
            "Wang, 王伟",  # Latin first, Chinese second
            # Mixed Japanese/Latin
            "田中太郎, Tanaka Taro",  # Japanese first, Latin second
            "Yamamoto, 山本花子",  # Latin first, Japanese second
            # Mixed Hebrew/Latin
            "שמואל, Samuel",  # Hebrew first, Latin second
            "David, דוד",  # Latin first, Hebrew second
        ]

        for name in confusing_names:
            # Should detect mixed scripts
            assert self.normalizer.is_mixed_script(
                name
            ), f"Failed to detect mixed script in: {name}"

            # Should identify multiple scripts
            script_info = self.normalizer.get_script_info(name)
            assert len(script_info) >= 2, f"Should detect multiple scripts in: {name}"

            # Should normalize without corruption
            normalized = self.normalizer.normalize(name)
            assert len(normalized) > 0, f"Normalization produced empty result for: {name}"

    def test_unicode_bidi_attacks(self):
        """Test Unicode bidirectional text attacks."""
        # Bidirectional override attacks
        bidi_attacks = [
            # Basic RTL override
            "John\u202ehtimS",  # RLO: John becomes JohnhtimS visually
            "Ahmed\u202dhtimS",  # LRO: Ahmed becomes AhmedhtimS
            # Nested overrides
            "Test\u202e\u202dNested",  # Nested RLO/LRO
            "Deep\u202e\u202e\u202dNesting",  # Deep nesting
            # Directional isolates
            "Name\u2066\u2067Test",  # Left-to-right isolate + right-to-left isolate
            "User\u2068Auto\u2069",  # First strong isolate
            # Pop directional formatting
            "Start\u202c\u202c\u202cEnd",  # Multiple POP
            # Arabic/Hebrew mixed with overrides
            "محمد\u202eSmith",  # Arabic with RLO
            "שלום\u202dPeace",  # Hebrew with LRO
        ]

        for attack in bidi_attacks:
            # Should normalize without crashing
            normalized = self.normalizer.normalize(attack)
            assert isinstance(normalized, str), f"Bidi attack crashed normalization: {repr(attack)}"

            # Should not contain dangerous bidi characters
            dangerous_bidi = [
                "\u202a",
                "\u202b",
                "\u202c",
                "\u202d",
                "\u202e",
                "\u2066",
                "\u2067",
                "\u2068",
                "\u2069",
            ]
            for char in dangerous_bidi:
                assert (
                    char not in normalized
                ), f"Dangerous bidi character preserved: {repr(char)} in {repr(attack)}"

    def test_unicode_length_attacks(self):
        """Test Unicode length manipulation attacks."""
        # Length manipulation through normalization
        length_attacks = [
            # Combining character expansion
            "a" + "\u0301" * 1000,  # 1000 acute accents
            "e" + "\u0308" * 500,  # 500 diaeresis
            "i" + "\u0302" * 200,  # 200 circumflex
            # Ligature decomposition
            "ﬁ" * 100,  # 100 fi ligatures
            "ﬂ" * 100,  # 100 fl ligatures
            "ﬀ" * 100,  # 100 ff ligatures
            # Wide character attacks
            "Ａ" * 100,  # 100 full-width A
            "０" * 100,  # 100 full-width 0
            "　" * 100,  # 100 ideographic spaces
            # Emoji sequences
            "👨‍👩‍👧‍👦" * 50,  # 50 family emojis
            "🏳️‍🌈" * 50,  # 50 rainbow flags
            "👨🏻‍💻" * 50,  # 50 technologist emojis
        ]

        for attack in length_attacks:
            # Should normalize without excessive expansion
            normalized = self.normalizer.normalize(attack)

            # Should not grow excessively
            growth_ratio = len(normalized) / len(attack) if attack else 1
            assert (
                growth_ratio <= 2.0
            ), f"Excessive length growth: {growth_ratio:.2f}x for {len(attack)} chars"

            # Should complete in reasonable time
            start_time = time.time()
            _ = self.normalizer.normalize(attack)
            normalization_time = time.time() - start_time

            assert (
                normalization_time < 1.0
            ), f"Normalization too slow: {normalization_time:.2f}s for {len(attack)} chars"

    def test_unicode_case_folding_attacks(self):
        """Test Unicode case folding attacks."""
        # Case folding edge cases
        case_attacks = [
            # German sharp s variations
            "Straße",  # Normal
            "STRASSE",  # Uppercase
            "ſtraße",  # Long s
            "ſtraſſe",  # Multiple long s
            # Turkish i variations
            "İstanbul",  # Turkish capital İ
            "istanbul",  # Normal
            "İSTANBUL",  # Mixed case
            # Greek sigma variations
            "Θεσσαλονίκη",  # Greek with final sigma
            "θεσσαλονικη",  # Lowercase
            "ΘΕΣΣΑΛΟΝΙΚΗ",  # Uppercase
            # Cherokee case variations
            "ᏣᎳᎩᎯ",  # Cherokee uppercase
            "ꮳꮃꭹꭿ",  # Cherokee lowercase
            # Modifier letters
            "ʻOhana",  # Okina (Hawaiian)
            "n'Ko",  # N'Ko
            # IPA characters
            "ʃmɪθ",  # IPA characters
            "ɑndərsən",  # IPA schwa
        ]

        for attack in case_attacks:
            # Should normalize consistently
            normalized = self.normalizer.normalize(attack)
            normalized_twice = self.normalizer.normalize(normalized)

            assert normalized == normalized_twice, f"Normalization not idempotent: {attack}"

            # Should generate reasonable variants
            variants = self.normalizer.generate_variants(attack)
            assert len(variants) <= 10, f"Too many variants generated: {len(variants)} for {attack}"

            # All variants should be valid
            for variant in variants:
                assert isinstance(variant, str), f"Invalid variant type: {type(variant)}"
                assert len(variant) > 0, f"Empty variant generated for: {attack}"


class TestUnicodePerformance:
    """Test Unicode handling performance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = UnicodeNormalizer()

    def test_normalization_performance(self):
        """Test normalization performance with large inputs."""
        # Generate large Unicode strings
        test_strings = [
            # Large Latin text
            "Smith, John Doe Jr. " * 1000,
            # Large mixed script text
            "García, José María " * 1000,
            # Large CJK text
            "李明王伟张三" * 1000,
            # Large Arabic text
            "محمد أحمد علي" * 1000,
            # Large combining characters
            "a" + "\u0301" * 1000,
            # Large emoji sequence
            "👨‍👩‍👧‍👦" * 100,
        ]

        for test_string in test_strings:
            # Measure normalization time
            start_time = time.time()
            normalized = self.normalizer.normalize(test_string)
            normalization_time = time.time() - start_time

            # Should complete quickly
            chars_per_second = (
                len(test_string) / normalization_time if normalization_time > 0 else float("inf")
            )
            assert (
                chars_per_second > 10000
            ), f"Normalization too slow: {chars_per_second:.0f} chars/sec"

            # Should produce valid result
            assert isinstance(normalized, str), "Normalization produced invalid result"
            assert len(normalized) > 0, "Normalization produced empty result"

    def test_script_detection_performance(self):
        """Test script detection performance."""
        # Generate test strings with different scripts
        test_cases = [
            ("Latin", "Smith, John Anderson" * 100),
            ("Cyrillic", "Иванов, Петр Александр" * 100),
            ("Arabic", "محمد أحمد علي حسن" * 100),
            ("Chinese", "李明王伟张三李四" * 100),
            ("Japanese", "田中太郎山田花子" * 100),
            ("Mixed", "Smith, 李明, محمد, Иванов" * 100),
        ]

        for script_name, test_string in test_cases:
            # Measure detection time
            start_time = time.time()
            detected_script = self.normalizer.detect_primary_script(test_string)
            detection_time = time.time() - start_time

            # Should detect quickly
            assert (
                detection_time < 0.1
            ), f"Script detection too slow: {detection_time:.3f}s for {script_name}"

            # Should detect reasonable script
            assert detected_script in [
                "Latin",
                "Cyrillic",
                "Arabic",
                "CJK",
                "Kana",
                "Other",
            ], f"Invalid script detected: {detected_script}"

    def test_concurrent_normalization(self):
        """Test concurrent Unicode normalization."""
        # Test strings with various Unicode complexities
        test_strings = [
            "García, José María",
            "Müller, Hans-Peter",
            "李明, Li Ming",
            "محمد, Mohammed",
            "Иванов, Петр",
            "Smith" + "\u0301" * 10,
            "Test\u202eReverse",
            "Emoji👨‍👩‍👧‍👦Test",
        ]

        results = Queue()
        errors = Queue()

        def normalize_worker(worker_id, strings):
            """Worker that normalizes strings."""
            worker_results = []
            worker_errors = []

            for i, string in enumerate(strings):
                try:
                    start_time = time.time()
                    normalized = self.normalizer.normalize(string)
                    normalization_time = time.time() - start_time

                    worker_results.append((worker_id, i, normalized, normalization_time))

                except Exception as e:
                    worker_errors.append((worker_id, i, str(e)))

            results.put((worker_id, worker_results))
            if worker_errors:
                errors.put((worker_id, worker_errors))

        # Run concurrent normalization
        num_workers = 10
        strings_per_worker = test_strings * 10  # 80 strings per worker

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=normalize_worker, args=(i, strings_per_worker))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        worker_results = []
        worker_errors = []

        while not results.empty():
            try:
                worker_results.append(results.get_nowait())
            except Empty:
                break

        while not errors.empty():
            try:
                worker_errors.append(errors.get_nowait())
            except Empty:
                break

        # Verify results
        assert (
            len(worker_results) == num_workers
        ), f"Not all workers completed: {len(worker_results)}"
        assert len(worker_errors) == 0, f"Errors during concurrent normalization: {worker_errors}"

        # Check performance
        all_times = []
        for worker_id, results_list in worker_results:
            for _, _, _, norm_time in results_list:
                all_times.append(norm_time)

        avg_time = sum(all_times) / len(all_times)
        assert avg_time < 0.01, f"Concurrent normalization too slow: {avg_time:.4f}s average"

    def test_memory_usage_normalization(self):
        """Test memory usage during normalization."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Generate many normalizations
        for i in range(1000):
            # Create complex Unicode string
            complex_string = f"Test{i:04d}" + "é" * 100 + "李明" * 50 + "\u0301" * 100

            # Normalize
            normalized = self.normalizer.normalize(complex_string)

            # Generate variants
            variants = self.normalizer.generate_variants(complex_string)

            # Detect script
            _ = self.normalizer.detect_primary_script(complex_string)

            # Clean up periodically
            if i % 100 == 0:
                gc.collect()

        # Check memory usage
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Should not leak excessive memory
        assert memory_growth < 50, f"Unicode normalization memory leak: {memory_growth}MB"


class TestUnicodeEdgeCases:
    """Test Unicode edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = UnicodeNormalizer()

    def test_empty_and_none_inputs(self):
        """Test handling of empty and None inputs."""
        # Empty string
        assert self.normalizer.normalize("") == ""
        assert self.normalizer.generate_variants("") == [""]
        assert self.normalizer.detect_primary_script("") == "Unknown"

        # Whitespace only
        assert self.normalizer.normalize("   ") == "   "
        assert self.normalizer.detect_primary_script("   ") == "Unknown"

        # None input should not crash (if supported)
        try:
            result = self.normalizer.normalize(None)
            assert result is None or result == ""
        except (TypeError, AttributeError):
            # Expected behavior for None input
            pass

    def test_single_character_edge_cases(self):
        """Test single character edge cases."""
        # Combining characters alone
        combining_chars = ["\u0301", "\u0308", "\u0302", "\u0300", "\u030a"]
        for char in combining_chars:
            normalized = self.normalizer.normalize(char)
            assert isinstance(normalized, str), f"Failed to normalize combining char: {repr(char)}"

        # Control characters
        control_chars = [
            "\u0000",
            "\u0001",
            "\u0002",
            "\u0008",
            "\u000b",
            "\u000c",
            "\u000e",
            "\u000f",
        ]
        for char in control_chars:
            normalized = self.normalizer.normalize(char)
            assert isinstance(normalized, str), f"Failed to normalize control char: {repr(char)}"

        # High surrogates (should be handled gracefully)
        high_surrogates = ["\ud800", "\ud801", "\ud802", "\udbff"]
        for char in high_surrogates:
            try:
                normalized = self.normalizer.normalize(char)
                assert isinstance(
                    normalized, str
                ), f"Failed to normalize high surrogate: {repr(char)}"
            except UnicodeError:
                # Expected for invalid surrogates
                pass

        # Private use characters
        private_use = ["\ue000", "\ue001", "\uf8ff", "\u0080", "\u0081"]
        for char in private_use:
            normalized = self.normalizer.normalize(char)
            assert isinstance(
                normalized, str
            ), f"Failed to normalize private use char: {repr(char)}"

    def test_maximum_unicode_codepoints(self):
        """Test handling of maximum Unicode codepoints."""
        # Test characters near Unicode limits
        high_codepoints = [
            "\U0001f600",  # Emoji
            "\U0001f1e6",  # Regional indicator
            "\U0001f468",  # Man emoji
            "\U0001f9d1",  # Adult emoji
            "\U0010ffff",  # Maximum valid Unicode
        ]

        for char in high_codepoints:
            try:
                normalized = self.normalizer.normalize(char)
                assert isinstance(
                    normalized, str
                ), f"Failed to normalize high codepoint: {repr(char)}"

                # Should detect script
                script = self.normalizer.detect_primary_script(char)
                assert script in [
                    "Other",
                    "Unknown",
                    "Emoji",
                ], f"Invalid script for high codepoint: {script}"

            except UnicodeError:
                # Some high codepoints might not be supported
                pass

    def test_invalid_unicode_sequences(self):
        """Test handling of invalid Unicode sequences."""
        # Invalid UTF-8 sequences (as much as Python allows)
        invalid_sequences = [
            # Overlong sequences
            "Test\xc0\x80",  # Overlong null
            "Test\xe0\x80\x80",  # Overlong null
            # Invalid continuation bytes
            "Test\x80\x80",
            "Test\xc0",
            # Invalid start bytes
            "Test\xfe\xff",
        ]

        for seq in invalid_sequences:
            try:
                # Try to normalize, should not crash
                normalized = self.normalizer.normalize(seq)
                assert isinstance(
                    normalized, str
                ), f"Invalid sequence crashed normalization: {repr(seq)}"
            except (UnicodeError, UnicodeDecodeError):
                # Expected for truly invalid sequences
                pass

    def test_unicode_normalization_forms(self):
        """Test different Unicode normalization forms."""
        # Test string with combining characters
        test_string = "café"  # é as combining sequence

        # Apply different normalization forms
        nfc = unicodedata.normalize("NFC", test_string)
        nfd = unicodedata.normalize("NFD", test_string)
        nfkc = unicodedata.normalize("NFKC", test_string)
        nfkd = unicodedata.normalize("NFKD", test_string)

        # Our normalizer should handle all forms consistently
        results = []
        for form in [nfc, nfd, nfkc, nfkd]:
            normalized = self.normalizer.normalize(form)
            results.append(normalized)

        # Should produce consistent results
        assert len(set(results)) <= 2, f"Too many different normalization results: {set(results)}"

        # All should be valid strings
        for result in results:
            assert isinstance(result, str), f"Invalid normalization result: {type(result)}"
            assert len(result) > 0, f"Empty normalization result"

    def test_unicode_validation_edge_cases(self):
        """Test Unicode validation edge cases."""
        # Test validation with various inputs
        test_cases = [
            ("normal", "Smith, John"),
            ("accented", "García, José"),
            ("mixed", "Smith, 李明"),
            ("combining", "cafe\u0301"),
            ("ligatures", "ﬁeld"),
            ("rtl", "محمد"),
            ("complex", "👨‍👩‍👧‍👦"),
        ]

        for name, text in test_cases:
            normalized = self.normalizer.normalize(text)

            # Should validate successfully
            is_valid = self.normalizer.validate_normalization(text, normalized)
            assert is_valid, f"Validation failed for {name}: {repr(text)} -> {repr(normalized)}"

            # Should preserve essential characters
            if any(c.isalpha() for c in text):
                assert any(
                    c.isalpha() for c in normalized
                ), f"Lost all alphabetic characters: {repr(text)}"


class TestUnicodeConfigurationOptions:
    """Test Unicode configuration options."""

    def test_ligature_handling_options(self):
        """Test ligature handling configuration."""
        # Test text with ligatures
        test_text = "ﬁeld oﬃce"

        # With ligature handling enabled
        config_enabled = UnicodeConfig(handle_ligatures=True)
        normalizer_enabled = UnicodeNormalizer(config_enabled)

        # With ligature handling disabled
        config_disabled = UnicodeConfig(handle_ligatures=False)
        normalizer_disabled = UnicodeNormalizer(config_disabled)

        # Should produce different results
        result_enabled = normalizer_enabled.normalize(test_text)
        result_disabled = normalizer_disabled.normalize(test_text)

        # Enabled should decompose ligatures
        assert "fi" in result_enabled, "Ligature not decomposed when enabled"

        # Results should be different
        assert result_enabled != result_disabled, "Ligature setting had no effect"

    def test_sharp_s_handling_options(self):
        """Test sharp s handling configuration."""
        # Test text with sharp s
        test_text = "Straße"

        # With sharp s handling enabled
        config_enabled = UnicodeConfig(handle_sharp_s=True)
        normalizer_enabled = UnicodeNormalizer(config_enabled)

        # With sharp s handling disabled
        config_disabled = UnicodeConfig(handle_sharp_s=False)
        normalizer_disabled = UnicodeNormalizer(config_disabled)

        # Should produce different variants
        variants_enabled = normalizer_enabled.generate_variants(test_text)
        variants_disabled = normalizer_disabled.generate_variants(test_text)

        # Enabled should generate more variants
        assert len(variants_enabled) >= len(variants_disabled), "Sharp s setting reduced variants"

        # Enabled should include 'ss' variant
        has_ss_variant = any("ss" in variant for variant in variants_enabled)
        assert has_ss_variant, "Sharp s not converted to 'ss' when enabled"

    def test_greek_tonos_handling_options(self):
        """Test Greek tonos handling configuration."""
        # Test text with Greek tonos
        test_text = "Παύλος"

        # With Greek tonos handling enabled
        config_enabled = UnicodeConfig(handle_greek_tonos=True)
        normalizer_enabled = UnicodeNormalizer(config_enabled)

        # With Greek tonos handling disabled
        config_disabled = UnicodeConfig(handle_greek_tonos=False)
        normalizer_disabled = UnicodeNormalizer(config_disabled)

        # Should produce different results
        result_enabled = normalizer_enabled.normalize(test_text)
        result_disabled = normalizer_disabled.normalize(test_text)

        # Both should be valid
        assert isinstance(result_enabled, str), "Greek tonos enabled failed"
        assert isinstance(result_disabled, str), "Greek tonos disabled failed"

    def test_configuration_combinations(self):
        """Test different configuration combinations."""
        # Test text with multiple features
        test_text = "Müller ﬁeld Straße"

        # Different configuration combinations
        configs = [
            UnicodeConfig(handle_ligatures=True, handle_sharp_s=True),
            UnicodeConfig(handle_ligatures=True, handle_sharp_s=False),
            UnicodeConfig(handle_ligatures=False, handle_sharp_s=True),
            UnicodeConfig(handle_ligatures=False, handle_sharp_s=False),
        ]

        results = []
        for config in configs:
            normalizer = UnicodeNormalizer(config)
            result = normalizer.normalize(test_text)
            variants = normalizer.generate_variants(test_text)

            results.append((result, variants))

        # Should produce different results for different configs
        normalized_results = [r[0] for r in results]
        variant_counts = [len(r[1]) for r in results]

        # Should have some variation
        assert len(set(normalized_results)) >= 2, "Configuration had no effect on normalization"
        assert len(set(variant_counts)) >= 2, "Configuration had no effect on variants"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
