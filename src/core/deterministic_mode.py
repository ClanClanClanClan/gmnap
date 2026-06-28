"""
Deterministic Mode for perfect idempotency.
Ensures reproducible processing with seed control.
"""

import hashlib
import json
import random
from datetime import datetime
from typing import Any, Dict, Optional

# Global deterministic mode state
_deterministic_mode: Optional["DeterministicMode"] = None


class DeterministicMode:
    """Ensures deterministic processing for perfect idempotency."""

    def __init__(self, seed: int = 42):
        """Initialize with a seed for reproducibility."""
        self.seed = seed
        random.seed(seed)
        self.enabled = False
        # Fixed timestamp for deterministic mode
        self.fixed_timestamp = datetime(2024, 1, 1, 0, 0, 0)

    def get_timestamp(self) -> datetime:
        """Return a fixed timestamp for deterministic mode."""
        return self.fixed_timestamp

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data deterministically."""
        # Create a deterministic hash of the input
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()

        # Return processed data with hash
        result = data.copy()
        result["DeterministicHash"] = data_hash
        result["ProcessedWithSeed"] = self.seed

        return result

    def reset(self):
        """Reset the random seed."""
        random.seed(self.seed)


def enable_deterministic_mode(seed: int = 42) -> DeterministicMode:
    """Enable deterministic mode globally."""
    global _deterministic_mode
    _deterministic_mode = DeterministicMode(seed)
    _deterministic_mode.enabled = True
    return _deterministic_mode


def get_deterministic_mode() -> Optional[DeterministicMode]:
    """Get the current deterministic mode instance."""
    return _deterministic_mode
