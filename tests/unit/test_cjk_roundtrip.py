#!/usr/bin/env python3
"""
Test CJK Round-Trip Implementation for V7 Compliance

V7 Specification Requirement:
"CJK Round-Trip – romanise+back-convert; >= 97% match (Dice coefficient after NFC casefold)"
"""

import sys

import pytest

sys.path.insert(0, ".")

from src.core.cjk_roundtrip import CJKRoundTrip, check_cjk_round_trip


class TestCJKRoundTrip:
    """Test CJK round-trip functionality per V7 specification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.roundtrip = CJKRoundTrip()

    @pytest.mark.timeout(15)
    def test_chinese_surname_romanization(self):
        """Test Chinese surname romanization."""
        test_cases = [
            ("王", "Wang"),
            ("李", "Li"),
            ("张", "Zhang"),
            ("刘", "Liu"),
            ("陈", "Chen"),
        ]

        for chinese, expected in test_cases:
            result = self.roundtrip.romanize(chinese)
            assert (
                expected in result
            ), f"Failed to romanize {chinese} to {expected}, got {result}"

    @pytest.mark.timeout(15)
    def test_korean_surname_romanization(self):
        """Test Korean surname romanization."""
        test_cases = [
            ("김", "Kim"),
            ("이", "Lee"),
            ("박", "Park"),
            ("최", "Choi"),
            ("정", "Jung"),
        ]

        for korean, expected in test_cases:
            result = self.roundtrip.romanize(korean)
            assert (
                expected in result
            ), f"Failed to romanize {korean} to {expected}, got {result}"

    @pytest.mark.timeout(15)
    def test_japanese_surname_romanization(self):
        """Test Japanese surname romanization."""
        test_cases = [
            ("佐藤", "Sato"),
            ("鈴木", "Suzuki"),
            ("高橋", "Takahashi"),
            ("田中", "Tanaka"),
            ("伊藤", "Ito"),
        ]

        for japanese, expected in test_cases:
            result = self.roundtrip.romanize(japanese)
            assert (
                expected in result
            ), f"Failed to romanize {japanese} to {expected}, got {result}"

    @pytest.mark.timeout(15)
    def test_dice_coefficient_calculation(self):
        """Test Dice coefficient calculation."""
        # Test identical strings
        score = self.roundtrip.dice_coefficient("test", "test")
        assert score == 1.0, "Identical strings should have Dice coefficient of 1.0"

        # Test completely different strings
        score = self.roundtrip.dice_coefficient("abc", "xyz")
        assert (
            score == 0.0
        ), "Completely different strings should have Dice coefficient of 0.0"

        # Test similar strings
        score = self.roundtrip.dice_coefficient("hello", "hallo")
        assert (
            0.5 <= score <= 0.8
        ), f"Similar strings should have moderate Dice coefficient, got {score}"

    @pytest.mark.timeout(15)
    def test_cjk_script_detection(self):
        """Test CJK script detection."""
        assert self.roundtrip.detect_cjk_script("김민준") == "korean"
        assert self.roundtrip.detect_cjk_script("王明") == "chinese"
        assert self.roundtrip.detect_cjk_script("さとう") == "japanese"
        assert self.roundtrip.detect_cjk_script("abc") is None

    @pytest.mark.timeout(15)
    def test_v7_round_trip_requirement_chinese(self):
        """Test V7 round-trip requirement for Chinese names."""
        test_names = ["王", "李", "张", "刘", "陈"]

        passed = 0
        for name in test_names:
            passes, score, back = self.roundtrip.test_round_trip(name)
            if passes:
                passed += 1
            print(
                f"  {name} -> {self.roundtrip.romanize(name)} -> {back}: {score:.2%} {'PASS' if passes else 'FAIL'}"
            )

        # At least 97% should pass per V7 spec
        pass_rate = passed / len(test_names)
        assert (
            pass_rate >= 0.97
        ), f"Chinese round-trip pass rate {pass_rate:.2%} < 97% V7 requirement"

    @pytest.mark.timeout(15)
    def test_v7_round_trip_requirement_korean(self):
        """Test V7 round-trip requirement for Korean names."""
        test_names = ["김", "이", "박", "최", "정"]

        passed = 0
        for name in test_names:
            passes, score, back = self.roundtrip.test_round_trip(name)
            if passes:
                passed += 1
            print(
                f"  {name} -> {self.roundtrip.romanize(name)} -> {back}: {score:.2%} {'PASS' if passes else 'FAIL'}"
            )

        # At least 97% should pass per V7 spec
        pass_rate = passed / len(test_names)
        assert (
            pass_rate >= 0.97
        ), f"Korean round-trip pass rate {pass_rate:.2%} < 97% V7 requirement"

    @pytest.mark.timeout(15)
    def test_v7_round_trip_requirement_japanese(self):
        """Test V7 round-trip requirement for Japanese names."""
        test_names = ["佐藤", "鈴木", "高橋", "田中", "伊藤"]

        passed = 0
        for name in test_names:
            passes, score, back = self.roundtrip.test_round_trip(name)
            if passes:
                passed += 1
            print(
                f"  {name} -> {self.roundtrip.romanize(name)} -> {back}: {score:.2%} {'PASS' if passes else 'FAIL'}"
            )

        # At least 97% should pass per V7 spec
        pass_rate = passed / len(test_names)
        assert (
            pass_rate >= 0.97
        ), f"Japanese round-trip pass rate {pass_rate:.2%} < 97% V7 requirement"

    @pytest.mark.timeout(15)
    def test_v7_compliance_verification(self):
        """Test overall V7 compliance verification."""
        results = self.roundtrip.verify_v7_compliance()

        print("\n=== V7 CJK Round-Trip Compliance ===")
        print(f"Total tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Compliance rate: {results['compliance_rate']:.2%}")
        print(
            f"Meets V7 requirement (>=97%): {'PASS' if results['meets_v7_requirement'] else 'FAIL'}"
        )

        for detail in results["details"]:
            status = "PASS" if detail["passes_v7"] else "FAIL"
            print(
                f"  {detail['original']} -> {detail['romanized']} -> {detail['back_converted']}: {detail['dice_score']:.2%} {status}"
            )

        assert results[
            "meets_v7_requirement"
        ], f"V7 compliance rate {results['compliance_rate']:.2%} < 97%"

    @pytest.mark.timeout(15)
    def test_module_level_function(self):
        """Test module-level convenience function."""
        # Test with a Korean name
        passes, score = check_cjk_round_trip("김")
        assert isinstance(passes, bool)
        assert 0.0 <= score <= 1.0

        # Test with Chinese name
        passes, score = check_cjk_round_trip("王")
        assert isinstance(passes, bool)
        assert 0.0 <= score <= 1.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
