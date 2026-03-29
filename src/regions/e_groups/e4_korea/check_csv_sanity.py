#!/usr/bin/env python3
"""Check CSV files for sanity and corruption."""

import csv
import os


def check_csv_file(filepath):
    """Check a CSV file for common issues."""
    print(f"\nChecking {os.path.basename(filepath)}...")

    issues = []
    line_count = 0
    empty_lines = 0
    malformed_lines = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader, 1):
            line_count += 1

            # Check for empty lines
            if not row or all(not cell for cell in row):
                empty_lines += 1
                continue

            # Check for malformed entries
            if any("CSV < /dev/null" in cell for cell in row):
                malformed_lines.append((i, row))
                issues.append(f"Line {i}: Malformed entry containing 'CSV < /dev/null'")

            # Check for unexpected column counts
            if filepath.endswith("variant_map.csv"):
                if len(row) not in [2, 3]:  # hangul,romanization[,tag]
                    issues.append(f"Line {i}: Expected 2-3 columns, got {len(row)}")
            elif filepath.endswith("rr_syllable_map.csv"):
                if len(row) != 2:  # hangul,romanization
                    issues.append(f"Line {i}: Expected 2 columns, got {len(row)}")

    print(f"  Total lines: {line_count}")
    print(f"  Empty lines: {empty_lines}")
    print(f"  Malformed lines: {len(malformed_lines)}")

    if issues:
        print(f"  Issues found: {len(issues)}")
        for issue in issues[:5]:  # Show first 5
            print(f"    - {issue}")
        if len(issues) > 5:
            print(f"    ... and {len(issues) - 5} more")
    else:
        print("  ✅ No issues found")

    return issues, malformed_lines


def check_duplicates(filepath):
    """Check for duplicate entries."""
    print(f"\nChecking duplicates in {os.path.basename(filepath)}...")

    seen = {}
    duplicates = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader, 1):
            if not row or all(not cell for cell in row):
                continue

            key = row[0] if row else ""
            if key in seen:
                duplicates.append((i, key, seen[key]))
            else:
                seen[key] = i

    if duplicates:
        print(f"  Found {len(duplicates)} duplicates:")
        for line, key, first_line in duplicates[:5]:
            print(f"    - Line {line}: '{key}' (first seen at line {first_line})")
        if len(duplicates) > 5:
            print(f"    ... and {len(duplicates) - 5} more")
    else:
        print("  ✅ No duplicates found")

    return duplicates


def main():
    print("CSV Sanity Check")
    print("=" * 50)

    csv_files = [
        "resources/variant_map.csv",
        "resources/rr_syllable_map.csv",
        "resources/common_tokens.csv",
    ]

    all_issues = {}

    for csv_file in csv_files:
        if os.path.exists(csv_file):
            issues, malformed = check_csv_file(csv_file)
            duplicates = check_duplicates(csv_file)

            if issues or duplicates:
                all_issues[csv_file] = {
                    "issues": issues,
                    "malformed": malformed,
                    "duplicates": duplicates,
                }

    print("\n" + "=" * 50)
    print("Summary:")

    if all_issues:
        print(f"⚠️  Issues found in {len(all_issues)} files")

        # Create cleanup script
        print("\nGenerating cleanup script...")
        with open("clean_csv_files.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("# CSV cleanup script\n\n")

            for filepath, data in all_issues.items():
                if data["malformed"]:
                    f.write(f"# Remove malformed lines from {filepath}\n")
                    f.write(f"sed -i.backup '/CSV < \\/dev\\/null/d' {filepath}\n\n")

                if data["issues"] and any("Empty" in i for i in data["issues"]):
                    f.write(f"# Remove empty lines from {filepath}\n")
                    f.write(f"sed -i '/^$/d' {filepath}\n\n")

        os.chmod("clean_csv_files.sh", 0o755)
        print("  Created clean_csv_files.sh")
    else:
        print("✅ All CSV files are clean")


if __name__ == "__main__":
    main()
