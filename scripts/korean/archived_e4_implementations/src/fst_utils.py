import pynini as pn


def first_output(fst: pn.Fst) -> str | None:
    try:
        shortest = pn.shortestpath(fst, nshortest=1, unique=True)
        if shortest.num_states() == 0:
            return None
        return shortest.string()
    except:
        return None
