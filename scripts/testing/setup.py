#!/usr/bin/env python3
"""
GMNAP - Global Mathematician Name Authority Platform
Setup configuration for pip installation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip()
        for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="gmnap",
    version="7.0.0",
    author="GMNAP Development Team",
    author_email="gmnap@example.com",
    description="Global Mathematician Name Authority Platform - V7 Implementation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gmnap",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/gmnap/issues",
        "Documentation": "https://gmnap.readthedocs.io",
        "Source Code": "https://github.com/yourusername/gmnap",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "sphinx-autodoc-typehints>=1.22.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "hypothesis>=6.0.0",
            "faker>=18.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "gmnap=gmnap.cli.main:main",
            "gmnap-pipeline=gmnap.core.pipeline_v7:cli_main",
        ],
    },
    include_package_data=True,
    package_data={
        "gmnap": [
            "config/*.yaml",
            "config/*.yml",
            "data/*.json",
            "resources/*",
        ],
    },
    zip_safe=False,
)
