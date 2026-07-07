"""
Global Mathematician Name Authority Project (GMNAP)
A comprehensive system for managing mathematician names across global regions.
"""

# The SOFTWARE release version — single source of truth, read by the CLI
# (--version), the API (FastAPI meta + /metrics fallback), and mirrored in
# pyproject.toml. NOT the spec generation: "v7" in class/doc names
# (V7Pipeline, "GMNAP v7") refers to docs/specs_v7_clean.yaml, the 7th
# generation of the SPEC. R55 untangled these — tags, pyproject,
# __version__, CLI, and API had drifted to four different values
# (v0.5.1 / 7.0.0 / 6.0.0 / 7.0).
__version__ = "0.6.0"
__author__ = "GMNAP Project"
