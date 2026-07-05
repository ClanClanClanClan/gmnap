"""Region-detection internals, split out of the former 6,851-line
``manager_optimized.py`` god-file (R45, behaviour-preserving).

- ``scorer``          — priority-rules lexicon + 3-tier suffix scorer (the
                        perf-critical ``_wb``/``_score_priority_rules`` path)
- ``fasttext_worker`` — persistent fastText CLI worker + model singleton
- ``result``          — the ``RegionDetectionResult`` dataclass

``src.regions.manager_optimized`` remains the public facade: it re-exports
everything from here, so existing imports keep working unchanged.
"""
