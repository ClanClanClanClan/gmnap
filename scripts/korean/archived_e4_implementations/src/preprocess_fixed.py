import regex as re


def tokenise(name: str) -> list[str]:
    """Tokenize name into words, handling spaces and hyphens correctly."""
    # Replace commas and parentheses with spaces
    name = re.sub(r"[,()]", " ", name)
    # Split on hyphens or whitespace (fixed regex)
    # Original had [-\\s]+ which is incorrect - should be [-\s]+
    return [p for p in re.split(r"[-\s]+", name) if p]
