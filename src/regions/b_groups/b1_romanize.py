from __future__ import annotations

_TABLE = {
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "G",
    "Д": "D",
    "Е": "E",
    "Ё": "Yo",
    "Ж": "Zh",
    "З": "Z",
    "И": "I",
    "Й": "Y",
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
    "Ъ": "U",
    "Ы": "Y",
    "Ь": "",
    "Э": "E",
    "Ю": "Yu",
    "Я": "Ya",
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "u",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    "І": "I",
    "і": "i",
    "Ї": "Yi",
    "ї": "yi",
    "Є": "Ye",
    "є": "ye",
    "Ґ": "G",
    "ґ": "g",
    "Ў": "U",
    "ў": "u",
}


def romanize_cyrillic(text: str) -> str:
    return "".join(_TABLE.get(ch, ch) for ch in text)


def canonical_family_given(canon_latin: str) -> str:
    if any("\u0400" <= ch <= "\u04ff" for ch in canon_latin):
        lat = romanize_cyrillic(canon_latin)
        parts = lat.split()
        if len(parts) == 2:
            return f"{parts[1]}, {parts[0]}"
        return lat
    return canon_latin
