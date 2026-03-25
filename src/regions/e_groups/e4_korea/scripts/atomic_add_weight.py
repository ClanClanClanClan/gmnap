#!/usr/bin/env python3
"""
Atomic weight addition with rollback capability.
Implements the production protocol for safe weight addition.
"""
import csv
import sys
import os
import shutil
import fcntl
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime


class ProductionError(Exception):
    pass


def acquire_lock(lockfile):
    """Acquire exclusive file lock."""
    try:
        fd = os.open(lockfile, os.O_CREAT | os.O_WRONLY)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except:
        raise ProductionError("Could not acquire lock - another process may be running")


def release_lock(fd):
    """Release file lock."""
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def backup_artifacts():
    """Create timestamped backups of CSV and FST files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups = {}

    # Backup CSV
    csv_path = Path("resources/rr_syllable_map.csv")
    csv_backup = csv_path.parent / f"{csv_path.stem}_backup_{timestamp}{csv_path.suffix}"
    shutil.copy2(csv_path, csv_backup)
    backups["csv"] = csv_backup

    # Backup FST models
    model_dir = Path("models")
    fst_backup_dir = model_dir.parent / f"models_backup_{timestamp}"
    shutil.copytree(model_dir, fst_backup_dir)
    backups["fst"] = fst_backup_dir

    return backups


def validate_weight_format(weight_line):
    """Validate weight format: hangul,roman,weight,context,pos"""
    parts = weight_line.strip().split(",")
    if len(parts) != 5:
        raise ProductionError(f"Invalid format - need 5 fields, got {len(parts)}")

    hangul, roman, weight, context, pos = parts

    # Validate hangul contains Korean characters
    if not hangul or not any("\uac00" <= c <= "\ud7af" for c in hangul):
        raise ProductionError("Hangul field must contain Korean characters")

    # Validate roman is ASCII only
    if not roman or not all(c.isascii() for c in roman):
        raise ProductionError("Roman field must be ASCII only")

    # Validate weight is numeric
    try:
        weight_val = float(weight)
        if weight_val < -2.5:
            raise ProductionError(f"Weight {weight_val} below safety threshold -2.5")
    except ValueError:
        raise ProductionError(f"Weight must be numeric, got: {weight}")

    # Validate position
    if pos not in ["S", "G", "SG"]:
        raise ProductionError(f"Position must be S, G, or SG, got: {pos}")

    return hangul, roman, weight_val, context, pos


def add_weight_to_csv(weight_line):
    """Add weight to CSV if not duplicate."""
    hangul, roman, weight, context, pos = validate_weight_format(weight_line)

    csv_path = Path("resources/rr_syllable_map.csv")

    # Check for duplicates
    existing = set()
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 5:
                key = (row[0], row[1], row[4])  # hangul, roman, pos
                existing.add(key)
                rows.append(row)

    key = (hangul, roman, pos)
    if key in existing:
        raise ProductionError(f"Duplicate mapping already exists: {hangul},{roman} (pos={pos})")

    # Add new row
    rows.append([hangul, roman, str(weight), context, pos])

    # Write atomically using temp file
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=csv_path.parent, delete=False
    ) as tmp:
        writer = csv.writer(tmp)
        writer.writerows(rows)
        temp_path = tmp.name

    # Atomic rename
    os.rename(temp_path, csv_path)
    print(f"✓ Added: {roman} → {hangul} (weight={weight}, pos={pos})")


def rebuild_fsts():
    """Rebuild FST models."""
    result = subprocess.run(
        [sys.executable, "scripts/build_fsts_multi.py"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise ProductionError(f"FST build failed: {result.stderr}")
    print("✓ FST models rebuilt")


def run_regression_check():
    """Run regression validation."""
    result = subprocess.run(
        [sys.executable, "scripts/validate_regression.py"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return False, result.stdout + result.stderr
    return True, result.stdout


def rollback(backups):
    """Rollback to backups."""
    print("\n⚠️  Rolling back changes...")

    # Restore CSV
    if "csv" in backups:
        shutil.copy2(backups["csv"], "resources/rr_syllable_map.csv")
        print(f"✓ Restored CSV from {backups['csv']}")

    # Restore FSTs
    if "fst" in backups:
        shutil.rmtree("models", ignore_errors=True)
        shutil.copytree(backups["fst"], "models")
        print(f"✓ Restored FSTs from {backups['fst']}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 atomic_add_weight.py 'hangul,roman,weight,context,pos'")
        sys.exit(1)

    weight_line = sys.argv[1]
    lockfile = "/tmp/korean_converter.lock"
    fd = None
    backups = {}

    try:
        # Acquire lock
        fd = acquire_lock(lockfile)
        print("✓ Acquired exclusive lock")

        # Create backups
        backups = backup_artifacts()
        print(f"✓ Created backups: CSV={backups['csv'].name}, FST={backups['fst'].name}")

        # Add weight
        add_weight_to_csv(weight_line)

        # Rebuild FSTs
        rebuild_fsts()

        # Check for regressions
        print("\n🔍 Checking for regressions...")
        passed, output = run_regression_check()

        if not passed:
            print("\n❌ REGRESSION DETECTED!")
            print(output)
            rollback(backups)
            sys.exit(1)

        print("\n✅ All checks passed - weight added successfully!")
        print("📝 Backups retained for manual rollback if needed")

    except ProductionError as e:
        print(f"\n❌ ERROR: {e}")
        if backups:
            rollback(backups)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        if backups:
            rollback(backups)
        sys.exit(1)
    finally:
        if fd:
            release_lock(fd)


if __name__ == "__main__":
    main()
