"""Graph coherence scorer"""


class GraphCoherenceScorer:
    """Scorer for graph coherence"""

    def __init__(self):
        self.threshold = 0.5

    def score(self, entry):
        """Score an entry"""
        return 0.5

    def validate(self, entry):
        """Validate an entry"""
        return self.score(entry) >= self.threshold


class GraphCoherenceResult:
    """Result of graph coherence scoring"""

    def __init__(self, score=0.5, valid=True, details=None):
        self.score = score
        self.valid = valid
        self.details = details or {}

    def __bool__(self):
        return self.valid
