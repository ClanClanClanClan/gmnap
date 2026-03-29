import pynini as pn, pathlib
from fst_utils import first_output
from preprocess import tokenise
from segment import segment
from lookup import rom2han
import unicodedata
import os


# Simple dice coefficient as originally specified
def _dice(a, b):
    # Normalize like validation does - remove punctuation and normalize
    a = "" if not a else a.replace(",", "").replace("-", " ")
    b = "" if not b else b.replace(",", "").replace("-", " ")
    a = (
        b""
        if not a
        else unicodedata.normalize("NFC", a.casefold().replace(" ", "")).encode()
    )
    b = (
        b""
        if not b
        else unicodedata.normalize("NFC", b.casefold().replace(" ", "")).encode()
    )
    bigr = lambda s: {s[i : i + 2] for i in range(len(s) - 1)}
    x, y = bigr(a), bigr(b)
    return (2 * len(x & y)) / (len(x) + len(y) or 1)


# Load position-specific FSTs as per Track B plan
_base_dir = os.path.dirname(os.path.dirname(__file__))
ROM2_SURNAME = pn.Fst.read(os.path.join(_base_dir, "models/rom2han_surname.fst"))
ROM2_GIVEN = pn.Fst.read(os.path.join(_base_dir, "models/rom2han_given.fst"))
ROM2_GENERAL = pn.Fst.read(os.path.join(_base_dir, "models/rom2han_multi.fst"))
HAN2_SURNAME = pn.Fst.read(os.path.join(_base_dir, "models/han2rom_surname.fst"))
HAN2_GIVEN = pn.Fst.read(os.path.join(_base_dir, "models/han2rom_given.fst"))
HAN2_GENERAL = pn.Fst.read(os.path.join(_base_dir, "models/han2rom_multi.fst"))


# Simple position-aware lookup - exactly as specified in Track B
def _rr2han_pos(rr: str, position: str) -> str | None:
    """Position-aware romanization to hangul - simple table lookup"""
    if position == "surname":
        result = first_output(pn.accep(rr) @ ROM2_SURNAME)
    elif position == "given":
        result = first_output(pn.accep(rr) @ ROM2_GIVEN)
    else:
        result = first_output(pn.accep(rr) @ ROM2_GENERAL)

    # Fallback to general if position-specific fails
    if result is None:
        result = first_output(pn.accep(rr) @ ROM2_GENERAL)

    # Final fallback to lookup table
    if result is None:
        result = rom2han().get(rr)

    return result


def _han2rr_pos(han: str, position: str) -> str | None:
    """Position-aware hangul to romanization - simple table lookup"""
    if position == "surname":
        result = first_output(pn.accep(han) @ HAN2_SURNAME)
    elif position == "given":
        result = first_output(pn.accep(han) @ HAN2_GIVEN)
    else:
        result = first_output(pn.accep(han) @ HAN2_GENERAL)

    # Fallback to general if position-specific fails
    if result is None:
        result = first_output(pn.accep(han) @ HAN2_GENERAL)

    return result


# Simple eng2kor - position-aware but no fancy scoring
def eng2kor(name: str):
    out = []
    tokens = list(tokenise(name))

    for idx, tok in enumerate(tokens):
        position = "surname" if idx == 0 else "given"

        for syl in segment(tok):
            h = _rr2han_pos(syl, position)
            if h is None:
                return None
            out.append(h)

    return "".join(out)


# Simple kor2eng - basic n-best without fancy scoring
def kor2eng(hangul: str, orig_roman: str | None = None):
    if not hangul:
        return None

    # Split into characters
    chars = list(hangul)

    # Convert each character using position information
    result_tokens = []

    # First character is surname
    if chars:
        first_rom = _han2rr_pos(chars[0], "surname")
        if first_rom is None:
            return None
        result_tokens.append(first_rom)

    # Rest are given name
    for char in chars[1:]:
        rom = _han2rr_pos(char, "given")
        if rom is None:
            return None
        result_tokens.append(rom)

    # Simple space handling
    if len(result_tokens) == 3:
        result = f"{result_tokens[0]} {result_tokens[1]}{result_tokens[2]}"
    elif len(result_tokens) == 2:
        result = f"{result_tokens[0]} {result_tokens[1]}"
    else:
        result = " ".join(result_tokens)

    return result


# Simple n-best for validation - no enhanced scoring
def eng2kor_nbest(name: str, n: int = 3):
    """Get n-best results using position-specific FSTs"""
    results = []

    # For now, just return the single best result
    best = eng2kor(name)
    if best:
        results.append(best)

    # Pad with None if needed
    while len(results) < n:
        results.append(None)

    return results[:n]
