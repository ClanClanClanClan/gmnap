#!/usr/bin/env python3
"""
Atomic operations with file locking for production safety.
Prevents race conditions when multiple processes modify the Korean name system.
"""

import fcntl
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path


class ProductionLock:
    """Production-grade file locking for atomic operations"""

    def __init__(self, lock_file="locks/.production.lock"):
        self.lock_file = Path(lock_file)
        self.lock_fd = None

    def __enter__(self):
        """Acquire exclusive lock"""
        # Ensure locks directory exists
        self.lock_file.parent.mkdir(exist_ok=True)

        # Open lock file
        self.lock_fd = open(self.lock_file, "w")

        try:
            # Attempt to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write process info for debugging
            self.lock_fd.write(f"pid={os.getpid()}\ntime={time.time()}\n")
            self.lock_fd.flush()

            return self
        except IOError:
            # Lock already held by another process
            self.lock_fd.close()
            raise ProductionError("Another Korean name operation is in progress. Wait and retry.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock"""
        if self.lock_fd:
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
            self.lock_fd.close()

            # Clean up lock file
            try:
                self.lock_file.unlink()
            except FileNotFoundError:
                pass


class ProductionError(Exception):
    """Structured production error with exit codes"""

    def __init__(self, message, exit_code=1, remediation=None):
        super().__init__(message)
        self.exit_code = exit_code
        self.remediation = remediation or []


class AtomicCSVOperation:
    """Atomic CSV operations with backup and rollback"""

    def __init__(self, csv_path="resources/rr_syllable_map.csv"):
        self.csv_path = Path(csv_path)
        self.backup_path = None
        self.temp_path = None

    def __enter__(self):
        """Create atomic backup"""
        timestamp = int(time.time())
        self.backup_path = self.csv_path.with_suffix(f".backup-{timestamp}")
        self.temp_path = self.csv_path.with_suffix(f".tmp-{timestamp}")

        # Create backup
        shutil.copy2(self.csv_path, self.backup_path)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary files"""
        if self.temp_path and self.temp_path.exists():
            self.temp_path.unlink()

    def add_weight(self, weight_line):
        """Add weight atomically"""
        # Read current content
        content = self.csv_path.read_text(encoding="utf8")

        # Add new weight
        new_content = content.rstrip() + f"\n# Safe addition {time.time()}\n{weight_line}\n"

        # Write to temp file
        self.temp_path.write_text(new_content, encoding="utf8")

        # Atomic move
        shutil.move(str(self.temp_path), str(self.csv_path))

    def rollback(self):
        """Rollback to backup"""
        if self.backup_path and self.backup_path.exists():
            shutil.copy2(self.backup_path, self.csv_path)
            self.backup_path.unlink()
            return True
        return False


class AtomicFSTRebuild:
    """Atomic FST rebuild - all or nothing"""

    def __init__(self, models_dir="models"):
        self.models_dir = Path(models_dir)
        self.temp_dir = None
        self.backup_dir = None

    def __enter__(self):
        """Prepare atomic rebuild"""
        timestamp = int(time.time())
        self.temp_dir = self.models_dir.parent / f".models-tmp-{timestamp}"
        self.backup_dir = self.models_dir.parent / f".models-backup-{timestamp}"

        # Create temp directory
        self.temp_dir.mkdir(exist_ok=True)

        # Backup existing models
        if self.models_dir.exists():
            shutil.copytree(self.models_dir, self.backup_dir)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary directories"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

        if self.backup_dir and self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)

    def rebuild(self):
        """Rebuild FSTs atomically"""
        # Build FSTs in temporary directory
        env = os.environ.copy()
        env["FST_OUTPUT_DIR"] = str(self.temp_dir)

        result = subprocess.run(
            ["python3", "scripts/build_fsts_multi.py"],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )

        if result.returncode != 0:
            raise ProductionError(
                f"FST rebuild failed: {result.stderr}",
                exit_code=2,
                remediation=[
                    "Check CSV format for invalid entries",
                    "Verify PyNini installation",
                    "Check available memory (requires ~2GB)",
                ],
            )

        # Verify all expected FST files were created
        expected_files = [
            "rom2han_surname.fst",
            "rom2han_given.fst",
            "rom2han_multi.fst",
            "han2rom_surname.fst",
            "han2rom_given.fst",
            "han2rom_multi.fst",
        ]

        for fst_file in expected_files:
            if not (self.temp_dir / fst_file).exists():
                raise ProductionError(
                    f"FST build incomplete: {fst_file} missing",
                    exit_code=3,
                    remediation=["Check build script for errors", "Verify CSV data integrity"],
                )

        # Atomic replacement of models directory
        if self.models_dir.exists():
            shutil.rmtree(self.models_dir)

        shutil.move(str(self.temp_dir), str(self.models_dir))
        self.temp_dir = None  # Prevent cleanup

    def rollback(self):
        """Rollback to backup models"""
        if self.backup_dir and self.backup_dir.exists():
            if self.models_dir.exists():
                shutil.rmtree(self.models_dir)
            shutil.move(str(self.backup_dir), str(self.models_dir))
            self.backup_dir = None  # Prevent cleanup
            return True
        return False


@contextmanager
def production_operation(operation_name="Korean name operation"):
    """Complete production operation with locking and error handling"""
    with ProductionLock():
        try:
            print(f"🔒 Starting {operation_name} (locked)")
            yield
            print(f"✅ {operation_name} completed successfully")
        except ProductionError:
            raise
        except Exception as e:
            raise ProductionError(
                f"{operation_name} failed: {e}",
                exit_code=4,
                remediation=[
                    "Check system resources",
                    "Verify file permissions",
                    "Review error logs",
                ],
            )


def validate_weight_format(weight_line):
    """Validate weight line format with comprehensive checks"""

    if not weight_line or not isinstance(weight_line, str):
        raise ProductionError(
            "Weight line must be a non-empty string",
            exit_code=7,
            remediation=["Provide weight in format: 한글,roman,-2.0,context,pos"],
        )

    # Split and check basic structure
    parts = weight_line.split(",")
    if len(parts) < 3:
        raise ProductionError(
            f"Invalid format - need at least 3 fields, got {len(parts)}",
            exit_code=7,
            remediation=[
                "Format: 한글,roman,weight[,context,pos]",
                "Example: 새로운,saeroun,-2.0,GN,G",
            ],
        )

    hangul, roman, weight_str = parts[0], parts[1], parts[2]
    context = parts[3] if len(parts) > 3 else ""
    pos = parts[4] if len(parts) > 4 else ""

    # Validate hangul (must contain Korean characters)
    if not hangul or not any("\uac00" <= c <= "\ud7af" for c in hangul):
        raise ProductionError(
            f"Hangul field '{hangul}' must contain Korean characters",
            exit_code=7,
            remediation=["Use actual Korean characters (한글) in first field"],
        )

    # Validate roman (must be ASCII, no spaces)
    if not roman or not roman.replace("-", "").replace("'", "").isalpha():
        raise ProductionError(
            f"Roman field '{roman}' must be ASCII letters only (no spaces/numbers)",
            exit_code=7,
            remediation=["Use only ASCII letters: a-z, A-Z, hyphens, apostrophes"],
        )

    # Validate weight (must be valid float)
    try:
        weight_val = float(weight_str)
        if abs(weight_val) > 20:
            raise ProductionError(
                f"Weight {weight_val} is extreme (|weight| > 20)",
                exit_code=7,
                remediation=[
                    "Use reasonable weights: -5.0 to +5.0 range recommended",
                    "Consider position qualifiers instead of extreme weights",
                ],
            )
    except ValueError:
        raise ProductionError(
            f"Weight '{weight_str}' must be a valid number",
            exit_code=7,
            remediation=["Use decimal format: -2.0, 1.5, 0.0, etc."],
        )

    # Validate position if provided
    if pos and pos not in ["S", "G", ""]:
        raise ProductionError(
            f"Position '{pos}' must be 'S' (surname), 'G' (given), or empty",
            exit_code=7,
            remediation=["Use: S=surname only, G=given only, empty=general"],
        )

    # Check for risky patterns
    if weight_val < -3.0 and not pos:
        raise ProductionError(
            f"Aggressive weight {weight_val} without position qualifier is risky",
            exit_code=7,
            remediation=[
                f"Add position: {hangul},{roman},{weight_str},SN,S (surname only)",
                f"Or: {hangul},{roman},{weight_str},GN,G (given only)",
                "Or use less aggressive weight: > -3.0",
            ],
        )

    return {
        "hangul": hangul,
        "roman": roman,
        "weight": weight_val,
        "context": context,
        "pos": pos,
        "formatted": weight_line,
    }


def safe_add_weight(weight_line, test_mode=False):
    """Safely add a weight with complete production safeguards and validation"""

    # First validate format comprehensively
    try:
        validated = validate_weight_format(weight_line)
        print(
            f"✅ Weight format validated: {validated['hangul']} → {validated['roman']} ({validated['weight']})"
        )
    except ProductionError as e:
        print(f"❌ Invalid weight format: {e}")
        if e.remediation:
            print("Remediation steps:")
            for step in e.remediation:
                print(f"  • {step}")
        raise

    with production_operation("Safe weight addition"):
        csv_op = AtomicCSVOperation()
        fst_op = AtomicFSTRebuild()

        try:
            with csv_op, fst_op:
                # Add weight to CSV
                csv_op.add_weight(weight_line)

                if not test_mode:
                    # Rebuild FSTs
                    fst_op.rebuild()

                # Validate regression
                result = subprocess.run(
                    ["python3", "scripts/validate_regression.py"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode != 0:
                    raise ProductionError(
                        "Regression detected - new weight breaks existing cases",
                        exit_code=5,
                        remediation=[
                            f"Weight {validated['hangul']},{validated['roman']},{validated['weight']} causes failures",
                            "Try smaller weight magnitude (closer to 0)",
                            "Add position qualifier: ,SN,S (surname) or ,GN,G (given)",
                            "Check for conflicting existing weights in CSV",
                            f"Alternative: {validated['hangul']},{validated['roman']},{validated['weight']/2:.1f}",
                        ],
                    )

                return {
                    "success": True,
                    "weight": weight_line,
                    "validated": validated,
                    "message": f"Weight added successfully: {validated['hangul']} → {validated['roman']} ({validated['weight']})",
                }

        except ProductionError:
            # Structured rollback
            print("🚨 Rolling back due to production error...")
            csv_op.rollback()
            if not test_mode:
                fst_op.rollback()
            raise

        except Exception as e:
            # Unexpected error - still rollback
            print(f"🚨 Unexpected error: {e}")
            csv_op.rollback()
            if not test_mode:
                fst_op.rollback()
            raise ProductionError(
                f"Unexpected error during weight addition: {e}",
                exit_code=6,
                remediation=[
                    "Check system logs",
                    "Verify file permissions",
                    "Contact system administrator",
                ],
            )


if __name__ == "__main__":
    # Example usage
    try:
        result = safe_add_weight("테스트,test,-1.5,GN,G", test_mode=True)
        print(f"Success: {result}")
    except ProductionError as e:
        print(f"Production error: {e}")
        print(f"Exit code: {e.exit_code}")
        if e.remediation:
            print("Remediation steps:")
            for step in e.remediation:
                print(f"  • {step}")
