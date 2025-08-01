#!/usr/bin/env python3
"""
Atomic weight addition with subprocess isolation to avoid module caching.
"""
import os, sys, shutil, subprocess, fcntl, time, csv
from pathlib import Path
from datetime import datetime

class ProductionError(Exception):
    pass

def acquire_lock(lockfile):
    """Acquire exclusive file lock."""
    try:
        fd = os.open(str(lockfile), os.O_CREAT | os.O_WRONLY)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except:
        raise ProductionError("Could not acquire lock - another process may be running")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 atomic_add_weight_subprocess.py 'hangul,roman,weight,context,pos'")
        sys.exit(1)
    
    weight_line = sys.argv[1]
    parts = weight_line.strip().split(',')
    if len(parts) != 5:
        raise ProductionError("Invalid format - need exactly 5 comma-separated fields")
    
    hangul, roman, weight, context, pos = parts
    
    # Lint check with subprocess
    lint_result = subprocess.run(
        ["python3", "scripts/lint_weights.py", weight_line],
        capture_output=True,
        text=True
    )
    
    if lint_result.returncode != 0:
        print(lint_result.stdout)
        sys.exit(1)
    
    # Acquire lock
    lockfile = Path(".production_lock")
    fd = acquire_lock(lockfile)
    print("✓ Acquired exclusive lock")
    
    # Create backups
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = Path("resources/rr_syllable_map.csv")
    csv_backup = Path(f"resources/rr_syllable_map_backup_{timestamp}.csv")
    fst_backup = Path(f"models_backup_{timestamp}")
    
    shutil.copy(csv_path, csv_backup)
    if Path("models").exists():
        shutil.copytree("models", fst_backup)
    
    print(f"✓ Created backups: CSV={csv_backup.name}, FST={fst_backup.name}")
    
    try:
        # Add weight
        with open(csv_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{weight_line}")
        
        pos_desc = {"S": "surname", "G": "given name", "SG": "both", "": "general"}[pos]
        print(f"✓ Added: {roman} → {hangul} (weight={weight}, pos={pos_desc})")
        
        # Rebuild FSTs
        build_result = subprocess.run(
            ["python3", "scripts/build_fsts_multi.py"],
            capture_output=True,
            text=True
        )
        
        if build_result.returncode != 0:
            raise ProductionError(f"FST build failed: {build_result.stderr}")
        
        print("✓ FST models rebuilt")
        
        # Test specific conversions with subprocess
        print("\n🔍 Testing conversions...")
        test_result = subprocess.run([
            "python3", "-c",
            """import sys; sys.path.insert(0, 'src'); import converter
print('Kim:', converter.eng2kor('Kim'))
print('Lee:', converter.eng2kor('Lee'))
print('Park:', converter.eng2kor('Park'))"""
        ], capture_output=True, text=True)
        
        print(test_result.stdout)
        
        # Check for regressions WITH SUBPROCESS
        print("\n🔍 Checking for regressions...")
        val_result = subprocess.run(
            ["python3", "scripts/validate_regression.py"],
            capture_output=True,
            text=True
        )
        
        if val_result.returncode != 0:
            print("\n❌ REGRESSION DETECTED!")
            print(val_result.stdout)
            raise ProductionError("Regression detected")
        
        print("✅ No regressions detected")
        
        # Clean up lock
        os.close(fd)
        lockfile.unlink()
        
        # Remove old backups after 10 minutes
        for old_backup in Path("resources").glob("rr_syllable_map_backup_*.csv"):
            if (time.time() - old_backup.stat().st_mtime) > 600:
                old_backup.unlink()
                print(f"✓ Removed old backup: {old_backup.name}")
        
        for old_backup in Path(".").glob("models_backup_*"):
            if old_backup.is_dir() and (time.time() - old_backup.stat().st_mtime) > 600:
                shutil.rmtree(old_backup)
                print(f"✓ Removed old backup: {old_backup.name}")
        
        print(f"\n✅ Successfully added: {roman} → {hangul}")
        
    except Exception as e:
        print(f"\n⚠️  Rolling back changes...")
        shutil.copy(csv_backup, csv_path)
        if fst_backup.exists():
            shutil.rmtree("models", ignore_errors=True)
            shutil.move(fst_backup, "models")
        
        print(f"✓ Restored CSV from {csv_backup.name}")
        print(f"✓ Restored FSTs from {fst_backup.name}")
        
        os.close(fd)
        lockfile.unlink()
        sys.exit(1)

if __name__ == "__main__":
    main()