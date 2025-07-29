import re

_SPLIT = re.compile(r"[ _]+")

def tokenise(name:str):
    # pre-cleanup commas etc.
    clean = re.sub(r"[,\.\u200b]", " ", name).strip()
    tokens = _SPLIT.split(clean)
    # keep hyphen inside token (Jung-Kook) but will be handled by beam search
    return [t for t in tokens if t]