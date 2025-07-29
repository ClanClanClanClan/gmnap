#!/usr/bin/env python3
"""Verify the environment is set up correctly for ground-zero recovery."""

import sys
import subprocess

def check_pynini():
    """Check PyNini version."""
    try:
        import pynini
        version = pynini.__version__
        if version != "2.1.5":
            print(f"⚠️  PyNini version {version} found (expected 2.1.5)")
            return False
        print(f"✅ PyNini {version} installed correctly")
        return True
    except ImportError:
        print("❌ PyNini not installed")
        return False

def check_baseline():
    """Check current baseline performance."""
    print("\nChecking baseline performance...")
    
    # Run mathematician test
    result = subprocess.run(
        ["python3", "scripts/validate.py"],
        capture_output=True,
        text=True
    )
    
    math_pass = None
    if "PASSED:" in result.stdout:
        line = [l for l in result.stdout.split('\n') if 'PASSED:' in l][0]
        math_pass = int(line.split()[1].split('/')[0])
        print(f"  Mathematician: {math_pass}/733 = {math_pass/733*100:.2f}%")
    
    # Run diverse test
    result = subprocess.run(
        ["python3", "scripts/test_diverse_dataset.py"],
        capture_output=True,
        text=True
    )
    
    div_pass = None
    if "PASSED:" in result.stdout:
        line = [l for l in result.stdout.split('\n') if 'PASSED:' in l][0]
        div_pass = int(line.split()[1].split('/')[0])
        print(f"  Diverse: {div_pass}/200 = {div_pass/200*100:.2f}%")
    
    return math_pass, div_pass

def main():
    print("Ground-Zero Recovery Environment Check")
    print("=" * 50)
    
    # Check Python version
    py_version = sys.version_info
    print(f"Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    # Check PyNini
    if not check_pynini():
        print("\n⚠️  Please install PyNini 2.1.5:")
        print("  pip install pynini==2.1.5")
        return 1
    
    # Check baseline
    math_pass, div_pass = check_baseline()
    
    print("\n" + "=" * 50)
    print("Expected baseline (from commit eceeeea):")
    print("  Mathematician: 619/733 = 84.45%")
    print("  Diverse: 141/200 = 70.50%")
    
    if math_pass and div_pass:
        math_diff = abs(math_pass - 619)
        div_diff = abs(div_pass - 141)
        
        if math_diff <= 5 and div_diff <= 5:
            print("\n✅ Baseline matches expected values (within tolerance)")
        else:
            print(f"\n⚠️  Baseline differs from expected:")
            print(f"  Math difference: {math_diff}")
            print(f"  Diverse difference: {div_diff}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())