"""Graph coherence module.

Re-exports the live coherence engine from ``coherence``. This used to do
``from .scorer import GraphCoherenceScorer``, but no ``scorer`` submodule
was ever created in this package, so importing the package raised
ModuleNotFoundError. That failure propagated up through
``stage6_bayesian.bayes_coherence`` (which imports ``betweenness_score``
from here), so the pipeline's stage-6 import caught it and logged
"BayesCoherence not available, skipping stage 6" — silently disabling the
entire graph-consistency / Bayesian-coherence stage. (The legacy
``GraphCoherenceScorer`` class lives in the sibling, now-shadowed
``src/core/graph_coherence.py`` file and has no live importers.)
"""

from .coherence import GraphCoherence, betweenness_score

__all__ = ["GraphCoherence", "betweenness_score"]
