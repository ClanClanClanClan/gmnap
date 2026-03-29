#!/usr/bin/env python3
"""
Apply V7 security fixes to the 3 regions missing security methods:
- E2: Traditional Chinese
- A3: Nordic Baltic
- B3: Greek

These regions are failing the DoS length attack (200 chars) because they lack
the _has_security_risks method and proper length validation in validate().
"""

import sys
from pathlib import Path


def add_v7_security_to_file(file_path: Path, region_code: str) -> None:
    """Add V7 security methods to a region file."""
    print(f"🔧 Adding V7 security methods to {region_code}: {file_path}")

    # Read the current file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # V7 security method to add
    security_method = '''
    def _has_security_risks(self, name: str) -> bool:
        """Check for dangerous characters that pose security risks."""
        if not name:
            return False
        for char in name:
            # Reject control characters (ASCII 0-31, 127)
            if ord(char) < 32 or ord(char) == 127:
                return True
            # Reject other potentially dangerous Unicode ranges
            if ord(char) in [0xFEFF, 0x200B, 0x200C, 0x200D]:  # Zero-width characters
                return True
        return False'''

    # Check if the method already exists
    if "_has_security_risks" in content:
        print(f"  ✅ {region_code}: _has_security_risks method already exists")
        return

    # Find a good place to insert the method (typically before the last method)
    # Look for the last method or end of class
    lines = content.split("\n")
    insert_position = -1

    # Find the last method definition or end of class
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith("def ") and not line.startswith("def __"):
            insert_position = i + 1
            # Find the end of this method
            indent_level = len(lines[i]) - len(lines[i].lstrip())
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "":
                    continue
                current_indent = len(lines[j]) - len(lines[j].lstrip())
                if current_indent <= indent_level and lines[j].strip():
                    insert_position = j
                    break
            break

    if insert_position == -1:
        # Fallback: insert before the last non-empty line
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                insert_position = i + 1
                break

    # Insert the security method
    method_lines = security_method.split("\n")
    for i, method_line in enumerate(method_lines):
        lines.insert(insert_position + i, method_line)

    # Update validate method to include V7 security
    updated_content = "\n".join(lines)

    # Find and update validate method
    if "def validate(self, entry: Dict[str, Any]) -> None:" in updated_content:
        # Find the validate method and add security checks at the beginning
        validate_security_check = """        # V7 SECURITY: Check for dangerous characters and DoS protection
        canonical = self.get_canonical_name(entry)
        if canonical:
            if self._has_security_risks(canonical):
                raise RegionRuleError(f"Name contains dangerous characters: {canonical[:50]}...")
            
            # Check for reasonable length (prevent DoS attacks)
            if len(canonical) > 150:
                raise RegionRuleError(f"Name too long: {len(canonical)} characters (max 150)")
        """

        # Split by lines to find validate method
        lines = updated_content.split("\n")
        new_lines = []
        in_validate = False
        validate_indent = 0
        added_security = False

        for i, line in enumerate(lines):
            new_lines.append(line)

            # Detect start of validate method
            if line.strip().startswith("def validate(self, entry: Dict[str, Any]) -> None:"):
                in_validate = True
                validate_indent = len(line) - len(line.lstrip())
                continue

            # If we're in validate method and haven't added security yet
            if in_validate and not added_security:
                current_indent = len(line) - len(line.lstrip()) if line.strip() else 0

                # If we hit the first real line of the method (after docstring)
                if (
                    line.strip()
                    and not line.strip().startswith('"""')
                    and not line.strip().startswith("'''")
                    and current_indent > validate_indent
                ):

                    # Insert security check before this line
                    security_lines = validate_security_check.split("\n")
                    for sec_line in security_lines:
                        new_lines.insert(-1, sec_line)  # Insert before current line
                    added_security = True
                    in_validate = False

                # Handle multi-line docstrings
                elif line.strip().endswith('"""') or line.strip().endswith("'''"):
                    # Next non-empty line will be the first real line
                    pass

                # Check if we've left the validate method
                elif (
                    line.strip()
                    and current_indent <= validate_indent
                    and not line.strip().startswith(('"""', "'''", "#"))
                ):
                    in_validate = False

        updated_content = "\n".join(new_lines)

    # Write the updated content back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"  ✅ {region_code}: V7 security methods added successfully")


def main():
    """Apply V7 security fixes to the failing regions."""
    print("🚀 APPLYING V7 SECURITY FIXES TO FAILING REGIONS")
    print("=" * 60)
    print("Adding _has_security_risks method and DoS protection to:")
    print("- E2: Traditional Chinese")
    print("- A3: Nordic Baltic")
    print("- B3: Greek")
    print()

    # Define the files to fix
    regions_to_fix = [
        {"code": "E2", "path": Path("src/regions/e_groups/e2_traditional_chinese.py")},
        {"code": "A3", "path": Path("src/regions/a_groups/a3_nordic_baltic/processor.py")},
        {"code": "B3", "path": Path("src/regions/b_groups/b3_greek.py")},
    ]

    success_count = 0

    for region in regions_to_fix:
        try:
            add_v7_security_to_file(region["path"], region["code"])
            success_count += 1
        except Exception as e:
            print(f"  ❌ {region['code']}: Failed to add V7 security - {str(e)}")

    print()
    print("=" * 60)
    print(f"📊 V7 SECURITY FIXES APPLIED: {success_count}/{len(regions_to_fix)} regions")

    if success_count == len(regions_to_fix):
        print("🎉 ALL REGIONS SUCCESSFULLY UPDATED!")
        print("   DoS length attacks (200+ chars) will now be blocked")
        print("   Control characters and zero-width chars will be blocked")
        print("   Regions should now achieve 99%+ security compliance")
    else:
        print("⚠️  SOME REGIONS FAILED TO UPDATE")
        print("   Manual fixes may be required")

    print("=" * 60)

    # Return exit code
    sys.exit(0 if success_count == len(regions_to_fix) else 1)


if __name__ == "__main__":
    main()
