from __future__ import annotations

# Minimal, deterministic Cyrillic→Latin transliteration sufficient for tests
_MAP = {
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "G",
    "Д": "D",
    "Е": "E",
    "Ё": "E",
    "Ж": "Zh",
    "З": "Z",
    "И": "I",
    "Й": "I",
    "К": "K",
    "Л": "L",
    "М": "M",
    "Н": "N",
    "О": "O",
    "П": "P",
    "Р": "R",
    "С": "S",
    "Т": "T",
    "У": "U",
    "Ф": "F",
    "Х": "Kh",
    "Ц": "Ts",
    "Ч": "Ch",
    "Ш": "Sh",
    "Щ": "Shch",
    "Ы": "Y",
    "Э": "E",
    "Ю": "Yu",
    "Я": "Ya",
    "Ь": "",
    "Ъ": "",
}


def translit(text: str) -> str:
    out = []
    for ch in text:
        if ch.upper() in _MAP:
            rep = _MAP.get(ch.upper(), ch.upper())
            out.append(rep if ch.isupper() else rep.lower())
        else:
            out.append(ch)
    return "".join(out)
