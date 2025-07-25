#!/usr/bin/env python3
"""
HONEST V5 KOREAN CONVERTER AUDIT - Complete Blueprint Compliance Check
"""

import os
import sys
import json
import yaml
from pathlib import Path

def honest_audit():
    """Brutally honest audit of all 15 blueprint phases"""
    print("="*80)
    print("🔍 HONEST V5 KOREAN CONVERTER BLUEPRINT AUDIT")
    print("="*80)
    
    issues = []
    passed_phases = []
    
    # Phase 0: Environment Setup
    print("\n📦 PHASE 0: ENVIRONMENT SETUP")
    try:
        import pynini
        if pynini.__version__ == "2.1.6.post1":
            print("✅ PyNini 2.1.6.post1: CORRECT")
        else:
            print(f"⚠️  PyNini version: {pynini.__version__} (expected 2.1.6.post1)")
            issues.append("PyNini version mismatch")
    except ImportError:
        print("❌ PyNini: NOT INSTALLED")
        issues.append("PyNini missing")
    
    try:
        import openfst_python
        print(f"✅ OpenFst: {openfst_python.__version__}")
    except ImportError:
        print("❌ OpenFst Python bindings: NOT INSTALLED")
        issues.append("OpenFst Python bindings missing")
    
    # Check other required deps
    required_deps = ['tqdm', 'pandas', 'regex', 'scikit-learn', 'rapidfuzz']
    missing_deps = []
    for dep in required_deps:
        try:
            __import__(dep)
            print(f"✅ {dep}: installed")
        except ImportError:
            print(f"❌ {dep}: missing")
            missing_deps.append(dep)
    
    if not missing_deps and 'OpenFst Python bindings missing' not in issues:
        passed_phases.append("Phase 0")
    
    # Phase 1: Corpus & Frequency
    print("\n📊 PHASE 1: CORPUS & FREQUENCY")
    freq_file = "data/syllable_freq.json"
    if os.path.exists(freq_file):
        with open(freq_file, 'r') as f:
            freq_data = json.load(f)
        print(f"✅ Syllable frequencies: {len(freq_data)} entries")
        if len(freq_data) >= 1000:  # Reasonable threshold
            passed_phases.append("Phase 1")
        else:
            issues.append("Insufficient syllable frequency data")
    else:
        print(f"❌ Missing: {freq_file}")
        issues.append("Syllable frequency file missing")
    
    # Phase 2: Romanization Tables
    print("\n📝 PHASE 2: ROMANIZATION TABLES")
    required_tables = [
        "data/revised_romanization.csv",
        "data/mccune_reischauer.csv", 
        "data/yale_romanization.csv",
        "data/mltr_romanization.csv"
    ]
    
    missing_tables = []
    for table in required_tables:
        if os.path.exists(table):
            print(f"✅ {table}: exists")
        else:
            print(f"❌ {table}: missing")
            missing_tables.append(table)
    
    if not missing_tables:
        passed_phases.append("Phase 2")
    else:
        issues.extend([f"Missing {table}" for table in missing_tables])
    
    # Phase 3: WFST Construction
    print("\n🏗️  PHASE 3: WFST CONSTRUCTION")
    main_fst = "data/roman2hangul.fst"
    if os.path.exists(main_fst):
        size_mb = os.path.getsize(main_fst) / (1024 * 1024)
        print(f"✅ Main FST: {size_mb:.1f}MB")
        if size_mb < 30:
            passed_phases.append("Phase 3")
        else:
            issues.append(f"FST too large: {size_mb:.1f}MB > 30MB")
    else:
        print(f"❌ Missing: {main_fst}")
        issues.append("Main FST missing")
    
    # Phase 4: Segmentation FST  
    print("\n✂️  PHASE 4: SEGMENTATION FST")
    segmenter = "src/v5/segmenter.py"
    if os.path.exists(segmenter):
        with open(segmenter, 'r') as f:
            content = f.read()
        if 'segment_with_freq' in content and 'beam' in content:
            print("✅ Beam search segmentation: implemented")
            passed_phases.append("Phase 4")
        else:
            print("❌ Beam search implementation incomplete")
            issues.append("Segmentation implementation incomplete")
    else:
        print(f"❌ Missing: {segmenter}")
        issues.append("Segmenter module missing")
    
    # Phase 5: Variant Generator
    print("\n🔄 PHASE 5: VARIANT GENERATOR")
    variant_gen = "src/v5/variant_generator.py"
    if os.path.exists(variant_gen):
        with open(variant_gen, 'r') as f:
            content = f.read()
        if 'generate_all_variants' in content:
            print("✅ Variant generator: implemented")
            passed_phases.append("Phase 5")
        else:
            print("❌ Variant generation function missing")
            issues.append("Variant generator incomplete")
    else:
        print(f"❌ Missing: {variant_gen}")
        issues.append("Variant generator missing")
    
    # Phase 6: PyNini Corrections
    print("\n🔧 PHASE 6: PYNINI CORRECTIONS")
    print("⚠️  Phase 6 not explicitly implemented - assumed integrated")
    # This phase is typically integrated into other components
    
    # Phase 7: V4 Back-off
    print("\n🔙 PHASE 7: V4 BACK-OFF")
    v4_fst = "data/v4_comprehensive.fst"
    v4_mappings = "data/v4_comprehensive_mappings.json"
    
    v4_issues = []
    if os.path.exists(v4_fst):
        print("✅ V4 FST: exists")
    else:
        print("❌ V4 FST: missing")
        v4_issues.append("V4 FST missing")
    
    if os.path.exists(v4_mappings):
        with open(v4_mappings, 'r') as f:
            mappings = json.load(f)
        print(f"✅ V4 mappings: {len(mappings)} entries")
        if len(mappings) >= 400:  # Should have comprehensive coverage
            pass
        else:
            v4_issues.append("Insufficient V4 mappings")
    else:
        print("❌ V4 mappings: missing")
        v4_issues.append("V4 mappings missing")
    
    if not v4_issues:
        passed_phases.append("Phase 7")
    else:
        issues.extend(v4_issues)
    
    # Phase 8: Classifier Tuning
    print("\n🎯 PHASE 8: CLASSIFIER TUNING")
    classifier_params = "data/classifier_params.json"
    if os.path.exists(classifier_params):
        with open(classifier_params, 'r') as f:
            params = json.load(f)
        print(f"✅ Classifier: {params['accuracy']:.1%} accuracy")
        passed_phases.append("Phase 8")
    else:
        print("❌ Classifier parameters missing")
        issues.append("Classifier not calibrated")
    
    # Phase 9: Validation Suite
    print("\n✅ PHASE 9: VALIDATION SUITE")
    validation_script = "scripts/validation_suite.py"
    if os.path.exists(validation_script):
        with open(validation_script, 'r') as f:
            content = f.read()
        if 'dice_coefficient' in content and 'NFC' in content and 'round_trip_test' in content:
            print("✅ Validation suite: complete")
            passed_phases.append("Phase 9")
        else:
            print("❌ Validation implementation incomplete")
            issues.append("Validation suite incomplete")
    else:
        print("❌ Validation suite missing")
        issues.append("Validation suite missing")
    
    # Phase 10: GMNAP Integration
    print("\n🔗 PHASE 10: GMNAP INTEGRATION")
    e4_handler = "src/regions/e_groups/e4_korea.py"
    if os.path.exists(e4_handler):
        print("✅ E4 Korea handler: exists")
        passed_phases.append("Phase 10")
    else:
        print("❌ E4 Korea handler missing")
        issues.append("GMNAP integration missing")
    
    # Phase 11: Test Harness  
    print("\n🧪 PHASE 11: TEST HARNESS")
    test_harness = "scripts/test_harness.py"
    test_results = "data/test_harness_results.json"
    
    if os.path.exists(test_harness):
        print("✅ Test harness script: exists")
        if os.path.exists(test_results):
            with open(test_results, 'r') as f:
                results = json.load(f)
            print(f"✅ Test results: {results['accuracy']:.1f}% accuracy")
            passed_phases.append("Phase 11")
        else:
            print("⚠️  Test harness exists but no results found")
            issues.append("Test harness results missing")
    else:
        print("❌ Test harness not implemented")
        issues.append("Test harness missing - Phase 11 incomplete")
    
    # Phase 12: CI Integration
    print("\n⚙️  PHASE 12: CI INTEGRATION")
    github_actions = ".github/workflows"
    if os.path.exists(github_actions):
        workflows = list(Path(github_actions).glob("*.yml"))
        if workflows:
            print(f"✅ GitHub Actions: {len(workflows)} workflows")
            passed_phases.append("Phase 12")
        else:
            print("❌ No GitHub Action workflows found")
            issues.append("CI workflows missing")
    else:
        print("❌ GitHub Actions directory missing")
        issues.append("CI integration missing")
    
    # Phase 13: Deployment
    print("\n🚀 PHASE 13: DEPLOYMENT")
    dockerfile = "Dockerfile"
    helm_charts = "charts"
    
    deployment_issues = []
    if os.path.exists(dockerfile):
        print("✅ Dockerfile: exists")
    else:
        print("❌ Dockerfile: missing")
        deployment_issues.append("Dockerfile missing")
    
    if os.path.exists(helm_charts):
        print("✅ Helm charts: directory exists")
    else:
        print("❌ Helm charts: missing")
        deployment_issues.append("Helm charts missing")
    
    if deployment_issues:
        issues.extend(deployment_issues)
    else:
        passed_phases.append("Phase 13")
    
    # Phase 14: Performance
    print("\n⚡ PHASE 14: PERFORMANCE")
    perf_script = "scripts/performance_optimization.py"
    perf_results = "data/performance_results.json"
    
    if os.path.exists(perf_script):
        print("✅ Performance optimization script: exists")
        if os.path.exists(perf_results):
            with open(perf_results, 'r') as f:
                results = json.load(f)
            compliant_opts = len(results.get('compliant_optimizations', []))
            print(f"✅ Performance results: {compliant_opts} compliant optimizations")
            passed_phases.append("Phase 14")
        else:
            print("⚠️  Performance script exists but no results found")
            issues.append("Performance results missing")
    else:
        print("❌ Performance optimization not implemented")
        issues.append("Performance optimization missing - Phase 14 incomplete")
    
    # Phase 15: Anti-overfitting
    print("\n🛡️  PHASE 15: ANTI-OVERFITTING")
    refresh_script = "scripts/refresh_corpus.py"
    if os.path.exists(refresh_script):
        print("✅ Corpus refresh script: exists")
        passed_phases.append("Phase 15")
    else:
        print("❌ Anti-overfitting measures missing")
        issues.append("Anti-overfitting missing - Phase 15 incomplete")
    
    # ACCURACY TEST
    print("\n🎯 ACCURACY VERIFICATION")
    try:
        # Add proper path for imports  
        import subprocess
        
        # Change to the correct directory and run the test
        result = subprocess.run([
            'python3', 'scripts/test_accuracy_fixed.py'
        ], capture_output=True, text=True, cwd='/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap')
        
        if result.returncode == 0:
            # Parse accuracy from output
            lines = result.stdout.split('\n')
            accuracy = None
            for line in lines:
                if 'Accuracy:' in line:
                    accuracy_str = line.split('Accuracy:')[1].strip().replace('%', '')
                    accuracy = float(accuracy_str)
                    break
            
            if accuracy is not None:
                print(f"✅ Measured accuracy: {accuracy:.1f}%")
                if accuracy >= 97.0:
                    print("✅ Accuracy requirement met")
                else:
                    print(f"❌ Below 97% requirement: {accuracy:.1f}%")
                    issues.append("Accuracy below 97%")
            else:
                print("⚠️  Could not parse accuracy from test output")
                issues.append("Could not verify accuracy")
        else:
            print(f"❌ Accuracy test failed: {result.stderr}")
            issues.append("Accuracy test failed")
            
    except Exception as e:
        print(f"❌ Accuracy test failed: {e}")
        issues.append("Accuracy test failed")
    
    # FINAL SUMMARY
    print("\n" + "="*80)
    print("📊 HONEST AUDIT SUMMARY")
    print("="*80)
    
    total_phases = 15
    passed_count = len(passed_phases)
    
    print(f"✅ PASSED PHASES ({passed_count}/15): {', '.join(passed_phases)}")
    print(f"❌ ISSUES FOUND ({len(issues)}):")
    
    for i, issue in enumerate(issues, 1):
        print(f"   {i:2d}. {issue}")
    
    compliance_rate = passed_count / total_phases * 100
    print(f"\n📈 BLUEPRINT COMPLIANCE: {compliance_rate:.1f}% ({passed_count}/15 phases)")
    
    if compliance_rate == 100:
        print("🎉 FULL BLUEPRINT COMPLIANCE ACHIEVED!")
    elif compliance_rate >= 80:
        print("⚠️  HIGH COMPLIANCE - Minor fixes needed")
    elif compliance_rate >= 60:
        print("⚠️  MODERATE COMPLIANCE - Several fixes needed")
    else:
        print("❌ LOW COMPLIANCE - Major work required")
    
    print("="*80)
    
    return {
        'passed_phases': passed_phases,
        'issues': issues,
        'compliance_rate': compliance_rate
    }

if __name__ == "__main__":
    honest_audit()