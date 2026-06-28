"""
Data collectors with expert's fixes (2025-11-01).

Includes:
- OpenAlex client (fixes 403 Forbidden with User-Agent + mailto)
- ORCID client (fixes AttributeError on None with safe navigation)
"""

# The OpenAlex/ORCID clients depend on the optional `requests` package
# (not a declared dependency). Importing them eagerly made the WHOLE
# package unimportable when requests is absent — which silently disabled
# the stdlib-only ror_client too (the geo branch's institution->country
# lookup does `from src.collectors.ror_client import get_ror_lookup`,
# guarded by try/except, so it just degraded to "no country"). Guard the
# optional imports so ror_client always works; the HTTP clients are still
# available when requests is installed.
try:
    from .openalex_client import OpenAlex
    from .orcid_client import Orcid

    __all__ = ["OpenAlex", "Orcid"]
except ImportError:  # pragma: no cover - optional `requests` not installed
    OpenAlex = None  # type: ignore
    Orcid = None  # type: ignore
    __all__ = []
