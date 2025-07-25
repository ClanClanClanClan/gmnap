#!/usr/bin/env python3
"""
Comprehensive audit of V5 Korean converter implementation against blueprint
"""

import os
import sys
import json
import yaml
import importlib
from pathlib import Path

def audit_phase_0():
    """Audit Phase 0: Environment Setup"""
    print("=== PHASE 0: ENVIRONMENT SETUP ===")
    
    try:
        import pynini
        pynini_version = pynini.__version__
        print(f"✅ PyNini: {pynini_version}")
        
        if pynini_version != "2.1.6.post1":
            print(f"⚠️  Expected PyNini 2.1.6.post1, got {pynini_version}")
    except ImportError:
        print("❌ PyNini not installed")
        return False
    
    try:
        import openfst_python
        openfst_version = openfst_python.__version__
        print(f"✅ OpenFst: {openfst_version}")
    except ImportError:
        print("❌ OpenFst not installed")
        return False
    
    # Check for required dependencies
    required_deps = ['tqdm', 'pandas', 'regex', 'scikit-learn', 'rapidfuzz']
    for dep in required_deps:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep}: available")
        except ImportError:
            print(f"❌ {dep}: missing")
    
    return True

def audit_phase_1():
    """Audit Phase 1: Corpus & Frequency"""
    print("\n=== PHASE 1: CORPUS & FREQUENCY ===")
    
    # Check for syllable frequency file
    freq_file = "data/syllable_freq.json"
    if os.path.exists(freq_file):
        with open(freq_file, 'r', encoding='utf-8') as f:
            freq_data = json.load(f)
        print(f"✅ Syllable frequencies: {len(freq_data)} entries")
        
        # Check coverage of common syllables
        common_syllables = ['가', '김', '이', '박', '최', '정', '강', '조', '윤', '장']
        covered = sum(1 for syll in common_syllables if syll in freq_data)
        print(f"✅ Common syllable coverage: {covered}/{len(common_syllables)}")
        
        return True
    else:
        print(f"❌ Missing: {freq_file}")
        return False

def audit_phase_2():
    """Audit Phase 2: Romanization Tables"""
    print("\n=== PHASE 2: ROMANIZATION TABLES ===")
    
    required_files = [
        "data/revised_romanization.csv",
        "data/mccune_reischauer.csv", 
        "data/yale_romanization.csv",
        "data/mltr_romanization.csv"
    ]
    
    found_files = 0
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}: exists")
            found_files += 1
        else:
            print(f"❌ {file_path}: missing")
    
    return found_files == len(required_files)

def audit_phase_3():
    """Audit Phase 3: WFST Construction"""
    print("\n=== PHASE 3: WFST CONSTRUCTION ===")
    
    fst_file = "data/roman2hangul.fst"
    if os.path.exists(fst_file):
        file_size = os.path.getsize(fst_file) / (1024 * 1024)  # MB
        print(f"✅ Main FST: {file_size:.1f}MB")
        
        if file_size < 30:
            print("✅ FST size within blueprint limit (<30MB)")
        else:
            print(f"⚠️  FST size {file_size:.1f}MB exceeds blueprint limit (30MB)")
        
        return True
    else:
        print(f"❌ Missing: {fst_file}")
        return False

def audit_phase_4():
    """Audit Phase 4: Segmentation FST"""
    print("\n=== PHASE 4: SEGMENTATION FST ===")
    
    # Check for segmenter module
    segmenter_path = "src/v5/segmenter.py"
    if os.path.exists(segmenter_path):
        print(f"✅ Segmenter module: {segmenter_path}")
        
        # Check for beam search implementation
        with open(segmenter_path, 'r') as f:
            content = f.read()
            if 'beam_search' in content or 'segment_with_freq' in content:
                print("✅ Beam search implementation found")
                return True
            else:
                print("❌ Beam search implementation missing")
                return False
    else:
        print(f"❌ Missing: {segmenter_path}")
        return False

def audit_phase_5():
    """Audit Phase 5: Variant Generator"""
    print("\n=== PHASE 5: VARIANT GENERATOR ===")
    
    variant_path = "src/v5/variant_generator.py"
    if os.path.exists(variant_path):
        print(f"✅ Variant generator: {variant_path}")
        
        # Check for key functions
        with open(variant_path, 'r') as f:
            content = f.read()
            if 'generate_all_variants' in content:
                print("✅ Variant generation function found")
                
                # Test the function
                try:
                    sys.path.append('src/v5')
                    from variant_generator import generate_all_variants
                    variants = generate_all_variants("Kim Sunghoon")
                    print(f"✅ Variant generation test: {len(variants)} variants")
                    return True
                except Exception as e:
                    print(f"❌ Variant generation test failed: {e}")
                    return False
            else:
                print("❌ Variant generation function missing")
                return False
    else:
        print(f"❌ Missing: {variant_path}")
        return False

