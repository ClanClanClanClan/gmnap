# Correct PyNini 2.1.6+ usage patterns
import pynini as pn

# Make acceptor (blueprint shows pn.acceptor but actual API is pn.accep)
correct_acceptor = lambda string: pn.accep(string, token_type="utf8")

# Compose
def compose_fsts(fst1, fst2):
    return fst1 @ fst2  # Same as before

# Optimize
def optimize_fst(fst):
    return fst.optimize()  # Same

# Count arcs
def count_total_arcs(fst):
    return sum(fst.num_arcs(s) for s in fst.states())

# Get shortest paths
def get_shortest_paths(fst, nshortest=1000, unique=True):
    return pn.shortestpath(fst, nshortest=nshortest, unique=unique)