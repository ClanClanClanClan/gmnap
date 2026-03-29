from __future__ import annotations
from prometheus_client import Counter, Histogram

harvest_total = Counter("gmnap_harvest_records_total", "Harvested records", "source")
edges_created_total = Counter("gmnap_edges_created_total", "Edges created", "verified")
edges_confidence = Histogram(
    "gmnap_edges_confidence_histogram",
    "Edge confidences",
    [0.5, 0.7, 0.8, 0.9, 0.95, 0.99],
)
