#!/usr/bin/env python3
"""
Phase 0: Environment Setup
Sets up Python 3.12 virtual environment and installs required dependencies
"""

import subprocess
import sys
import os

def create_virtual_environment():
    """Create Python 3.12 virtual environment"""
    print("Creating Python 3.12 virtual environment...")
    
    # Create virtual environment
    result = subprocess.run([
        "python3.12", "-m", "venv", ".venv"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error creating virtual environment: {result.stderr}")
        return False
    
    print("✅ Virtual environment created")
    return True

def install_dependencies():
    """Install all required libraries"""
    print("Installing required libraries...")
    
    # Required packages from blueprint line 45
    packages = [
        "pynini==2.1.6.post1",
        "openfst-python==1.7.2", 
        "tqdm",
        "pandas",
        "regex",
        "scikit-learn",
        "konlpy",
        "mecab-python3",
        "rapidfuzz"
    ]
    
    # Install packages
    pip_cmd = [".venv/bin/pip", "install"] + packages
    result = subprocess.run(pip_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error installing packages: {result.stderr}")
        return False
    
    print("✅ Dependencies installed")
    return True

def verify_installation():
    """Verify installation matches blueprint requirements"""
    print("Verifying installation...")
    
    # Verification script from blueprint lines 57-61
    verification_code = '''
import pynini, openfst_python
assert pynini.string_file
print("PyNini", pynini.__version__, "OpenFst", openfst_python.__version__)
'''
    
    # Run verification
    result = subprocess.run([
        ".venv/bin/python", "-c", verification_code
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Verification failed: {result.stderr}")
        return False
    
    output = result.stdout.strip()
    print(f"Verification output: {output}")
    
    # Check expected output from blueprint line 64
    expected = "PyNini 2.1.6.post1 OpenFst 1.8.3"
    if expected in output:
        print("✅ Verification passed - matches expected output")
        return True
    else:
        print(f"❌ Verification failed - expected '{expected}', got '{output}'")
        return False

def install_system_dependencies():
    """Install system dependencies (macOS/Ubuntu)"""
    import platform
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        print("Installing macOS system dependencies...")
        # From blueprint line 47-48
        packages = ["gcc", "automake", "libtool"]
        for package in packages:
            result = subprocess.run(["brew", "install", package], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: Could not install {package} via brew")
    
    elif system == "linux":  # Ubuntu
        print("Installing Ubuntu system dependencies...")
        # From blueprint line 50-51
        result = subprocess.run([
            "sudo", "apt-get", "install", "-y",
            "build-essential", "automake", "libtool", "pkg-config"
        ], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: Could not install system dependencies: {result.stderr}")
    
    print("✅ System dependencies processed")

def run_phase_0_setup():
    """Run complete Phase 0 environment setup"""
    print("=== Phase 0: Environment Setup ===")
    
    # Install system dependencies first
    install_system_dependencies()
    
    # Create virtual environment
    if not create_virtual_environment():
        return False
    
    # Install Python dependencies
    if not install_dependencies():
        return False
    
    # Verify installation
    if not verify_installation():
        return False
    
    print("🎉 Phase 0 setup completed successfully!")
    return True

if __name__ == "__main__":
    success = run_phase_0_setup()
    sys.exit(0 if success else 1)