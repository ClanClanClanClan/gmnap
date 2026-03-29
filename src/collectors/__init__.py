"""
Data collectors with expert's fixes (2025-11-01).

Includes:
- OpenAlex client (fixes 403 Forbidden with User-Agent + mailto)
- ORCID client (fixes AttributeError on None with safe navigation)
"""

from .openalex_client import OpenAlex
from .orcid_client import Orcid

__all__ = ["OpenAlex", "Orcid"]
