#!/usr/bin/env python3
"""
Week 1 Simple Verification: Test regional processors without full pipeline
"""

print("=" * 80)
print("WEEK 1 SIMPLE VERIFICATION - TESTING REGIONAL PROCESSORS")
print("=" * 80)

# Test 1: Regional Processors Have Process Method
print("\n1. Testing Regional Processors...")
print("-" * 40)


def test_regional_processors():
    # Import processors directly
    from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor
    from src.regions.e_groups.e1_sinophone_mainland import E1_SinophoneMainland
    from src.regions.b_groups.b1_east_slavic.processor import B1_EastSlavic
    from src.regions.e_groups.e3_japan.processor import E3_Japan
    from src.regions.c_groups.c3_arabic_levant_nile.processor import C3_ArabicLevantNile

    test_cases = [
        ("E4", E4KoreanProcessor(), "김민수", "Korean"),
        ("E1", E1_SinophoneMainland(), "李明", "Chinese"),
        ("B1", B1_EastSlavic(), "Иван Петров", "Russian"),
        ("E3", E3_Japan(), "山田太郎", "Japanese"),
        ("C3", C3_ArabicLevantNile(), "محمد أحمد", "Arabic"),
    ]

    working = 0
    failed = []

    for region_code, region, native_name, language in test_cases:
        try:
            # Check process method exists
            if not hasattr(region, "process"):
                print(f"  {region_code} ({language}): ❌ No process method")
                failed.append(f"{region_code}: No process method")
                continue

            # Test it actually works
            entry = {"GlobalID": f"TEST_{region_code}", "CanonicalNative": native_name}

            result = region.process(entry)

            # Check if it produced Latin output
            if "CanonicalLatin" in result and result["CanonicalLatin"]:
                if result["CanonicalLatin"] != native_name:
                    print(
                        f"  {region_code} ({language}): ✅ {native_name} → {result['CanonicalLatin']}"
                    )
                    working += 1
                else:
                    print(f"  {region_code} ({language}): ⚠️ No transformation")
                    failed.append(f"{region_code}: No transformation")
            else:
                print(f"  {region_code} ({language}): ❌ No Latin output")
                failed.append(f"{region_code}: No Latin output")

        except Exception as e:
            print(f"  {region_code} ({language}): ❌ Error: {str(e)[:50]}")
            failed.append(f"{region_code}: {str(e)[:50]}")

    print(f"\nResult: {working}/{len(test_cases)} regions working")

    if working >= 2:
        print("✅ WEEK 1 REQUIREMENT MET: At least 2 regions working")
    else:
        print("❌ WEEK 1 REQUIREMENT NOT MET: Need at least 2 working regions")

    return working >= 2, failed


# Test 2: Check for performance cheats
print("\n2. Checking for Performance Cheats...")
print("-" * 40)


def check_performance_cheats():
    import os

    pipeline_file = "src/core/pipeline_v7_complete_final.py"

    if not os.path.exists(pipeline_file):
        print("  ⚠️ Pipeline file not found")
        return True

    with open(pipeline_file, "r") as f:
        content = f.read()

    cheats = ["skip_heavy_stages", "Skipping Stage", "small batch optimization"]

    found_cheats = []
    for cheat in cheats:
        if cheat in content:
            found_cheats.append(cheat)

    if found_cheats:
        print(f"  ❌ Found cheats: {found_cheats}")
        return False
    else:
        print("  ✅ No performance cheats found")
        return True


# Run tests
print("\n" + "=" * 80)
print("RUNNING TESTS...")
print("=" * 80)

regions_pass, region_issues = test_regional_processors()
cheats_pass = check_performance_cheats()

# Summary
print("\n" + "=" * 80)
print("WEEK 1 VERIFICATION SUMMARY")
print("=" * 80)

print(f"\n✓ Regional Processors: {'PASS' if regions_pass else 'FAIL'}")
if region_issues:
    print(f"  Issues: {', '.join(region_issues)}")

print(f"✓ Performance Cheats Removed: {'PASS' if cheats_pass else 'FAIL'}")

overall_pass = regions_pass and cheats_pass
print(f"\n{'✅ WEEK 1 COMPLETE' if overall_pass else '❌ WEEK 1 INCOMPLETE'}")

if not overall_pass:
    print("\nTO FIX:")
    if not regions_pass:
        print("  - Fix regional processors to transform names properly")
    if not cheats_pass:
        print("  - Remove performance cheats from pipeline")
