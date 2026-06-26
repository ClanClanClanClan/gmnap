from __future__ import annotations

import ipaddress
import os
import time
from typing import Any, Awaitable, Callable, Dict, Optional

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..ops.hashcash import verify_hashcash
from ..ops.metrics_security import (
    AUTHN_FAILED,
    AUTHZ_FAILED,
    HASHCASH_VERIFIED,
    HASHCASH_VERIFY_LATENCY,
    JWT_VERIFIED,
    RATE_LIMIT_DROPPED,
    SECURITY_EVENT,
)
from ..ops.rate_limit import RateLimiter


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Enforces:
      - Bearer JWT for paid tier (Authorization: Bearer <token>)
      - OR Hashcash for free tier (X-Hashcash: <stamp>)
      - Rate limiting (different RPM for free vs paid)
      - Basic RBAC via JWT 'role' claim ∈ {admin, operator, viewer}
    Config (env or config file reflected as env):
      GMNAP_HASHCASH_BITS (default 18)
      GMNAP_RPM_FREE (default 60)
      GMNAP_RPM_PAID (default 10000)
      GMNAP_JWT_SECRET (HS256) or GMNAP_JWT_PUBLIC_PEM (RS256)
      GMNAP_REQUIRED_ROLE (optional)
    """

    def __init__(self, app, required_role: Optional[str] = None):
        super().__init__(app)
        self.bits = int(os.getenv("GMNAP_HASHCASH_BITS", "18"))
        self.rpm_free = int(os.getenv("GMNAP_RPM_FREE", "60"))
        self.rpm_paid = int(os.getenv("GMNAP_RPM_PAID", "10000"))
        self.jwt_secret = os.getenv("GMNAP_JWT_SECRET")
        self.jwt_public_pem = os.getenv("GMNAP_JWT_PUBLIC_PEM")
        self.required_role = required_role or os.getenv("GMNAP_REQUIRED_ROLE")
        self.rl = RateLimiter(rpm_free=self.rpm_free, rpm_paid=self.rpm_paid)

    def _client_key(self, request: Request) -> str:
        xfwd = request.headers.get("x-forwarded-for") or request.client.host
        # normalise to truncated IPv4/IPv6 token
        try:
            ip = ipaddress.ip_address(xfwd.split(",")[0].strip())
            return ip.compressed
        except Exception:
            return xfwd or "unknown"

    def _verify_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            if self.jwt_public_pem:
                payload = jwt.decode(token, self.jwt_public_pem, algorithms=["RS256"])
            elif self.jwt_secret:
                payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            else:
                return None
            JWT_VERIFIED.inc()
            return payload
        except Exception:
            return None

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path or "/"
        key = self._client_key(request)
        paid = False
        role = "viewer"
        user = "anon"

        authz_header = request.headers.get("authorization")
        hashcash_header = request.headers.get("x-hashcash")

        # Prefer JWT if present
        if authz_header and authz_header.lower().startswith("bearer "):
            token = authz_header.split(" ", 1)[1].strip()
            claims = self._verify_jwt(token)
            if not claims:
                AUTHN_FAILED.inc()
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            paid = True
            role = claims.get("role") or claims.get("roles") or "viewer"
            user = claims.get("sub") or "jwt"
        else:
            # Require Hashcash for free tier
            if not hashcash_header:
                AUTHN_FAILED.inc()
                return JSONResponse({"error": "missing_auth"}, status_code=401)
            with HASHCASH_VERIFY_LATENCY.time():
                ok, reason = verify_hashcash(
                    hashcash_header, min_bits=self.bits, resource=path
                )
            if not ok:
                AUTHN_FAILED.inc()
                SECURITY_EVENT.labels(event=f"hashcash_{reason}").inc()
                return JSONResponse(
                    {"error": "invalid_hashcash", "reason": reason}, status_code=401
                )
            HASHCASH_VERIFIED.inc()
            user = f"hashcash:{key}"

        # Rate limit
        if not await self.rl.allow(key, paid=paid, cost=1):
            RATE_LIMIT_DROPPED.inc()
            return JSONResponse({"error": "rate_limited"}, status_code=429)

        # RBAC if configured
        if self.required_role:
            roles = {str(role)} if isinstance(role, str) else set(role or [])
            if self.required_role not in roles:
                AUTHZ_FAILED.inc()
                return JSONResponse({"error": "forbidden"}, status_code=403)

        # Proceed
        resp = await call_next(request)
        # Attach security headers
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Permissions-Policy", "geolocation=()")
        return resp
