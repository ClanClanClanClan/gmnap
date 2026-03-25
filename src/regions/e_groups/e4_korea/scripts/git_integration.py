#!/usr/bin/env python3
"""
Git integration for production Korean name system.
Implements tagging, pre-commit hooks, and CI/CD readiness.
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_command(cmd, check=True, capture_output=True):
    """Run shell command with proper error handling"""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, capture_output=capture_output, text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        raise


def create_green_tag():
    """Create immutable green baseline tag"""
    # Get current performance
    try:
        math_result = subprocess.run(
            ["python3", "scripts/validate.py"], capture_output=True, text=True, timeout=60
        )

        math_line = math_result.stdout.split("\n")[0] if math_result.stdout else "Unknown"

        # Get git info
        commit = run_command("git rev-parse --short HEAD").stdout.strip()
        timestamp = datetime.now().strftime("%Y-%m-%d")

        # Create tag
        tag_name = f"krp-green-{timestamp}"
        tag_message = f"Green baseline: {math_line} (commit {commit})"

        result = run_command(f'git tag -a {tag_name} -m "{tag_message}"')

        print(f"🏷️  Created tag: {tag_name}")
        print(f"📊 Performance: {math_line}")
        print(f"💡 Commit: {commit}")

        return tag_name

    except Exception as e:
        print(f"❌ Failed to create green tag: {e}")
        return None


def install_pre_commit_hook():
    """Install production-grade pre-commit hook"""

    hook_content = """#!/bin/bash
# Production pre-commit hook for Korean name system
# Prevents commits that would break regression locks

set -e

echo "🔍 Running Korean name system pre-commit checks..."

# Check if this is a Korean name system change
if git diff --cached --name-only | grep -q "resources/rr_syllable_map.csv\\|src/converter.py\\|scripts/"; then
    echo "  📝 Korean name system files modified - running validation..."
    
    # Run regression validation
    if ! python3 scripts/validate_regression.py; then
        echo ""
        echo "❌ PRE-COMMIT REJECTED: Regression detected"
        echo ""
        echo "🚨 Your changes break existing successful cases!"
        echo ""
        echo "Remediation:"
        echo "  1. Review the regression errors above"
        echo "  2. Adjust your weights/changes to avoid breaking existing cases"
        echo "  3. Use: make add-weight WEIGHT='your,weight,-2.0,pos' for safe addition"
        echo "  4. Or revert changes: git restore resources/rr_syllable_map.csv"
        echo ""
        exit 1
    fi
    
    # Check weight safety
    echo "  ⚖️  Checking weight safety bounds..."
    python3 -c "
import csv
dangerous = []
with open('resources/rr_syllable_map.csv', 'r', encoding='utf8') as f:
    for n, row in enumerate(csv.reader(f)):
        if not row or row[0].startswith('#'): continue
        if len(row) < 3: continue
        try:
            w = float(row[2])
            pos = row[4] if len(row) >= 5 else ''
            if w < -3.5 and not pos:
                dangerous.append((n+1, row))
            if abs(w) > 15:
                dangerous.append((n+1, row, 'EXTREME'))
        except: pass
        
if dangerous:
    print('⚠️  Dangerous weights detected:')
    for item in dangerous[:3]:
        print(f'  Line {item[0]}: {item[1]}')
    if len(dangerous) > 3:
        print(f'  ... and {len(dangerous)-3} more')
    print('Consider adding position qualifiers (,SN,S or ,GN,G)')
"
    
    # Check for duplicate weights
    echo "  🔄 Checking for duplicate entries..."
    python3 -c "
import csv
from collections import Counter
entries = []
with open('resources/rr_syllable_map.csv', 'r', encoding='utf8') as f:
    for row in csv.reader(f):
        if len(row) >= 2 and not row[0].startswith('#'):
            entries.append((row[0], row[1]))

duplicates = [(k, v) for k, v in Counter(entries).items() if v > 1]
if duplicates:
    print('⚠️  Duplicate entries found:')
    for (hangul, roman), count in duplicates[:5]:
        print(f'  {hangul},{roman} appears {count} times')
"
    
    echo "  ✅ Pre-commit checks passed"
else
    echo "  ℹ️  No Korean name system files modified - skipping checks"
fi

echo "🎯 Pre-commit validation complete"
"""

    hook_path = Path(".git/hooks/pre-commit")

    # Ensure hooks directory exists
    hook_path.parent.mkdir(exist_ok=True)

    # Write hook
    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)  # Make executable

    print("🪝 Pre-commit hook installed")
    print("   Location: .git/hooks/pre-commit")
    print("   All commits will now be validated automatically")

    return True


def setup_ci_workflow():
    """Create GitHub Actions workflow for CI/CD"""

    workflow_content = """name: Korean Name System CI

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'resources/rr_syllable_map.csv'
      - 'src/converter.py'
      - 'scripts/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'resources/rr_syllable_map.csv'
      - 'src/converter.py'
      - 'scripts/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pynini PyYAML
    
    - name: Build FSTs
      run: python3 scripts/build_fsts_multi.py
      timeout-minutes: 5
    
    - name: Validate regression locks
      run: python3 scripts/validate_regression.py
      timeout-minutes: 3
    
    - name: Run performance validation
      run: |
        echo "📊 Math dataset validation:"
        python3 scripts/validate.py | head -1
        
        echo "📊 Checking for performance regression..."
        PERFORMANCE=$(python3 scripts/validate.py | head -1 | grep -o '[0-9.]*%' | head -1 | tr -d '%')
        echo "Current performance: ${PERFORMANCE}%"
        
        # Fail if performance drops below 97%
        if (( $(echo "$PERFORMANCE < 97.0" | bc -l) )); then
          echo "❌ Performance regression detected: ${PERFORMANCE}% < 97.0%"
          exit 1
        fi
        
        echo "✅ Performance check passed: ${PERFORMANCE}%"
      timeout-minutes: 2

  resource-check:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pynini PyYAML psutil
    
    - name: Resource monitoring test
      run: |
        echo "🔍 Testing resource limits..."
        python3 -c "