def audit_phase_7():
    """Audit Phase 7: V4 Back-off"""
    print("\n=== PHASE 7: V4 BACK-OFF ===")
    
    v4_fst = "data/v4_comprehensive.fst"
    v4_mappings = "data/v4_comprehensive_mappings.json"
    
    success = True
    
    if os.path.exists(v4_fst):
        file_size = os.path.getsize(v4_fst) / 1024  # KB
        print(f"✅ V4 FST: {file_size:.1f}KB")
    else:
        print(f"❌ Missing: {v4_fst}")
        success = False
    
    if os.path.exists(v4_mappings):
        with open(v4_mappings, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        print(f"✅ V4 mappings: {len(mappings)} entries")
        
        # Check for key surnames
        key_surnames = ['kim', 'lee', 'park', 'choi', 'jung', 'eom', 'uhm', 'you']
        covered = sum(1 for surname in key_surnames if surname in mappings)
        print(f"✅ Key surname coverage: {covered}/{len(key_surnames)}")
        
        if covered < len(key_surnames):
            success = False
    else:
        print(f"❌ Missing: {v4_mappings}")
        success = False
    
    return success

def audit_phase_10():
    """Audit Phase 10: GMNAP Integration"""
    print("\n=== PHASE 10: GMNAP INTEGRATION ===")
    
    # Check for E4 Korea handler
    e4_handler = "src/regions/e_groups/e4_korea.py"
    if os.path.exists(e4_handler):
        print(f"✅ E4 Korea handler: {e4_handler}")
        return True
    else:
        print(f"❌ Missing: {e4_handler}")
        return False

def audit_accuracy():
    """Audit conversion accuracy"""
    print("\n=== ACCURACY AUDIT ===")
    
    try:
        # Import the fixed accuracy test
        import subprocess
        result = subprocess.run(['python3', 'scripts/test_accuracy_fixed.py'], 
                              capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            # Parse the output for accuracy
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Accuracy:' in line:
                    accuracy_str = line.split('Accuracy:')[1].strip().replace('%', '')
                    accuracy = float(accuracy_str)
                    print(f"✅ Conversion accuracy: {accuracy:.1f}%")
                    
                    if accuracy >= 97.0:
                        print("✅ Blueprint accuracy requirement met (≥97%)")
                        return True
                    else:
                        print(f"❌ Below blueprint requirement: {accuracy:.1f}% < 97%")
                        return False
            
            print("⚠️  Could not parse accuracy from output")
            return False
        else:
            print(f"❌ Accuracy test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Accuracy test failed: {e}")
        return False

def audit_phase_8():
    """Audit Phase 8: Classifier Recalibration"""
    print("\n=== PHASE 8: CLASSIFIER RECALIBRATION ===")
    
    classifier_file = "data/classifier_params.json"
    if os.path.exists(classifier_file):
        with open(classifier_file, 'r') as f:
            params = json.load(f)
        print(f"✅ Classifier parameters: {params['n_samples']} samples")
        print(f"✅ Training accuracy: {params['accuracy']:.1%}")
        return True
    else:
        print(f"❌ Missing: {classifier_file}")
        return False

def audit_phase_9():
    """Audit Phase 9: Validation Suite"""
    print("\n=== PHASE 9: VALIDATION SUITE ===")
    
    # Check if validation suite exists and can run
    validation_script = "scripts/validation_suite.py"
    if os.path.exists(validation_script):
        print(f"✅ Validation suite: {validation_script}")
        
        # Check for Dice coefficient implementation
        with open(validation_script, 'r') as f:
            content = f.read()
            if 'dice_coefficient' in content and 'NFC' in content:
                print("✅ Dice coefficient with NFC normalization implemented")
                return True
            else:
                print("❌ Missing proper Dice coefficient implementation")
                return False
    else:
        print(f"❌ Missing: {validation_script}")
        return False

def audit_blueprint_compliance():
    """Overall blueprint compliance audit"""
    print("\n" + "="*60)
    print("🔍 V5 KOREAN CONVERTER BLUEPRINT COMPLIANCE AUDIT")
    print("="*60)
    
    phases = [
        ("Phase 0: Environment", audit_phase_0),
        ("Phase 1: Corpus & Frequency", audit_phase_1),
        ("Phase 2: Romanization Tables", audit_phase_2), 
        ("Phase 3: WFST Construction", audit_phase_3),
        ("Phase 4: Segmentation", audit_phase_4),
        ("Phase 5: Variant Generator", audit_phase_5),
        ("Phase 7: V4 Back-off", audit_phase_7),
        ("Phase 8: Classifier Recalibration", audit_phase_8),
        ("Phase 9: Validation Suite", audit_phase_9),
        ("Phase 10: GMNAP Integration", audit_phase_10),
        ("Accuracy Requirements", audit_accuracy)
    ]
    
    passed = 0
    total = len(phases)
    
    for phase_name, audit_func in phases:
        try:
            if audit_func():
                passed += 1
                print(f"\n✅ {phase_name}: PASSED")
            else:
                print(f"\n❌ {phase_name}: FAILED")
        except Exception as e:
            print(f"\n❌ {phase_name}: ERROR - {e}")
    
    print("\n" + "="*60)
    print(f"📊 AUDIT SUMMARY: {passed}/{total} phases passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 FULL BLUEPRINT COMPLIANCE ACHIEVED!")
    else:
        print("⚠️  Blueprint compliance incomplete - see failures above")
        
    print("="*60)
    
    return passed == total

if __name__ == "__main__":
    audit_blueprint_compliance()