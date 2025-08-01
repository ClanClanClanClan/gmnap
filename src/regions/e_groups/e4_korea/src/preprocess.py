import regex as re
def tokenise(name:str)->list[str]:
    name=re.sub(r"[,()]", " ", name)
    return [p for p in re.split(r"[-\\s]+", name) if p]