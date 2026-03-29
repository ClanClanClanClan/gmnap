"""
Korean Toolkit - Consolidated Korean Processing Module
Replaces 166+ individual scripts with unified interface
"""

from .analyzer import KoreanAnalyzer
from .fixer import KoreanFixer
from .validator import KoreanValidator
from .builder import KoreanBuilder

__version__ = "1.0.0"
__all__ = ["KoreanAnalyzer", "KoreanFixer", "KoreanValidator", "KoreanBuilder"]


# Unified interface
class KoreanToolkit:
    """Main interface for all Korean processing operations."""

    def __init__(self):
        self.analyzer = KoreanAnalyzer()
        self.fixer = KoreanFixer()
        self.validator = KoreanValidator()
        self.builder = KoreanBuilder()

    def analyze(self, data, mode="all"):
        """Run analysis on Korean text/data."""
        return self.analyzer.analyze(data, mode)

    def fix(self, issue_type, data):
        """Fix specific issues in Korean data."""
        return self.fixer.fix(issue_type, data)

    def validate(self, data, rules="all"):
        """Validate Korean text/mappings."""
        return self.validator.validate(data, rules)

    def build(self, target, config=None):
        """Build FSTs, mappings, or other artifacts."""
        return self.builder.build(target, config)
