import regex as re


def tokenise(name: str) -> list[str]:
    name = re.sub(r"[,()]", " ", name)
    # R51: r"[-\\s]+" (double-escaped \s in a raw string) made the class
    # match '-', a literal backslash, and the LETTER 's' — not whitespace.
    # Every "Family, Given" name and any token with a lowercase 's' was
    # mangled, zeroing the FST gate (0/733). Mangled at repo-import; the
    # recorded 641/182 baselines predate it.
    return [p for p in re.split(r"[-\s]+", name) if p]
