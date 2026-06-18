# Compatibility shim — all real metadata lives in pyproject.toml.
#
# Why this exists: older pip (< 21.3) doesn't support PEP-660 editable
# installs from pyproject.toml alone. On macOS the system Python ships
# pip 21.2.4, which fails `pip install -e .` with "File 'setup.py' or
# 'setup.cfg' not found". This empty shim lets the install succeed on
# bare system Python without requiring users to upgrade pip first.
#
# When everyone is on pip ≥ 23 this file can go.
from setuptools import setup

setup()