import psutil, os, time, subprocess

# Monitor FST build resource usage
process = subprocess.Popen(['python3', 'scripts/build_fsts_multi.py'])
max_memory = 0

while process.poll() is None:
    try:
        p = psutil.Process(process.pid)
        memory_mb = p.memory_info().rss / 1024 / 1024
        max_memory = max(max_memory, memory_mb)
        time.sleep(0.1)
    except psutil.NoSuchProcess:
        break

process.wait()

print(f'Max memory usage: {max_memory:.1f} MB')

if max_memory > 2048:  # 2GB limit
    print(f'❌ Memory limit exceeded: {max_memory:.1f} MB > 2048 MB')
    exit(1)
else:
    print(f'✅ Memory usage within limits: {max_memory:.1f} MB <= 2048 MB')
"
"""

    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)

    workflow_path = workflow_dir / "korean-validation.yml"
    workflow_path.write_text(workflow_content)

    print("🚀 GitHub Actions workflow created")
    print("   Location: .github/workflows/korean-validation.yml")
    print("   Features: Regression validation, performance monitoring, resource limits")

    return True


def create_release_checklist():
    """Create release checklist for production deployment"""

    checklist_content = """# Korean Name System - Production Release Checklist

## Pre-Release Validation
- [ ] `make validate-all` passes (exit code 0)
- [ ] All regression locks validate successfully  
- [ ] Performance ≥ 97% on math dataset
- [ ] No dangerous weights without position qualifiers
- [ ] Memory usage < 2GB during FST builds
- [ ] Runtime < 10 minutes for full validation

## Git Status
- [ ] All changes committed to main branch
- [ ] Pre-commit hooks installed and working
- [ ] Green tag created: `make tag-green`
- [ ] No unstaged changes in production files

## Production Readiness
- [ ] Lock files are read-only (444 permissions)
- [ ] No race condition testing conflicts
- [ ] Atomic operations tested (FST + CSV)
- [ ] Emergency rollback procedure tested

## Documentation
- [ ] All new weights documented with rationale
- [ ] Performance impact assessed and documented
- [ ] Rollback procedures updated if needed

## Deployment Commands
```bash
# Final validation
make validate-all

# Create immutable baseline
make tag-green

# Deploy to production
git push origin main --tags
```

## Emergency Procedures
```bash
# Emergency rollback
git checkout krp-green-YYYY-MM-DD
make build-fsts
make validate-all

# Quick fixes
make restore-backup
make add-weight WEIGHT="fix,fix,-1.0,GN,G"
```

## Post-Deployment
- [ ] Monitor first 24 hours for issues
- [ ] Update regression locks if new cases added
- [ ] Archive old performance baselines
- [ ] Update team documentation
"""

    checklist_path = Path("RELEASE_CHECKLIST.md")
    checklist_path.write_text(checklist_content)

    print("📋 Release checklist created")
    print("   Location: RELEASE_CHECKLIST.md")

    return True


def setup_non_interactive():
    """Set up git integration without prompts (for make)"""

    print("🔧 Setting up Git integration for Korean name system...")

    # Check if we're in a git repository
    try:
        run_command("git rev-parse --git-dir")
    except subprocess.CalledProcessError:
        print("❌ Not in a git repository")
        return False

    # Install pre-commit hook
    if install_pre_commit_hook():
        print("✅ Pre-commit hook installed")

    # Create CI/CD workflow
    if setup_ci_workflow():
        print("✅ GitHub Actions workflow created")

    # Create release checklist
    if create_release_checklist():
        print("✅ Release checklist created")

    print("\n🎯 Git integration setup complete!")
    print("   • Pre-commit validation enabled")
    print("   • CI/CD workflow ready")
    print("   • Release checklist available")
    print("   • Use 'make tag-green' to create baseline tag")

    return True


def main():
    """Set up complete git integration"""

    # Check for non-interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--non-interactive":
        return setup_non_interactive()

    print("🔧 Setting up Git integration for Korean name system...")

    # Check if we're in a git repository
    try:
        run_command("git rev-parse --git-dir")
    except subprocess.CalledProcessError:
        print("❌ Not in a git repository")
        return False

    # Install pre-commit hook
    if install_pre_commit_hook():
        print("✅ Pre-commit hook installed")

    # Create CI/CD workflow
    if setup_ci_workflow():
        print("✅ GitHub Actions workflow created")

    # Create release checklist
    if create_release_checklist():
        print("✅ Release checklist created")

    # Offer to create green tag
    print("\n🏷️  Create green baseline tag? (y/n): ", end="")
    try:
        if input().lower().startswith("y"):
            if create_green_tag():
                print("✅ Green tag created")
    except EOFError:
        print("\n⚠️  Skipping tag creation (non-interactive mode)")

    print("\n🎯 Git integration setup complete!")
    print("   • Pre-commit validation enabled")
    print("   • CI/CD workflow ready")
    print("   • Release checklist available")
    print("   • Ready for production deployment")

    return True


if __name__ == "__main__":
    main()
