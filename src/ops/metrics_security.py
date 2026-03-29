from __future__ import annotations
from prometheus_client import Counter, Histogram

AUTHN_FAILED = Counter("gmnap_authn_failed_total", "AuthN failures (401)")
AUTHZ_FAILED = Counter("gmnap_authz_failed_total", "AuthZ failures (403)")
RATE_LIMIT_DROPPED = Counter(
    "gmnap_rate_limit_dropped_total", "Requests dropped due to rate limiting"
)
HASHCASH_VERIFIED = Counter(
    "gmnap_hashcash_verified_total", "Valid Hashcash stamps verified"
)
JWT_VERIFIED = Counter("gmnap_jwt_verified_total", "Valid JWTs verified")
SECURITY_EVENT = Counter(
    "gmnap_security_events_total", "Security events by type", ["event"]
)
HASHCASH_VERIFY_LATENCY = Histogram(
    "gmnap_hashcash_verify_seconds", "Latency to verify Hashcash stamps (s)"
)
