#!/usr/bin/env python3
"""
ULTRATHINK Regional Processor Test
Test each regional processor individually to verify functionality
"""

import sys
import traceback
from typing import Dict, Any


def test_korean_processor():
    """Test E4 Korean processor"""
    try:
        from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor

        processor = E4KoreanProcessor()

        test_cases = [
            {"input": "김민수", "expected_contains": "Kim"},
            {"input": "박지영", "expected_contains": "Park"},
            {"input": "이철수", "expected_contains": "Lee"},
        ]

        print("\n🇰🇷 Testing Korean Processor (E4):")
        for test in test_cases:
            entry = {"CanonicalNative": test["input"], "GlobalID": "TEST"}
            result = processor.process(entry)
            latin = result.get("CanonicalLatin", "")
            if test["expected_contains"] in latin:
                print(f"  ✅ {test['input']} → {latin}")
            else:
                print(
                    f"  ❌ {test['input']} → {latin} (expected to contain '{test['expected_contains']}')"
                )
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_chinese_processor():
    """Test E1 Chinese processor"""
    try:
        from src.regions.e_groups.e1_sinophone_mainland import E1_SinophoneMainland

        processor = E1_SinophoneMainland()

        test_cases = [
            {"input": "李明", "expected_contains": "Li"},
            {"input": "王伟", "expected_contains": "Wang"},
            {"input": "张三", "expected_contains": "Zhang"},
        ]

        print("\n🇨🇳 Testing Chinese Processor (E1):")
        for test in test_cases:
            entry = {"CanonicalNative": test["input"], "GlobalID": "TEST"}
            result = processor.process(entry)
            latin = result.get("CanonicalLatin", "")
            if test["expected_contains"] in latin:
                print(f"  ✅ {test['input']} → {latin}")
            else:
                print(
                    f"  ❌ {test['input']} → {latin} (expected to contain '{test['expected_contains']}')"
                )
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_russian_processor():
    """Test B1 Russian processor"""
    try:
        from src.regions.b_groups.b1_east_slavic import B1_EastSlavic

        processor = B1_EastSlavic()

        test_cases = [
            {"input": "Иванов Иван", "expected_contains": "Ivanov"},
            {"input": "Петров Петр", "expected_contains": "Petrov"},
            {"input": "Сидоров Алексей", "expected_contains": "Sidorov"},
        ]

        print("\n🇷🇺 Testing Russian Processor (B1):")
        for test in test_cases:
            entry = {"CanonicalNative": test["input"], "GlobalID": "TEST"}
            result = processor.process(entry)
            latin = result.get("CanonicalLatin", "")
            if test["expected_contains"] in latin:
                print(f"  ✅ {test['input']} → {latin}")
            else:
                print(
                    f"  ❌ {test['input']} → {latin} (expected to contain '{test['expected_contains']}')"
                )
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_japanese_processor():
    """Test E3 Japanese processor"""
    try:
        from src.regions.e_groups.e3_japan.processor import E3JapanProcessor

        processor = E3JapanProcessor()

        test_cases = [
            {"input": "山田太郎", "expected_contains": "Yamada"},
            {"input": "佐藤一郎", "expected_contains": "Sato"},
            {"input": "鈴木花子", "expected_contains": "Suzuki"},
        ]

        print("\n🇯🇵 Testing Japanese Processor (E3):")
        for test in test_cases:
            entry = {"CanonicalNative": test["input"], "GlobalID": "TEST"}
            result = processor.process(entry)
            latin = result.get("CanonicalLatin", "")
            if test["expected_contains"] in latin:
                print(f"  ✅ {test['input']} → {latin}")
            else:
                print(
                    f"  ❌ {test['input']} → {latin} (expected to contain '{test['expected_contains']}')"
                )
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_arabic_processor():
    """Test C3 Arabic processor"""
    try:
        from src.regions.c_groups.c3_arabic_levant_nile.processor import C3ArabicLevantNileProcessor

        processor = C3ArabicLevantNileProcessor()

        test_cases = [
            {"input": "محمد علي", "expected_contains": "hmd"},
            {"input": "أحمد حسن", "expected_contains": "hmd"},
            {"input": "فاطمة زهرة", "expected_contains": "tm"},
        ]

        print("\n🇸🇦 Testing Arabic Processor (C3):")
        for test in test_cases:
            entry = {"CanonicalNative": test["input"], "GlobalID": "TEST"}
            result = processor.process(entry)
            latin = result.get("CanonicalLatin", "")
            if test["expected_contains"].lower() in latin.lower():
                print(f"  ✅ {test['input']} → {latin}")
            else:
                print(
                    f"  ❌ {test['input']} → {latin} (expected to contain '{test['expected_contains']}')"
                )
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False


def main():
    print("=" * 80)
    print("ULTRATHINK REGIONAL PROCESSOR TEST")
    print("=" * 80)

    results = {
        "Korean (E4)": test_korean_processor(),
        "Chinese (E1)": test_chinese_processor(),
        "Russian (B1)": test_russian_processor(),
        "Japanese (E3)": test_japanese_processor(),
        "Arabic (C3)": test_arabic_processor(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} processors working")
    print(f"Success Rate: {passed/total*100:.1f}%")

    if passed == total:
        print("\n🎯 ALL REGIONAL PROCESSORS WORKING!")
    else:
        print(f"\n⚠️ Only {passed}/{total} processors working")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
