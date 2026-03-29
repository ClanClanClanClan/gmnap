"""
YAML schema validation for GMNAP entries.
Validates against the JSON schema defined in docs/schema.json
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft7Validator
from ruamel.yaml import YAML


class SchemaValidator:
    """Validates GMNAP entries against the JSON schema."""

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the validator.

        Args:
            schema_path: Path to JSON schema file. If None, uses default.
        """
        if schema_path is None:
            # Default to v1.5 schema in docs/
            current_dir = Path(__file__).parent
            schema_path = current_dir.parent.parent / "docs" / "schema_v1.5.json"

        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)

    def _load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema from file."""
        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file: {e}")

    def validate_entry(self, entry_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single entry against the schema.

        Args:
            entry_data: Dictionary containing entry data (not the full YAML file)

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            # For single entry validation, wrap in a dummy key
            if "GlobalID" in entry_data and "CanonicalLatin" in entry_data:
                # This is a single entry
                canonical = entry_data.get("CanonicalLatin", "Entry")
                wrapped = {canonical: entry_data}
                return self.validate_file_structure(wrapped)
            else:
                # This might be a full file structure
                return self.validate_file_structure(entry_data)
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    def validate_file_structure(self, file_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a full YAML file structure.

        Args:
            file_data: Dictionary containing full YAML file data

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        try:
            # Validate against JSON schema
            schema_errors = list(self.validator.iter_errors(file_data))
            for error in schema_errors:
                errors.append(
                    f"Schema error at {'.'.join(str(p) for p in error.path)}: {error.message}"
                )

            # Additional custom validations
            custom_errors = self._custom_validations(file_data)
            errors.extend(custom_errors)

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return len(errors) == 0, errors

    def _custom_validations(self, entry_data: Dict[str, Any]) -> List[str]:
        """
        Perform custom validations beyond JSON schema.

        Args:
            entry_data: Dictionary containing entry data

        Returns:
            List of validation errors
        """
        errors = []

        # Validate each entry in the YAML file
        for canonical_latin, entry in entry_data.items():
            if not isinstance(entry, dict):
                continue

            # Check canonical name consistency
            if entry.get("CanonicalLatin") != canonical_latin:
                errors.append(
                    f"CanonicalLatin mismatch: key='{canonical_latin}', value='{entry.get('CanonicalLatin')}'"
                )

            # Validate GlobalID format (Base32, 22 chars + optional collision suffix)
            global_id = entry.get("GlobalID", "")
            if not self._is_valid_global_id(global_id):
                errors.append(f"Invalid GlobalID format: {global_id}")

            # Validate birth/death year consistency
            birth_year = entry.get("BirthYear")
            death_year = entry.get("DeathYear")
            if birth_year and death_year:
                # Extract numeric years for comparison
                birth_num = self._extract_year_number(birth_year)
                death_num = self._extract_year_number(death_year)
                if birth_num is not None and death_num is not None:
                    if death_num < birth_num:
                        errors.append(f"DeathYear ({death_year}) before BirthYear ({birth_year})")

            # Validate MSC codes
            msc_codes = entry.get("PrimaryMSC", [])
            for msc in msc_codes:
                if not self._is_valid_msc_code(msc.get("code", "")):
                    errors.append(f"Invalid MSC code: {msc.get('code')}")
                if "source" not in msc:
                    errors.append(f"MSC code {msc.get('code')} missing source")

            # Validate ORCID format
            auth_ids = entry.get("AuthorityIDs", {})
            orcid = auth_ids.get("ORCID")
            if orcid and not self._is_valid_orcid(orcid):
                errors.append(f"Invalid ORCID format: {orcid}")

            # Check proprietary sources have license field
            proprietary_sources = ["Scopus", "Dimensions", "WoS", "CNKI"]
            for source in proprietary_sources:
                if source in auth_ids:
                    value = auth_ids[source]
                    if isinstance(value, dict) and "license" not in value:
                        errors.append(f"{source} missing required license field")
                    elif isinstance(value, str):
                        errors.append(f"{source} must be object with id and license fields")

            # Validate country codes
            country_codes = entry.get("CountryCodes", [])
            for code in country_codes:
                if not self._is_valid_country_code(code):
                    errors.append(f"Invalid country code: {code}")

            # Validate language codes
            languages = entry.get("LanguageOfPublication", [])
            if len(languages) > 10:
                errors.append(f"Too many languages: {len(languages)} (max 10)")
            for lang in languages:
                if not self._is_valid_language_code(lang):
                    errors.append(f"Invalid language code: {lang}")

            # Validate confidence score
            confidence = entry.get("Confidence")
            if confidence is not None and not (0 <= confidence <= 100):
                errors.append(f"Confidence score out of range: {confidence}")

            # Validate name events chronology
            name_events = entry.get("NameEvents", [])
            if len(name_events) > 1:
                years = [event.get("year") for event in name_events if event.get("year")]
                if years != sorted(years):
                    errors.append("NameEvents not in chronological order")

            # Validate advisor references
            advisors = entry.get("Advisors", [])
            for advisor_id in advisors:
                if not self._is_valid_global_id(advisor_id):
                    errors.append(f"Invalid advisor GlobalID: {advisor_id}")

            # Validate synthesised variant types
            synthesised = entry.get("Variants", {}).get("Synthesised", [])
            valid_types = {
                "ascii-lossy",
                "tone-number",
                "diac-drop",
                "order-swap",
                "romanisation-alt",
                "particle-drop",
                "initial-collapse",
            }
            for variant in synthesised:
                if variant.get("type") not in valid_types:
                    errors.append(f"Invalid synthesised variant type: {variant.get('type')}")

            # Validate affiliation timeline
            timeline = entry.get("AffiliationTimeline", [])
            for i, affiliation in enumerate(timeline):
                if "country" not in affiliation:
                    errors.append(f"AffiliationTimeline[{i}] missing country")
                elif not self._is_valid_country_code(affiliation["country"]):
                    errors.append(
                        f"Invalid country in AffiliationTimeline[{i}]: {affiliation['country']}"
                    )

                # Check from/to consistency
                from_year = affiliation.get("from")
                to_year = affiliation.get("to")
                if from_year is not None and to_year is not None:
                    if to_year < from_year:
                        errors.append(
                            f"AffiliationTimeline[{i}]: to ({to_year}) before from ({from_year})"
                        )

        return errors

    def _is_valid_global_id(self, global_id: str) -> bool:
        """Check if GlobalID is valid Base32 format with optional collision suffix."""
        if not global_id:
            return False

        # Check for collision suffix
        if "--" in global_id:
            parts = global_id.split("--")
            if len(parts) != 2:
                return False
            base_id, suffix = parts
            # Validate suffix is a non-negative integer (0 is valid)
            try:
                if int(suffix) < 0:
                    return False
            except ValueError:
                return False
        else:
            base_id = global_id

        # Base ID must be exactly 22 chars
        if len(base_id) != 22:
            return False

        # Base32 alphabet (without padding)
        base32_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")
        return all(c in base32_chars for c in base_id)

    def _is_valid_msc_code(self, code: str) -> bool:
        """Check if MSC code follows correct format."""
        if not code or len(code) != 5:
            return False

        # Format: DDaDD where D=digit, a=letter
        return code[:2].isdigit() and code[2].isalpha() and code[3:].isdigit()

    def _is_valid_orcid(self, orcid: str) -> bool:
        """Check if ORCID follows correct format."""
        if not orcid:
            return False

        # Format: XXXX-XXXX-XXXX-XXXX where last char can be X
        parts = orcid.split("-")
        if len(parts) != 4:
            return False

        # First 3 parts must be digits
        for i in range(3):
            if len(parts[i]) != 4 or not parts[i].isdigit():
                return False

        # Last part: 3 digits + 1 digit or X
        if len(parts[3]) != 4:
            return False
        if not parts[3][:3].isdigit():
            return False
        if not (parts[3][3].isdigit() or parts[3][3] == "X"):
            return False

        return True

    def _is_valid_country_code(self, code: str) -> bool:
        """Check if country code is valid ISO 3166-1 alpha-2."""
        if not code or len(code) != 2:
            return False

        return code.isupper() and code.isalpha()

    def _is_valid_language_code(self, code: str) -> bool:
        """Check if language code is valid ISO 639-3."""
        if not code or not (2 <= len(code) <= 3):
            return False

        return code.islower() and code.isalpha()

    def _extract_year_number(self, year_value) -> Optional[int]:
        """Extract numeric year from various formats."""
        if isinstance(year_value, int):
            return year_value

        if isinstance(year_value, str):
            # Handle formats: "1970s" -> 1970, "-500" -> -500, "c1150" -> 1150, "1150/1160" -> 1150
            if year_value.endswith("s"):
                # Decade format
                return int(year_value[:-1])
            elif year_value.startswith("c"):
                # Circa format
                return int(year_value[1:])
            elif "/" in year_value:
                # Range format - take first year
                return int(year_value.split("/")[0])
            else:
                # Try direct conversion
                try:
                    return int(year_value)
                except ValueError:
                    return None

        return None

    def validate_yaml_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Validate a YAML file containing GMNAP entries.

        Args:
            file_path: Path to YAML file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            yaml = YAML()
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.load(f)

            if not isinstance(data, dict):
                return False, ["YAML file must contain a dictionary"]

            return self.validate_file_structure(data)

        except FileNotFoundError:
            return False, [f"File not found: {file_path}"]
        except Exception as e:
            return False, [f"Error reading YAML file: {str(e)}"]

    def validate_multiple_entries(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate multiple entries.

        Args:
            entries: List of entry dictionaries

        Returns:
            Dictionary mapping entry index to (is_valid, errors)
        """
        results = {}

        for i, entry in enumerate(entries):
            is_valid, errors = self.validate_entry(entry)
            results[f"entry_{i}"] = (is_valid, errors)

        return results

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get information about the schema.

        Returns:
            Dictionary with schema metadata
        """
        return {
            "schema_version": self.schema.get("$id", "unknown"),
            "title": self.schema.get("title", "unknown"),
            "description": self.schema.get("description", ""),
            "required_fields": self._get_required_fields(),
            "optional_fields": self._get_optional_fields(),
        }

    def _get_required_fields(self) -> List[str]:
        """Get list of required fields from schema."""
        pattern_props = self.schema.get("patternProperties", {})
        for pattern, props in pattern_props.items():
            return props.get("required", [])
        return []

    def _get_optional_fields(self) -> List[str]:
        """Get list of optional fields from schema."""
        pattern_props = self.schema.get("patternProperties", {})
        for pattern, props in pattern_props.items():
            all_props = set(props.get("properties", {}).keys())
            required_props = set(props.get("required", []))
            return list(all_props - required_props)
        return []


def validate_entry(
    entry_data: Dict[str, Any], schema_path: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a single entry.

    Args:
        entry_data: Entry data to validate
        schema_path: Optional path to schema file

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = SchemaValidator(schema_path)
    return validator.validate_entry(entry_data)


def validate_yaml_file(file_path: str, schema_path: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a YAML file.

    Args:
        file_path: Path to YAML file
        schema_path: Optional path to schema file

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = SchemaValidator(schema_path)
    return validator.validate_yaml_file(file_path)
