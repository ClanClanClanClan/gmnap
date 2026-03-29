"""Linguistics module with round-trip validation."""

# Support both the old and new roundtrip interfaces
try:
    from .roundtrip import RoundTripValidator

    __all__ = [
        "RoundTripValidator",
        "roundtrip_score",
        "dice",
        "romanise",
        "back_convert",
    ]
except ImportError:
    # If RoundTripValidator doesn't exist, just import the functions
    from .roundtrip import back_convert, dice, romanise, roundtrip_score

    __all__ = ["roundtrip_score", "dice", "romanise", "back_convert"]
