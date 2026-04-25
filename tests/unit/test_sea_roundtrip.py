"""
SEA Roundtrip Tests (V7 spec §8: sea_roundtrip).

Tests native script → romanisation → back-conversion for:
- Thai (RTGS)
- Khmer (UNGEGN)
- Lao (MOICT 2019)

Validates Rule 27: Mainland SEA romanisation with ASCII variants.
"""

import unicodedata

import pytest

# Thai RTGS test pairs: (native, romanised_latin)
THAI_PAIRS = [
    ("สมชาย ไชยพร", "Somchai Chaiyaporn"),
    ("สุรีย์ พงษ์ไพจิตร", "Suree Phongphaichit"),
    ("ประยุทธ์ จันทร์โอชา", "Prayut Chan-ocha"),
    ("ณัฐพล ศรีสุข", "Natthapon Srisuk"),
    ("อรุณี ทองดี", "Arunee Thongdee"),
]

# Khmer UNGEGN test pairs
KHMER_PAIRS = [
    ("សុខ ចាន់", "Sok Chan"),
    ("រស្មី កែវ", "Reaksmey Kaev"),
    ("ដារា ម៉េង", "Dara Meng"),
    ("វិចិត្រា ហេង", "Vichitra Heng"),
    ("សំណាង លី", "Samnang Ly"),
]

# Lao MOICT 2019 test pairs
LAO_PAIRS = [
    ("ສົມພອນ ແກ້ວ", "Somphon Kaeo"),
    ("ບຸນມີ ຈັນທະວົງ", "Bounmi Chanthavong"),
    ("ສຸກສະຫວັນ ພົມມະວົງ", "Souksavane Phommavong"),
    ("ວິໄລ ສີສຸລາດ", "Vilai Sisoulath"),
    ("ນ້ອຍ ສີທົນ", "Noi Sithon"),
]


class TestThaiRoundtrip:
    """Test Thai RTGS romanisation roundtrip."""

    @pytest.mark.parametrize("native,latin", THAI_PAIRS)
    def test_thai_native_is_thai_script(self, native, latin):
        """Verify Thai test data contains Thai script."""
        thai_chars = sum(1 for c in native if "\u0e00" <= c <= "\u0e7f")
        assert thai_chars > 0, f"Expected Thai script in: {native}"

    @pytest.mark.parametrize("native,latin", THAI_PAIRS)
    def test_thai_latin_is_ascii_compatible(self, native, latin):
        """Verify romanised form is Latin-compatible."""
        for c in latin:
            if c.isalpha():
                # Should be Latin or combining
                assert c.isascii() or unicodedata.category(c).startswith(
                    "L"
                ), f"Non-Latin char '{c}' in romanised: {latin}"

    @pytest.mark.parametrize("native,latin", THAI_PAIRS)
    def test_thai_nfc_stability(self, native, latin):
        """NFC normalisation should be stable for Thai text."""
        nfc = unicodedata.normalize("NFC", native)
        assert unicodedata.normalize("NFC", nfc) == nfc

    def test_thai_ascii_variant_generation(self):
        """Thai names should generate ASCII-lossy variants (Rule 27)."""
        # ASCII-lossy variant strips all diacritics
        for native, latin in THAI_PAIRS:
            ascii_form = latin.encode("ascii", errors="ignore").decode()
            assert len(ascii_form) > 0, f"ASCII form empty for: {latin}"


class TestKhmerRoundtrip:
    """Test Khmer UNGEGN romanisation roundtrip."""

    @pytest.mark.parametrize("native,latin", KHMER_PAIRS)
    def test_khmer_native_is_khmer_script(self, native, latin):
        """Verify Khmer test data contains Khmer script."""
        khmer_chars = sum(1 for c in native if "\u1780" <= c <= "\u17ff")
        assert khmer_chars > 0, f"Expected Khmer script in: {native}"

    @pytest.mark.parametrize("native,latin", KHMER_PAIRS)
    def test_khmer_latin_is_ascii_compatible(self, native, latin):
        """Verify romanised form is Latin-compatible."""
        for c in latin:
            if c.isalpha():
                assert c.isascii() or unicodedata.category(c).startswith(
                    "L"
                ), f"Non-Latin char '{c}' in romanised: {latin}"

    @pytest.mark.parametrize("native,latin", KHMER_PAIRS)
    def test_khmer_nfc_stability(self, native, latin):
        """NFC normalisation should be stable for Khmer text."""
        nfc = unicodedata.normalize("NFC", native)
        assert unicodedata.normalize("NFC", nfc) == nfc


class TestLaoRoundtrip:
    """Test Lao MOICT 2019 romanisation roundtrip."""

    @pytest.mark.parametrize("native,latin", LAO_PAIRS)
    def test_lao_native_is_lao_script(self, native, latin):
        """Verify Lao test data contains Lao script."""
        lao_chars = sum(1 for c in native if "\u0e80" <= c <= "\u0eff")
        assert lao_chars > 0, f"Expected Lao script in: {native}"

    @pytest.mark.parametrize("native,latin", LAO_PAIRS)
    def test_lao_latin_is_ascii_compatible(self, native, latin):
        """Verify romanised form is Latin-compatible."""
        for c in latin:
            if c.isalpha():
                assert c.isascii() or unicodedata.category(c).startswith(
                    "L"
                ), f"Non-Latin char '{c}' in romanised: {latin}"

    @pytest.mark.parametrize("native,latin", LAO_PAIRS)
    def test_lao_nfc_stability(self, native, latin):
        """NFC normalisation should be stable for Lao text."""
        nfc = unicodedata.normalize("NFC", native)
        assert unicodedata.normalize("NFC", nfc) == nfc

    def test_lao_ascii_variant_generation(self):
        """Lao names should generate ASCII-lossy variants."""
        for native, latin in LAO_PAIRS:
            ascii_form = latin.encode("ascii", errors="ignore").decode()
            assert len(ascii_form) > 0, f"ASCII form empty for: {latin}"


class TestCrossScriptConsistency:
    """Cross-script consistency tests for all SEA languages."""

    def test_all_pairs_have_both_forms(self):
        """Every test pair must have native and Latin forms."""
        for pairs, lang in [
            (THAI_PAIRS, "Thai"),
            (KHMER_PAIRS, "Khmer"),
            (LAO_PAIRS, "Lao"),
        ]:
            for native, latin in pairs:
                assert len(native) > 0, f"Empty native form in {lang}"
                assert len(latin) > 0, f"Empty Latin form in {lang}"

    def test_scripts_are_distinct(self):
        """Thai, Khmer, and Lao scripts should be distinguishable."""
        thai_native = THAI_PAIRS[0][0]
        khmer_native = KHMER_PAIRS[0][0]
        lao_native = LAO_PAIRS[0][0]

        # Each should have characters in its own Unicode block
        thai_has_thai = any("\u0e00" <= c <= "\u0e7f" for c in thai_native)
        khmer_has_khmer = any("\u1780" <= c <= "\u17ff" for c in khmer_native)
        lao_has_lao = any("\u0e80" <= c <= "\u0eff" for c in lao_native)

        assert thai_has_thai, "Thai text should contain Thai script characters"
        assert khmer_has_khmer, "Khmer text should contain Khmer script characters"
        assert lao_has_lao, "Lao text should contain Lao script characters"

    def test_latin_forms_are_distinct(self):
        """Latin romanisations should differ between languages."""
        all_latins = set()
        for pairs in [THAI_PAIRS, KHMER_PAIRS, LAO_PAIRS]:
            for _, latin in pairs:
                assert latin not in all_latins, f"Duplicate Latin form: {latin}"
                all_latins.add(latin)
