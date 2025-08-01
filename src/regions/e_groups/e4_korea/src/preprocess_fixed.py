import re

def tokenise(name: str) -> list[str]:
    """Tokenize name by splitting on common separators."""
    if not name:
        return []
    
    # Remove commas and parentheses, replace with spaces
    name = re.sub(r"[,()]", " ", name)
    
    # Split on hyphens, underscores and whitespace, filter empty strings
    tokens = []
    for part in re.split(r"[-_\s]+", name):
        part = part.strip()
        if part:
            tokens.append(part)
    
    return tokens