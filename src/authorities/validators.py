"""
Authority input validators and utilities.
"""

import re
from typing import Optional


class AuthorityInputError(Exception):
    """Exception raised for invalid authority input."""

    pass


def ensure_orcid(orcid_id: str) -> str:
    """
    Validate and normalize ORCID identifier.

    Args:
        orcid_id: ORCID identifier to validate

    Returns:
        Normalized ORCID ID

    Raises:
        AuthorityInputError: If ORCID format is invalid
    """
    if not orcid_id:
        raise AuthorityInputError("ORCID ID cannot be empty")

    # Remove any whitespace
    orcid_id = orcid_id.strip()

    # Add https://orcid.org/ prefix if missing
    if not orcid_id.startswith("http"):
        if orcid_id.startswith("orcid.org/"):
            orcid_id = "https://" + orcid_id
        elif orcid_id.startswith("0000-"):
            orcid_id = "https://orcid.org/" + orcid_id
        else:
            raise AuthorityInputError(f"Invalid ORCID format: {orcid_id}")

    # Validate ORCID pattern
    orcid_pattern = r"https://orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]"
    if not re.match(orcid_pattern, orcid_id):
        raise AuthorityInputError(f"Invalid ORCID format: {orcid_id}")

    return orcid_id


def safe_startswith(text: Optional[str], prefix: str) -> bool:
    """
    Safely check if text starts with prefix, handling None values.

    Args:
        text: Text to check (can be None)
        prefix: Prefix to look for

    Returns:
        True if text starts with prefix, False if text is None or doesn't start with prefix
    """
    if text is None:
        return False
    return text.startswith(prefix)


def validate_doi(doi: str) -> bool:
    """
    Validate DOI format.

    Args:
        doi: DOI to validate

    Returns:
        True if valid DOI format
    """
    if not doi:
        return False

    # Basic DOI pattern: 10.xxxx/yyyy
    doi_pattern = r"^10\.\d{4,}/[^\s]+$"
    return bool(re.match(doi_pattern, doi))


def normalize_doi(doi: str) -> str:
    """
    Normalize DOI by removing prefixes and ensuring lowercase.

    Args:
        doi: DOI to normalize

    Returns:
        Normalized DOI
    """
    if not doi:
        return doi

    # Remove common prefixes
    for prefix in [
        "http://dx.doi.org/",
        "https://dx.doi.org/",
        "http://doi.org/",
        "https://doi.org/",
        "doi:",
    ]:
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]

    return doi.lower().strip()
